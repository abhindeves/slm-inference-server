#!/bin/bash
set -e

echo "Waiting for instance to be ready..."
sleep 60

echo "Installing dependencies..."
apt update -y
apt install -y python3-pip python3-venv git

echo "Creating virtual environment..."
python3 -m venv /opt/venv

echo "Activating venv and installing huggingface_hub..."
source /opt/venv/bin/activate
pip install --upgrade pip
pip install huggingface_hub

echo "Downloading model from Hugging Face..."
/opt/venv/bin/python - <<EOF
from huggingface_hub import snapshot_download

snapshot_download(
    repo_id="$MODEL_REPO",
    local_dir="/root/model",
    token="$HF_TOKEN",
    allow_patterns=["*q4_k_m.gguf"],
    local_dir_use_symlinks=False,
    resume_download=True,
    max_workers=1
)
EOF

echo "Pulling llama.cpp image..."
docker pull ghcr.io/ggml-org/llama.cpp:server

echo "Starting model server..."
docker run -d \
  --name llama-server \
  --restart always \
  -p 8000:8000 \
  -v /root/model:/models \
  ghcr.io/ggml-org/llama.cpp:server \
  -m /models/*.gguf \
  --host 0.0.0.0 --port 8000

echo "Deployment complete!"