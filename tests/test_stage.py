import os
import pytest
import yaml
from PIL import Image
from scripts.stage import append_meta, resize_image


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
