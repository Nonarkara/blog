#!/usr/bin/env python3
"""Build the static diary for diary.nonarkara.org.

Reads the unpacked WordPress export (default /tmp/wp-export) and writes HTML
into the repository root. Images are rewritten through media/map.json when a
local mirror exists. Grammar mending uses LanguageTool when it is installed,
limited to a short allow-list, plus hand fixes for three entries.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import sys
from html import escape, unescape
from pathlib import Path

from bs4 import BeautifulSoup, Comment, NavigableString, Tag

ROOT = Path(__file__).resolve().parents[1]
SITE_HOST = "diary.nonarkara.org"
SITE = f"https://{SITE_HOST}"
sys.path.insert(0, str(ROOT / "tools"))
from i18n_posts import BODIES, HAND  # noqa: E402

EXPORT = Path("/tmp/wp-export")
MAP_PATH = ROOT / "media" / "map.json"
MONTHS = [
    "",
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]
MONTHS_TH = [
    "",
    "มกราคม",
    "กุมภาพันธ์",
    "มีนาคม",
    "เมษายน",
    "พฤษภาคม",
    "มิถุนายน",
    "กรกฎาคม",
    "สิงหาคม",
    "กันยายน",
    "ตุลาคม",
    "พฤศจิกายน",
    "ธันวาคม",
]

SAFE_RULES = {
    "COMMA_PARENTHESIS_WHITESPACE",
    "WHITESPACE_RULE",
    "DOUBLE_PUNCTUATION",
    "MOST_COMPARATIVE",
    "DID_BASEFORM",
    "MD_BASEFORM",
    "NON3PRS_VERB",
    "HAVE_PART_AGREEMENT",
    "BEEN_PART_AGREEMENT",
    "NEITHER_NOR",
    "MUCH_COUNTABLE",
    "SUPERIOR_THAN_TO",
    "TO_RB_TO_VB",
    "THIS_NNS",
    "EN_COMPOUNDS_PROOF_READING",
    "LIGHT_COMPOUNDS",
    "KEEP_SEEING",
    "ALL_MOST_SOME_OF_NOUN",
}

PAGE_SLUGS = {
    1: "i-started-a-blog",
    284: "why-i-teach",
    4710: "only-if-you-can-do-these-12-things",
    4781: "the-credo",
    4957: "lat-krabang-to-harvard",
    4993: "12-rules-for-life",
}

ROOMS = [
    ("demon", "Demon", "ปีศาจ", "恶魔"),
    ("vice", "Vice", "อบายมุข", "恶习"),
    ("folly", "Folly", "ความเขลา", "愚行"),
    ("consistency", "Consistency", "ความคงเส้นคงวา", "一致"),
    ("inconsistency", "Inconsistency", "ความไม่คงเส้นคงวา", "不一致"),
    ("uniqueness", "Uniqueness", "เอกลักษณ์", "独特性"),
]

HINDSIGHT = {
    "en": "4 October 2026. He called this diary a real history of confusion. Looking back more than ten years, he said hindsight shows how far he has come, and that his present is peace: writing made him Buddha, he has been to nirvana, and ecstasy is a daily thing. This is later distance. It does not rewrite the entry.",
    "th": "4 ตุลาคม 2026. เขาเรียกบันทึกนี้ว่าประวัติศาสตร์จริงของความสับสน เมื่อมองย้อนกลับไปกว่าสิบปี เขากล่าวว่าการมองย้อนทำให้เห็นว่าเขามาไกลเพียงใด และปัจจุบันของเขาคือความสงบ: การเขียนทำให้เขาเป็นพระพุทธะ เขาเคยถึงนิพพาน และความปีติเป็นเรื่องของทุกวัน นี่คือระยะห่างในภายหลัง มันไม่ได้เขียนทับบันทึกนั้น",
    "zh": "2026年10月4日。他称这本日记是一段真实的困惑史。回看十多年，他说后见之明让他看见自己走了多远，而他的现在是平静：写作使他成佛，他到过涅槃，狂喜是每日的事。这是后来的距离。它不改写那一篇。",
}

SHANGHAI = {
    "en": "Resident fieldwork in Shanghai began on 21 June 2013, after visits from 2006 to 2013. He lived at Jing’an Villa, near Nanjing West Road. A later public reading edition of the Shanghai work is at <a href=\"https://shanghai.nonarkara.org\">shanghai.nonarkara.org</a>. The 2015 post did not know that site.",
    "th": "งานภาคสนามแบบพำนักในเซี่ยงไฮ้เริ่มวันที่ 21 มิถุนายน 2013 หลังจากไปเยือนระหว่างปี 2006 ถึง 2013 เขาอยู่ที่จิงอันวิลลา ใกล้ถนนหนานจิงตะวันตก ฉบับอ่านสาธารณะในภายหลังของงานเซี่ยงไฮ้อยู่ที่ <a href=\"https://shanghai.nonarkara.org\">shanghai.nonarkara.org</a> บทความปี 2015 ยังไม่รู้จักไซต์นั้น",
    "zh": "在上海的驻地田野开始于2013年6月21日，在此之前是2006年至2013年的访问。他住在静安别墅，靠近南京西路。上海作品后来的公开阅读版在 <a href=\"https://shanghai.nonarkara.org\">shanghai.nonarkara.org</a>。2015年的这篇还不知道那个站点。",
}


def canon(url: str) -> str:
    url = unescape(url or "").replace("&amp;", "&").split("#")[0].split("?")[0]
    url = re.sub(r"^https://i\d\.wp\.com/", "https://", url)
    url = url.replace("http://", "https://")
    return url


def load_map() -> dict:
    if MAP_PATH.exists():
        return json.loads(MAP_PATH.read_text())
    return {}


IMG_MAP = load_map()
UNMIRRORED: set[str] = set()
GRAMMAR_LOG: list[str] = []


def esc(s: str) -> str:
    return escape(s or "", quote=True)


def fmt_date(iso: str) -> str:
    d = dt.date.fromisoformat(iso[:10])
    return f"{d.day} {MONTHS[d.month]} {d.year}"


def fmt_date_th(iso: str) -> str:
    d = dt.date.fromisoformat(iso[:10])
    return f"{d.day} {MONTHS_TH[d.month]} {d.year}"


def fmt_date_zh(iso: str) -> str:
    d = dt.date.fromisoformat(iso[:10])
    return f"{d.year}年{d.month}月{d.day}日"


def mostly_thai(s: str) -> bool:
    th = sum(1 for ch in s if "\u0e00" <= ch <= "\u0e7f")
    lat = sum(1 for ch in s if ("A" <= ch <= "Z") or ("a" <= ch <= "z"))
    return th > 40 and th > lat


def punct(s: str) -> str:
    s = s.replace("\xa0", " ")
    s = re.sub(r"[ \t]+([,.;:!?])", r"\1", s)
    s = re.sub(r"[ \t]{2,}", " ", s)
    return s


def phrases(s: str) -> str:
    s = s.replace("the my ", "my ")
    s = s.replace("the their ", "their ")
    s = s.replace(" a the ", " the ")
    return s


def choose_replacement(rule_id: str, matched: str, replacements: list[str], text: str, off: int) -> str | None:
    reps = [r for r in replacements if r and "(" not in r and ")" not in r]
    if not reps:
        return None
    if len(reps[0].split()) > len(matched.split()) + 3:
        return None
    if rule_id == "THIS_NNS":
        low = matched.lower()
        if len(matched.split()) < 2:
            return None
        if any(w in low for w in ("advice", "wisdom", "news", "information")):
            return None
        first = matched.split()[0].lower()
        for r in reps:
            if r.lower().startswith(first):
                return r
        return None
    if rule_id == "MD_BASEFORM":
        window = text[max(0, off - 24) : off].lower()
        if not re.search(r"\b(can|could|may|might|must|shall|should|will|would)\s+$", window):
            return None
    if rule_id == "COMMA_PARENTHESIS_WHITESPACE":
        nxt = text[off + len(matched) : off + len(matched) + 1]
        prev = text[off - 1 : off]
        if prev.isdigit() and nxt.isdigit():
            return None
    if rule_id == "TO_RB_TO_VB":
        for r in reps:
            if r.strip() == "not to":
                return r
        return reps[0]
    if rule_id == "ALL_MOST_SOME_OF_NOUN":
        for r in reps:
            if " the " in f" {r} ":
                return r
        return reps[0]
    if rule_id == "DOUBLE_PUNCTUATION":
        for r in reps:
            if r in {".", ",", "?", "!"}:
                return r
        return None
    if rule_id == "CD_NN":
        return None
    return reps[0]


def mend_text(text: str, tool, cache: dict, post_id: int) -> str:
    text = phrases(punct(text))
    if tool is None or post_id in HAND or mostly_thai(text) or len(text.strip()) < 20:
        return text
    key = hashlib.sha1(text.encode()).hexdigest()
    if key in cache:
        return cache[key]
    try:
        matches = tool.check(text)
    except Exception:
        cache[key] = text
        return text
    edits = []
    for m in matches:
        if m.rule_id not in SAFE_RULES:
            continue
        rep = choose_replacement(m.rule_id, m.matched_text, list(m.replacements or []), text, m.offset)
        if not rep or rep == m.matched_text:
            continue
        edits.append((m.offset, m.error_length, rep, m.rule_id, m.matched_text))
    for off, length, rep, rid, matched in sorted(edits, key=lambda x: -x[0]):
        text = text[:off] + rep + text[off + length :]
        GRAMMAR_LOG.append(f"{post_id}\t{rid}\t{matched!r} -> {rep!r}")
    cache[key] = text
    return text


def apply_hand(soup: BeautifulSoup, post_id: int) -> None:
    pairs = HAND.get(post_id) or []
    if not pairs:
        return
    for node in list(soup.find_all(string=True)):
        if not isinstance(node, NavigableString) or isinstance(node, Comment):
            continue
        parent = node.parent
        if parent is None or parent.name in {"script", "style"}:
            continue
        s = str(node)
        n = s
        for a, b in pairs:
            n = n.replace(a, b)
        if n != s:
            node.replace_with(n)


def local_image(url: str) -> str:
    c = canon(url)
    if c in IMG_MAP:
        return "/" + IMG_MAP[c]
    if c:
        UNMIRRORED.add(c)
    return url


def rewrite_links(soup: BeautifulSoup, href_map: dict) -> None:
    for a in soup.find_all("a"):
        href = a.get("href") or ""
        c = canon(href)
        if c in IMG_MAP:
            a["href"] = "/" + IMG_MAP[c]
            continue
        key = c.rstrip("/")
        if key in href_map:
            a["href"] = href_map[key]
        elif "nonharvard.wordpress.com" in href and "?p=" in href:
            m = re.search(r"[?&]p=(\d+)", href)
            if m and f"id:{m.group(1)}" in href_map:
                a["href"] = href_map[f"id:{m.group(1)}"]


def clean_html(html: str, href_map: dict) -> BeautifulSoup:
    soup = BeautifulSoup(f"<div id='root'>{html or ''}</div>", "lxml")
    root = soup.find(id="root")
    for c in root.find_all(string=lambda t: isinstance(t, Comment)):
        c.extract()
    for bad in root.find_all(["script", "style", "noscript", "form", "iframe"]):
        if bad.name == "iframe":
            src = bad.get("src") or ""
            p = soup.new_tag("p")
            p["class"] = ["embed"]
            a = soup.new_tag("a", href=unescape(src) if src else "#")
            host = "media"
            if "soundcloud" in src:
                host = "SoundCloud"
            elif "youtube" in src or "youtu.be" in src:
                host = "YouTube"
            elif "vimeo" in src:
                host = "Vimeo"
            a.string = f"Embedded {host}"
            p.append(a)
            bad.replace_with(p)
        else:
            bad.decompose()
    for cap in list(root.select("div.wp-caption, div[id^=attachment_]")):
        fig = soup.new_tag("figure")
        img = cap.find("img")
        if img:
            fig.append(img.extract())
        caption = cap.find(class_="wp-caption-text")
        if caption:
            fc = soup.new_tag("figcaption")
            for child in list(caption.contents):
                fc.append(child.extract() if isinstance(child, Tag) else NavigableString(str(child)))
            if fc.get_text(strip=True) or fc.find("img"):
                fig.append(fc)
        cap.replace_with(fig)
    for div in list(root.find_all("div")):
        classes = " ".join(div.get("class") or [])
        if "gallery" in classes or "tiled-gallery" in classes:
            gal = soup.new_tag("div")
            gal["class"] = ["gallery"]
            for img in div.find_all("img"):
                gal.append(img.extract())
            div.replace_with(gal)
    for tag in list(root.find_all(True)):
        if tag.name in {"div", "span", "section", "article", "font", "center"}:
            if tag.get("class") == ["gallery"]:
                continue
            tag.unwrap()
    allowed_attrs = {"a": {"href"}, "img": {"src", "alt"}}
    for tag in list(root.find_all(True)):
        if tag.name == "h1":
            tag.name = "h2"
        keep = set(allowed_attrs.get(tag.name, set()))
        if tag.name == "div" and tag.get("class") == ["gallery"]:
            keep.add("class")
        if tag.name == "p" and tag.get("class") == ["embed"]:
            keep.add("class")
        for attr in list(tag.attrs):
            if attr not in keep:
                del tag[attr]
        if tag.name == "img":
            src = tag.get("src") or ""
            tag["src"] = local_image(src)
            if not tag.get("alt"):
                tag["alt"] = ""
    for child in list(root.children):
        if isinstance(child, NavigableString) and str(child).strip():
            p = soup.new_tag("p")
            child.wrap(p)
    # second pass: data-orig was stripped before we could prefer it.
    rewrite_links(root, href_map)
    for p in list(root.find_all("p")):
        if not p.get_text(strip=True) and not p.find("img"):
            p.decompose()
    return root


def clean_html_prefer_orig(html: str, href_map: dict) -> BeautifulSoup:
    """Like clean_html, but image sources prefer data-orig-file before attributes are stripped."""
    soup = BeautifulSoup(f"<div id='root'>{html or ''}</div>", "lxml")
    root = soup.find(id="root")
    for img in root.find_all("img"):
        orig = img.get("data-orig-file") or img.get("data-large-file") or img.get("src") or ""
        img["src"] = orig
    inner = root.decode_contents()
    return clean_html(inner, href_map)


def prepend_featured(root: Tag, featured: str, href_map: dict) -> None:
    if not featured:
        return
    c = canon(featured)
    for img in root.find_all("img"):
        if canon(img.get("src") or "") == c or canon(featured) in (img.get("src") or ""):
            return
        # local path may already differ; compare by map
        mapped = IMG_MAP.get(c)
        if mapped and (img.get("src") or "").endswith(mapped.split("/")[-1]):
            return
    fig = BeautifulSoup("<figure><img alt=''></figure>", "lxml").figure
    fig.img["src"] = local_image(featured)
    root.insert(0, fig)


def figure_list(root: Tag) -> list[str]:
    seen = set()
    out = []
    for img in root.find_all("img"):
        parent = img.find_parent("figure")
        node = parent if parent is not None else img
        key = id(node)
        if key in seen:
            continue
        seen.add(key)
        if parent is None:
            out.append(f"<figure>{img}</figure>")
        else:
            out.append(str(parent))
    return out


def fill_slots(html: str, figures: list[str]) -> str:
    soup = BeautifulSoup(f"<div id='root'>{html}</div>", "lxml")
    root = soup.find(id="root")
    used = set()
    for slot in list(root.select("[data-fig]")):
        i = int(slot.get("data-fig") or -1)
        if 0 <= i < len(figures):
            frag = BeautifulSoup(figures[i], "lxml")
            node = frag.find("figure") or frag.find("img")
            if node:
                slot.replace_with(node)
                used.add(i)
            else:
                slot.decompose()
        else:
            slot.decompose()
    for i, fig in enumerate(figures):
        if i not in used:
            frag = BeautifulSoup(fig, "lxml")
            node = frag.find("figure") or frag.find("img")
            if node:
                root.append(node)
    return root.decode_contents()


def soup_inner(root: Tag) -> str:
    return root.decode_contents().strip()


def mend_tree(root: Tag, tool, cache: dict, post_id: int) -> None:
    for node in list(root.find_all(string=True)):
        if not isinstance(node, NavigableString) or isinstance(node, Comment):
            continue
        parent = node.parent
        if parent is None or parent.name in {"script", "style"}:
            continue
        s = str(node)
        if not s.strip():
            continue
        n = mend_text(s, tool, cache, post_id)
        if n != s:
            node.replace_with(n)
    apply_hand(root, post_id)


def tri(en: str, th: str, zh: str, cls: str = "ti") -> str:
    return (
        f'<span class="{cls} en">{en}</span>'
        f'<span class="{cls} th">{th}</span>'
        f'<span class="{cls} zh">{zh}</span>'
    )


def header() -> str:
    return f"""<a class="skip" href="#content">{tri("Skip to text", "ข้ามไปที่ข้อความ", "跳到正文")}</a>
