import re
from typing import Match, Optional, Tuple

italic = re.compile(r"([\s>~*]|^)_(.+?)_([^a-zA-Z\d]|$)")
bold = re.compile(r"([\s>_~]|^)\*(.+?)\*([^a-zA-Z\d]|$)")
strike = re.compile(r"([\s>_*]|^)~(.+?)~([^a-zA-Z\d]|$)")
code_block = re.compile("```((?:.|\n)+?)```")


def code_block_repl(match: Match) -> str:
    text = match.group(1)
    if "\n" in text:
        return f"<pre><code>{text}</code></pre>"
    return f"<code>{text}</code>"


def whatsapp_to_matrix(text: str) -> Tuple[Optional[str], str]:
    # Change the format of the text to be compatible with matrix
    html = italic.sub(r"\1<em>\2</em>\3", text)
    html = bold.sub(r"\1<strong>\2</strong>\3", html)
    html = strike.sub(r"\1<del>\2</del>\3", html)
    html = code_block.sub(code_block_repl, html)
    if html != text:
        return html.replace("\n", "<br/>"), text
    return None, text
