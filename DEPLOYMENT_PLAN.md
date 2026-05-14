# Q&Ace Deployment Plan
> Goal: Public live link using your fine-tuned Llama 3.1 8B model — $0/month forever.

---

## Overview

| Phase | What | Where | Time |
|---|---|---|---|
| 1 | Fuse & upload fine-tuned model | Your Mac → HuggingFace | 1–2 hrs |
| 2 | Oracle Cloud VM setup | Oracle Cloud | 1–2 hrs |
| 3 | Deploy backend + models on VM | Oracle VM | 2–3 hrs |
| 4 | Deploy frontend | Vercel | 30 min |
| 5 | Connect everything + custom domain | DNS/Nginx | 1 hr |
| 6 | Test & go live | — | 30 min |

**Total estimated time: 1 day**

---

## Phase 1 — Fuse & Upload Your Fine-Tuned Model

> Do this on your Mac before anything else.

### 1.1 Fuse LoRA adapters into the base model

```bash
source ~/.venvs/qace-mlx/bin/activate
cd /Users/aziqrauf/LLM
```

**Fuse evaluator adapter:**
```bash
python -m mlx_lm.fuse \
  --model mlx-community/Meta-Llama-3.1-8B-Instruct-4bit \
  --adapter-path /Users/aziqrauf/LLM/adapters/evaluator \
  --save-path /Users/aziqrauf/LLM/qace-evaluator-merged \
  --de-quantize
```

**Fuse coach adapter:**
```bash
python -m mlx_lm.fuse \
  --model mlx-community/Meta-Llama-3.1-8B-Instruct-4bit \
  --adapter-path /Users/aziqrauf/LLM/adapters/coach \
  --save-path /Users/aziqrauf/LLM/qace-coach-merged \
  --de-quantize
```

> `--de-quantize` is required — converts from Apple 4-bit format to standard float16 that works on Linux/NVIDIA.  
> Each fused model will be ~15GB. Make sure you have ~35GB free disk space.

### 1.2 Create a Hugging Face account

