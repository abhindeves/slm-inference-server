import pulumi
import pulumi_digitalocean as digitalocean

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
SIZE = "s-2vcpu-4gb"         # e.g., s-1vcpu-1gb, s-2vcpu-2gb
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
HUGGINGFACE_TOKEN = config.require_secret("huggingfacetoken")
MODEL_REPO = "Qwen/Qwen2.5-0.5B-Instruct-GGUF"

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

def make_user_data(hf_token: str, model_repo: str) -> str:
    return f"""#cloud-config
runcmd:
  - exec > /tmp/startup.log 2>&1
  - set -x

  - apt update -y
  - apt install -y docker.io python3-pip
  - systemctl enable --now docker

  - python3 -m pip install --upgrade pip
  - python3 -m pip install huggingface-hub

  # Create model directory
  - mkdir -p /models

  # Write Python script safely
  - |
    cat <<EOF > /tmp/download.py
    from huggingface_hub import snapshot_download

    snapshot_download(
        repo_id="{model_repo}",
        cache_dir="/models/model",
        token="{hf_token}",
        allow_patterns=["*q4_k_m.gguf"]
    )

    print("Download complete")
    EOF

  # Run download
  - python3 /tmp/download.py

  # Find model file
  - MODEL_PATH=$(find /models/model -name "*.gguf" | head -n 1)
  - echo "Model path: $MODEL_PATH"

  # Run container
  - docker pull ghcr.io/ggml-org/llama.cpp:server
  - docker rm -f llama-server || true
  - docker run --name llama-server --restart=always -d \
      -v /models:/models \
      -p 8080:8080 \
      ghcr.io/ggml-org/llama.cpp:server \
      -m $MODEL_PATH \
      --host 0.0.0.0 --port 8080
"""

user_data = pulumi.Output.all(HUGGINGFACE_TOKEN, MODEL_REPO).apply(
    lambda args: make_user_data(*args)
)

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
