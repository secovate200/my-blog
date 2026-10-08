import json
import re
from html import escape
from html.parser import HTMLParser
from urllib.parse import urlparse


ALLOWED_BLOCKS = {
    "paragraph", "header", "list", "quote", "checklist", "table", "warning",
    "embed", "video", "linkCard", "code", "delimiter", "image", "attaches",
}
ALLOWED_INLINE_TAGS = {"a", "b", "br", "code", "em", "i", "mark", "s", "strong", "u"}


def _safe_href(value):
    parsed = urlparse(value.strip())
    return value.strip() if parsed.scheme in {"http", "https", "mailto"} else ""


def _safe_asset_url(value, endpoint):
    parsed = urlparse(str(value or ""))
    pattern = rf"^/blog/assets/[0-9a-f-]+/{endpoint}/$"
    return value if parsed.scheme in {"", "http", "https"} and re.match(pattern, parsed.path) else ""


def _non_negative_int(value):
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _safe_embed_url(value):
    parsed = urlparse(str(value or "").strip())
    allowed_hosts = {
        "www.youtube.com", "youtube.com", "player.vimeo.com", "codepen.io",
        "www.youtube-nocookie.com", "coub.com", "www.instagram.com",
        "platform.twitter.com", "twitframe.com", "i.imgur.com",
    }
    return parsed.geturl() if parsed.scheme == "https" and parsed.hostname in allowed_hosts else ""


def _safe_video_source(value):
    parsed = urlparse(str(value or "").strip())
    allowed_hosts = {"youtube.com", "www.youtube.com", "youtu.be", "vimeo.com", "www.vimeo.com"}
    return parsed.geturl() if parsed.scheme in {"http", "https"} and parsed.hostname in allowed_hosts else ""