<header class="site-header">
  <a class="mark" href="/">{tri("Non Arkaraprasertkul", "นน อัครประเสริฐกุล", "Non Arkaraprasertkul")}</a>
  <nav class="nav" aria-label="Site">
    <a href="/">{tri("Diary", "บันทึก", "日记")}</a>
    <a href="/about/">{tri("About", "เกี่ยวกับ", "关于")}</a>
    <a href="/english-only/">{tri("English only", "ยังเป็นภาษาอังกฤษ", "仅英文")}</a>
  </nav>
  <div class="langs" role="group" aria-label="Language">
    <button type="button" data-set-lang="en" aria-pressed="true">English</button>
    <button type="button" data-set-lang="th" aria-pressed="false">ไทย</button>
    <button type="button" data-set-lang="zh" aria-pressed="false">中文</button>
  </div>
</header>"""


def footer() -> str:
    rooms = " ".join(
        f'<a href="/rooms/{slug}/">{tri(en, th, zh)}</a>' for slug, en, th, zh in ROOMS
    )
    return f"""<footer class="site-footer">
  <p>{tri(
        "A public archive of the diary at nonharvard.wordpress.com.",
        "หอจดหมายเหตุสาธารณะของบันทึกที่ nonharvard.wordpress.com",
        "nonharvard.wordpress.com 上那本日记的公开存档。",
    )}</p>
  <p class="rooms-nav"><span class="kicker">{tri("Later rooms", "ห้องภายหลัง", "日后的房间")}</span> {rooms}</p>
