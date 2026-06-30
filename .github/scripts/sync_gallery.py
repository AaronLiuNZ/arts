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
