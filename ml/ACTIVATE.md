# Activating the Pragma Model

## Current Status
- [x] Training data generation — running (`ml/data/train.jsonl` + `eval.jsonl`)
- [ ] HuggingFace account + token
- [ ] Fine-tune on Google Colab
- [ ] Set `CUSTOM_MODEL_REPO` on Railway

---

## Step 1 — Create HuggingFace Account (5 min)

1. Go to https://huggingface.co/join
2. Create a free account (username will be your repo prefix, e.g. `mleng009`)
3. Go to **Settings → Access Tokens → New token**
   - Name: `pragma-train`
   - Role: **Write**
4. Copy the token — looks like `hf_xxxxxxxxxxxxxxxxxxxxxxxx`

---

## Step 2 — Upload Data to Google Colab (2 min)

1. Open `ml/pragma_train_colab.ipynb` in Google Colab:
   - Go to https://colab.research.google.com
   - File → Upload notebook → select `ml/pragma_train_colab.ipynb`
2. **Runtime → Change runtime type → T4 GPU** (free tier)
3. In left sidebar → Files icon → Upload:
   - `ml/data/train.jsonl`
   - `ml/data/eval.jsonl`
4. Go to **Secrets (🔑 icon in left sidebar) → Add new secret**:
   - Name: `HF_TOKEN`
   - Value: your HuggingFace token from Step 1

---

## Step 3 — Configure and Run (90 min, unattended)

In the notebook, edit **Step 2: Config**:
```python
HF_REPO = 'YOUR_HF_USERNAME/pragma-ethics-v1'   # e.g. mleng009/pragma-ethics-v1
```

Then: **Runtime → Run all**

The notebook will:
- Install dependencies
- Load Phi-3-mini-4k-instruct (4-bit quantized, fits on T4)
- Fine-tune with LoRA for 3 epochs
- Push the trained adapter to HuggingFace Hub
- Print a quick inference test at the end

---

## Step 4 — Activate on Railway (2 min)

Once training completes, the notebook prints:
```
✅ Model live at: https://huggingface.co/YOUR_USERNAME/pragma-ethics-v1
Set this in Railway dashboard:
  CUSTOM_MODEL_REPO = YOUR_USERNAME/pragma-ethics-v1
```

Go to Railway dashboard → your service → **Variables** → add:
```
CUSTOM_MODEL_REPO = YOUR_USERNAME/pragma-ethics-v1
HF_TOKEN          = hf_xxxxxxxxxxxxxxxxxxxxxxxx   (only if model is private)
```

Railway auto-redeploys. Next request hits `/health-check` and you'll see:
```json
{ "model": { "pragma": true, "claude": true, "openai": true } }
```

---

## Step 5 — Verify It's Working

After deployment, run a test evaluation. The response will include:
```json
{ "provider": "pragma", "confidence_score": 0.85, ... }
```

Instead of `"provider": "claude"` — that's your model running.

---

## Running the Feedback Flywheel (after 50+ ratings)

```bash
# See which categories users are thumbs-down-ing
DATABASE_URL=postgresql://... python ml/collect_feedback.py --dry_run

# Generate more training data for weak categories
DATABASE_URL=postgresql://... ANTHROPIC_API_KEY=sk-ant-... \
    python ml/collect_feedback.py --threshold 0.70 --extra_per_weak 10

# Re-run training on Colab with updated train.jsonl (bump version to v2)
# Change HF_REPO = 'mleng009/pragma-ethics-v2' in the notebook
```

---

## Estimated Timeline

| Step | Time |
|---|---|
| Data generation (running now) | ~35 min |
| HuggingFace account setup | 5 min |
| Upload to Colab + configure | 5 min |
| Fine-tuning (T4 GPU) | ~90 min |
| Railway deploy | 2 min |
| **Total** | **~2.5 hours** |