</footer>"""


def shell(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="Public archive of Non Arkaraprasertkul’s diary from nonharvard.wordpress.com.">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/fonts/fonts.css">
<link rel="stylesheet" href="/assets/site.css">
<script>try{{var l=localStorage.getItem('diary-lang');if(l==='th'||l==='zh'){{document.documentElement.setAttribute('data-lang',l);document.documentElement.lang=l==='zh'?'zh-Hans':l;}}}}catch(e){{}}</script>
</head>
<body>
{header()}
{body}
{footer()}
<script src="/assets/main.js"></script>
</body>
</html>
"""


def margin_html(kind: str | None) -> str:
    if kind == "hindsight":
        block = HINDSIGHT
    elif kind == "shanghai":
        block = SHANGHAI
    else:
        return ""
    return f"""<aside class="margin">
  <p class="kicker">{tri("Margin", "ขอบ", "页边")}</p>
  <p class="tb en">{block["en"]}</p>
  <p class="tb th">{block["th"]}</p>
  <p class="tb zh">{block["zh"]}</p>
</aside>"""


def copy_switch() -> str:
    return f"""<div class="copy-switch" role="group" aria-label="Copy">
  <button type="button" data-set-copy="reading" aria-pressed="true">{tri("Reading copy", "สำเนาสำหรับอ่าน", "阅读稿")}</button>
  <button type="button" data-set-copy="original" aria-pressed="false">{tri("Original", "ต้นฉบับ", "原文")}</button>
</div>
<p class="only-en">{tri(
        "Grammar only. The title is unchanged.",
        "แก้แต่ไวยากรณ์ ชื่อเรื่องคงเดิม",
        "只改语法。标题不动。",
    )}</p>"""


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def load_entries():
    posts = []
    for path in (EXPORT / "raw").glob("*.json"):
        posts.append(json.loads(path.read_text()))
    pages = []
    for path in (EXPORT / "raw" / "pages").glob("*.json"):
        pages.append(json.loads(path.read_text()))
    posts.sort(key=lambda d: (d["date"], d["ID"]))
    pages.sort(key=lambda d: (d["date"], d["ID"]))
    return posts, pages


