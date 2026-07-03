# Gallery Auto-Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatically rename new gallery images with an order prefix and update `_galleries/<name>.yml` via a GitHub Action when images are pushed to `images/galleries/`.

**Architecture:** A Python script reads each gallery directory, diffs against the existing YML, renames new images with a zero-padded 2-digit order prefix, and appends new YML entries using values from an optional `.meta.yml` file (or defaults). A GitHub Action triggers on push to `main` when `images/galleries/**` changes, runs the script, and opens a PR with the changes for review before merging to main.

**Tech Stack:** Python 3.11, PyYAML, GitHub Actions, `gh` CLI (pre-installed on runners)

## Global Constraints

- Default artist: `Aaron Liu`
- Default description: `tbc`
- Default title: original filename without extension (e.g. `IMG_9780.png` → `IMG_9780`)
- Supported image extensions: `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`
- Order prefix format: zero-padded 2 digits (e.g. `01_`, `14_`)
- Meta file keyed by **original filename** (before rename)
- Existing YML entries and existing image files are never modified — append-only
- Action triggers on push to `main` branch only
- PR branch name: `auto/gallery-sync-<YYYYMMDD-HHMMSS>`

---

### Task 1: Core pure functions with tests

**Files:**
- Create: `.github/scripts/sync_gallery.py`
- Create: `tests/conftest.py`
- Create: `tests/test_sync_gallery.py`

**Interfaces:**
- Produces:
  - `get_existing_filenames(arts: list) -> set` — returns set of base filenames from YML arts list
  - `find_new_images(gallery_dir: Path, existing: set) -> list` — returns sorted list of new image filenames not in `existing`
  - `next_order(arts: list) -> int` — returns `max(order) + 1` across arts list, or `1` if empty
  - `make_entry(gallery_name: str, new_filename: str, original_filename: str, order: int, meta: dict) -> dict` — returns a complete YML arts entry dict
  - `format_entry(entry: dict) -> str` — returns YAML-formatted string for one entry (no trailing newline)

- [ ] **Step 1: Create test infrastructure**

Create `tests/conftest.py`:
```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / '.github' / 'scripts'))
```

Create `tests/test_sync_gallery.py`:
```python
import pytest
from pathlib import Path
from sync_gallery import (
    get_existing_filenames,
    find_new_images,
    next_order,
    make_entry,
    format_entry,
)
```

- [ ] **Step 2: Write failing tests for `get_existing_filenames`**

Add to `tests/test_sync_gallery.py`:
```python
def test_get_existing_filenames_empty():
    assert get_existing_filenames([]) == set()

def test_get_existing_filenames_extracts_basename():
    arts = [
        {'image': 'images/galleries/illustration/01_IMG_001.png', 'order': '1'},
        {'image': 'images/galleries/illustration/02_IMG_002.jpg', 'order': '2'},
    ]
    assert get_existing_filenames(arts) == {'01_IMG_001.png', '02_IMG_002.jpg'}
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
cd /mnt/c/work/source/jason/aaron/arts
pip install pytest pyyaml
pytest tests/test_sync_gallery.py -v 2>&1 | head -20
```
Expected: `ModuleNotFoundError: No module named 'sync_gallery'`

- [ ] **Step 4: Create `.github/scripts/sync_gallery.py` with `get_existing_filenames`**

```bash
mkdir -p /mnt/c/work/source/jason/aaron/arts/.github/scripts
```

Create `.github/scripts/sync_gallery.py`:
```python
import shutil
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("PyYAML required: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
DEFAULT_ARTIST = 'Aaron Liu'
DEFAULT_DESCRIPTION = 'tbc'


def get_existing_filenames(arts: list) -> set:
    return {Path(entry['image']).name for entry in arts}
```

- [ ] **Step 5: Run tests to verify `get_existing_filenames` passes**

```bash
pytest tests/test_sync_gallery.py -k "get_existing" -v
```
Expected: 2 PASSED

- [ ] **Step 6: Write failing tests for `find_new_images`**

