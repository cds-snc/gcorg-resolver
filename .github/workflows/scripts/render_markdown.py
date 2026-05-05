#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "markdown-it-py>=3.0.0",
#     "jinja2>=3.0.0",
# ]
# ///

"""
Converts Markdown READMEs into GCDS-style HTML pages.

OVERVIEW
    Reads one or more Markdown files, converts them to HTML using GC Design
    System web components (gcds-*), and renders the result into a Jinja2
    HTML template. Output files are written to the paths defined in PAGES.

    Each page requires:
        - a Markdown file (md_path)
        - a TOML config file (config_path)
        - an output path (output_path)

    All pages share a single Jinja2 template (TEMPLATE_PATH).

TEMPLATE VARIABLES
    The following variables are available in the Jinja2 template:

        config.lang               Language code, e.g. "en" or "fr"
        config.title              Page title
        config.description        Meta description for SEO
        config.lang_toggle_href   URL for the language toggle link in the header
        config.breadcrumbs        List of (label, href) tuples
        config.date_modified      Today's date in YYYY-MM-DD format (auto-set)
        config.footer_heading     Contextual footer heading
        config.footer_links       Dict of label -> href for the contextual footer
        body                      Rendered HTML body content from the Markdown file

MARKDOWN CONVERSION
    Markdown elements are mapped to GC Design System components where possible:

        # Heading       ->  <gcds-heading tag="h1">
        ## Heading      ->  <gcds-heading tag="h2">
        paragraph       ->  <gcds-text>
        [link](url)     ->  <gcds-link href="url">
        code block      ->  <pre><code>
        image           ->  <img>
        list            ->  <ul> or <ol>

    Raw HTML blocks in the Markdown are passed through unchanged.
    Bare URLs are linkified automatically.

    Language toggle links at the top of each README (i.e., links to README.md
    or README_fr.md) are stripped before conversion, as language switching is
    handled by the template.

DATE MODIFIED
    The date_modified field in each TOML config file is automatically
    overwritten with today's date on every run. This keeps the config file
    and the rendered HTML in sync.

DEPENDENCIES
    markdown-it-py>=3.0.0
    jinja2>=3.0.0
    tomllib (standard library, Python 3.11+)
"""

import tomllib
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from markdown_it import MarkdownIt

# --- Pages ---
# Add one dict per page to render.

GITHUB_URL = "https://github.com/your-org/gcorg-resolver"

BASE_PATH = Path(__file__).resolve().parents[3]
STATIC_PATH = BASE_PATH / "src/gcorg_resolver/static"
TEMPLATE_PATH = STATIC_PATH / "gcds_template.html"

PAGES = [
    {
        "md_path": BASE_PATH / "README.md",
        "config_path": STATIC_PATH / "index_en.toml",
        "output_path": STATIC_PATH / "index_en.html",
    },
    {
        "md_path": BASE_PATH / "README_fr.md",
        "config_path": STATIC_PATH / "index_fr.toml",
        "output_path": STATIC_PATH / "index_fr.html",
    },
]

# --- File loading and template setup ---