def entry_paths(posts, pages):
    href_map = {}
    located = []
    for d in posts:
        m = re.search(r"/(\d{4})/(\d{2})/(\d{2})/", d["URL"])
        y, mo, da = m.group(1), m.group(2), m.group(3)
        rel = f"/{y}/{mo}/{da}/{d['slug']}/"
        href_map[canon(d["URL"]).rstrip("/")] = rel
        href_map[f"id:{d['ID']}"] = rel
        located.append((d, rel, "post"))
    for d in pages:
        slug = PAGE_SLUGS[d["ID"]]
        rel = f"/pages/{slug}/"
        href_map[canon(d["URL"]).rstrip("/")] = rel
        href_map[f"id:{d['ID']}"] = rel
        located.append((d, rel, "page"))
    return located, href_map


def render_entry(d, rel, kind, tool, cache, href_map, prev_item, next_item, margin):
    title = unescape(d["title"] or "").strip()
    iso = d["date"][:10]
    original = clean_html_prefer_orig(d.get("content") or "", href_map)
    featured = d.get("featured_image") or ""
    if isinstance(featured, str):
        prepend_featured(original, featured, href_map)
    reading = BeautifulSoup(f"<div id='root'>{soup_inner(original)}</div>", "lxml").find(id="root")
    orig_html = soup_inner(reading)
    thai_page = mostly_thai(reading.get_text(" ", strip=True))
    if not thai_page:
        mend_tree(reading, tool, cache, d["ID"])
    read_html = soup_inner(reading)
    translated = d["ID"] in BODIES
    figures = figure_list(reading)
    bodies = ""
    if translated:
        th = fill_slots(BODIES[d["ID"]]["th"], figures)
        zh = fill_slots(BODIES[d["ID"]]["zh"], figures)
        bodies = (
            f'<div class="tb en"><div class="prose" lang="en">{read_html}</div></div>'
            f'<div class="tb th"><div class="prose" lang="th">{th}</div></div>'
            f'<div class="tb zh"><div class="prose" lang="zh-Hans">{zh}</div></div>'
        )
    else:
        note = ""
        if thai_page:
            note = f'<p class="only-en">{tri("This page was written in Thai.", "หน้านี้เขียนเป็นภาษาไทย", "这一页是用泰语写的。")}</p>'
        else:
            note = f'<p class="only-en">{tri("This entry is in English only.", "บันทึกนี้มีแต่ภาษาอังกฤษ", "此篇仅有英文。")}</p>'
        bodies = note + f'<div class="prose" lang="{"th" if thai_page else "en"}">{read_html}</div>'
    changed = read_html != orig_html
    switch = ""
    original_block = ""
    if changed:
        switch = copy_switch()
        original_block = f"""<div class="copy-original">
  <p class="origin-note">{tri("Unedited original.", "ต้นฉบับที่ไม่ได้แก้", "未经修改的原文。")}</p>
  <div class="prose" lang="{"th" if thai_page else "en"}">{orig_html}</div>
</div>"""
        reading_block = f'<div class="copy-reading">{bodies}</div>'
    else:
        reading_block = bodies
    margin_block = margin_html(margin)
    entry_class = "entry" if margin else "entry no-margin"
    kicker = tri("Diary", "บันทึก", "日记") if kind == "post" else tri("Page from the old site", "หน้าจากไซต์เก่า", "旧站上的一页")
    date_html = tri(fmt_date(iso), fmt_date_th(iso), fmt_date_zh(iso))
    pager = ""
    if kind == "post":
        earlier = ""
        later = ""
        if prev_item:
            earlier = f'<a class="earlier" href="{prev_item[1]}"><span class="ti en">Earlier</span><span class="ti th">ก่อนหน้า</span><span class="ti zh">较早</span><br>{esc(unescape(prev_item[0]["title"]))}</a>'
        if next_item:
            later = f'<a class="next" href="{next_item[1]}"><span class="ti en">Later</span><span class="ti th">ถัดไป</span><span class="ti zh">较晚</span><br>{esc(unescape(next_item[0]["title"]))}</a>'
        pager = f'<nav class="pager" aria-label="Entries">{earlier}{later}</nav>'
    source = f'<p class="source"><a href="{esc(d["URL"])}">{tri("First published on nonharvard.wordpress.com", "เผยแพร่ครั้งแรกที่ nonharvard.wordpress.com", "首发于 nonharvard.wordpress.com")}</a></p>'
    body = f"""<main class="sheet" id="content">
  <article class="{entry_class}">
    <div class="text">
      <p class="kicker">{kicker}</p>
      <h1>{esc(title)}</h1>
      <p class="meta"><time datetime="{iso}">{date_html}</time></p>
      {switch}
      {reading_block}
      {original_block}
      {source}
      {pager}
    </div>
    {margin_block}
  </article>
</main>"""
    page_title = f"{title} — Non Arkaraprasertkul"
    write(ROOT / rel.strip("/") / "index.html", shell(page_title, body))
    return changed


