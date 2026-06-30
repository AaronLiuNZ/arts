# Image Staging Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `scripts/stage.py` — a CLI script that resizes staged images, calls a vision LLM to generate title/description metadata, and archives the originals.

**Architecture:** A single self-contained script with three pure functions (`resize_image`, `append_meta`, `_parse_json`) and three provider classes (`ClaudeProvider`, `OpenAIProvider`, `GeminiProvider`). The CLI wires them together via `process_gallery` and `main`. All functions are importable for testing without side effects.

**Tech Stack:** Python 3.10, Pillow (image resize), PyYAML (meta file), anthropic SDK, openai SDK, google-generativeai SDK, pytest.

## Global Constraints

- Run from the repo root — all paths are relative to repo root.
- Supported image extensions: `.jpg`, `.jpeg`, `.png` only.
- Meta file keyed by **original filename** (before any sync-script renaming). Key format: `IMG_9780.png`.
- Meta file is append-only — existing keys are never overwritten.
- LLM model strings: Claude → `claude-opus-4-8`, OpenAI → `gpt-4o`, Gemini → `gemini-2.0-flash`.
- Provider auto-detect order: Claude first, then OpenAI, then Gemini.
- On any LLM error: log warning, fall back to `title = <stem>`, `description = "tbc"`.
- JPEG resize: quality 85. PNG: lossless. Max long edge: 1600px. Images already smaller than 1600px are saved as-is (same format/quality, not scaled up).

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `.gitignore` | Modify | Add `images/raw/` |
| `requirements.txt` | Create | Python deps |
| `scripts/stage.py` | Create | The staging script |
| `tests/test_stage.py` | Create | Unit tests for pure functions |

---

### Task 1: Project scaffold

**Files:**
- Modify: `.gitignore`
- Create: `requirements.txt`
- Create: `images/stage/.gitkeep`

**Interfaces:**
- Produces: nothing consumed by later tasks — pure setup

- [ ] **Step 1: Add `images/raw/` to `.gitignore`**

Open `.gitignore` and append:
```
images/raw/
```

- [ ] **Step 2: Create `requirements.txt`**

```
anthropic
openai
google-generativeai
Pillow
PyYAML
pytest
```

- [ ] **Step 3: Create the stage directory placeholder**

```bash
mkdir -p images/stage
touch images/stage/.gitkeep
```

