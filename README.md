# Digital Ocean / Pulumi Deployment

This repo provisions a DigitalOcean droplet using Pulumi and configures it to run the `llama.cpp` server with a model downloaded directly from Hugging Face.

The GitHub Actions workflow runs `pulumi preview` for pull requests and `pulumi up` on `main`.

---

## ✅ What’s included

- `infra/__main__.py` — Pulumi program (Python) that creates a Droplet and bootstraps it via cloud-init.
- `.github/workflows/pulumi-ci.yml` — GitHub Actions workflow that installs dependencies, logs into Pulumi, and deploys.
- `infra/Pulumi.yaml` / `infra/Pulumi.<stack>.yaml` — Pulumi project + stack config.

---

## 🔧 Prerequisites (GitHub Actions)

You will need to configure the following secrets in GitHub (Repository Settings → Secrets → Actions):

| Secret | Description |
|--------|-------------|
| `PULUMI_ACCESS_TOKEN` | Pulumi Service access token (https://app.pulumi.com/account/tokens) |
| `DIGITALOCEAN_TOKEN` | DigitalOcean API token (read/write) |
| `HUGGINGFACE_TOKEN` | Hugging Face token used to download private / gated models |

---

## 🚀 Working locally

1. Create and activate a virtualenv (recommended):

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r infra/requirements.txt
```

3. Set required env vars:

```bash
export DIGITALOCEAN_TOKEN="..."
export PULUMI_ACCESS_TOKEN="..."
export HUGGINGFACE_TOKEN="..."
```

4. Select your stack and deploy:

```bash
cd infra
pulumi stack select dev || pulumi stack init dev
pulumi config set digitalocean:token --secret "$DIGITALOCEAN_TOKEN"
pulumi config set huggingface:token --secret "$HUGGINGFACE_TOKEN"
pulumi up
```

---

## 🔧 Customizing the model and droplet

You can override the model repository and the file name that is passed to `llama.cpp` via Pulumi config:

```bash
pulumi config set modelRepo "<user>/<repo>"
pulumi config set modelFile "<filename>.gguf"
```

If you need to change the droplet size, region, or tags, edit `infra/__main__.py`.