def render_index(posts_located, pages_located):
    years = {}
    for d, rel, _ in posts_located:
        years.setdefault(d["date"][:4], []).append((d, rel))
    blocks = []
    for year in sorted(years):
        items = []
        for d, rel in years[year]:
            iso = d["date"][:10]
            title = unescape(d["title"] or "")
            items.append(
                f'<li><a href="{rel}"><time datetime="{iso}">{esc(fmt_date(iso))}</time><span class="ttl">{esc(title)}</span></a></li>'
            )
        blocks.append(f'<section class="year"><h2>{year}</h2><ol class="toc">{"".join(items)}</ol></section>')
    page_items = []
    for d, rel, _ in pages_located:
        title = unescape(d["title"] or "")
        page_items.append(f'<li><a href="{rel}"><span class="ttl">{esc(title)}</span></a></li>')
    lede_en = "A public archive of the diary kept at nonharvard.wordpress.com, from 14 September 2015 to 30 November 2025. One hundred and twenty-six entries. The reading copy mends grammar. The unedited original sits beside it. Titles are as he published them."
    lede_th = "หอจดหมายเหตุสาธารณะของบันทึกที่ nonharvard.wordpress.com ตั้งแต่วันที่ 14 กันยายน 2015 ถึง 30 พฤศจิกายน 2025 หนึ่งร้อยยี่สิบหกชิ้น สำเนาสำหรับอ่านแก้ไวยากรณ์ ต้นฉบับที่ไม่ได้แก่อยู่ข้างกัน ชื่อเรื่องเป็นอย่างที่เขาเผยแพร่"
    lede_zh = "nonharvard.wordpress.com 上那本日记的公开存档，自2015年9月14日至2025年11月30日。一百二十六篇。阅读稿只补语法。未经修改的原文并置在旁。标题照他发表时的样子，不动。"
    body = f"""<main class="sheet" id="content">
  <p class="kicker">{tri("Diary", "บันทึก", "日记")}</p>
  <h1>{tri("Non Arkaraprasertkul", "นน อัครประเสริฐกุล", "Non Arkaraprasertkul")}</h1>
  <div class="lede"><p class="tb en">{lede_en}</p><p class="tb th">{lede_th}</p><p class="tb zh">{lede_zh}</p></div>
  <form class="find" action="#" onsubmit="return false">
    <label for="q">{tri("Find an entry", "หาบันทึก", "找一篇")}</label>
    <input id="q" type="search" autocomplete="off">
  </form>
  {''.join(blocks)}
  <section class="pages-block">
    <h2>{tri("Pages from the old site", "หน้าจากไซต์เก่า", "旧站上的页面")}</h2>
    <p>{tri(
        "Six WordPress pages came with the export. They are not counted among the one hundred and twenty-six entries. The 2015 about page is one of them. This site’s About is separate.",
        "มีหน้าเวิร์ดเพรสหกหน้ามากับไฟล์ส่งออก ไม่นับในหนึ่งร้อยยี่สิบหกชิ้น หน้าเกี่ยวกับของปี 2015 เป็นหนึ่งในนั้น หน้าเกี่ยวกับของไซต์นี้แยกต่างหาก",
        "导出里有六篇 WordPress 页面。它们不算在一百二十六篇之内。2015年的关于页是其中之一。本站的关于页是另外一页。",
    )}</p>
    <ol class="toc">{''.join(page_items)}</ol>
  </section>
</main>"""
    write(ROOT / "index.html", shell("Non Arkaraprasertkul — Diary", body))