Add to `tests/test_sync_gallery.py`:
```python
def test_find_new_images_returns_sorted(tmp_path):
    gallery_dir = tmp_path / 'illustration'
    gallery_dir.mkdir()
    (gallery_dir / 'zebra.jpg').touch()
    (gallery_dir / 'apple.png').touch()
    (gallery_dir / 'mango.jpeg').touch()
    assert find_new_images(gallery_dir, set()) == ['apple.png', 'mango.jpeg', 'zebra.jpg']

def test_find_new_images_excludes_existing(tmp_path):
    gallery_dir = tmp_path / 'illustration'
    gallery_dir.mkdir()
    (gallery_dir / '01_apple.png').touch()
    (gallery_dir / 'mango.jpeg').touch()
    assert find_new_images(gallery_dir, {'01_apple.png'}) == ['mango.jpeg']

def test_find_new_images_ignores_non_images(tmp_path):
    gallery_dir = tmp_path / 'illustration'
    gallery_dir.mkdir()
    (gallery_dir / 'photo.jpg').touch()
    (gallery_dir / 'readme.txt').touch()
    (gallery_dir / 'meta.yml').touch()
    assert find_new_images(gallery_dir, set()) == ['photo.jpg']
```

- [ ] **Step 7: Run tests to verify they fail**

```bash
pytest tests/test_sync_gallery.py -k "find_new_images" -v
```
Expected: `ImportError` or `AttributeError`

- [ ] **Step 8: Implement `find_new_images`**

Add to `sync_gallery.py`:
```python
def find_new_images(gallery_dir: Path, existing: set) -> list:
    images = [
        f.name for f in gallery_dir.iterdir()
        if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS and f.name not in existing
    ]
    return sorted(images)
```

- [ ] **Step 9: Run tests to verify they pass**

```bash
pytest tests/test_sync_gallery.py -k "find_new_images" -v
```
Expected: 3 PASSED

- [ ] **Step 10: Write failing tests for `next_order`**

Add to `tests/test_sync_gallery.py`:
```python
def test_next_order_empty_list():
    assert next_order([]) == 1

def test_next_order_returns_max_plus_one():
    arts = [{'order': '3'}, {'order': '1'}, {'order': '5'}]
    assert next_order(arts) == 6

def test_next_order_handles_string_orders():
    assert next_order([{'order': '13'}]) == 14
```

- [ ] **Step 11: Run tests to verify they fail**

```bash
pytest tests/test_sync_gallery.py -k "next_order" -v
```
Expected: `ImportError` or `AttributeError`

- [ ] **Step 12: Implement `next_order`**

Add to `sync_gallery.py`:
```python
def next_order(arts: list) -> int:
    if not arts:
        return 1
    return max(int(entry.get('order', 0)) for entry in arts) + 1
```

- [ ] **Step 13: Run tests to verify they pass**

```bash
pytest tests/test_sync_gallery.py -k "next_order" -v
```
Expected: 3 PASSED

- [ ] **Step 14: Write failing tests for `make_entry`**

Add to `tests/test_sync_gallery.py`:
```python
def test_make_entry_defaults():
    entry = make_entry('illustration', '14_IMG_9780.png', 'IMG_9780.png', 14, {})
    assert entry == {
        'image': 'images/galleries/illustration/14_IMG_9780.png',
        'order': '14',
        'title': 'IMG_9780',
        'artist': 'Aaron Liu',
        'description': 'tbc',
    }

def test_make_entry_uses_meta_title_and_description():
    meta = {'IMG_9780.png': {'title': 'My Painting', 'description': 'Oil on canvas'}}
    entry = make_entry('illustration', '14_IMG_9780.png', 'IMG_9780.png', 14, meta)
    assert entry['title'] == 'My Painting'
    assert entry['description'] == 'Oil on canvas'
    assert entry['artist'] == 'Aaron Liu'

def test_make_entry_meta_overrides_artist():
    meta = {'IMG_9780.png': {'artist': 'Guest Artist'}}
    entry = make_entry('illustration', '14_IMG_9780.png', 'IMG_9780.png', 14, meta)
    assert entry['artist'] == 'Guest Artist'

def test_make_entry_partial_meta_falls_back_to_defaults():
    meta = {'IMG_9780.png': {'title': 'Only Title'}}
    entry = make_entry('illustration', '14_IMG_9780.png', 'IMG_9780.png', 14, meta)
    assert entry['title'] == 'Only Title'
    assert entry['description'] == 'tbc'
    assert entry['artist'] == 'Aaron Liu'
```

