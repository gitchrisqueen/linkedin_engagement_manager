import re


def sanitize_for_linkedin(text: str) -> str:
    """Strip markdown syntax from AI-generated text so it renders cleanly on LinkedIn.

    LinkedIn does not render standard markdown. This function removes formatting
    markers while preserving the underlying text, emojis, hashtags, and line breaks.
    """
    if not text:
        return text

    # Remove markdown headers (# through ######) at line start, keep the text
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)

    # Convert markdown unordered bullets (- item or * item at line start) → • item
    # Must run BEFORE italic stripping so "* item" isn't consumed by the italic regex
    text = re.sub(r"^[-*]\s+", "• ", text, flags=re.MULTILINE)

    # Remove horizontal rules (--- or *** or ___ on their own line)
    text = re.sub(r"^[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)

    # Remove bold markers (**text** or __text__)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"__(.+?)__", r"\1", text, flags=re.DOTALL)

    # Remove italic markers (*text* or _text_) — only single * not preceded/followed by *
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"(?<!_)_(?!_)(.+?)(?<!_)_(?!_)", r"\1", text, flags=re.DOTALL)

    # Convert markdown links [text](url) → text (url)
    text = re.sub(r"\[(.+?)\]\((.+?)\)", r"\1 (\2)", text)

    # Remove inline code backticks `code` → code
    text = re.sub(r"`(.+?)`", r"\1", text)

    # Convert numbered lists (1. item) → keep numbering but clean up spacing
    text = re.sub(r"^(\d+)\.\s+", r"\1. ", text, flags=re.MULTILINE)

    # Strip trailing whitespace on each line
    text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)

    # Normalize excessive blank lines (3 or more newlines → 2)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()
