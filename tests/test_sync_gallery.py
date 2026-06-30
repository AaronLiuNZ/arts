from pathlib import Path
from sync_gallery import (
    get_existing_filenames,
    find_new_images,
    next_order,
    make_entry,
    format_entry,
    load_yml_arts,
    load_meta,
    rename_image,
    append_entries_to_yml,
    sync_gallery,
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


# --- load_yml_arts ---

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


# --- load_meta ---

def test_load_meta_parses_dict(tmp_path):
    meta = tmp_path / 'illustration.meta.yml'
    meta.write_text('IMG_001.png:\n  title: "My Art"\n  description: "Oil"\n')
    result = load_meta(meta)
    assert result['IMG_001.png']['title'] == 'My Art'
    assert result['IMG_001.png']['description'] == 'Oil'


def test_load_meta_returns_empty_for_missing_file(tmp_path):
    assert load_meta(tmp_path / 'missing.meta.yml') == {}


# --- rename_image ---

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


# --- append_entries_to_yml ---

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


# --- sync_gallery ---

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