def render_about():
    def block(iso, en, th, zh):
        return f"""<article>
  <h2><time datetime="{iso}">{tri(fmt_date(iso), fmt_date_th(iso), fmt_date_zh(iso))}</time></h2>
  <p class="tb en">{en}</p>
  <p class="tb th">{th}</p>
  <p class="tb zh">{zh}</p>
</article>"""
    dates = [
        block(
            "2015-09-14",
            "He started the blog. The rule was “Never a day without a line,” during the dissertation fog.",
            "เขาเริ่มบล็อก กฎคือ “ไม่มีวันใดไร้บรรทัด” ในหมอกของวิทยานิพนธ์",
            "他开始写这个博客。规矩是“没有一天没有一行”，是在学位论文的雾里。",
        ),
        block(
            "2025-04-15",
            "He returned to it, after little on the blog since 2019.",
            "เขากลับมาหาบันทึก หลังจากบนบล็อกมีน้อยนับแต่ปี 2019",
            "他回到这里。自2019年以来，博客上很少有新的东西。",
        ),
        block(
            "2026-10-04",
            "In his words, the diary is a real history of confusion. Looking back more than ten years, hindsight shows how far he has come. He describes his present as peace: writing made him Buddha, he has been to nirvana, and ecstasy is a daily thing.",
            "ตามคำของเขา บันทึกนี้เป็นประวัติศาสตร์จริงของความสับสน เมื่อมองย้อนกลับไปกว่าสิบปี การมองย้อนทำให้เห็นว่าเขามาไกลเพียงใด เขาบรรยายปัจจุบันของตนว่าเป็นความสงบ: การเขียนทำให้เขาเป็นพระพุทธะ เขาเคยถึงนิพพาน และความปีติเป็นเรื่องของทุกวัน",
            "用他的话说，这本日记是一段真实的困惑史。回看十多年，后见之明显示出他走了多远。他把现在描述为平静：写作使他成佛，他到过涅槃，狂喜是每日的事。",
        ),
    ]
    body = f"""<main class="sheet" id="content">
  <article class="entry">
    <div class="text">
      <p class="kicker">{tri("About", "เกี่ยวกับ", "关于")}</p>
      <h1>{tri("Three dates", "สามวัน", "三个日期")}</h1>
      <div class="about-dates">{''.join(dates)}</div>
    </div>
    {margin_html("hindsight")}
  </article>
</main>"""
    write(ROOT / "about" / "index.html", shell("About — Non Arkaraprasertkul", body))


