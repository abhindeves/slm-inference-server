#!/bin/bash
set -e

echo "Waiting for instance to be ready..."
sleep 60

echo "Installing dependencies..."
apt update -y
apt install -y python3-pip git

echo "Installing huggingface_hub..."
pip3 install huggingface_hub

echo "Downloading model from Hugging Face..."
python3 - <<EOF
from huggingface_hub import snapshot_download

snapshot_download(
    repo_id="$MODEL_REPO",
    local_dir="/root/model",
    token="$HF_TOKEN"
)
EOF

echo "Pulling llama.cpp image..."
docker pull ghcr.io/ggerganov/llama.cpp:server

echo "Starting model server..."
docker run -d \
  --name llama-server \
  --restart always \
  -p 8000:8000 \
  -v /root/model:/models \
  ghcr.io/ggerganov/llama.cpp:server \
  -m /models/*.gguf \
  --host 0.0.0.0 --port 8000

echo "Deployment complete!"