- [ ] **Step 4: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: packages install without errors. (Skip providers you don't have API keys for — they install fine regardless.)

- [ ] **Step 5: Commit**

```bash
git add .gitignore requirements.txt images/stage/.gitkeep
git commit -m "chore: scaffold staging pipeline dependencies and directories"
```

---

### Task 2: Image resizer

**Files:**
- Create: `scripts/stage.py` (partial — `resize_image` function only)
- Create: `tests/test_stage.py` (partial — resize tests only)

**Interfaces:**
- Produces: `resize_image(src_path: str, dst_path: str, max_long_edge: int = 1600) -> None`

- [ ] **Step 1: Create `scripts/__init__.py` (empty) and `scripts/stage.py` with the resize function**

Create `scripts/__init__.py`:
```python
```
(empty file)

Create `scripts/stage.py`:
```python
import os
from PIL import Image


def resize_image(src_path: str, dst_path: str, max_long_edge: int = 1600) -> None:
    with Image.open(src_path) as img:
        w, h = img.size
        if max(w, h) > max_long_edge:
            scale = max_long_edge / max(w, h)
            img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        os.makedirs(os.path.dirname(dst_path) or '.', exist_ok=True)
        ext = os.path.splitext(src_path)[1].lower()
        if ext in ('.jpg', '.jpeg'):
            img.save(dst_path, 'JPEG', quality=85)
        else:
            img.save(dst_path, 'PNG')
```

- [ ] **Step 2: Write failing tests**

Create `tests/__init__.py` (empty), then create `tests/test_stage.py`:
```python
import os
import pytest
from PIL import Image
from scripts.stage import resize_image


def make_image(tmp_path, width, height, fmt='JPEG', name='test.jpg'):
    path = str(tmp_path / name)
    img = Image.new('RGB', (width, height), color=(100, 150, 200))
    img.save(path, fmt)
    return path


def test_resize_large_jpeg_downscales(tmp_path):
    src = make_image(tmp_path, 3200, 2400, 'JPEG', 'big.jpg')
    dst = str(tmp_path / 'out.jpg')
    resize_image(src, dst)
    with Image.open(dst) as img:
        assert max(img.size) == 1600


def test_resize_small_jpeg_unchanged(tmp_path):
    src = make_image(tmp_path, 800, 600, 'JPEG', 'small.jpg')
    dst = str(tmp_path / 'out.jpg')
    resize_image(src, dst)
    with Image.open(dst) as img:
        assert img.size == (800, 600)


def test_resize_landscape_jpeg(tmp_path):
    src = make_image(tmp_path, 3200, 1800, 'JPEG', 'wide.jpg')
    dst = str(tmp_path / 'out.jpg')
    resize_image(src, dst)
    with Image.open(dst) as img:
        assert img.size[0] == 1600
        assert img.size[1] == 900


def test_resize_png_stays_png(tmp_path):
    src = make_image(tmp_path, 3200, 2400, 'PNG', 'big.png')
    dst = str(tmp_path / 'out.png')
    resize_image(src, dst)
    with Image.open(dst) as img:
        assert img.format == 'PNG'
        assert max(img.size) == 1600


def test_resize_creates_output_directory(tmp_path):
    src = make_image(tmp_path, 800, 600, 'JPEG', 'test.jpg')
    dst = str(tmp_path / 'nested' / 'dir' / 'out.jpg')
    resize_image(src, dst)
    assert os.path.exists(dst)
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
pytest tests/test_stage.py -v
```

Expected: `ModuleNotFoundError: No module named 'scripts.stage'` or similar — good, confirms the test harness works.

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_stage.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/__init__.py scripts/stage.py tests/__init__.py tests/test_stage.py
git commit -m "feat: add image resizer with tests"
```

---

### Task 3: Meta file appender

**Files:**
- Modify: `scripts/stage.py` — add `append_meta`
- Modify: `tests/test_stage.py` — add meta tests

**Interfaces:**
- Consumes: nothing from earlier tasks
- Produces: `append_meta(meta_path: str, filename: str, title: str, description: str) -> bool`
  - Returns `True` if the entry was added, `False` if the key already existed (skipped).

- [ ] **Step 1: Write failing tests**

Append to `tests/test_stage.py`:
```python
import yaml
from scripts.stage import append_meta


def test_append_meta_creates_new_file(tmp_path):
    meta = str(tmp_path / 'test.meta.yml')
    result = append_meta(meta, 'IMG_001.jpg', 'My Title', 'My description.')
    assert result is True
    with open(meta) as f:
        data = yaml.safe_load(f)
    assert data['IMG_001.jpg']['title'] == 'My Title'
    assert data['IMG_001.jpg']['description'] == 'My description.'


def test_append_meta_skips_existing_key(tmp_path):
    meta = str(tmp_path / 'test.meta.yml')
    append_meta(meta, 'IMG_001.jpg', 'Original', 'Original desc.')
    result = append_meta(meta, 'IMG_001.jpg', 'New Title', 'New desc.')
    assert result is False
    with open(meta) as f:
        data = yaml.safe_load(f)
    assert data['IMG_001.jpg']['title'] == 'Original'


def test_append_meta_preserves_existing_entries(tmp_path):
    meta = str(tmp_path / 'test.meta.yml')
    append_meta(meta, 'IMG_001.jpg', 'First', 'First desc.')
    append_meta(meta, 'IMG_002.jpg', 'Second', 'Second desc.')
    with open(meta) as f:
        data = yaml.safe_load(f)
    assert 'IMG_001.jpg' in data
    assert 'IMG_002.jpg' in data
    assert data['IMG_001.jpg']['title'] == 'First'
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_stage.py::test_append_meta_creates_new_file -v
```

Expected: `ImportError: cannot import name 'append_meta'`

- [ ] **Step 3: Add `append_meta` to `scripts/stage.py`**

Add this import at the top of `scripts/stage.py`:
```python
import yaml
```

Add this function after `resize_image`:
```python
def append_meta(meta_path: str, filename: str, title: str, description: str) -> bool:
    data = {}
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            data = yaml.safe_load(f) or {}
    if filename in data:
        return False
    data[filename] = {'title': title, 'description': description}
    with open(meta_path, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
    return True
```

- [ ] **Step 4: Run all tests to verify they pass**

```bash
pytest tests/test_stage.py -v
```

Expected: all 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/stage.py tests/test_stage.py
git commit -m "feat: add meta file appender with tests"
```

---

### Task 4: LLM providers

**Files:**
- Modify: `scripts/stage.py` — add `PROMPT`, `_parse_json`, provider classes, `get_provider`
- Modify: `tests/test_stage.py` — add provider tests

**Interfaces:**
- Produces:
  - `_parse_json(text: str) -> dict | None`
  - `ClaudeProvider.analyze_image(image_path: str) -> dict` — returns `{"title": str, "description": str}`
  - `OpenAIProvider.analyze_image(image_path: str) -> dict`
  - `GeminiProvider.analyze_image(image_path: str) -> dict`
  - `get_provider(name: str | None = None) -> ClaudeProvider | OpenAIProvider | GeminiProvider`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_stage.py`:
```python
import json
from unittest.mock import patch, MagicMock
from scripts.stage import _parse_json, get_provider, ClaudeProvider, OpenAIProvider, GeminiProvider


def test_parse_json_clean():
    result = _parse_json('{"title": "Art", "description": "A painting."}')
    assert result == {'title': 'Art', 'description': 'A painting.'}


def test_parse_json_markdown_fences():
    text = '```json\n{"title": "Art", "description": "A painting."}\n```'
    result = _parse_json(text)
    assert result == {'title': 'Art', 'description': 'A painting.'}


def test_parse_json_invalid_returns_none():
    result = _parse_json('not valid json at all')
    assert result is None


def test_get_provider_explicit_claude(monkeypatch):
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'test-key')
    provider = get_provider('claude')
    assert isinstance(provider, ClaudeProvider)


def test_get_provider_explicit_openai(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'test-key')
    provider = get_provider('openai')
    assert isinstance(provider, OpenAIProvider)


def test_get_provider_explicit_gemini(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'test-key')
    provider = get_provider('gemini')
    assert isinstance(provider, GeminiProvider)


def test_get_provider_auto_prefers_claude(monkeypatch):
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'test-key')
    monkeypatch.setenv('OPENAI_API_KEY', 'test-key')
    provider = get_provider()
    assert isinstance(provider, ClaudeProvider)


