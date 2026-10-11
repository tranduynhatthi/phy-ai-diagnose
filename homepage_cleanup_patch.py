"""Remove homepage marketing without removing the authentication section."""

from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path


ROLE_HEADING = "Hai không gian làm việc, một hệ thống dữ liệu"
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


@dataclass
class Element:
    tag: str
    attrs: dict
    start: int
    end: int = 0
    text: list = field(default_factory=list)


class HomepageParser(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.html = html
        self.lines = [0]
        for line in html.splitlines(keepends=True):
            self.lines.append(self.lines[-1] + len(line))
        self.stack = []
        self.elements = []
        self.feed(html)

    def source_offset(self):
        line, column = self.getpos()
        return self.lines[line - 1] + column

    def handle_starttag(self, tag, attrs):
        if tag not in VOID_TAGS:
            element = Element(tag, dict(attrs), self.source_offset())
            self.stack.append(element)
            self.elements.append(element)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index].tag == tag:
                self.stack[index].end = self.html.find(">", self.source_offset()) + 1
                del self.stack[index:]
                break

    def handle_data(self, data):
        for element in self.stack:
            element.text.append(data)


def cleanup_homepage(html):
    parser = HomepageParser(html)
    auth = next((e for e in parser.elements if e.attrs.get("id") == "authView"), None)
    if auth is None or not auth.end:
        raise ValueError("Homepage must retain a complete authView section")
    removals = []
    for element in parser.elements:
        if not (auth.start < element.start < element.end < auth.end):
            continue
        classes = element.attrs.get("class", "").split()
        text = " ".join("".join(element.text).split())
        role_marketing = (
            element.tag == "h2" and text == ROLE_HEADING
            or element.tag == "p" and "landing-section-sub" in classes
            or element.tag == "div" and "role-preview" in classes
        )
        long_description = (
            element.tag in {"p", "div"}
            and text.startswith("PHY-AI DIAGNOSE giúp học sinh")
            and text.endswith("dashboard thống nhất.")
        )
        if role_marketing or long_description:
            removals.append((element.start, element.end))
    # Ignore nested matches so offsets stay valid when removing whole elements.
    selected = []
    for start, end in sorted(removals):
        if not selected or start >= selected[-1][1]:
            selected.append((start, end))
    for start, end in reversed(selected):
        html = html[:start] + html[end:]
    return html


def apply_patch(root=Path("/app")):
    frontend = Path(root) / "app/static/index.html"
    html = cleanup_homepage(frontend.read_text(encoding="utf-8"))
    frontend.write_text(html, encoding="utf-8")


if __name__ == "__main__":
    apply_patch()
