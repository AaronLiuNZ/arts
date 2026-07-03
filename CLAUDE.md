# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

This is Aaron Liu's art portfolio site built on the **Starving Artist Jekyll Theme** — a Jekyll-based static site for displaying image galleries, blog posts, and artist information. It is deployed to GitHub Pages at `https://aaronliunz.github.io/arts`.

## Commands

```bash
# Install dependencies
bundle install

# Local development (watches for changes, uses localhost config)
bundle exec rake watch
# or directly:
bundle exec jekyll serve --config '_config.yml,_config_localhost.yml' --watch

# Production build
bundle exec rake build

# Build the gem theme (if working on the theme itself)
bundle exec rake buildgem
bundle exec rake releasegem
```

Browse the local dev server at `http://localhost:4000`.

## Architecture

**Jekyll site** using the `starving-artist-jekyll-theme` gem. All theme files (layouts, includes, base sass) come from the gem; this repo holds the content and local overrides.

### Key directories

- `_galleries/` — YAML data files defining each gallery (e.g. `covers.yml`, `illustration.yml`). Each file has a `name:` field and an `arts:` list with `image`, `order`, `artist`, `title`, `description` per entry. The `name:` must match the page slug for "active" nav highlighting to work.
- `_data/` — Navigation and social link definitions (`horiznav.yml`, `nav.yml`, `socials.yml`, etc.) consumed by includes.
- `_pages/` — Static pages (about, blog, contact, gallery index pages). Included in the Jekyll build via `include: ['_pages']` in `_config.yml`.
- `_posts/` — Blog posts following standard Jekyll naming (`YYYY-MM-DD-title.md`).
- `_layouts/` and `_includes/` — Override files for the gem theme. Additions here take precedence over the gem's versions.
- `_sass/` — SCSS partials. `_starving-artist.scss` is the main entry point; `_variables.scss` holds theme variables to override.
- `css/` — Compiled CSS output target.
- `images/` — Site images; gallery images live under `images/galleries/<gallery-name>/`.

### Config split

- `_config.yml` — Production config (GitHub Pages URL, analytics, SEO).
- `_config_localhost.yml` — Overrides for local dev (sets `url` to `http://localhost:4000`, disables asset cache).

### Gallery workflow

To add a new gallery: create `_galleries/<name>.yml` with a `name:` field and `arts:` list, create a corresponding page in `_pages/`, add images to `images/galleries/<name>/`, and add a nav entry to `_data/horiznav.yml`.

### Contact form

Uses Formspree (configured via `contact_form` in `_config.yml`). No server-side code required.
