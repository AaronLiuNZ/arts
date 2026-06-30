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
