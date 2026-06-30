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
