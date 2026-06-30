# Image Staging Pipeline Design

**Date:** 2026-06-30  
**Status:** Approved

## Problem

Before images reach the gallery sync pipeline, two manual steps are required: resizing images to an appropriate display size and writing title/description metadata. Without this, images land in the gallery with placeholder text ("tbc"), and raw originals accumulate without a clear home.

## Solution

A local Python script (`scripts/stage.py`) processes images dropped into `images/stage/<gallery>/`. It resizes each image, calls a vision-capable LLM to generate title and description, appends results to the gallery's `.meta.yml` file (consumed by the existing sync pipeline), and archives the original. The script is run manually before pushing to GitHub.

## Architecture

```
images/stage/<gallery>/    (drop raw images here)
        │
        ▼
python scripts/stage.py
        │
        ├─► images/galleries/<gallery>/      resized image (feeds gallery sync)
        ├─► _galleries/<gallery>.meta.yml    LLM-generated title + description (appended)
        └─► images/raw/<gallery>/            original archived (git-ignored)
```

After running the script, push `images/galleries/` and `_galleries/*.meta.yml` to GitHub. The existing GitHub Action picks up the new images and opens a sync PR as normal.

## Script Interface

```bash
# Process all galleries that have staged images
python scripts/stage.py

# Process one specific gallery
python scripts/stage.py --gallery illustration

# Skip LLM calls (resize + archive only)
python scripts/stage.py --no-llm

# Force a specific LLM provider
python scripts/stage.py --provider claude
python scripts/stage.py --provider openai
python scripts/stage.py --provider gemini
```

The `--no-llm` flag is useful when the API key is not available or when metadata will be written by hand.

## Processing Flow (per image)

For each image found in `images/stage/<gallery>/`:

1. **Resize** — Pillow; max 1600px long edge. JPEG saved at quality 85. PNG saved lossless (stays PNG). Output written to `images/galleries/<gallery>/` with the same filename.
2. **LLM analysis** — send the resized image (base64-encoded) to the configured provider with a prompt asking for `title` and `description` suitable for an art portfolio. Returns JSON.
3. **Append to meta file** — write to `_galleries/<gallery>.meta.yml`, keyed by the original filename (the key the sync script matches on). Skips the key if it already exists — never overwrites existing entries.
4. **Archive original** — move (not copy) the file from `images/stage/<gallery>/` to `images/raw/<gallery>/`.

**Supported extensions:** `.jpg`, `.jpeg`, `.png`

## LLM Provider Support

The script supports three vision-capable providers. When `--provider` is not specified, it auto-detects by checking which API key is present in the environment (Claude first, then OpenAI, then Gemini).

| Provider | Env var | Model |
|---|---|---|
| Claude | `ANTHROPIC_API_KEY` | `claude-opus-4-8` |
| OpenAI | `OPENAI_API_KEY` | `gpt-4o` |
| Gemini | `GEMINI_API_KEY` | `gemini-2.0-flash` |

**Prompt (same across all providers):**

> You are writing metadata for an art portfolio. Given the artwork image, return a JSON object with exactly two fields:
> - `title`: a short, evocative title for the artwork (max 10 words)
> - `description`: 1–2 sentences describing the medium, style, and subject

**On API error:** logs a warning and writes `title: <filename without extension>` / `description: "tbc"` as fallback so the sync pipeline is never blocked.

Each provider is imported lazily — a missing package for an unused provider does not cause a startup error.

## Meta File Output

Appended to `_galleries/<gallery>.meta.yml`:

```yaml
IMG_9780.png:
  title: "Autumn Reflections"
  description: "Acrylic on canvas capturing the warmth of fallen leaves over still water."
```

Keys are original filenames (before any order-prefix renaming by the sync script). This matches the lookup key the sync script uses — see the gallery auto-sync design spec.

## Files

| File | Change |
|---|---|
| `scripts/stage.py` | New file — the staging script |
| `requirements.txt` | Add `anthropic`, `openai`, `google-generativeai`, `Pillow`, `pyyaml` |
| `.gitignore` | Add `images/raw/` |

No changes to any existing gallery files, sync scripts, or GitHub Actions.

## Out of Scope

- Running automatically on file-system events (watch mode) — manual trigger only
- Uploading directly to GitHub — that remains the existing sync pipeline's job
- Generating metadata for images already in `images/galleries/` — staging only handles new images
- Batch concurrency / parallel LLM calls — processes one image at a time for simplicity