- [ ] **Step 15: Run tests to verify they fail**

```bash
pytest tests/test_sync_gallery.py -k "make_entry" -v
```
Expected: `ImportError` or `AttributeError`

- [ ] **Step 16: Implement `make_entry`**

Add to `sync_gallery.py`:
```python
def make_entry(gallery_name: str, new_filename: str, original_filename: str, order: int, meta: dict) -> dict:
    image_meta = meta.get(original_filename, {})
    return {
        'image': f'images/galleries/{gallery_name}/{new_filename}',
        'order': str(order),
        'title': image_meta.get('title', Path(original_filename).stem),
        'artist': image_meta.get('artist', DEFAULT_ARTIST),
        'description': image_meta.get('description', DEFAULT_DESCRIPTION),
    }
```

- [ ] **Step 17: Run tests to verify they pass**

```bash
pytest tests/test_sync_gallery.py -k "make_entry" -v
```
Expected: 4 PASSED

- [ ] **Step 18: Write failing test for `format_entry`**

Add to `tests/test_sync_gallery.py`:
```python
def test_format_entry():
    entry = {
        'image': 'images/galleries/illustration/14_IMG_9780.png',
        'order': '14',
        'title': 'IMG_9780',
        'artist': 'Aaron Liu',
        'description': 'tbc',
    }
    assert format_entry(entry) == (
        '- image: "images/galleries/illustration/14_IMG_9780.png"\n'
        '  order: "14"\n'
        '  title: "IMG_9780"\n'
        '  artist: "Aaron Liu"\n'
        '  description: "tbc"'
    )
```

- [ ] **Step 19: Run test to verify it fails**

```bash
pytest tests/test_sync_gallery.py::test_format_entry -v
```
Expected: `ImportError` or `AttributeError`

- [ ] **Step 20: Implement `format_entry`**

Add to `sync_gallery.py`:
```python
def format_entry(entry: dict) -> str:
    return (
        f'- image: "{entry["image"]}"\n'
        f'  order: "{entry["order"]}"\n'
        f'  title: "{entry["title"]}"\n'
        f'  artist: "{entry["artist"]}"\n'
        f'  description: "{entry["description"]}"'
    )
```

- [ ] **Step 21: Run all tests**

```bash
pytest tests/test_sync_gallery.py -v
```
Expected: All PASSED

- [ ] **Step 22: Commit**

```bash
git add .github/scripts/sync_gallery.py tests/conftest.py tests/test_sync_gallery.py
git commit -m "feat: add core gallery sync pure functions with tests"
```

---

### Task 2: File I/O, renaming, and main orchestration

**Files:**
- Modify: `.github/scripts/sync_gallery.py`
- Modify: `tests/test_sync_gallery.py`

**Interfaces:**
- Consumes: `get_existing_filenames`, `find_new_images`, `next_order`, `make_entry`, `format_entry` from Task 1
- Produces:
  - `load_yml_arts(yml_path: Path) -> list` — parses YML file, returns `arts` list (empty list if file missing or arts absent)
  - `load_meta(meta_path: Path) -> dict` — parses meta YML, returns dict (empty dict if file missing)
  - `rename_image(gallery_dir: Path, filename: str, order: int) -> str` — renames file on disk, returns new filename
  - `append_entries_to_yml(yml_path: Path, gallery_name: str, new_entries: list) -> None` — appends formatted entries to YML, preserving all existing content including comments
  - `sync_gallery(gallery_name: str, images_base: Path, galleries_base: Path) -> bool` — orchestrates one gallery, returns `True` if any images were added
  - `main()` — iterates all gallery dirs that have a matching YML, calls `sync_gallery` on each

- [ ] **Step 1: Write failing tests for `load_yml_arts` and `load_meta`**

