#!/bin/bash

set -e
exec > /var/log/llm-deploy.log 2>&1

echo "Waiting for cloud-init..."
cloud-init status --wait

echo "=== Starting Deployment ==="

mkdir -p /models/model

echo "Installing dependencies..."
pip3 install huggingface_hub

# -------------------------
# MODEL DOWNLOAD (RETRY)
# -------------------------
if [ ! -f "/models/model/model.gguf" ]; then
  echo "Downloading model..."

  for i in 1 2 3; do
    huggingface-cli login --token "$HF_TOKEN" && \
    huggingface-cli download "$MODEL_REPO" \
      --include "*q4_k_m.gguf" \
      --local-dir /models/model && break

    echo "Retry $i..."
    sleep 5
  done
fi

MODEL_PATH=$(find /models/model -name "*.gguf" | head -n 1)

if [ -z "$MODEL_PATH" ]; then
  echo "Model not found!"
  exit 1
fi

# -------------------------
# DOCKER IMAGE
# -------------------------
echo "Pulling Docker image..."
docker pull ghcr.io/ggml-org/llama.cpp:server

# -------------------------
# BLUE-GREEN DEPLOY
# -------------------------
echo "Starting new container..."
docker rm -f llama-server-new || true

docker run -d --name llama-server-new \
  -p 8081:8080 \
  -v /models:/models \
  ghcr.io/ggml-org/llama.cpp:server \
  -m $MODEL_PATH \
  --host 0.0.0.0 --port 8080

# -------------------------
# HEALTH CHECK
# -------------------------
echo "Checking health..."

for i in 1 2 3 4 5; do
  if curl -f http://localhost:8081/health; then
    echo "New container healthy"

    docker rm -f llama-server || true
    docker rename llama-server-new llama-server

    echo "Deployment successful"
    exit 0
  fi

  echo "Retry $i..."
  sleep 5
done

echo "Deployment failed, rolling back..."
docker rm -f llama-server-new

exit 1