import pytest
from pathlib import Path
from sync_gallery import (
    get_existing_filenames,
    find_new_images,
    next_order,
    make_entry,
    format_entry,
)


def test_get_existing_filenames_empty():
    assert get_existing_filenames([]) == set()


def test_get_existing_filenames_extracts_basename():
    arts = [
        {'image': 'images/galleries/illustration/01_IMG_001.png', 'order': '1'},
        {'image': 'images/galleries/illustration/02_IMG_002.jpg', 'order': '2'},
    ]
    assert get_existing_filenames(arts) == {'01_IMG_001.png', '02_IMG_002.jpg'}


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


def test_next_order_empty_list():
    assert next_order([]) == 1


def test_next_order_returns_max_plus_one():
    arts = [{'order': '3'}, {'order': '1'}, {'order': '5'}]
    assert next_order(arts) == 6


def test_next_order_handles_string_orders():
    assert next_order([{'order': '13'}]) == 14


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