Add to `tests/test_sync_gallery.py` (update imports at top to include `load_yml_arts, load_meta`):
```python
from sync_gallery import load_yml_arts, load_meta

def test_load_yml_arts_parses_arts_list(tmp_path):
    yml = tmp_path / 'illustration.yml'
    yml.write_text(
        '---\nname: "illustration"\narts:\n'
        '- image: "images/galleries/illustration/01_test.png"\n'
        '  order: "1"\n  title: "Test"\n  artist: "Aaron Liu"\n  description: "tbc"\n---\n'
    )
    arts = load_yml_arts(yml)
    assert len(arts) == 1
    assert arts[0]['order'] == '1'
    assert arts[0]['title'] == 'Test'

def test_load_yml_arts_returns_empty_for_missing_file(tmp_path):
    assert load_yml_arts(tmp_path / 'missing.yml') == []

def test_load_yml_arts_returns_empty_for_empty_arts(tmp_path):
    yml = tmp_path / 'empty.yml'
    yml.write_text('---\nname: "test"\narts:\n---\n')
    assert load_yml_arts(yml) == []

def test_load_meta_parses_dict(tmp_path):
    meta = tmp_path / 'illustration.meta.yml'
    meta.write_text('IMG_001.png:\n  title: "My Art"\n  description: "Oil"\n')
    result = load_meta(meta)
    assert result['IMG_001.png']['title'] == 'My Art'
    assert result['IMG_001.png']['description'] == 'Oil'

def test_load_meta_returns_empty_for_missing_file(tmp_path):
    assert load_meta(tmp_path / 'missing.meta.yml') == {}
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_sync_gallery.py -k "load_" -v
```
Expected: `ImportError`

- [ ] **Step 3: Implement `load_yml_arts` and `load_meta`**

Add to `sync_gallery.py`:
```python
def load_yml_arts(yml_path: Path) -> list:
    if not yml_path.exists():
        return []
    with open(yml_path, encoding='utf-8') as f:
        data = yaml.safe_load(f)
    if not data or 'arts' not in data:
        return []
    return data['arts'] or []


def load_meta(meta_path: Path) -> dict:
    if not meta_path.exists():
        return {}
    with open(meta_path, encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return data or {}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_sync_gallery.py -k "load_" -v
```
Expected: 5 PASSED

- [ ] **Step 5: Write failing tests for `rename_image`**

Add to `tests/test_sync_gallery.py` (update imports to include `rename_image`):
```python
from sync_gallery import rename_image

def test_rename_image_moves_file_with_order_prefix(tmp_path):
    gallery_dir = tmp_path / 'illustration'
    gallery_dir.mkdir()
    (gallery_dir / 'IMG_9780.png').write_bytes(b'fake image')
    new_name = rename_image(gallery_dir, 'IMG_9780.png', 14)
    assert new_name == '14_IMG_9780.png'
    assert (gallery_dir / '14_IMG_9780.png').exists()
    assert not (gallery_dir / 'IMG_9780.png').exists()

def test_rename_image_zero_pads_single_digit_order(tmp_path):
    gallery_dir = tmp_path / 'illustration'
    gallery_dir.mkdir()
    (gallery_dir / 'photo.jpg').write_bytes(b'fake')
    new_name = rename_image(gallery_dir, 'photo.jpg', 3)
    assert new_name == '03_photo.jpg'
```

- [ ] **Step 6: Run tests to verify they fail**

```bash
pytest tests/test_sync_gallery.py -k "rename_image" -v
```
Expected: `ImportError`

- [ ] **Step 7: Implement `rename_image`**

Add to `sync_gallery.py`:
```python
def rename_image(gallery_dir: Path, filename: str, order: int) -> str:
    new_name = f'{order:02d}_{filename}'
    shutil.move(str(gallery_dir / filename), str(gallery_dir / new_name))
    return new_name
```

- [ ] **Step 8: Run tests to verify they pass**

```bash
pytest tests/test_sync_gallery.py -k "rename_image" -v
```
Expected: 2 PASSED

- [ ] **Step 9: Write failing tests for `append_entries_to_yml`**

