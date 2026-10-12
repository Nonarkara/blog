#!/usr/bin/env python3
"""Keep private diary material out of the public tree.

The WordPress site had 126 posts. This reading copy keeps the essays that
were written for a public reader. It drops entries whose subject is a private
person, a family member, a medical episode, personal money, or a home, and it
strips those details when they sit inside an essay that otherwise stays.

Does not rewrite git history. A rebuild should call apply() after render.
"""

from __future__ import annotations

import json
import re
import shutil
from html import escape, unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Slugs withheld from the public tree. A rebuild must not write them back.
WITHHELD_SLUGS = {
    "day-15-all-about-nana",
    "day-20-my-cousin-or-on-education",
    "day-41-all-about-nana-part-2",
    "day-66-on-a-failed-relationship-i-thought-i-was-lucky",
    "124-the-only-thing-that-matters",
    "125-fragments-chapter-1",
    "designated-survivor-bangkok",
}

NOTE = "<p><em>[A private detail was removed from this public copy.]</em></p>"
INLINE = "<em>[A private detail was removed from this public copy.]</em>"
PHOTO_NOTE = "<p><em>[A private photograph was removed from this public copy.]</em></p>"

PRIVATE_IMAGE = re.compile(
    r"("
    r"\bmy father\b|\bmy mother\b|\bmy brother\b|\bmy (?:little )?cousin\b|"
    r"\bmy family\b(?!\s+or\b)|\bgrandmother\b|"
    r"\bjohnnie\b|\bwith john\b|\bfuneral\b|"
    r"nancy royal|my colleagues"
    r")",
    re.I,
)
IMAGE_KEEP = ("lennon", "oliver", "locke", "john maeda", "thermos", "montblanc", "fieldnote")

# Residence sentence in the Shanghai margin, three languages.
RESIDENCE = [
    " He lived at Jing’an Villa, near Nanjing West Road.",
    " He lived at Jing'an Villa, near Nanjing West Road.",
    " เขาอยู่ที่จิงอันวิลลา ใกล้ถนนหนานจิงตะวันตก",
    "他住在静安别墅，靠近南京西路。",
]


def is_private_image(text: str) -> bool:
    t = unescape(text or "")
    low = t.lower()
    if any(k in low for k in IMAGE_KEEP):
        return False
    return bool(PRIVATE_IMAGE.search(t))


def _figure_text(block: str) -> str:
    cap = re.search(r"<figcaption>(.*?)</figcaption>", block, re.S)
    alts = " ".join(re.findall(r'alt="([^"]*)"', block))
    raw = (cap.group(1) if cap else "") + " " + alts
    return unescape(re.sub(r"<[^>]+>", " ", raw))


def strip_figures(html: str) -> str:
    def repl(m: re.Match) -> str:
        block = m.group(0)
        if is_private_image(_figure_text(block)):
            return PHOTO_NOTE
        return block

    return re.sub(r"<figure\b[^>]*>.*?</figure>", repl, html, flags=re.S)


def strip_private_imgs(html: str) -> str:
    def repl(m: re.Match) -> str:
        alt = unescape(m.group(1) or "")
        if is_private_image(alt):
            return ""
        return m.group(0)

    return re.sub(r"<img\b[^>]*alt=\"([^\"]*)\"[^>]*/?\s*>", repl, html, flags=re.S)


def subn(pattern: str, repl: str, html: str, flags: int = 0) -> tuple[str, int]:
    new, n = re.subn(pattern, repl, html, flags=flags)
    return new, n


