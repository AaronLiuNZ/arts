import base64
import json
import os
import re
import sys
import yaml
from PIL import Image


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
        self._client = anthropic.Anthropic()

    def analyze_image(self, image_path: str) -> dict:
        import anthropic
        ext = os.path.splitext(image_path)[1].lower()
        media_type = 'image/png' if ext == '.png' else 'image/jpeg'
        with open(image_path, 'rb') as f:
            data = base64.standard_b64encode(f.read()).decode()
        response = self._client.messages.create(
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
        self._client = openai.OpenAI()

    def analyze_image(self, image_path: str) -> dict:
        ext = os.path.splitext(image_path)[1].lower()
        media_type = 'image/png' if ext == '.png' else 'image/jpeg'
        with open(image_path, 'rb') as f:
            data = base64.standard_b64encode(f.read()).decode()
        response = self._client.chat.completions.create(
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
        self._model = genai.GenerativeModel('gemini-2.0-flash')

    def analyze_image(self, image_path: str) -> dict:
        from PIL import Image as PILImage
        img = PILImage.open(image_path)
        response = self._model.generate_content([PROMPT, img])
        return _parse_json(response.text)


def get_provider(name: str = None):
    if name == 'claude' or (name is None and os.environ.get('ANTHROPIC_API_KEY')):
        return ClaudeProvider()
    if name == 'openai' or (name is None and os.environ.get('OPENAI_API_KEY')):
        return OpenAIProvider()
    if name == 'gemini' or (name is None and os.environ.get('GEMINI_API_KEY')):
        return GeminiProvider()
    raise RuntimeError(
        'No LLM provider available. Set ANTHROPIC_API_KEY, OPENAI_API_KEY, or GEMINI_API_KEY.'
    )


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
