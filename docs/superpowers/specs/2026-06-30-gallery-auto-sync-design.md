# Gallery Auto-Sync Design

**Date:** 2026-06-30  
**Status:** Approved

## Problem

Adding images to a gallery requires two manual steps: copying the image into `images/galleries/<name>/` and then editing `_galleries/<name>.yml` to add the new entry. This is error-prone and easy to forget, leading to images sitting in the folder with no YML entry (and therefore not appearing on the site).

## Solution

A GitHub Action runs automatically whenever images are pushed to any folder under `images/galleries/`. A Python script diffs the folder contents against the YML and appends entries for any images not yet listed.

## Architecture

```
Push to main (images/galleries/**)
        │
        ▼
GitHub Action triggered (.github/workflows/sync-gallery.yml)
        │
        ▼
Python script: .github/scripts/sync_gallery.py
  1. Scan all subdirectories under images/galleries/
  2. For each folder, load matching _galleries/<name>.yml
  3. Diff: find images in folder not present in YML
  4. Sort new images alphabetically
  5. Append new entries with default values
  6. Write updated YML
        │
        ▼
Action commits "auto: sync gallery" back to main
(skipped via git diff --quiet if no changes)
```

## Files

| File | Purpose |
|---|---|
| `.github/workflows/sync-gallery.yml` | GitHub Action definition |
| `.github/scripts/sync_gallery.py` | Sync logic |

## Script Behaviour

**Scope:** Loops over every folder under `images/galleries/` and finds its matching `_galleries/<name>.yml`. Fully generic — new galleries are picked up automatically with no script changes.

**Supported image extensions:** `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`

**New entry defaults:**

| Field | Value |
|---|---|
| `image` | `images/galleries/<name>/<filename>` |
| `title` | Filename without extension (e.g. `IMG_9776.png` → `IMG_9776`) |
| `artist` | `Aaron Liu` |
| `description` | `tbc` |
| `order` | Max existing `order` value + 1, incrementing per new file |

**Ordering:** New images are sorted alphabetically before being appended, so order is deterministic across runs.

**Safety:** Existing entries are never modified or removed. The script is append-only.

## GitHub Action

```yaml
on:
  push:
    branches: [main]
    paths:
      - 'images/galleries/**'
```

Steps:
1. Checkout repo with write permissions
2. Run `sync_gallery.py`
3. If YML changed, commit with message `auto: sync gallery` and push to main

## Out of Scope

- Removing YML entries when images are deleted (manual cleanup)
- Reordering existing entries
- Syncing galleries other than those with a matching `_galleries/<name>.yml`
