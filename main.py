from huggingface_hub import snapshot_download

snapshot_download(
    repo_id="Qwen/Qwen2.5-0.5B-Instruct-GGUF",
    allow_patterns=["*q4_k_m.gguf"],
    local_dir="./models/qwen"
)