def redact_phrases(html: str) -> tuple[str, int]:
    n = 0
    edits = [
        # Home: the margin named a residence. Fieldwork dates stay.
        (r" He lived at Jing[’']an Villa, near Nanjing West Road\.", ""),
        (r" เขาอยู่ที่จิงอันวิลลา ใกล้ถนนหนานจิงตะวันตก", ""),
        (r"他住在静安别墅，靠近南京西路。", ""),
        # README-style mention, if a page still carries it.
        (r"; Jing[’']an Villa near Nanjing West Road", ""),
        # A private person's name, staff page, and where he had lived.
        (
            r"without our friend </p><a href=\"https://www.soas.ac.uk/staff/staff90182.php\">.*?</a><p>who once lived around the corner from where we went for food\. It’s ironic because three of us had, in the past 12 months, always talked about the plan to have dinner together there, but it only happened after Leo had left Shanghai to return to London to continue his study at the </p><a href=\"https://www.soas.ac.uk/anthropology/\">School of Oriental and African Studies \(SOAS\)</a><p>\.",
            "without our friend. It’s ironic because three of us had, in the past 12 months, always talked about the plan to have dinner together there, but it only happened after he had left Shanghai.",
        ),
        (
            r'<a href="https://www.soas.ac.uk/staff/staff90182.php"[^>]*>(?:Leo Pang|a friend)\s*</a>',
            "",
        ),
        (
            r"Leo Pang who once lived around the corner from where we went for food",
            "a friend",
        ),
        (r"\bLeo Pang\b", "a friend"),
        (r"\bafter Leo had left Shanghai\b", "after he had left Shanghai"),
        # Family health inside an otherwise public essay.
        (
            r",? ?which might help to explain why he was never in good health, and therefore passed away so prematurely five years ago when I he was just 63\.?",
            ".",
        ),
        (
            r"So, excessive working eventually led to the quick deterioration of health\. By the time he was retiring, he was going to the hospital on a weekly basis for al kinds of medication\. ",
            "",
        ),
        (
            r" ?[DdSs]espite the fact that his physical condition wasn[’']t good enough for him to ride a bike anymore during the last decade of his life, he also (?:<em>)?always wanted to get a Brompton\.?(?:</em>)?",
            "",
        ),
        # Public scholar: keep the dedication, drop the clinical facts.
        (
            r" Prof\. Tapp passed away due to illness on October 10, 2015 at the Shanghai Huashan Hospital\. He was 63 years old\. ",
            " ",
        ),
        (
            r"I was thinking about visiting him at the hospital in the summer\. ",
            "",
        ),
        # Savings and a relative's illness, inside a published profile.
        (
            r" The pivotal moment for him was when he realized that his most important plan, which was to take his father around the world, was shattered into pieces because of his father’s abruptly and unexpectedly died\. In Thailand, his father worked for the government therefore his retirement age was strictly at 60\. Non had hoped that once his father retired, he could take his father around the world with his savings\. His father retired at 60, but unfortunately at 61 he passed away owing to his chronic illness\.",
            " " + INLINE,
        ),
        # Family money and how the family name was made.
        (
            r" owing to my family’s lack of financial resources among other things \(such as the fact that we’re members of a underprivileged class in the Thai society\)",
            "",
        ),
        (
            r" My father was the one who came up with our family’s Thai last name in order to get the family registered and to get himself to go to school since during the time he was growing up there’s a strong anti-Chinese sentiment everywhere\. Despite our long need-no-introduction last name, it’s a made-up one\. My father came up with it by looking up words he liked in a dictionary and put them together\.",
            " " + INLINE,
        ),
        # Personal health inside an essay about a public book. The book stays.
        (
            r"Then I slipped into the thinking that it would have been painful to everyone around me had I decided to leave this world upon the death of my father\. ?",
            INLINE + " ",
        ),
        # A child relative used as an example inside a public design essay.
        (
            r"My little cousin\s+though can easily be pleased sometime with the most basic things, she dislikes complicated things\. The more complicated things are, the more she’s likely to be bored by;?",
            INLINE,
        ),
        (
            r"My cousin would not engage in anything that is not fun\. So, she’s trying to make everything fun \(including studying\)\. So, when testing my idea on anything with her, I need to make sure that whatever I propose will give both the meaning and playfulness to those involved in the process; and,?",
            INLINE,
        ),
        # A fieldnote caption named a relative on a trip. The page stays.
        (r" when I visited Japan with my mother", " when I visited Japan"),
        (r" since my father gave it to me in 2004 — ", " — "),
        # Jealousy essay: drop the named relatives, keep the essay.
        (r"of my cousins and my mother", "of anyone"),
        (r"beyond my cousins and my mother", "toward anyone"),
    ]
    for pat, repl in edits:
        html, k = subn(pat, repl, html)
        n += k
    return html, n


# Substrings that mark a private health note or a family roster.
# Do not match the bare word "suicide": public essays argue with Camus, Kant,
# Durkheim, and Kahneman. Do not match "cremation" or "my cousins".
SENTENCE_NEEDLES = (
    "deep depression",
    "loathed my existence",
    "did not want to live",
    "end all pain",
    "my little cousin",
    "paternal grandmother",
    "maternal grandfather",
    "grandmother’s funeral",
    "grandmother's funeral",
    "looked suicidal",
    "suicidal sleepless",
    "depression-ridden suicidal",
)


def sentence_is_private(low: str) -> bool:
    if any(needle in low for needle in SENTENCE_NEEDLES):
        return True
    # "my cousin" but not "my cousins".
    return bool(re.search(r"\bmy cousin\b", low))