# Load the Markdown file as a string with the right encoding
def load_markdown(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


# Load the TOML config file and return a dict.
# Processes the breadcrumbs (i.e., the link path) as a list of (label, href) tuples
def load_config(path: str) -> dict:
    with open(path, "rb") as f:
        config = tomllib.load(f)
    config["breadcrumbs"] = [
        (b["label"], b["href"]) for b in config.get("breadcrumbs", [])
    ]
    return config


# Load the HTML template - this is a Jinja-fied version of the GCDS starter template
# See: https://design-system.canada.ca/en/page-templates/basic/
def load_template(template_path: str):
    path = Path(template_path)
    env = Environment(
        loader=FileSystemLoader(str(path.parent)),
        autoescape=False,
    )
    return env.get_template(path.name)


# --- Markdown parsing and rendering ---


def parse_markdown(md_text: str) -> str:
    md = MarkdownIt().enable("linkify")
    tokens = md.parse(md_text)
    return tokens_to_gcds(tokens)


# This turns Markdown into GCDS-style web components. It handles a minimal set of
# components for now, but can be exanded as more bits and pieces are needed.
def tokens_to_gcds(tokens: list) -> str:
    output = []
    i = 0

    while i < len(tokens):
        token = tokens[i]

        if token.type == "heading_open":
            tag = token.tag
            inline = tokens[i + 1]
            text = render_inline(inline.children)
            output.append(f'<gcds-heading tag="{tag}">{text}</gcds-heading>')
            i += 3

        elif token.type == "paragraph_open":
            inline = tokens[i + 1]
            text = render_inline(inline.children)
            output.append(f"<gcds-text>{text}</gcds-text>")
            i += 3

        elif token.type == "fence":
            lang = token.info.strip()
            code = token.content.rstrip()
            lang_attr = f' class="language-{lang}"' if lang else ""
            output.append(f"<pre><code{lang_attr}>{escape(code)}</code></pre>")
            i += 1

        elif token.type == "bullet_list_open":
            items, consumed = render_list(tokens, i, ordered=False)
            output.append(items)
            i += consumed

        elif token.type == "ordered_list_open":
            items, consumed = render_list(tokens, i, ordered=True)
            output.append(items)
            i += consumed

        elif token.type == "hr":
            output.append("<hr>")
            i += 1

        elif token.type == "html_block":
            output.append(token.content.strip())
            i += 1

        else:
            i += 1

    return "\n".join(output)


# This renders the inline content of a Markdown token, like text, links, etc
# It returns a string of GCDS-like HTML. Right now, it doesn't work with nested
# formatting. That's probably a TODO.


def render_inline(children: list) -> str:
    parts = []
    for child in children:
        if child.type == "text":
            parts.append(escape(child.content))
        elif child.type == "softbreak":
            parts.append(" ")
        elif child.type == "hardbreak":
            parts.append("<br>")
        elif child.type == "code_inline":
            parts.append(f"<code>{escape(child.content)}</code>")
        elif child.type == "strong_open":
            parts.append("<strong>")
        elif child.type == "strong_close":
            parts.append("</strong>")
        elif child.type == "em_open":
            parts.append("<em>")
        elif child.type == "em_close":
            parts.append("</em>")
        elif child.type == "link_open":
            attrs = dict(child.attrs) if child.attrs else {}
            href = attrs.get("href", "#")
            parts.append(f'<gcds-link href="{href}">')
        elif child.type == "link_close":
            parts.append("</gcds-link>")
        elif child.type == "image":
            attrs = dict(child.attrs) if child.attrs else {}
            src = attrs.get("src", "")
            alt = child.children[0].content if child.children else ""
            parts.append(f'<img src="{src}" alt="{escape(alt)}">')
    return "".join(parts)


# This renders a Markdown list (ordered or unordered) and any nested lists it contains.
def render_list(tokens: list, start: int, ordered: bool) -> tuple[str, int]:
    tag = "ol" if ordered else "ul"
    close_type = "ordered_list_close" if ordered else "bullet_list_close"
    parts = [f"<{tag}>"]
    i = start + 1
    consumed = 2

    while i < len(tokens) and tokens[i].type != close_type:
        token = tokens[i]
        if token.type == "list_item_open":
            parts.append("<li>")
        elif token.type == "list_item_close":
            parts.append("</li>")
        elif token.type == "inline":
            parts.append(render_inline(token.children))
        elif token.type in ("bullet_list_open", "ordered_list_open"):
            nested, nested_consumed = render_list(
                tokens, i, token.type == "ordered_list_open"
            )
            parts.append(nested)
            i += nested_consumed
            consumed += nested_consumed
            continue
        i += 1
        consumed += 1

    parts.append(f"</{tag}>")
    return "\n".join(parts), consumed


# Escapes special HTML characters in text so we don't break something
def escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


# The README files contain links to the READMEs in the other official language. This
# is handled by the GCDS page (in the top right corner), so we don't need to render
# them ourselves. This function strips out any lines that look like language toggles
# (e.g. README.md, README_fr.md) and replaces them with a link back to the original
# Github repository.
def replace_language_toggle_with_github_link(md_text: str, lang: str) -> str:
    github_link_en = f"[View this project on GitHub]({GITHUB_URL})"
    github_link_fr = f"[Voir ce projet sur GitHub]({GITHUB_URL})"
    github_link = github_link_en if lang == "en" else github_link_fr

    lines = md_text.splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith("[") and (
            "README_fr.md" in line or "README.md" in line
        ):
            lines[i] = github_link
            break
    return "\n".join(lines)


# Updates the TOML file with today's date for date_modified
def update_config_date(config_path: Path, today: str):
    """Rewrite the date_modified field in the TOML file."""
    content = config_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("date_modified"):
            lines[i] = f'date_modified = "{today}"'
            break
    config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# The main conversion function - this is called once per page defined in PAGES.
# We'll iterate through pages with this function to create multiple docs.
def convert(page: dict, template):
    today = date.today().isoformat()
    update_config_date(page["config_path"], today)
    config = load_config(page["config_path"])
    md_text = replace_language_toggle_with_github_link(
        load_markdown(page["md_path"]), config["lang"]
    )
    body = parse_markdown(md_text)
    html = template.render(body=body, config=config)
    Path(page["output_path"]).write_text(html, encoding="utf-8")
    print(f"Written to {page['output_path']}")


if __name__ == "__main__":
    template = load_template(TEMPLATE_PATH)
    for page in PAGES:
        convert(page, template)