1. Go to [huggingface.co](https://huggingface.co) → Sign up (free)
2. Go to Settings → Access Tokens → New Token → Role: **Write**
3. Copy the token

### 1.3 Upload fused models to HuggingFace (private repos)

```bash
pip install huggingface_hub
huggingface-cli login
# Paste your HF token when prompted
```

```bash
# Create private repos and upload
huggingface-cli upload YOUR_HF_USERNAME/qace-evaluator \
  /Users/aziqrauf/LLM/qace-evaluator-merged \
  --private

huggingface-cli upload YOUR_HF_USERNAME/qace-coach \
  /Users/aziqrauf/LLM/qace-coach-merged \
  --private
```

> Upload will take 30–60 min depending on your internet speed (uploading ~15GB each).  
> While it uploads, continue to Phase 2.

### 1.4 Checkpoint ✅
- [ ] `qace-evaluator-merged/` folder exists locally
- [ ] `qace-coach-merged/` folder exists locally  
- [ ] Both repos visible on huggingface.co/YOUR_HF_USERNAME (as private)

---

## Phase 2 — Oracle Cloud Always Free VM Setup

> Oracle gives 4 ARM CPUs + 24GB RAM free forever. Perfect for running your full stack.

### 2.1 Create Oracle Cloud account

1. Go to [cloud.oracle.com](https://cloud.oracle.com) → Sign Up
2. Choose your region (pick one close to you — e.g. UK South, US East)
3. Enter credit card (required for verification — you will NOT be charged on Always Free)
4. Complete verification

> ⚠️ Use a real credit card. Oracle won't charge you for Always Free resources but needs it to verify identity.

### 2.2 Create the VM instance

1. In Oracle Console → **Compute → Instances → Create Instance**
2. Name: `qace-server`
3. Image: **Ubuntu 22.04** (Canonical)
4. Shape: Click **Change Shape** → **Ampere** → `VM.Standard.A1.Flex`
   - OCPUs: **4**
   - Memory: **24 GB**
5. Networking: Create new VCN, leave defaults
6. SSH Keys: **Upload your public key** or let Oracle generate one (download private key)
7. Boot volume: Set to **100 GB** (free tier allows up to 200 GB total)
8. Click **Create**

> VM will be ready in ~3 minutes.

### 2.3 Open required ports in Oracle firewall

In Oracle Console → **Networking → Virtual Cloud Networks → your VCN → Security Lists → Default Security List**

Add these **Ingress Rules**:
| Port | Protocol | Description |
|---|---|---|
| 22 | TCP | SSH |
| 80 | TCP | HTTP |
| 443 | TCP | HTTPS |
| 8000 | TCP | FastAPI backend |
| 11434 | TCP | Ollama (model server) |

Also run on the VM itself after SSH-ing in:
```bash
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8000 -j ACCEPT
sudo netfilter-persistent save
```

### 2.4 SSH into your VM

```bash
ssh -i /path/to/your/private_key ubuntu@YOUR_VM_PUBLIC_IP
```

### 2.5 Checkpoint ✅
- [ ] VM is running and showing green in Oracle Console
- [ ] You can SSH into it
- [ ] All ports open

---

## Phase 3 — Deploy Backend + Models on the VM

> Everything below is run on the Oracle VM via SSH.

### 3.1 Update system and install dependencies

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.11 python3.11-venv python3-pip git nginx certbot python3-certbot-nginx ffmpeg curl
```

### 3.2 Install Ollama (model server)

```bash
curl -fsSL https://ollama.com/install.sh | sh
sudo systemctl enable ollama
sudo systemctl start ollama
```

### 3.3 Pull your fine-tuned model into Ollama

First, login to Hugging Face on the VM:
```bash
pip3 install huggingface_hub
huggingface-cli login
# Enter your HF token
```

Pull the evaluator model:
```bash
ollama pull hf.co/YOUR_HF_USERNAME/qace-evaluator
ollama pull hf.co/YOUR_HF_USERNAME/qace-coach
```

> This downloads ~15GB per model — may take 20–40 min.  
> Test it works: `ollama run hf.co/YOUR_HF_USERNAME/qace-evaluator "Hello"` — you should get a response.

### 3.4 Clone your repo

```bash
cd ~
git clone git@github.com:abdullahjamil42/FYP-QnAce-Main-Repo.git
cd FYP-QnAce-Main-Repo
```

> If SSH key not set up on VM, use HTTPS:  
> `git clone https://github.com/abdullahjamil42/FYP-QnAce-Main-Repo.git`

### 3.5 Create Python virtual environment and install requirements

```bash
cd ~/FYP-QnAce-Main-Repo/server
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

> ⚠️ Remove the Windows CUDA torch line from `requirements.txt` before installing:  
> Delete the line: `torch==2.6.0+cu124; sys_platform == "win32" and python_version == "3.11"`  
> Then run: `pip install torch --index-url https://download.pytorch.org/whl/cpu`

### 3.6 Download perception models on the VM

```bash
cd ~/FYP-QnAce-Main-Repo
mkdir -p models/silero-vad models/text-quality models/face-emotion

# Silero VAD
python3 -c "
import urllib.request
url = 'https://github.com/snakers4/silero-vad/raw/master/src/silero_vad/data/silero_vad.onnx'
urllib.request.urlretrieve(url, 'models/silero-vad/silero_vad.onnx')
print('VAD downloaded')
"

# Whisper small.en (downloaded automatically on first run by faster-whisper)
# BERT and face models — copy from your Mac via scp:
# scp -i /path/to/key -r models/text-quality ubuntu@YOUR_VM_IP:~/FYP-QnAce-Main-Repo/models/
# scp -i /path/to/key -r models/face-emotion ubuntu@YOUR_VM_IP:~/FYP-QnAce-Main-Repo/models/
```

### 3.7 Create production `.env` on the VM

```bash
cat > ~/FYP-QnAce-Main-Repo/.env << 'EOF'
QACE_ENV=production
QACE_HOST=0.0.0.0
QACE_PORT=8000
QACE_LOG_LEVEL=info

QACE_CORS_ORIGINS=https://YOUR_VERCEL_APP.vercel.app,https://yourdomain.com

# LLM — using your fine-tuned model via Ollama
QACE_LLM_PROVIDER=local
QACE_LOCAL_LLM_BASE_URL=http://localhost:11434/v1
QACE_LOCAL_LLM_BASE_MODEL=hf.co/YOUR_HF_USERNAME/qace-evaluator
QACE_LOCAL_LLM_PATH=/root
QACE_LOCAL_LLM_ADAPTER_PATH=
QACE_LOCAL_LLM_SERVER_SCRIPT=

# Perception Models
QACE_MODEL_DIR=/home/ubuntu/FYP-QnAce-Main-Repo/models
QACE_WHISPER_MODEL=small.en
QACE_SILERO_ONNX=/home/ubuntu/FYP-QnAce-Main-Repo/models/silero-vad/silero_vad.onnx
QACE_VOCAL_MODEL=ehcalabres/wav2vec2-lg-xlsr-en-speech-emotion-recognition
QACE_VOCAL_DEVICE=cpu
QACE_FACE_ONNX=/home/ubuntu/FYP-QnAce-Main-Repo/models/face-emotion/efficientnet_b2.onnx
QACE_BERT_ONNX=/home/ubuntu/FYP-QnAce-Main-Repo/models/text-quality/bert_quality.onnx
QACE_BERT_TOKENIZER=/home/ubuntu/FYP-QnAce-Main-Repo/models/text-quality
QACE_CHROMA_DIR=/home/ubuntu/FYP-QnAce-Main-Repo/data/chroma

QACE_TTS_BACKEND=edge
QACE_VAD_SILENCE_MS=300
QACE_VAD_MIN_SPEECH_S=1.0

# Supabase
SUPABASE_SERVICE_ROLE_KEY=YOUR_SUPABASE_KEY
SUPABASE_JWT_SECRET=YOUR_JWT_SECRET
EOF
```

### 3.8 Create systemd service to keep FastAPI running

```bash
sudo nano /etc/systemd/system/qace.service
```

Paste:
```ini
[Unit]
Description=Q&Ace FastAPI Backend
After=network.target ollama.service

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/FYP-QnAce-Main-Repo/server
ExecStart=/home/ubuntu/FYP-QnAce-Main-Repo/server/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=5
Environment="PYTHONPATH=/home/ubuntu/FYP-QnAce-Main-Repo/server"
EnvironmentFile=/home/ubuntu/FYP-QnAce-Main-Repo/.env

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable qace
sudo systemctl start qace
sudo systemctl status qace   # should show green "active (running)"
```

### 3.9 Configure Nginx as reverse proxy

```bash
sudo nano /etc/nginx/sites-available/qace
```

Paste:
```nginx
server {
    listen 80;
    server_name api.yourdomain.com;  # or YOUR_VM_PUBLIC_IP

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 300;
        proxy_send_timeout 300;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/qace /etc/nginx/sites-enabled/
sudo nginx -t   # should say "syntax is ok"
sudo systemctl restart nginx
```

### 3.10 Add free TURN server for WebRTC

In your signaling/WebRTC config, add Metered.ca free TURN credentials:

1. Sign up free at [metered.ca](https://www.metered.ca)
2. Get your TURN credentials
3. Add to `.env`:
```env
QACE_TURN_URLS=turn:openrelay.metered.ca:80
QACE_TURN_USERNAME=your_metered_username
QACE_TURN_CREDENTIAL=your_metered_password
```

### 3.11 Checkpoint ✅
- [ ] `sudo systemctl status qace` shows active/running
- [ ] `curl http://localhost:8000/health` returns 200
- [ ] `curl http://YOUR_VM_IP:8000/health` returns 200 from outside
- [ ] Ollama running: `ollama list` shows your models

---

## Phase 4 — Deploy Frontend on Vercel

> Do this on your Mac.

### 4.1 Sign up on Vercel

1. Go to [vercel.com](https://vercel.com) → Sign up with GitHub
2. Click **Add New Project** → Import your GitHub repo
3. Set **Root Directory** to `client`
4. Framework: **Next.js** (auto-detected)

### 4.2 Add environment variables in Vercel

In Vercel project settings → Environment Variables, add:
```
NEXT_PUBLIC_API_URL = https://api.yourdomain.com
# or if no custom domain yet:
NEXT_PUBLIC_API_URL = http://YOUR_ORACLE_VM_IP:8000
```

Also add your Supabase public key if used client-side:
```
NEXT_PUBLIC_SUPABASE_URL = https://YOUR_PROJECT.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY = your_anon_key
```

### 4.3 Deploy

Click **Deploy** — Vercel will build and deploy in ~2 minutes.  
You get a URL like: `https://qnace.vercel.app` ✅

### 4.4 Checkpoint ✅
- [ ] Vercel build succeeded (green)
- [ ] `https://your-app.vercel.app` loads the frontend
- [ ] Frontend can reach the backend API

---

## Phase 5 — Custom Domain (Optional but Recommended for CV)

### 5.1 Buy a domain

Go to [Namecheap.com](https://namecheap.com) — `.me` or `.tech` domains are **~$1–5/year** for students.  
Suggested: `qnace.me` or `qnace.tech`

### 5.2 Point domain to Vercel (frontend)

In Namecheap DNS settings:
```
Type: CNAME
Host: @
Value: cname.vercel-dns.com
```

In Vercel → Project → Settings → Domains → Add `yourdomain.com`

### 5.3 Point subdomain to Oracle VM (backend)

```
Type: A
Host: api
Value: YOUR_ORACLE_VM_PUBLIC_IP
```

### 5.4 Add HTTPS to backend with Certbot

On the Oracle VM:
```bash
sudo certbot --nginx -d api.yourdomain.com
# Follow prompts, enter email
# Select option to redirect HTTP to HTTPS
```

Certbot auto-renews every 90 days.

### 5.5 Update CORS in backend `.env`

```env
QACE_CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

Restart: `sudo systemctl restart qace`

### 5.6 Checkpoint ✅
- [ ] `https://yourdomain.com` loads frontend
- [ ] `https://api.yourdomain.com/health` returns 200
- [ ] HTTPS padlock shows on both

---

## Phase 6 — Final Test & Go Live

### 6.1 End-to-end test checklist

- [ ] Frontend loads at your domain
- [ ] Can create an account / log in (Supabase auth)
- [ ] Notes page loads, Ace chatbot responds
- [ ] MCQ practice works, questions load
- [ ] Can start an interview session (WebRTC connects)
- [ ] Audio/video streams correctly during interview
- [ ] Post-interview report generates
- [ ] LLM responses come from your fine-tuned model (check logs: `sudo journalctl -u qace -f`)

### 6.2 Verify the fine-tuned model is being used

```bash
# On the Oracle VM
sudo journalctl -u qace -f | grep -i "model\|llm\|ollama"
```

You should see requests going to `http://localhost:11434/v1`.

### 6.3 Monitor resource usage

```bash
htop          # CPU + RAM usage
df -h         # disk space
ollama ps     # check model is loaded in memory
```

### 6.4 Put it on your CV

```
Q&Ace — AI Interview Preparation Platform
Live: https://qnace.me
GitHub: github.com/abdullahjamil42/FYP-QnAce-Main-Repo

Fine-tuned Llama 3.1 8B (LoRA) | FastAPI | Next.js | WebRTC | 
Whisper STT | ChromaDB RAG | Oracle Cloud | Vercel
```

---

## Cost Summary

| Service | Plan | Cost |
|---|---|---|
| Oracle Cloud (VM — 4 CPU, 24GB RAM) | Always Free | **$0/month** |
| Vercel (frontend) | Hobby | **$0/month** |
| Groq API (backup LLM) | Free tier | **$0/month** |
| Supabase (database) | Free tier | **$0/month** |
| HuggingFace (model storage) | Free private repo | **$0/month** |
| Metered.ca (TURN server) | Free tier | **$0/month** |
| Domain name | Namecheap | **~$3/year** |
| **Total** | | **~$3/year** |

---

## Troubleshooting Quick Reference

| Problem | Fix |
|---|---|
| `qace.service` fails to start | `sudo journalctl -u qace -n 50` to see error |
| Model not responding | `ollama list` — check model downloaded; `ollama run MODEL "test"` |
| Frontend can't reach API | Check CORS origins in `.env`, check nginx config |
| WebRTC won't connect | Add TURN server credentials, check firewall port 3478 |
| Out of disk space | `df -h` — ONNX models + fused LLM use ~20GB |
| Whisper slow on ARM | Normal — ARM CPU inference is slower, consider `tiny.en` for speed |

---

## Quick Commands Reference (Oracle VM)

```bash
# Check backend status
sudo systemctl status qace

# Restart backend
sudo systemctl restart qace

# View live backend logs
sudo journalctl -u qace -f

# Check model server
ollama list
ollama ps

# Pull latest code and restart
cd ~/FYP-QnAce-Main-Repo && git pull && sudo systemctl restart qace

# Check memory usage
free -h

# Check disk usage
df -h
```