def redact_paragraphs(html: str) -> tuple[str, int]:
    """Drop sentences of private health or a family roster. Leave the essay."""
    n = 0

    def consider(m: re.Match) -> str:
        nonlocal n
        block = m.group(0)
        open_tag, inner, close = re.match(
            r"(<(?:p|li)\b[^>]*>)(.*?)(</(?:p|li)>)", block, re.S
        ).groups()
        plain = unescape(re.sub(r"<[^>]+>", " ", inner)).lower()
        if not sentence_is_private(plain):
            return block
        # Split after a period even when a tag or a closing quote sits in between,
        # so a public sentence is not dropped with the private one beside it.
        parts = re.split(r"(?<=\.)(?:</[^>]+>|[\"“”'’])*\s+", inner)
        kept: list[str] = []
        for part in parts:
            # A closing tag after the previous period belongs to that sentence.
            closes = ""
            rest = part
            while True:
                m = re.match(r"\s*(</[^>]+>)", rest)
                if not m:
                    break
                closes += m.group(1)
                rest = rest[m.end():]
            if closes and kept:
                kept[-1] = kept[-1].rstrip() + closes
            low = unescape(re.sub(r"<[^>]+>", " ", rest)).lower()
            if sentence_is_private(low):
                n += 1
                continue
            if rest.strip():
                kept.append(rest.lstrip() if kept else rest)
        body = " ".join(p for p in kept if unescape(re.sub(r"<[^>]+>", "", p)).strip())
        if not body.strip():
            if open_tag.startswith("<li"):
                return open_tag + INLINE + "</li>"
            return NOTE
        return open_tag + body + close

    html = re.sub(r"<p\b[^>]*>.*?</p>", consider, html, flags=re.S)

    def consider_li(m: re.Match) -> str:
        if "<p" in m.group(0):
            return m.group(0)
        return consider(m)

    html = re.sub(r"<li\b[^>]*>.*?</li>", consider_li, html, flags=re.S)
    return html, n


def strip_withheld_links(html: str) -> str:
    """Keep the sentence, drop the link, when it points at a withheld entry."""

    def repl(m: re.Match) -> str:
        href = m.group(1)
        if any(slug in href for slug in WITHHELD_SLUGS):
            return m.group(2)
        return m.group(0)

    return re.sub(r'<a href="([^"]*)"[^>]*>(.*?)</a>', repl, html, flags=re.S)


def collect_media(html: str) -> set[str]:
    return set(re.findall(r"/media/[A-Za-z0-9._-]+", html))


def apply(root: Path | None = None) -> dict:
    root = root or ROOT
    changed_files: list[str] = []
    withheld_media: set[str] = set()

    # Gather images from entries we are about to remove.
    for slug in WITHHELD_SLUGS:
        for page in root.rglob("index.html"):
            if page.parent.name == slug:
                withheld_media |= collect_media(page.read_text(encoding="utf-8", errors="ignore"))

    removed_dirs = []
    for slug in sorted(WITHHELD_SLUGS):
        for page in list(root.rglob("index.html")):
            if page.parent.name != slug:
                continue
            if ".git" in page.parts:
                continue
            directory = page.parent
            shutil.rmtree(directory)
            removed_dirs.append(str(directory.relative_to(root)))
            # Drop empty date folders.
            parent = directory.parent
            while parent != root and parent.is_dir() and not any(parent.iterdir()):
                parent.rmdir()
                parent = parent.parent

    before_private_media: set[str] = set(withheld_media)
    for page in root.rglob("index.html"):
        if ".git" in page.parts:
            continue
        html = page.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r"<figure\b[^>]*>.*?</figure>", html, flags=re.S):
            if is_private_image(_figure_text(m.group(0))):
                before_private_media |= collect_media(m.group(0))
        for m in re.finditer(r"<img\b[^>]*alt=\"([^\"]*)\"[^>]*/?\s*>", html):
            if is_private_image(unescape(m.group(1) or "")):
                before_private_media |= collect_media(m.group(0))

    for page in root.rglob("*.html"):
        if ".git" in page.parts:
            continue
        original = page.read_text(encoding="utf-8", errors="ignore")
        html = strip_figures(original)
        html = strip_private_imgs(html)
        html = strip_withheld_links(html)
        html, _ = redact_phrases(html)
        html, _ = redact_paragraphs(html)
        # A phrase note is inline. Never leave it wrapped in a paragraph inside a paragraph.
        html = html.replace(" " + NOTE, " " + INLINE)
        html = html.replace(NOTE + NOTE, NOTE)
        html = html.replace(INLINE + INLINE, INLINE)
        html = html.replace(PHOTO_NOTE + PHOTO_NOTE, PHOTO_NOTE)
        if html != original:
            page.write_text(html, encoding="utf-8")
            changed_files.append(str(page.relative_to(root)))

    # Markdown and the generator's residence sentence, if still present.
    for path in (root / "README.md", root / "tools" / "build_site.py"):
        if not path.exists():
            continue
        original = path.read_text(encoding="utf-8")
        html = original
        for sentence in RESIDENCE:
            html = html.replace(sentence, "")
        html = html.replace("; Jing’an Villa near Nanjing West Road", "")
        html = html.replace("; Jing'an Villa near Nanjing West Road", "")
        if html != original:
            path.write_text(html, encoding="utf-8")
            changed_files.append(str(path.relative_to(root)))

    rewire_navigation(root)

    # Delete image files that belonged only to withheld entries or removed portraits.
    still = set()
    for page in root.rglob("*.html"):
        if ".git" in page.parts:
            continue
        still |= collect_media(page.read_text(encoding="utf-8", errors="ignore"))
    # map.json and css do not count as publishing the picture in a page,
    # but keep a file if any html still points at it.
    deleted_media = []
    for src in sorted(before_private_media):
        if src in still:
            continue
        rel = src.lstrip("/")
        path = root / rel
        if path.is_file():
            path.unlink()
            deleted_media.append(rel)
    prune_map(root, deleted_media)

    return {
        "removed_dirs": removed_dirs,
        "changed_files": changed_files,
        "deleted_media": deleted_media,
    }


