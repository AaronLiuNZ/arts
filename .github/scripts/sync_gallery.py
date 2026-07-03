import shutil
import sys
from pathlib import Path

import yaml

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
DEFAULT_ARTIST = 'Aaron Liu'
DEFAULT_DESCRIPTION = 'tbc'


def get_existing_filenames(arts: list) -> set:
    return {Path(entry['image']).name for entry in arts}


def find_new_images(gallery_dir: Path, existing: set) -> list:
    images = [
        f.name for f in gallery_dir.iterdir()
        if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS and f.name not in existing
    ]
    return sorted(images)


def next_order(arts: list) -> int:
    if not arts:
        return 1
    return max(int(entry.get('order', 0)) for entry in arts) + 1


def make_entry(gallery_name: str, new_filename: str, original_filename: str, order: int, meta: dict) -> dict:
    image_meta = meta.get(original_filename, {})
    return {
        'image': f'images/galleries/{gallery_name}/{new_filename}',
        'order': str(order),
        'title': image_meta.get('title', Path(original_filename).stem),
        'artist': image_meta.get('artist', DEFAULT_ARTIST),
        'description': image_meta.get('description', DEFAULT_DESCRIPTION),
    }


def format_entry(entry: dict) -> str:
    return (
        f'- image: "{entry["image"]}"\n'
        f'  order: "{entry["order"]}"\n'
        f'  title: "{entry["title"]}"\n'
        f'  artist: "{entry["artist"]}"\n'
        f'  description: "{entry["description"]}"'
    )


def load_yml_arts(yml_path: Path) -> list:
    if not yml_path.exists():
        return []
    with open(yml_path, encoding='utf-8') as f:
        data = next(yaml.safe_load_all(f), None)
    if not data or 'arts' not in data:
        return []
    return data['arts'] or []


def load_meta(meta_path: Path) -> dict:
    if not meta_path.exists():
        return {}
    with open(meta_path, encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return data or {}


def rename_image(gallery_dir: Path, filename: str, order: int) -> str:
    new_name = f'{order:02d}_{filename}'
    shutil.move(str(gallery_dir / filename), str(gallery_dir / new_name))
    return new_name


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
