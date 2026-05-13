# Q&Ace — What's Done and What's Left

This file is the live status of the auth/session/deployment work. Treat it as
your checklist. Once you finish all the manual steps below, the app is fully
deployment-ready.

---

## What I changed for you

### Frontend route guard (Next.js middleware)
- New file: `client/src/middleware.ts` — runs on every navigation. Redirects
  unsigned-in users to `/login?next=...`, and force-logs-out anyone whose
  `qace_login_at` cookie is older than 24 hours.
- Public routes that bypass the guard: `/`, `/login`, `/signup`, `/about`,
  `/help`, `/auth/callback`, `/api/*`, `/_next/*`, static assets.
- Protected routes (now require login): `/setup`, `/session/*`, `/interview/*`,
  `/dashboard`, `/history`, `/practice`, `/reports/*`, `/settings`.

### 24-hour absolute logout
- `client/src/lib/supabase.ts` exports `markLoginNow()`, `clearLoginMarker()`,
  `loginAgeMs()`, `SESSION_MAX_AGE_MS`.
- Login + signup pages call `markLoginNow()` after a successful auth.
- `client/src/components/AppShell.tsx` runs a `setInterval` watchdog every 60 s
  that calls `supabase.auth.signOut()` once the cookie crosses 24 h. Catches
  users who keep a tab open without navigating.
- Sign-out (header menu and landing page) clears the cookie.

### Email verification flow
- New file: `client/src/app/auth/callback/route.ts` — handles the link in the
  Supabase verification email, exchanges the code for a session, signs the user
  back out so they re-enter the app via the password form (which sets the
  24 h cookie), and bounces to `/login?verified=1`.
- Login page shows `Email verified. You can now sign in.` banner on success
  and `Your session expired after 24 hours.` banner on expiry.
- Signup page now tells the user "We sent a verification link to your email"
  and stops auto-redirecting (waits for them to verify).
- Login form refuses sign-in if `email_confirmed_at` is null and asks them
  to verify first.

### Backend JWT enforcement
- `server/app/auth.py` hardened: explicit `verify_exp` + `verify_aud` + missing
  `sub` rejection, 401 with `WWW-Authenticate: Bearer` header.
- `server/app/preparation.py` `/generate-notes`: now requires JWT.
- `server/app/coding/routes.py` `/dsa/problems` and `/dsa/problems/{id}`:
  now require JWT.
- All other routes (`/coding/interview/*`, `/coaching/generate`, `/notes/*`,
  `/webrtc/offer`) already had `Depends(require_user)` — verified.
- `/health` stays public for uptime checks.
- `.env`: added `SUPABASE_URL` and `QACE_REQUIRE_AUTH=false`. **Set this to
  `true` in your Oracle VM `.env`** so the dependency actually rejects requests.

### History per profile
- `client/src/lib/interview-session-store.ts` `persistSession()` now also writes
  `per_question_scores` and `coding_round` into the Supabase row (previously
  these only went to localStorage).
- New: `docs/migrations/006_per_question_scores.sql` — adds the
  `per_question_scores jsonb` column. Apply this in the Supabase SQL editor
  (instructions below).
- Pre-existing infrastructure that already worked (verified in
  `interview-session-store.ts`, `mcq-progress-store.ts`,
  `docs/supabase_schema.sql`):
  - `interview_sessions` (RLS: `auth.uid() = user_id`)
  - `mcq_attempts`, `mcq_topic_progress` (RLS: `auth.uid() = user_id`)
  - `user_profiles` with CV upload (RLS: `auth.uid() = id`)

### Models for production
- Both LoRA adapters fused and dequantized to standard float16:
  - `/Users/aziqrauf/LLM/qace-evaluator-merged/` — 15 GB, 4-shard safetensors
  - `/Users/aziqrauf/LLM/qace-coach-merged/` — 15 GB, 4-shard safetensors
- These work on Linux/NVIDIA — ready to upload to HuggingFace and pull into
  Ollama on the Oracle VM.