def render_english_only(posts_located):
    links = {
        4: None,
        83: None,
        5144: None,
    }
    for d, rel, _ in posts_located:
        if d["ID"] in links:
            links[d["ID"]] = (unescape(d["title"]), rel, d["date"][:10])
    items = []
    for pid in (4, 83, 5144):
        title, rel, iso = links[pid]
        items.append(
            f'<li><a href="{rel}"><time datetime="{iso}">{esc(fmt_date(iso))}</time> <span class="ttl">{esc(title)}</span></a></li>'
        )
    en = "Thai and Chinese on this site cover the frame, the first entry, Day 9 (Three Years in Shanghai), and the return of 15 April 2025. The other one hundred and twenty-three entries stay in his English. This page is here so that absence is not mistaken for a finished translation."
    th = "ภาษาไทยและภาษาจีนบนไซต์นี้ครอบคลุมกรอบของไซต์ บันทึกชิ้นแรก วันที่ 9 (สามปีในเซี่ยงไฮ้) และการกลับมาในวันที่ 15 เมษายน 2025 อีกหนึ่งร้อยยี่สิบสามชิ้นคงเป็นภาษาอังกฤษของเขา หน้านี้มีไว้เพื่อไม่ให้การไม่มีคำแปลถูกเข้าใจว่าแปลจบแล้ว"
    zh = "本站的泰语和中文只覆盖站点的框架、第一篇、第9日（在上海的三年），以及2025年4月15日的归来。其余一百二十三篇仍是他的英文。这一页在这里，是为了不把“没有译文”误当成“已经译完”。"
    body = f"""<main class="sheet" id="content">
  <div class="entry no-margin">
    <div class="text">
      <p class="kicker">{tri("English only", "ยังเป็นภาษาอังกฤษ", "仅英文")}</p>
      <h1>{tri("What is translated", "สิ่งที่แปลแล้ว", "译了什么")}</h1>
      <div class="lede"><p class="tb en">{en}</p><p class="tb th">{th}</p><p class="tb zh">{zh}</p></div>
      <ol class="toc">{''.join(items)}</ol>
    </div>
  </div>
</main>"""
    write(ROOT / "english-only" / "index.html", shell("English only — Non Arkaraprasertkul", body))


def render_rooms():
    for slug, en, th, zh in ROOMS:
        body = f"""<main class="sheet room" id="content">
  <p class="kicker">{tri("Later room", "ห้องภายหลัง", "日后的房间")}</p>
  <h1>{tri(en, th, zh)}</h1>
  <div class="tb en"><p>No note has been sourced.</p></div>
  <div class="tb th"><p>ยังไม่มีบันทึกที่อ้างอิงได้</p></div>
  <div class="tb zh"><p>还没有可依据的笔记。</p></div>
</main>"""
        write(ROOT / "rooms" / slug / "index.html", shell(f"{en} — Non Arkaraprasertkul", body))


def render_404():
    body = f"""<main class="sheet" id="content">
  <p class="kicker">{tri("Diary", "บันทึก", "日记")}</p>
  <h1>{tri("This page is not in the diary.", "ไม่มีหน้านี้ในบันทึก", "日记里没有这一页。")}</h1>
  <p><a href="/">{tri("Back to the diary", "กลับไปที่บันทึก", "回到日记")}</a></p>
</main>"""
    write(ROOT / "404.html", shell("Not in the diary", body))


def render_sitemap(rels: list[str]) -> None:
    urls = [f"{SITE}/", f"{SITE}/about/", f"{SITE}/english-only/"]
    urls += [f"{SITE}{rel}" for rel in rels]
    urls += [f"{SITE}/rooms/{slug}/" for slug, *_ in ROOMS]
    body = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">\n"
    body += "\n".join(f"  <url><loc>{esc(u)}</loc></url>" for u in urls)
    body += "\n</urlset>\n"
    write(ROOT / "sitemap.xml", body)


