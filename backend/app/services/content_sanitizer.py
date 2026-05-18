import re

from app.core.config import settings


def sanitize_content(text: str) -> str:
    s = text or ""
    emphasis_mode = (getattr(settings, "emphasis_mode", "") or "").strip().lower()

    # 1) Bold markers
    if emphasis_mode == "caps":
        s = re.sub(r"\*\*(.+?)\*\*", lambda m: m.group(1).upper(), s, flags=re.DOTALL)
    else:
        s = re.sub(r"\*\*(.+?)\*\*", r"\1", s, flags=re.DOTALL)

    # 2) Italic single markers
    s = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", s, flags=re.DOTALL)
    s = re.sub(r"(?<!_)_(?!_)(.+?)(?<!_)_(?!_)", r"\1", s, flags=re.DOTALL)

    # 3) Underline markers
    s = re.sub(r"__(.+?)__", r"\1", s, flags=re.DOTALL)

    # 4) Inline HTML/style tags
    s = re.sub(r"</?(span|b|i|u|color)(\s+[^>]*)?>", "", s, flags=re.IGNORECASE)
    s = re.sub(r"<[^>]+>", "", s)

    # 5) hashtag#word -> #word
    s = re.sub(r"\bhashtag#(\w+)", r"#\1", s, flags=re.IGNORECASE)

    # 7) collapse 3+ blank lines into 2
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def sanitize_post_payload(content: str, cta: str, title: str = "") -> tuple[str, str, str]:
    clean_content = sanitize_content(content)
    clean_cta = sanitize_content(cta)
    clean_title = sanitize_content(title)

    # 6) Duplicate CTA at end of content -> remove from content, keep in cta
    if clean_cta:
        c_norm = clean_content.rstrip()
        t_norm = clean_cta.strip()
        if c_norm.lower().endswith(t_norm.lower()):
            clean_content = c_norm[: len(c_norm) - len(t_norm)].rstrip()
            clean_content = re.sub(r"\n{3,}", "\n\n", clean_content).strip()

    return clean_content, clean_cta, clean_title