### Build verification
- `cd client && npm run build` runs clean. Middleware is registered (81.8 kB).
  All 22 pages compile, including the new `/auth/callback` route.

---

## What you need to do — manual steps

### 1) Apply the per_question_scores migration in Supabase

1. Open https://supabase.com/dashboard/project/hgcjkdeqzayvhgaustuv/sql/new
2. Paste this:
   ```sql
   alter table public.interview_sessions
     add column if not exists per_question_scores jsonb not null default '[]'::jsonb;
   ```
3. Click "Run". You should see "Success. No rows returned."
4. Verify with: `select column_name from information_schema.columns where table_name='interview_sessions';` — `per_question_scores` should be in the list.

### 2) Enable email verification in Supabase

1. Open https://supabase.com/dashboard/project/hgcjkdeqzayvhgaustuv/auth/providers
2. Find "Email" provider → click to expand.
3. Toggle "**Confirm email**" ON.
4. Toggle "**Secure email change**" ON (recommended).
5. Click "Save".
6. Go to Authentication → URL Configuration:
   - Site URL: `http://localhost:3000` (for dev). Once you have a Vercel URL, change to `https://your-app.vercel.app`.
   - Add to "Redirect URLs":
     - `http://localhost:3000/auth/callback`
     - `https://your-app.vercel.app/auth/callback` (after Vercel deploy)
     - `https://yourdomain.com/auth/callback` (after custom domain)
7. (Optional but recommended) Authentication → Email Templates → "Confirm signup" — customise the email subject/body to match Q&Ace branding.

### 3) Sanity test locally (5 min)

1. `cd FYP-QnAce-Main-Repo/client && npm run dev`
2. Open http://localhost:3000 — landing page should load.
3. Try to visit http://localhost:3000/dashboard directly without signing in — should bounce to `/login?next=%2Fdashboard`.
4. Click "Signup" — create a new account with a real email + your CV.
5. Check your inbox for the Supabase verification email.
6. Click the verification link → should land on `/login?verified=1` with green banner.
7. Sign in with your password → land on `/setup`.
8. Navigate to `/dashboard`, `/history`, `/practice`, `/settings` — all should load.
9. Click your avatar → "Sign out" → confirm you bounce to `/`.
10. (Optional 24 h test) In DevTools Console: `document.cookie = "qace_login_at=" + (Date.now() - 25*60*60*1000) + "; Path=/"` then refresh — should redirect to `/login?reason=expired` with amber banner. Reload page once more to confirm. Then `document.cookie = "qace_login_at=; Max-Age=0; Path=/"` to reset.

### 4) Deploy when ready — follow `DEPLOYMENT_PLAN.md`

The original `DEPLOYMENT_PLAN.md` is still your main script. Three notes/diffs based on the work above:

**Phase 1 (HuggingFace upload):**
- The fuse step is **already done** — skip section 1.1, your fused models live at:
  - `/Users/aziqrauf/LLM/qace-evaluator-merged/`
  - `/Users/aziqrauf/LLM/qace-coach-merged/`
- The CLI flag in the doc is wrong — use `--dequantize` (one word), not `--de-quantize`. Already used correctly in the fuse you already ran.
- For 1.2-1.3: create your HF account, generate a Write token, then run:
  ```bash
  ~/.venvs/qace-mlx/bin/python -m huggingface_hub.commands.huggingface_cli login
  # Paste your HF Write token

  # Upload (the CLI command in the plan is fine, but the modern equivalent is)
  ~/.venvs/qace-mlx/bin/python -c "
  from huggingface_hub import HfApi
  api = HfApi()
  api.create_repo('YOUR_HF_USERNAME/qace-evaluator', private=True, exist_ok=True)
  api.upload_folder(
      folder_path='/Users/aziqrauf/LLM/qace-evaluator-merged',
      repo_id='YOUR_HF_USERNAME/qace-evaluator',
  )
  api.create_repo('YOUR_HF_USERNAME/qace-coach', private=True, exist_ok=True)
  api.upload_folder(
      folder_path='/Users/aziqrauf/LLM/qace-coach-merged',
      repo_id='YOUR_HF_USERNAME/qace-coach',
  )
  "
  ```
  This will take 30-60 min depending on upload speed. Run it overnight if needed.