class InlineHTMLSanitizer(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.output = []

    def handle_starttag(self, tag, attrs):
        if tag not in ALLOWED_INLINE_TAGS:
            return
        attributes = ""
        if tag == "a":
            href = _safe_href(dict(attrs).get("href", ""))
            if href:
                attributes = (
                    f' href="{escape(href, quote=True)}"'
                    ' target="_blank" rel="noopener noreferrer"'
                )
        self.output.append(f"<{tag}{attributes}>")

    def handle_endtag(self, tag):
        if tag in ALLOWED_INLINE_TAGS and tag != "br":
            self.output.append(f"</{tag}>")

    def handle_data(self, data):
        self.output.append(escape(data))

    def get_html(self):
        return "".join(self.output)


def sanitize_inline_html(value):
    sanitizer = InlineHTMLSanitizer()
    sanitizer.feed(str(value or ""))
    sanitizer.close()
    html = sanitizer.get_html()
    return re.sub(r"^(?:\s*<br>\s*)+|(?:\s*<br>\s*)+$", "", html, flags=re.IGNORECASE)


def _sanitize_list_items(items, checklist=False):
    cleaned = []
    for item in items if isinstance(items, list) else []:
        if isinstance(item, str):
            cleaned.append(sanitize_inline_html(item))
        elif isinstance(item, dict):
            cleaned.append(
                {
                    "content": sanitize_inline_html(item.get("content", "")),
                    "meta": {"checked": bool(item.get("meta", {}).get("checked"))} if checklist else {},
                    "items": _sanitize_list_items(item.get("items", []), checklist=checklist),
                }
            )
    return cleaned


def _sanitize_block(block):
    block_type = block.get("type")
    data = block.get("data", {})
    heading_match = re.fullmatch(r"heading([1-6])", str(block_type or ""))
    if heading_match:
        data = {**data, "level": int(heading_match.group(1))}
        block_type = "header"
    if block_type not in ALLOWED_BLOCKS or not isinstance(data, dict):
        return None

    if block_type == "paragraph":
        cleaned_data = {"text": sanitize_inline_html(data.get("text", ""))}
    elif block_type == "header":
        level = data.get("level", 2)
        cleaned_data = {
            "text": sanitize_inline_html(data.get("text", "")),
            "level": level if level in {1, 2, 3, 4, 5, 6} else 2,
        }
    elif block_type == "list":
        style = data.get("style") if data.get("style") in {"ordered", "unordered", "checklist"} else "unordered"
        cleaned_data = {
            "style": style,
            "meta": {},
            "items": _sanitize_list_items(data.get("items", []), checklist=style == "checklist"),
        }
    elif block_type == "quote":
        cleaned_data = {
            "text": sanitize_inline_html(data.get("text", "")),
            "caption": sanitize_inline_html(data.get("caption", "")),
            "alignment": data.get("alignment") if data.get("alignment") in {"left", "center"} else "left",
        }
    elif block_type == "checklist":
        cleaned_data = {
            "items": [
                {
                    "text": sanitize_inline_html(item.get("text", "")),
                    "checked": bool(item.get("checked")),
                }
                for item in data.get("items", [])
                if isinstance(item, dict)
            ]
        }
    elif block_type == "table":
        cleaned_data = {
            "withHeadings": bool(data.get("withHeadings")),
            "stretched": bool(data.get("stretched")),
            "content": [
                [sanitize_inline_html(cell) for cell in row]
                for row in data.get("content", [])
                if isinstance(row, list)
            ],
        }
    elif block_type == "warning":
        cleaned_data = {
            "title": sanitize_inline_html(data.get("title", "")),
            "message": sanitize_inline_html(data.get("message", "")),
        }
    elif block_type == "embed":
        embed_url = _safe_embed_url(data.get("embed", ""))
        if not embed_url:
            return None
        cleaned_data = {
            "service": str(data.get("service", ""))[:30],
            "source": _safe_href(data.get("source", "")),
            "embed": embed_url,
            "width": _non_negative_int(data.get("width", 0)),
            "height": _non_negative_int(data.get("height", 0)),
            "caption": sanitize_inline_html(data.get("caption", "")),
        }
    elif block_type == "video":
        source = _safe_video_source(data.get("url", ""))
        if not source:
            return None
        cleaned_data = {
            "url": source,
            "caption": sanitize_inline_html(data.get("caption", "")),
        }
    elif block_type == "linkCard":
        url = _safe_href(data.get("url", ""))
        if not url:
            return None
        cleaned_data = {
            "url": url,
            "title": sanitize_inline_html(data.get("title", "")),
            "description": sanitize_inline_html(data.get("description", "")),
        }
    elif block_type == "code":
        cleaned_data = {"code": str(data.get("code", ""))}
    elif block_type == "image":
        url = _safe_asset_url(data.get("file", {}).get("url", ""), "content")
        if not url:
            return None
        cleaned_data = {
            "file": {"url": url},
            "caption": sanitize_inline_html(data.get("caption", "")),
            "withBorder": bool(data.get("withBorder")),
            "withBackground": bool(data.get("withBackground")),
            "stretched": bool(data.get("stretched")),
        }
    elif block_type == "attaches":
        file_data = data.get("file", {})
        url = _safe_asset_url(file_data.get("url", ""), "download")
        if not url:
            return None
        cleaned_data = {
            "file": {
                "url": url,
                "name": str(file_data.get("name", "첨부파일"))[:255],
                "size": _non_negative_int(file_data.get("size", 0)),
                "extension": str(file_data.get("extension", ""))[:10],
            },
            "title": sanitize_inline_html(data.get("title", "")),
        }
    else:
        cleaned_data = {}
    return {"type": block_type, "data": cleaned_data}


def sanitize_content(value):
    """Editor.js JSON을 허용된 블록과 안전한 인라인 서식으로 제한합니다."""
    try:
        document = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return value
    if not isinstance(document, dict) or not isinstance(document.get("blocks"), list):
        return value

    blocks = []
    for block in document["blocks"]:
        if isinstance(block, dict):
            cleaned = _sanitize_block(block)
            if cleaned:
                blocks.append(cleaned)
    cleaned_document = {
        "time": document.get("time"),
        "blocks": blocks,
        "version": str(document.get("version", "")),
    }
    return json.dumps(cleaned_document, ensure_ascii=False, separators=(",", ":"))