def test_get_provider_no_keys_raises(monkeypatch):
    monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    with pytest.raises(RuntimeError, match='No LLM provider'):
        get_provider()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_stage.py::test_parse_json_clean -v
```

Expected: `ImportError: cannot import name '_parse_json'`

- [ ] **Step 3: Add provider code to `scripts/stage.py`**

Add these imports at the top of `scripts/stage.py`:
```python
import base64
import json
import re
import sys
```

Add the prompt constant and helpers after the existing imports:
```python
PROMPT = (
    "You are writing metadata for an art portfolio. Given the artwork image, "
    "return a JSON object with exactly two fields:\n"
    '- "title": a short, evocative title for the artwork (max 10 words)\n'
    '- "description": 1-2 sentences describing the medium, style, and subject\n\n'
    "Return only valid JSON. No markdown, no extra text."
)


def _parse_json(text: str):
    text = re.sub(r'^```(?:json)?\s*', '', text.strip(), flags=re.MULTILINE)
    text = re.sub(r'```\s*$', '', text.strip(), flags=re.MULTILINE)
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        return None


class ClaudeProvider:
    def __init__(self):
        import anthropic
        self._client = anthropic.Anthropic()

    def analyze_image(self, image_path: str) -> dict:
        import anthropic
        ext = os.path.splitext(image_path)[1].lower()
        media_type = 'image/png' if ext == '.png' else 'image/jpeg'
        with open(image_path, 'rb') as f:
            data = base64.standard_b64encode(f.read()).decode()
        response = self._client.messages.create(
            model='claude-opus-4-8',
            max_tokens=256,
            messages=[{'role': 'user', 'content': [
                {'type': 'image', 'source': {'type': 'base64', 'media_type': media_type, 'data': data}},
                {'type': 'text', 'text': PROMPT},
            ]}],
        )
        return _parse_json(response.content[0].text)


