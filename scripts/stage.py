import base64
import json
import os
import re
import shutil
import sys
import yaml
from PIL import Image


SUPPORTED_EXTS = {'.jpg', '.jpeg', '.png'}
STAGE_DIR = 'images/stage'
GALLERIES_DIR = 'images/galleries'
RAW_DIR = 'images/raw'
GALLERIES_DATA_DIR = '_galleries'
META_SUFFIX = '.meta.yml'


PROMPT = (
    "You are writing metadata for an art portfolio. Given the artwork image, "
    "return a JSON object with exactly two fields:\n"
    '- "title": a short, evocative title for the artwork (max 10 words)\n'
    '- "description": 1-2 sentences describing the medium, style, and subject\n\n'
    "Return only valid JSON. No markdown, no extra text."
)


def _parse_json(text: str):
    text = re.sub(r'^```(?:json)?\s*', '', text.strip(), flags=re.MULTILINE)
    text = re.sub(r'```\s*$', '', text.strip(), flags=re.MULTILINE)
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        return None


class ClaudeProvider:
    def __init__(self):
        import anthropic
        self._anthropic = anthropic

    def analyze_image(self, image_path: str) -> dict:
        client = self._anthropic.Anthropic()
        ext = os.path.splitext(image_path)[1].lower()
        media_type = 'image/png' if ext == '.png' else 'image/jpeg'
        with open(image_path, 'rb') as f:
            data = base64.standard_b64encode(f.read()).decode()
        response = client.messages.create(
            model='claude-opus-4-8',
            max_tokens=256,
            messages=[{'role': 'user', 'content': [
                {'type': 'image', 'source': {'type': 'base64', 'media_type': media_type, 'data': data}},
                {'type': 'text', 'text': PROMPT},
            ]}],
        )
        return _parse_json(response.content[0].text)


class OpenAIProvider:
    def __init__(self):
        import openai
        self._openai = openai

    def analyze_image(self, image_path: str) -> dict:
        client = self._openai.OpenAI()
        ext = os.path.splitext(image_path)[1].lower()
        media_type = 'image/png' if ext == '.png' else 'image/jpeg'
        with open(image_path, 'rb') as f:
            data = base64.standard_b64encode(f.read()).decode()
        response = client.chat.completions.create(
            model='gpt-4o',
            max_tokens=256,
            messages=[{'role': 'user', 'content': [
                {'type': 'image_url', 'image_url': {'url': f'data:{media_type};base64,{data}'}},
                {'type': 'text', 'text': PROMPT},
            ]}],
        )
        return _parse_json(response.choices[0].message.content)


class GeminiProvider:
    def __init__(self):
        import google.generativeai as genai
        genai.configure(api_key=os.environ.get('GEMINI_API_KEY'))
        self._genai = genai

    def analyze_image(self, image_path: str) -> dict:
        model = self._genai.GenerativeModel('gemini-2.0-flash')
        from PIL import Image as PILImage
        img = PILImage.open(image_path)
        response = model.generate_content([PROMPT, img])
        return _parse_json(response.text)


def get_provider(name: str = None):
    if name == 'claude':
        if not os.environ.get('ANTHROPIC_API_KEY'):
            raise RuntimeError('ANTHROPIC_API_KEY is required for --provider claude')
        return ClaudeProvider()
    if name == 'openai':
        if not os.environ.get('OPENAI_API_KEY'):
            raise RuntimeError('OPENAI_API_KEY is required for --provider openai')
        return OpenAIProvider()
    if name == 'gemini':
        if not os.environ.get('GEMINI_API_KEY'):
            raise RuntimeError('GEMINI_API_KEY is required for --provider gemini')
        return GeminiProvider()
    if name is None:
        if os.environ.get('ANTHROPIC_API_KEY'):
            return ClaudeProvider()
        if os.environ.get('OPENAI_API_KEY'):
            return OpenAIProvider()
        if os.environ.get('GEMINI_API_KEY'):
            return GeminiProvider()
    raise RuntimeError(
        'No LLM provider available. Set ANTHROPIC_API_KEY, OPENAI_API_KEY, or GEMINI_API_KEY.'
    )


def process_gallery(gallery: str, provider=None, no_llm: bool = False) -> None:
    stage_path = os.path.join(STAGE_DIR, gallery)
    if not os.path.isdir(stage_path):
        print(f'  No stage folder: {stage_path}')
        return

    images = sorted(
        f for f in os.listdir(stage_path)
        if os.path.splitext(f)[1].lower() in SUPPORTED_EXTS
    )
    if not images:
        print(f'  No staged images in {stage_path}')
        return

    gallery_out = os.path.join(GALLERIES_DIR, gallery)
    raw_out = os.path.join(RAW_DIR, gallery)
    meta_path = os.path.join(GALLERIES_DATA_DIR, f'{gallery}{META_SUFFIX}')
    os.makedirs(gallery_out, exist_ok=True)
    os.makedirs(raw_out, exist_ok=True)

    for filename in images:
        src = os.path.join(stage_path, filename)
        dst = os.path.join(gallery_out, filename)
        archive = os.path.join(raw_out, filename)
        stem = os.path.splitext(filename)[0]

        print(f'  {filename}')

        resize_image(src, dst)
        print(f'    resized → {dst}')

        if not no_llm and provider is not None:
            try:
                result = provider.analyze_image(dst)
                title = result.get('title', stem) if result else stem
                description = result.get('description', 'tbc') if result else 'tbc'
            except Exception as e:
                print(f'    LLM warning: {e}')
                title, description = stem, 'tbc'
        else:
            title, description = stem, 'tbc'

        appended = append_meta(meta_path, filename, title, description)
        if appended:
            print(f'    meta: {title!r}')
        else:
            print(f'    meta: already exists, skipped')

        shutil.move(src, archive)
        print(f'    archived → {archive}')


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Stage images for the gallery pipeline.')
    parser.add_argument('--gallery', help='Process only this gallery (default: all)')
    parser.add_argument('--provider', choices=['claude', 'openai', 'gemini'],
                        help='LLM provider (default: auto-detect from env)')
    parser.add_argument('--no-llm', action='store_true',
                        help='Skip LLM calls (resize + archive only)')
    args = parser.parse_args()

    provider = None
    if not args.no_llm:
        try:
            provider = get_provider(args.provider)
            print(f'Provider: {type(provider).__name__}')
        except RuntimeError as e:
            print(f'Warning: {e}')
            print('Continuing without LLM metadata (use --no-llm to suppress this warning).')

    if args.gallery:
        galleries = [args.gallery]
    else:
        if not os.path.isdir(STAGE_DIR):
            print(f'Stage directory not found: {STAGE_DIR}')
            print('Create images/stage/<gallery-name>/ and drop images there.')
            sys.exit(0)
        galleries = sorted(
            d for d in os.listdir(STAGE_DIR)
            if os.path.isdir(os.path.join(STAGE_DIR, d))
        )
        if not galleries:
            print('No gallery subfolders found in images/stage/')
            sys.exit(0)

    for gallery in galleries:
        print(f'Gallery: {gallery}')
        process_gallery(gallery, provider=provider, no_llm=args.no_llm)


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


def append_meta(meta_path: str, filename: str, title: str, description: str) -> bool:
    data = {}
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            data = yaml.safe_load(f) or {}
    if filename in data:
        return False
    data[filename] = {'title': title, 'description': description}
    with open(meta_path, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
    return True


if __name__ == '__main__':
    main()