Add to `tests/test_sync_gallery.py` (update imports to include `append_entries_to_yml`):
```python
from sync_gallery import append_entries_to_yml

def test_append_to_existing_yml_preserves_original_content(tmp_path):
    yml = tmp_path / 'illustration.yml'
    yml.write_text(
        '---\nname: "illustration"\narts:\n'
        '- image: "images/galleries/illustration/01_old.png"\n'
        '  order: "1"\n  title: "Old"\n  artist: "Aaron Liu"\n  description: "tbc"\n---\n'
    )
    new_entries = [{
        'image': 'images/galleries/illustration/02_new.png',
        'order': '2', 'title': 'new', 'artist': 'Aaron Liu', 'description': 'tbc',
    }]
    append_entries_to_yml(yml, 'illustration', new_entries)
    content = yml.read_text()
    assert '01_old.png' in content
    assert '02_new.png' in content
    assert content.endswith('---\n')

def test_append_creates_new_yml_when_missing(tmp_path):
    yml = tmp_path / 'newgallery.yml'
    new_entries = [{
        'image': 'images/galleries/newgallery/01_photo.jpg',
        'order': '1', 'title': 'photo', 'artist': 'Aaron Liu', 'description': 'tbc',
    }]
    append_entries_to_yml(yml, 'newgallery', new_entries)
    content = yml.read_text()
    assert '01_photo.jpg' in content
    assert 'name: "newgallery"' in content

def test_append_preserves_comments_in_existing_yml(tmp_path):
    yml = tmp_path / 'illustration.yml'
    yml.write_text(
        '---\nname: "illustration"\narts:\n# Column 1\n'
        '- image: "old.png"\n  order: "1"\n  title: "t"\n  artist: "a"\n  description: "d"\n---\n'
    )
    new_entries = [{'image': 'new.png', 'order': '2', 'title': 't', 'artist': 'a', 'description': 'd'}]
    append_entries_to_yml(yml, 'illustration', new_entries)
    assert '# Column 1' in yml.read_text()
```

- [ ] **Step 10: Run tests to verify they fail**

```bash
pytest tests/test_sync_gallery.py -k "append_" -v
```
Expected: `ImportError`

- [ ] **Step 11: Implement `append_entries_to_yml`**

Add to `sync_gallery.py`:
```python
def append_entries_to_yml(yml_path: Path, gallery_name: str, new_entries: list) -> None:
    if yml_path.exists():
        content = yml_path.read_text(encoding='utf-8').rstrip()
        if content.endswith('---'):
            content = content[:-3].rstrip()
    else:
        content = f'---\nname: "{gallery_name}"\narts:'

    parts = [content]
    for entry in new_entries:
        parts.append(format_entry(entry))
    parts.append('---\n')

    yml_path.write_text('\n'.join(parts), encoding='utf-8')
```

- [ ] **Step 12: Run tests to verify they pass**

```bash
pytest tests/test_sync_gallery.py -k "append_" -v
```
Expected: 3 PASSED

- [ ] **Step 13: Write failing integration tests for `sync_gallery`**