class OpenAIProvider:
    def __init__(self):
        import openai
        self._client = openai.OpenAI()

    def analyze_image(self, image_path: str) -> dict:
        ext = os.path.splitext(image_path)[1].lower()
        media_type = 'image/png' if ext == '.png' else 'image/jpeg'
        with open(image_path, 'rb') as f:
            data = base64.standard_b64encode(f.read()).decode()
        response = self._client.chat.completions.create(
            model='gpt-4o',
            max_tokens=256,
            messages=[{'role': 'user', 'content': [
                {'type': 'image_url', 'image_url': {'url': f'data:{media_type};base64,{data}'}},
                {'type': 'text', 'text': PROMPT},
            ]}],
        )
        return _parse_json(response.choices[0].message.content)


class GeminiProvider:
    def __init__(self):
        import google.generativeai as genai
        genai.configure(api_key=os.environ.get('GEMINI_API_KEY'))
        self._model = genai.GenerativeModel('gemini-2.0-flash')

    def analyze_image(self, image_path: str) -> dict:
        from PIL import Image as PILImage
        img = PILImage.open(image_path)
        response = self._model.generate_content([PROMPT, img])
        return _parse_json(response.text)


def get_provider(name: str = None):
    if name == 'claude' or (name is None and os.environ.get('ANTHROPIC_API_KEY')):
        return ClaudeProvider()
    if name == 'openai' or (name is None and os.environ.get('OPENAI_API_KEY')):
        return OpenAIProvider()
    if name == 'gemini' or (name is None and os.environ.get('GEMINI_API_KEY')):
        return GeminiProvider()
    raise RuntimeError(
        'No LLM provider available. Set ANTHROPIC_API_KEY, OPENAI_API_KEY, or GEMINI_API_KEY.'
    )
```

- [ ] **Step 4: Run all tests to verify they pass**

```bash
pytest tests/test_stage.py -v
```

Expected: all 19 tests PASS. (Provider constructor tests instantiate provider classes — they will import the SDK but not make network calls, so they pass as long as the SDK is installed.)

- [ ] **Step 5: Commit**

```bash
git add scripts/stage.py tests/test_stage.py
git commit -m "feat: add LLM providers and JSON parser with tests"
```

---

### Task 5: Main orchestration and CLI

**Files:**
- Modify: `scripts/stage.py` — add `process_gallery` and `main`

**Interfaces:**
- Consumes:
  - `resize_image(src_path, dst_path)` from Task 2
  - `append_meta(meta_path, filename, title, description)` from Task 3
  - `get_provider(name)` from Task 4
- Produces: runnable CLI script

- [ ] **Step 1: Add constants and `process_gallery` to `scripts/stage.py`**

Add these constants after the imports in `scripts/stage.py`:
```python
SUPPORTED_EXTS = {'.jpg', '.jpeg', '.png'}
STAGE_DIR = 'images/stage'
GALLERIES_DIR = 'images/galleries'
RAW_DIR = 'images/raw'
GALLERIES_DATA_DIR = '_galleries'
META_SUFFIX = '.meta.yml'
```

Add `process_gallery` after `get_provider`:
```python
def process_gallery(gallery: str, provider=None, no_llm: bool = False) -> None:
    stage_path = os.path.join(STAGE_DIR, gallery)
    if not os.path.isdir(stage_path):
        print(f'  No stage folder: {stage_path}')
        return

    images = sorted(
        f for f in os.listdir(stage_path)
        if os.path.splitext(f)[1].lower() in SUPPORTED_EXTS
    )
    if not images:
        print(f'  No staged images in {stage_path}')
        return

    gallery_out = os.path.join(GALLERIES_DIR, gallery)
    raw_out = os.path.join(RAW_DIR, gallery)
    meta_path = os.path.join(GALLERIES_DATA_DIR, f'{gallery}{META_SUFFIX}')
    os.makedirs(gallery_out, exist_ok=True)
    os.makedirs(raw_out, exist_ok=True)

    for filename in images:
        src = os.path.join(stage_path, filename)
        dst = os.path.join(gallery_out, filename)
        archive = os.path.join(raw_out, filename)
        stem = os.path.splitext(filename)[0]

        print(f'  {filename}')

        resize_image(src, dst)
        print(f'    resized → {dst}')

        if not no_llm and provider is not None:
            try:
                result = provider.analyze_image(dst)
                title = result.get('title', stem) if result else stem
                description = result.get('description', 'tbc') if result else 'tbc'
            except Exception as e:
                print(f'    LLM warning: {e}')
                title, description = stem, 'tbc'
        else:
            title, description = stem, 'tbc'

        appended = append_meta(meta_path, filename, title, description)
        if appended:
            print(f'    meta: {title!r}')
        else:
            print(f'    meta: already exists, skipped')

        import shutil
        shutil.move(src, archive)
        print(f'    archived → {archive}')
