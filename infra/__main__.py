import os
import pulumi
import pulumi_digitalocean as digitalocean
from pulumi_command import remote

# -----------------------------------------------------------------------------
# Parameters
# -----------------------------------------------------------------------------
DROPLET_NAME = "pulumi-slm-droplet"
REGION = "blr1"
SIZE = "s-1vcpu-2gb"
IMAGE = "ubuntu-24-04-x64"
TAGS = ["pulumi", "env:dev", "service:web"]

ENABLE_IPV6 = True
ENABLE_BACKUPS = False
ENABLE_MONITORING = True
RESIZE_DISK = False

# -----------------------------------------------------------------------------
# Pulumi config
# -----------------------------------------------------------------------------
config = pulumi.Config()

ssh_fingerprint = config.require("ssh_fingerprint")
hf_token = config.require_secret("hf_token")
model_repo = config.require("model_repo")

# ✅ Read private key from environment (NOT Pulumi config)
private_key = os.environ["PRIVATE_KEY"]

# -----------------------------------------------------------------------------
# Cloud-init
# -----------------------------------------------------------------------------
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
    ssh_keys=[ssh_fingerprint],  # ✅ IMPORTANT
)

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------
pulumi.export("public_ip", server.ipv4_address)

# -----------------------------------------------------------------------------
# Load deployment script
# -----------------------------------------------------------------------------
with open("deploy.sh") as f:
    script_content = f.read()

deploy_script = pulumi.Output.all(hf_token, model_repo).apply(
    lambda args: script_content
    .replace("$HF_TOKEN", args[0])
    .replace("$MODEL_REPO", args[1])
)

# -----------------------------------------------------------------------------
# Remote execution
# -----------------------------------------------------------------------------
connection = remote.ConnectionArgs(
    host=server.ipv4_address,
    user="root",  # or "ubuntu"
    private_key=private_key,
)

deploy = remote.Command(
    "deploy-llm",
    connection=connection,
    create=deploy_script,
    opts=pulumi.ResourceOptions(depends_on=[server]),
)