Add to `tests/test_sync_gallery.py` (update imports to include `sync_gallery`):
```python
from sync_gallery import sync_gallery

def test_sync_gallery_renames_and_appends_new_image(tmp_path):
    images_base = tmp_path / 'images' / 'galleries'
    galleries_base = tmp_path / '_galleries'
    gallery_dir = images_base / 'illustration'
    gallery_dir.mkdir(parents=True)
    galleries_base.mkdir()
    (gallery_dir / 'new_photo.jpg').write_bytes(b'fake')
    (galleries_base / 'illustration.yml').write_text('---\nname: "illustration"\narts:\n---\n')

    changed = sync_gallery('illustration', images_base, galleries_base)

    assert changed is True
    assert (gallery_dir / '01_new_photo.jpg').exists()
    assert not (gallery_dir / 'new_photo.jpg').exists()
    content = (galleries_base / 'illustration.yml').read_text()
    assert '01_new_photo.jpg' in content
    assert 'Aaron Liu' in content
    assert '"tbc"' in content

def test_sync_gallery_returns_false_when_no_new_images(tmp_path):
    images_base = tmp_path / 'images' / 'galleries'
    galleries_base = tmp_path / '_galleries'
    gallery_dir = images_base / 'illustration'
    gallery_dir.mkdir(parents=True)
    galleries_base.mkdir()
    (gallery_dir / '01_existing.png').write_bytes(b'fake')
    (galleries_base / 'illustration.yml').write_text(
        '---\nname: "illustration"\narts:\n'
        '- image: "images/galleries/illustration/01_existing.png"\n'
        '  order: "1"\n  title: "t"\n  artist: "a"\n  description: "d"\n---\n'
    )
    assert sync_gallery('illustration', images_base, galleries_base) is False

def test_sync_gallery_uses_meta_file(tmp_path):
    images_base = tmp_path / 'images' / 'galleries'
    galleries_base = tmp_path / '_galleries'
    (images_base / 'illustration').mkdir(parents=True)
    galleries_base.mkdir()
    (images_base / 'illustration' / 'painting.jpg').write_bytes(b'fake')
    (galleries_base / 'illustration.yml').write_text('---\nname: "illustration"\narts:\n---\n')
    (galleries_base / 'illustration.meta.yml').write_text(
        'painting.jpg:\n  title: "My Painting"\n  description: "Oil on canvas"\n'
    )

    sync_gallery('illustration', images_base, galleries_base)

    content = (galleries_base / 'illustration.yml').read_text()
    assert 'My Painting' in content
    assert 'Oil on canvas' in content

def test_sync_gallery_assigns_sequential_orders_for_multiple_new_images(tmp_path):
    images_base = tmp_path / 'images' / 'galleries'
    galleries_base = tmp_path / '_galleries'
    gallery_dir = images_base / 'illustration'
    gallery_dir.mkdir(parents=True)
    galleries_base.mkdir()
    (gallery_dir / 'alpha.jpg').write_bytes(b'fake')
    (gallery_dir / 'beta.jpg').write_bytes(b'fake')
    (galleries_base / 'illustration.yml').write_text(
        '---\nname: "illustration"\narts:\n'
        '- image: "images/galleries/illustration/01_old.png"\n'
        '  order: "1"\n  title: "t"\n  artist: "a"\n  description: "d"\n---\n'
    )

    sync_gallery('illustration', images_base, galleries_base)

    content = (galleries_base / 'illustration.yml').read_text()
    assert '02_alpha.jpg' in content
    assert '03_beta.jpg' in content
```

- [ ] **Step 14: Run tests to verify they fail**

```bash
pytest tests/test_sync_gallery.py -k "sync_gallery" -v
```
Expected: `ImportError`

- [ ] **Step 15: Implement `sync_gallery` and `main`**

Add to `sync_gallery.py`:
```python
def sync_gallery(gallery_name: str, images_base: Path, galleries_base: Path) -> bool:
    gallery_dir = images_base / gallery_name
    yml_path = galleries_base / f'{gallery_name}.yml'
    meta_path = galleries_base / f'{gallery_name}.meta.yml'

    arts = load_yml_arts(yml_path)
    meta = load_meta(meta_path)
    existing = get_existing_filenames(arts)
    new_images = find_new_images(gallery_dir, existing)

    if not new_images:
        return False

    order = next_order(arts)
    new_entries = []
    for filename in new_images:
        new_filename = rename_image(gallery_dir, filename, order)
        new_entries.append(make_entry(gallery_name, new_filename, filename, order, meta))
        order += 1

    append_entries_to_yml(yml_path, gallery_name, new_entries)
    return True


def main():
    repo_root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('.')
    images_base = repo_root / 'images' / 'galleries'
    galleries_base = repo_root / '_galleries'

    if not images_base.exists():
        print(f'images/galleries/ not found in {repo_root}', file=sys.stderr)
        sys.exit(1)

    for gallery_dir in sorted(images_base.iterdir()):
        if not gallery_dir.is_dir():
            continue
        gallery_name = gallery_dir.name
        if not (galleries_base / f'{gallery_name}.yml').exists():
            continue
        if sync_gallery(gallery_name, images_base, galleries_base):
            print(f'Synced: {gallery_name}')


if __name__ == '__main__':
    main()
```

- [ ] **Step 16: Run all tests**

```bash
pytest tests/test_sync_gallery.py -v
```
Expected: All PASSED

- [ ] **Step 17: Commit**