def render_readme(posts, pages, changed_count):
    missing = sorted(UNMIRRORED)
    lines = "\n".join(f"- {u}" for u in missing) if missing else "- None."
    text = f"""# {SITE_HOST}

Public archive of the diary Non Arkaraprasertkul kept at [nonharvard.wordpress.com](https://nonharvard.wordpress.com).

This is not the fictional 100daysofnon project. It is the reading site for what he published there: {len(posts)} posts and {len(pages)} pages, from 14 September 2015 through 30 November 2025.

The reading copy mends grammar. The unedited original sits on the same page. Titles are unchanged, including “Daniel Kahmeman”. {changed_count} entries differ between the two copies; where they do not, only one text is shown.

Thai and Chinese cover the site frame, the first entry, Day 9 (Three Years in Shanghai), and the return of 15 April 2025. The other entries stay in his English.

The About page is three dates only: 14 September 2015, 15 April 2025, and 4 October 2026. The same later distance is in the margin of the first entry, the return, and About. The Shanghai entry’s margin is limited to the fieldwork note (resident from 21 June 2013, after visits 2006–2013; Jing’an Villa near Nanjing West Road) and the later reading edition at [shanghai.nonarkara.org](https://shanghai.nonarkara.org), which the 2015 post did not know.

Six later rooms are names only. They stay empty until a real sourced note exists.

## Images

Images used in the posts are mirrored under `media/` when the file could be fetched, so the diary can still be read if WordPress goes away. Hotlinked files that could not be fetched stay as remote URLs:

{lines}

## Pages

This is static HTML. There is no build step. `.nojekyll` is present so Jekyll does not rewrite the diary. `CNAME` is `{SITE_HOST}`.

GitHub Pages should serve the `main` branch from the site root (`/`). The publish token used here can push the files and cannot turn Pages on (the Pages API returned 403). Do not enable GitHub Pages through the API when it returns 403. Non must: Settings → Pages → Deploy from a branch → `main` → `/ (root)`, then add the custom domain `{SITE_HOST}`. Links in the HTML are root-absolute, for `{SITE_HOST}`, not for a `/blog/` project-site prefix.

`blog.nonarkara.org` already hosts a different Cloudflare Pages archive (“Dr Non ● Arkara — the archive”). Leave that hostname and that site alone.

Fonts are self-hosted (Source Serif 4, Noto Serif Thai, Noto Serif SC).

DNS, which only Non can set: CNAME name `diary` → `nonarkara.github.io`. After `{SITE_HOST}` resolves, HTTPS can be turned on in the repository’s GitHub Pages settings.

To rebuild from the WordPress export, unpack it and run `python3 tools/build_site.py` with the export at `/tmp/wp-export`. The generator does not publish account metadata from the export.
"""
    write(ROOT / "README.md", text)


def main() -> None:
    if not EXPORT.exists():
        sys.exit(f"missing export at {EXPORT}")
    tool = None
    try:
        import language_tool_python

        tool = language_tool_python.LanguageTool("en-US")
        print("LanguageTool ready")
    except Exception as exc:
        print("LanguageTool unavailable, punctuation and hand fixes only:", exc)
    cache_path = Path("/tmp/lt_cache.json")
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    posts, pages = load_entries()
    located, href_map = entry_paths(posts, pages)
    post_located = [x for x in located if x[2] == "post"]
    page_located = [x for x in located if x[2] == "page"]
    changed = 0
    margins = {4: "hindsight", 83: "shanghai", 5144: "hindsight"}
    for i, (d, rel, kind) in enumerate(post_located):
        prev_item = post_located[i - 1] if i else None
        next_item = post_located[i + 1] if i + 1 < len(post_located) else None
        if render_entry(d, rel, kind, tool, cache, href_map, prev_item, next_item, margins.get(d["ID"])):
            changed += 1
        if (i + 1) % 20 == 0:
            print("posts", i + 1, "grammar edits", len(GRAMMAR_LOG))
            cache_path.write_text(json.dumps(cache))
    for d, rel, kind in page_located:
        if render_entry(d, rel, kind, tool, cache, href_map, None, None, None):
            changed += 1
    cache_path.write_text(json.dumps(cache))
    Path("/tmp/grammar.log").write_text("\n".join(GRAMMAR_LOG) + "\n", encoding="utf-8")
    render_index(post_located, page_located)
    render_about()
    render_english_only(post_located)
    render_rooms()
    render_404()
    render_sitemap([rel for _, rel, _ in located])
    (ROOT / ".nojekyll").write_text("")
    (ROOT / "CNAME").write_text(SITE_HOST + "\n")
    render_readme(posts, pages, changed)
    print("posts", len(posts), "pages", len(pages), "changed", changed)
    print("unmirrored", len(UNMIRRORED))
    print("grammar edits", len(GRAMMAR_LOG))


if __name__ == "__main__":
    main()