```

- [ ] **Step 2: Add `main` and the `if __name__` guard**

Append to the end of `scripts/stage.py`:
```python
def main():
    import argparse
    parser = argparse.ArgumentParser(description='Stage images for the gallery pipeline.')
    parser.add_argument('--gallery', help='Process only this gallery (default: all)')
    parser.add_argument('--provider', choices=['claude', 'openai', 'gemini'],
                        help='LLM provider (default: auto-detect from env)')
    parser.add_argument('--no-llm', action='store_true',
                        help='Skip LLM calls (resize + archive only)')
    args = parser.parse_args()

    provider = None
    if not args.no_llm:
        try:
            provider = get_provider(args.provider)
            print(f'Provider: {type(provider).__name__}')
        except RuntimeError as e:
            print(f'Warning: {e}')
            print('Continuing without LLM metadata (use --no-llm to suppress this warning).')

    if args.gallery:
        galleries = [args.gallery]
    else:
        if not os.path.isdir(STAGE_DIR):
            print(f'Stage directory not found: {STAGE_DIR}')
            print('Create images/stage/<gallery-name>/ and drop images there.')
            sys.exit(0)
        galleries = sorted(
            d for d in os.listdir(STAGE_DIR)
            if os.path.isdir(os.path.join(STAGE_DIR, d))
        )
        if not galleries:
            print('No gallery subfolders found in images/stage/')
            sys.exit(0)

    for gallery in galleries:
        print(f'Gallery: {gallery}')
        process_gallery(gallery, provider=provider, no_llm=args.no_llm)


if __name__ == '__main__':
    main()
```

- [ ] **Step 3: Smoke-test with `--no-llm`**

```bash
mkdir -p images/stage/illustration
cp images/galleries/illustration/IMG_9776.png images/stage/illustration/test_smoke.png
python scripts/stage.py --gallery illustration --no-llm
```

Expected output:
```
Gallery: illustration
  test_smoke.png
    resized → images/galleries/illustration/test_smoke.png
    meta: 'test_smoke'
    archived → images/raw/illustration/test_smoke.png
```

Verify:
```bash
ls images/galleries/illustration/test_smoke.png   # should exist
ls images/raw/illustration/test_smoke.png          # should exist
ls images/stage/illustration/test_smoke.png        # should NOT exist (moved)
cat _galleries/illustration.meta.yml               # should contain test_smoke.png entry
```

- [ ] **Step 4: Clean up smoke-test artifacts**

```bash
rm images/galleries/illustration/test_smoke.png
rm images/raw/illustration/test_smoke.png
# Remove the test entry from _galleries/illustration.meta.yml manually
# (open the file and delete the test_smoke.png block)
```

- [ ] **Step 5: Run full test suite**

```bash
pytest tests/test_stage.py -v
```

Expected: all 19 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/stage.py
git commit -m "feat: add staging pipeline orchestration and CLI"
```

---

## End-to-End Verification

After all tasks are done, run the full pipeline with a real image and an API key:

```bash
# Copy a real artwork image into the stage folder
cp /path/to/new-painting.jpg images/stage/illustration/

# Run with Claude (or replace --provider with openai/gemini)
ANTHROPIC_API_KEY=your-key python scripts/stage.py --gallery illustration

# Check outputs
cat _galleries/illustration.meta.yml      # new entry with LLM title + description
ls images/galleries/illustration/         # resized image present
ls images/raw/illustration/               # original archived
ls images/stage/illustration/             # should be empty (file moved)
```

Then push to trigger the existing gallery sync:
```bash
git add images/galleries/ _galleries/
git push origin main
```
The GitHub Action opens a sync PR as normal.