```bash
git add .github/scripts/sync_gallery.py tests/test_sync_gallery.py
git commit -m "feat: add file I/O, renaming, and sync orchestration"
```

---

### Task 3: GitHub Action workflow

**Files:**
- Create: `.github/workflows/sync-gallery.yml`

**Interfaces:**
- Consumes: `.github/scripts/sync_gallery.py` (Task 2 `main()` entry point, called as `python .github/scripts/sync_gallery.py .`)

- [ ] **Step 1: Create `.github/workflows/sync-gallery.yml`**

```bash
mkdir -p /mnt/c/work/source/jason/aaron/arts/.github/workflows
```

Create `.github/workflows/sync-gallery.yml`:
```yaml
name: Sync Gallery

on:
  push:
    branches: [main]
    paths:
      - 'images/galleries/**'

jobs:
  sync:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install pyyaml

      - name: Run sync script
        run: python .github/scripts/sync_gallery.py .

      - name: Check for changes
        id: changes
        run: |
          if [ -z "$(git status --porcelain)" ]; then
            echo "changed=false" >> $GITHUB_OUTPUT
          else
            echo "changed=true" >> $GITHUB_OUTPUT
          fi

      - name: Create branch, commit, and open PR
        if: steps.changes.outputs.changed == 'true'
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          BRANCH="auto/gallery-sync-$(date +%Y%m%d-%H%M%S)"
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git checkout -b "$BRANCH"
          git add -A
          git commit -m "auto: sync gallery"
          git push origin "$BRANCH"
          gh pr create \
            --title "auto: sync gallery" \
            --body "Auto-generated by the gallery sync action.

Images have been renamed with order prefixes and YML entries appended with default values.

Review the diff — update any titles or descriptions directly in the YML before merging." \
            --base main \
            --head "$BRANCH"
```

- [ ] **Step 2: Verify the workflow YAML is valid**

```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/sync-gallery.yml'))" && echo "Valid YAML"
```
Expected: `Valid YAML`

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/sync-gallery.yml
git commit -m "feat: add GitHub Action to auto-sync gallery on image push"
```

- [ ] **Step 4: Push and verify the Action is registered**

```bash
git push origin main
```

Open `https://github.com/aaronliunz/arts/actions` — confirm "Sync Gallery" appears in the workflows list. It won't trigger on this push (no images changed), but the workflow should be visible.

- [ ] **Step 5: End-to-end smoke test**

Push one new test image to `images/galleries/illustration/` on `main`. Verify on GitHub Actions that:
1. The "Sync Gallery" workflow triggers
2. It completes successfully
3. A PR is opened with branch `auto/gallery-sync-<timestamp>`
4. The PR diff shows the renamed image file and the updated `_galleries/illustration.yml` with the new entry

---

## Spec Coverage

| Requirement | Task |
|---|---|
| Triggered on push to `main`, path `images/galleries/**` | Task 3 |
| Script scans all gallery subdirs | Task 2, `main()` |
| Loads matching `_galleries/<name>.yml` | Task 2, `load_yml_arts` |
| Loads optional `_galleries/<name>.meta.yml` | Task 2, `load_meta` |
| Diffs: finds images not in YML | Task 1, `find_new_images` |
| Sorts new images alphabetically | Task 1, `find_new_images` |
| Renames with zero-padded 2-digit prefix | Task 2, `rename_image` |
| YML entry uses meta values or defaults | Task 1, `make_entry` |
| Appends to YML without modifying existing content | Task 2, `append_entries_to_yml` |
| Creates branch `auto/gallery-sync-<YYYYMMDD-HHMMSS>` | Task 3 |
| Opens PR to main | Task 3 |
| Skips if no new images | Task 3, `changed` step |
| Default artist: `Aaron Liu` | Task 1, `make_entry` |
| Default description: `tbc` | Task 1, `make_entry` |
| Default title: filename without extension | Task 1, `make_entry` |
| Meta keyed by original filename (before rename) | Tasks 1–2, `make_entry` + `load_meta` |
| Meta file is never modified by Action | Task 3 (Action only reads meta) |
| Generic — new galleries auto-discovered | Task 2, `main()` |
