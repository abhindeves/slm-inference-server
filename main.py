from huggingface_hub import snapshot_download

snapshot_download(
    repo_id="unsloth/Qwen3.5-0.8B-GGUF",
    allow_patterns=["*Q4_K_M.gguf"],
    local_dir="./models/qwen"
)