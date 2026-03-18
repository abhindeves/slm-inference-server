import pulumi
import pulumi_digitalocean as digitalocean
from pulumi_command import remote

# This program provisions a DigitalOcean Droplet and configures it to run the
# llama.cpp server with a model downloaded directly from Hugging Face.
#
# Key behavior:
#   1) Droplet bootstraps itself via cloud-init (no SSH/rsync deployment required).
#   2) Model is downloaded directly in the instance using a Hugging Face token.
#   3) Docker service is configured to restart the container automatically.

# -----------------------------------------------------------------------------
# Parameters (hard-coded for an out-of-the-box run; adjust as desired)
# -----------------------------------------------------------------------------
DROPLET_NAME = "pulumi-slm-droplet"
REGION = "blr1"             # e.g., nyc3, blr1
SIZE = "s-1vcpu-2gb"         # e.g., s-1vcpu-1gb, s-2vcpu-2gb
IMAGE = "ubuntu-24-04-x64"      # e.g., ubuntu-22-04-x64, docker-20-04
TAGS = ["pulumi", "env:dev", "service:web"]
ENABLE_IPV6 = True
ENABLE_BACKUPS = False
ENABLE_MONITORING = True
RESIZE_DISK = False

# -----------------------------------------------------------------------------
# Pulumi config (expects secrets for tokens)
# -----------------------------------------------------------------------------
config = pulumi.Config()

ssh_fingerprint = config.require("ssh_fingerprint")
hf_token = config.require_secret("hf_token")
model_repo = config.require("model_repo")  or "Qwen/Qwen2.5-0.5B-Instruct-GGUF"
private_key = config.require_secret("private_key")

# -----------------------------------------------------------------------------
# Cloud-init script (runs on first boot)
# -----------------------------------------------------------------------------
# The script:
#   * Installs Docker, Python, and huggingface_hub.
#   * Downloads the model from Hugging Face (with retries).
#   * Starts the llama.cpp server in a restart-always container.
#
# Notes:
#   * The Hugging Face token is passed into the droplet via cloud-init.
#   * `pulumi up` may take a while because the model download can be large.

def make_user_data() -> str:
    return """#cloud-config
package_update: true
package_upgrade: true

packages:
  - docker.io

runcmd:
  - systemctl enable docker
  - systemctl start docker
  - usermod -aG docker ubuntu || true
"""

user_data = make_user_data()

# NOTE: This program assumes your DigitalOcean access token is already set in the
# environment for the Pulumi DigitalOcean provider. Typically you run:
#   pulumi config set digitalocean:token <token> --secret
# prior to `pulumi up`.

# -----------------------------------------------------------------------------
# Droplet
# -----------------------------------------------------------------------------
server = digitalocean.Droplet(
    "droplet",
    name=DROPLET_NAME,
    region=REGION,
    size=SIZE,
    image=IMAGE,
    tags=TAGS,
    ipv6=ENABLE_IPV6,
    backups=ENABLE_BACKUPS,
    monitoring=ENABLE_MONITORING,
    resize_disk=RESIZE_DISK,
    user_data=user_data,
)

# -----------------------------------------------------------------------------
# Exports
# -----------------------------------------------------------------------------
pulumi.export("droplet_id", server.id)
pulumi.export("droplet_name", server.name)
pulumi.export("public_ipv4", server.ipv4_address)
pulumi.export("public_ipv6", server.ipv6_address)
pulumi.export("private_ipv4", server.ipv4_address_private)


# -------------------------------
# Read deployment script
# -------------------------------
with open("deploy.sh") as f:
    script_content = f.read()

deploy_script = pulumi.Output.all(hf_token, model_repo).apply(
    lambda args: script_content
    .replace("$HF_TOKEN", args[0])
    .replace("$MODEL_REPO", args[1])
)

# -------------------------------
# Remote execution
# -------------------------------
connection = remote.ConnectionArgs(
    host=digitalocean.Droplet.ipv4_address,
    user="root",
    private_key=private_key,
)

deploy = remote.Command(
    "deploy-llm",
    connection=connection,
    create=deploy_script,
    opts=pulumi.ResourceOptions(depends_on=[server]),
)