def prune_map(root: Path, deleted_media: list[str]) -> None:
    path = root / "media" / "map.json"
    if not path.exists() or not deleted_media:
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    gone = set(deleted_media)
    pruned = {k: v for k, v in data.items() if v not in gone}
    if len(pruned) != len(data):
        path.write_text(json.dumps(pruned, ensure_ascii=False, separators=(", ", ": ")), encoding="utf-8")
        path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")


def post_title(html: str) -> str:
    m = re.search(r"<h1>(.*?)</h1>", html, re.S)
    if not m:
        return ""
    return unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip()


def rewire_navigation(root: Path) -> None:
    index = root / "index.html"
    if not index.exists():
        return
    text = index.read_text(encoding="utf-8")
    # Drop table-of-contents rows and sitemap URLs for withheld slugs.
    for slug in WITHHELD_SLUGS:
        text = re.sub(
            rf'<li><a href="[^"]*{re.escape(slug)}/">.*?</a></li>',
            "",
            text,
        )
    index.write_text(text, encoding="utf-8")

    sitemap = root / "sitemap.xml"
    if sitemap.exists():
        lines = sitemap.read_text(encoding="utf-8").splitlines(keepends=True)
        kept = []
        for line in lines:
            if any(slug in line for slug in WITHHELD_SLUGS):
                continue
            kept.append(line)
        sitemap.write_text("".join(kept), encoding="utf-8")

    # Earlier/later links follow the index order that remains.
    hrefs = re.findall(r'<a href="(/(?:20)[^"]+)"', index.read_text(encoding="utf-8"))
    # The index lists posts as /YYYY/MM/DD/slug/. Pages use /pages/.
    posts = [h for h in hrefs if re.match(r"/20\d\d/", h)]
    # Unique, in order.
    seen = set()
    ordered = []
    for h in posts:
        if h in seen:
            continue
        seen.add(h)
        ordered.append(h)

    titles = {}
    pages = []
    for href in ordered:
        path = root / href.strip("/") / "index.html"
        if not path.exists():
            continue
        pages.append(href)
        titles[href] = post_title(path.read_text(encoding="utf-8", errors="ignore"))

    def link(kind: str, href: str) -> str:
        label = {
            "earlier": ("Earlier", "ก่อนหน้า", "较早"),
            "next": ("Later", "ถัดไป", "较晚"),
        }[kind]
        en, th, zh = label
        title = escape(titles.get(href, ""))
        return (
            f'<a class="{kind}" href="{href}">'
            f'<span class="ti en">{en}</span><span class="ti th">{th}</span>'
            f'<span class="ti zh">{zh}</span><br>{title}</a>'
        )

    for i, href in enumerate(pages):
        path = root / href.strip("/") / "index.html"
        html = path.read_text(encoding="utf-8")
        earlier = link("earlier", pages[i - 1]) if i else ""
        later = link("next", pages[i + 1]) if i + 1 < len(pages) else ""
        pager = f'<nav class="pager" aria-label="Entries">{earlier}{later}</nav>'
        new, k = re.subn(r'<nav class="pager" aria-label="Entries">.*?</nav>', pager, html, count=1, flags=re.S)
        if k and new != html:
            path.write_text(new, encoding="utf-8")


def main() -> None:
    result = apply(ROOT)
    print("removed", len(result["removed_dirs"]))
    for d in result["removed_dirs"]:
        print(" dir", d)
    print("edited", len(result["changed_files"]))
    for f in result["changed_files"]:
        print(" edit", f)
    print("media", len(result["deleted_media"]))
    for m in result["deleted_media"]:
        print(" media", m)


if __name__ == "__main__":
    main()