**Phase 3 (Oracle VM `.env`):**
The plan's example `.env` is missing two new keys we now require. Use this updated block instead of the one in DEPLOYMENT_PLAN section 3.7:

```env
QACE_ENV=production
QACE_HOST=0.0.0.0
QACE_PORT=8000
QACE_LOG_LEVEL=info

# CRITICAL: prod must enforce auth
QACE_REQUIRE_AUTH=true

QACE_CORS_ORIGINS=https://your-vercel-app.vercel.app,https://yourdomain.com

QACE_LLM_PROVIDER=local
QACE_LOCAL_LLM_BASE_URL=http://localhost:11434/v1
QACE_LOCAL_LLM_BASE_MODEL=hf.co/YOUR_HF_USERNAME/qace-evaluator
QACE_LOCAL_LLM_PATH=/root
QACE_LOCAL_LLM_ADAPTER_PATH=
QACE_LOCAL_LLM_SERVER_SCRIPT=

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

# Supabase (matches local .env, but with the prod URL above)
SUPABASE_URL=https://hgcjkdeqzayvhgaustuv.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<your service role key>
SUPABASE_JWT_SECRET=<your JWT secret>
```

**Phase 4 (Vercel envs):**
The Vercel project envs are documented in `client/.env.production.example`. Three keys, all NEXT_PUBLIC_*:
```
NEXT_PUBLIC_SUPABASE_URL=https://hgcjkdeqzayvhgaustuv.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<your anon public key>
NEXT_PUBLIC_QACE_API_URL=https://api.yourdomain.com   # or http://VM_IP:8000 if no domain yet
```

NOTE: Vercel is HTTPS, your VM is HTTP by default. Browser will block mixed-content fetch from a Vercel HTTPS page to a plain-HTTP API. Either:
  - Use a custom domain + Certbot (Phase 5 in DEPLOYMENT_PLAN), or
  - Use Cloudflare Tunnel as a free HTTPS terminator in front of the VM, or
  - Skip Vercel and serve the frontend with `next start` from the same Oracle VM behind nginx.

**Phase 5 (custom domain):**
Plan as written. After certbot, also update `Site URL` in Supabase Auth → URL Configuration to your custom domain so verification emails point at the right place.

---

## Files changed in this session (for code review)

New:
- `client/src/middleware.ts`
- `client/src/app/auth/callback/route.ts`
- `client/.env.production.example`
- `docs/migrations/006_per_question_scores.sql`
- `DEPLOYMENT_NEXT_STEPS.md` (this file)

Modified:
- `client/package.json` (+ `@supabase/ssr`)
- `client/src/lib/supabase.ts` (cookie helpers)
- `client/src/lib/interview-session-store.ts` (extended insert payload)
- `client/src/app/login/page.tsx` (banners, cookie, next-redirect, verification gate)
- `client/src/app/signup/page.tsx` (verification messaging, emailRedirectTo)
- `client/src/components/AppShell.tsx` (24 h watchdog, sign-out cleanup)
- `client/src/app/page.tsx` (sign-out cleanup)
- `client/src/app/settings/page.tsx` (Supabase type-cast for build)
- `server/app/auth.py` (hardened JWT validation)
- `server/app/preparation.py` (added auth dep)
- `server/app/coding/routes.py` (added auth dep on two GETs)
- `.env` (added SUPABASE_URL and QACE_REQUIRE_AUTH=false)
- `.env.example` (documented new keys)
- `docs/supabase_schema.sql` (added per_question_scores column)

---

## Quick reference: rollback

If anything goes wrong, revert by:
- Setting `QACE_REQUIRE_AUTH=false` in `.env` (backend stops requiring JWTs)
- Renaming `client/src/middleware.ts` → `client/src/middleware.ts.disabled` (frontend stops redirecting)

The rest of the changes are additive and won't break anything.
