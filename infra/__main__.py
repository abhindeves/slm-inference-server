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
MODEL_REPO = config.get("modelRepo") or "Qwen/qwen2.5-0.5b-instruct-q4_k_m"
MODEL_FILE = config.get("modelFile") or "qwen2.5-0.5b-instruct-q4_k_m.gguf"

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

def make_user_data(hf_token: str, model_repo: str, model_file: str) -> str:
    return """#cloud-config
runcmd:
  - echo "HELLO FROM CLOUD INIT" > /tmp/test.txt
  - apt update -y
  - apt install -y docker.io
  - systemctl enable --now docker
"""

# def make_user_data(hf_token: str, model_repo: str, model_file: str) -> str:
#     return f"""#cloud-config
# package_update: true
# package_upgrade: true
# packages:
#   - apt-transport-https
#   - ca-certificates
#   - curl
#   - gnupg
#   - lsb-release
#   - python3
#   - python3-pip
# runcmd:
#   - |
#     set -euo pipefail

#     # Install Docker (if not already installed)
#     if ! command -v docker >/dev/null; then
#       curl -fsSL https://get.docker.com | sh
#     fi
#     systemctl enable --now docker

#     # Install the Hugging Face client (used to download the model)
#     python3 -m pip install --upgrade pip
#     python3 -m pip install --no-cache-dir huggingface-hub

#     mkdir -p /models
#     chmod 755 /models

#     # Download the model from Hugging Face (retries on failure)
#     for attempt in $(seq 1 6); do
#       echo "[cloud-init] downloading model (attempt $attempt)"
#       python3 <<EOF
# from huggingface_hub import snapshot_download

# try:
#     snapshot_download(
#         repo_id={model_repo!r},
#         cache_dir="/models/model",
#         use_auth_token={hf_token!r},
#         resume_download=True,
#     )
#     print("[cloud-init] model download succeeded")
#     raise SystemExit(0)
# except Exception as e:
#     print(f"[cloud-init] model download failed")
#     raise
# PY
#       if [ $? -eq 0 ]; then
#         break
#       fi
#       echo "[cloud-init] retrying in 30s..."
#       sleep 30
#     done

#     # Start the llama.cpp server
#     docker pull ghcr.io/ggml-org/llama.cpp:server
#     docker rm -f llama-server || true
#     docker run --name llama-server --restart=always -d \
#       -v /models/model:/models \
#       -p 8080:8080 \
#       ghcr.io/ggml-org/llama.cpp:server \
#       -m /models/model/{model_file} \
#       --port 8080 --host 0.0.0.0 -n 1024
# """

user_data = pulumi.Output.all(HUGGINGFACE_TOKEN, MODEL_REPO, MODEL_FILE).apply(
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
