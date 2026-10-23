"""Optional extras saved next to a download: description (HTML, links clickable) and
transcript (plain text from subtitles). No Qt imports; pure functions plus small file writers."""
from __future__ import annotations

import html
import re
from urllib.parse import quote
from pathlib import Path
from typing import Iterable, List, Optional

_URL = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
_TAG = re.compile(r"<[^>]*>")
_STAMP = re.compile(r"^(\s*)((?:(\d{1,2}):)?(\d{1,2}):(\d{2}))(?=\s|$)")
_TIMING = re.compile(r"^\s*(?:\d+:)?\d{1,2}:\d{2}[.,]\d{3}\s+-->\s+")


def has_description(info: Optional[dict]) -> bool:
    return bool(info and str(info.get("description") or "").strip())


def has_transcript(info: Optional[dict]) -> bool:
    return bool(info and (info.get("subtitles") or info.get("automatic_captions")))


def _linkify(escaped: str) -> str:
    def repl(match: "re.Match[str]") -> str:
        url = match.group(0)
        tail = ""
        while url and url[-1] in ".,;:!?)]":
            tail = url[-1] + tail
            url = url[:-1]
        return f'<a href="{url}" target="_blank" rel="noopener noreferrer">{url}</a>{tail}'
    return _URL.sub(repl, escaped)


def embed_url(info: dict) -> str:
    """Official embeddable player URL for sites that offer one (YouTube, Vimeo), else ''."""
    vid = str(info.get("id") or "")
    site = str(info.get("extractor_key") or info.get("extractor") or "").lower()
    if site.startswith("youtube") and re.fullmatch(r"[\w-]{11}", vid):
        return f"https://www.youtube-nocookie.com/embed/{vid}"
    if site == "vimeo" and vid.isdigit():
        return f"https://player.vimeo.com/video/{vid}"
    return ""


def description_html(info: dict, media_name: str = "", media_kind: str = "video",
                     online_player: bool = False, theme: str = "auto", lyrics: Optional[dict] = None) -> str:
    """Standalone HTML page with the description (http(s) links clickable). When `media_name`
    is given, the file next to the page is embedded as a player (relative link)."""
    title = html.escape(str(info.get("title") or "Description"))
    meta = []
    if info.get("uploader") or info.get("channel"):
        meta.append(html.escape(str(info.get("uploader") or info.get("channel"))))
    date = str(info.get("upload_date") or "")
    if re.fullmatch(r"\d{8}", date):
        meta.append(f"{date[:4]}-{date[4:6]}-{date[6:]}")
    source = str(info.get("webpage_url") or "")
    if source.startswith(("http://", "https://")):
        meta.append(_linkify(html.escape(source)))
    player = ""
    if media_name:
        tag = "audio" if media_kind == "audio" else "video"
        src = html.escape(quote(media_name), quote=True)
        player = (f'<{tag} controls preload="metadata" src="{src}"></{tag}>\n'
                  f'<p class="meta"><a href="{src}">{html.escape(media_name)}</a></p>\n')
    embed = embed_url(info) if online_player else ""
    if embed:   # online player first (like on the site); the local file player stays below
        page = html.escape(source, quote=True)
        poster = ""
        if "youtube" in embed:   # shown instead of the player when the page is opened from disk
            poster = f'<img src="https://i.ytimg.com/vi/{html.escape(str(info.get("id")))}/hqdefault.jpg" alt="">'
        try:   # portrait/square videos: no black side bars, the frame follows the real aspect ratio
            vw, vh = float(info.get("width") or 0), float(info.get("height") or 0)
        except (TypeError, ValueError):
            vw = vh = 0.0
        ar = f' style="--ar:{vw:g}/{vh:g};width:min(100%,calc(85vh*{vw:g}/{vh:g}))"' if vw and vh and vh > vw * 0.99 else ""
        player = (f'<div class="embed" id="online"{ar} data-src="{html.escape(embed, quote=True)}" '
                  f'data-title="{title}">'
                  f'<a class="poster" href="{page}" target="_blank" rel="noopener noreferrer">{poster}'
                  '<span>&#9654; Watch on the original site</span></a></div>\n'
                  '<p class="meta">Online player (needs internet). It plays inside this page when it is opened '
                  'with "Open page" in Yeal; opened from disk, the picture links to the original site.</p>\n'
                  '<script>(function(){var b=document.getElementById("online");'
                  'if(!/^https?:$/.test(location.protocol))return;'
                  'var f=document.createElement("iframe");f.src=b.dataset.src;f.title=b.dataset.title;'
                  'f.allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; fullscreen";'
                  'f.allowFullscreen=true;f.referrerPolicy="strict-origin-when-cross-origin";'
                  'b.replaceChildren(f)})();</script>\n'
                  + player)
    lines = _linkify(html.escape(str(info.get("description") or ""))).replace("\r\n", "\n").split("\n")
    tracks = len(info.get("chapters") or []) >= 2
    if tracks:   # tracklist: every leading timestamp jumps to that position in the player
        def stamp(line: str) -> str:
            m = _STAMP.match(line)
            if not m:
                return line
            secs = int(m.group(3) or 0) * 3600 + int(m.group(4)) * 60 + int(m.group(5))
            return f'{m.group(1)}<a href="#" class="ts" data-t="{secs}">{m.group(2)}</a>' + line[m.end():]
        lines = [stamp(ln) for ln in lines]
    body = "<br>\n".join(lines)
    seek = ""
    if tracks:
        seek = ('<script>document.addEventListener("click",function(e){var a=e.target.closest(".ts");'
                'if(!a)return;e.preventDefault();var t=+a.dataset.t;'
                'var m=document.querySelector("video,audio");'
                'if(m){m.currentTime=t;m.play();m.scrollIntoView({block:"nearest"})}'
                'var f=document.querySelector("#online iframe");'
                'if(f){var u=new URL(f.src);u.searchParams.set("start",t);u.searchParams.set("autoplay","1");f.src=u.href}'
                '});</script>\n')
    lyr = ""
    if lyrics and lyrics.get("plain"):
        from . import lyrics as lyr_mod   # local import: keeps extras importable on its own
        rows = lyr_mod.parse_lrc(lyrics.get("synced", ""))
        note = " (from captions)" if lyrics.get("source") == "captions" else ""
        if rows:
            items = "".join(f'<p class="ly" data-t="{t:.2f}">{html.escape(x) or "&nbsp;"}</p>' for t, x in rows)
        else:
            items = "".join(f"<p>{html.escape(x) or '&nbsp;'}</p>" for x in lyrics["plain"].splitlines())
        lyr = (f'<h2>Lyrics{note}</h2>\n<div id="lyrics">{items}</div>\n'
               '<script>(function(){var L=document.querySelectorAll(".ly");if(!L.length)return;'
               'var m=document.querySelector("video,audio"),cur=-1;'
               'function t(i){return +L[i].dataset.t}'
               'if(m)m.addEventListener("timeupdate",function(){var i=-1;'
               'for(var k=0;k<L.length;k++){if(t(k)<=m.currentTime)i=k;else break}'
               'if(i!==cur){if(cur>=0)L[cur].classList.remove("on");cur=i;'
               'if(i>=0){L[i].classList.add("on");L[i].scrollIntoView({block:"nearest",behavior:"smooth"})}}});'
               'document.getElementById("lyrics").addEventListener("click",function(e){'
               'var p=e.target.closest(".ly");if(!p)return;var s=+p.dataset.t;'
               'if(m){m.currentTime=s;m.play()}'
               'var f=document.querySelector("#online iframe");'
               'if(f){var u=new URL(f.src);u.searchParams.set("start",Math.floor(s));u.searchParams.set("autoplay","1");f.src=u.href}'
               '})})();</script>\n')
    css_vars = ("color:#1d1d1f;background:#fff", ".meta{color:#6e6e73}a{color:#0071e3}")
    dark_vars = ("color:#f5f5f7;background:#121214", ".meta{color:#a1a1a6}a{color:#2997ff}")
    if theme == "dark":
        theme_css, scheme = f"html{{color-scheme:dark}}body{{{dark_vars[0]}}}{dark_vars[1]}", "dark"
    elif theme == "light":
        theme_css, scheme = f"html{{color-scheme:light}}body{{{css_vars[0]}}}{css_vars[1]}", "light"
    else:
        theme_css = (f"body{{{css_vars[0]}}}{css_vars[1]}@media(prefers-color-scheme:dark)"
                     f"{{body{{{dark_vars[0]}}}{dark_vars[1]}}}")
        scheme = "light dark"
    return (
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f'<meta name="color-scheme" content="{scheme}">\n'
        f"<title>{title}</title>\n<style>\n"
        "body{font:16px/1.55 system-ui,sans-serif;max-width:46rem;margin:2rem auto;padding:0 1rem;"
        "}h1{font-size:1.5rem}.meta{font-size:.9rem}"
        "audio{width:100%;border-radius:12px;height:3rem}"
        "video{display:block;width:auto;height:auto;max-width:100%;max-height:85vh;margin:0 auto;border-radius:12px}"
        ".embed{position:relative;aspect-ratio:var(--ar,16/9);max-width:100%;max-height:85vh;margin:0 auto;"
        "border-radius:12px;overflow:hidden;background:#000}"
        ".embed iframe,.embed .poster{position:absolute;inset:0;width:100%;height:100%;border:0}"
        ".poster{display:flex;align-items:center;justify-content:center;color:#fff;text-decoration:none;font-weight:600}"
        ".poster img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:.7}"
        "#lyrics .ly{cursor:pointer;margin:.15rem 0;padding:.1rem .4rem;border-radius:6px;opacity:.75}"
        "#lyrics .ly.on{opacity:1;font-weight:600;background:#8884}#lyrics p{margin:.15rem 0}"
        ".poster span{position:relative;background:#000a;padding:.6rem 1rem;border-radius:999px}"
        f"{theme_css}\n</style>\n</head>\n<body>\n"
        f"<h1>{title}</h1>\n<p class=\"meta\">{' &middot; '.join(meta)}</p>\n{player}"
        f"<div>\n{body}\n</div>\n{lyr}{seek}</body>\n</html>\n")


def playlist_html(title: str, uploader: str, source: str, items: List[dict],
                  media_kind: str = "video", theme: str = "auto") -> str:
    """Standalone page for a downloaded playlist: one player, the track list below it. A click on an entry
    plays that file (relative links, so the page works from the playlist folder), the next entry follows
    automatically. items: [{index, title, duration, file, page}] - `file` '' = not downloaded (greyed out),
    `page` = the entry's own description page, if one was saved."""
    esc = html.escape
    tag = "audio" if media_kind == "audio" else "video"
    rows = []
    for it in items:
        f = str(it.get("file") or "")
        page = str(it.get("page") or "")
        dur = esc(str(it.get("duration") or ""))
        link = f' <a class="pg" href="{esc(quote(page), quote=True)}" title="Description">&#9432;</a>' if page else ""
        if f:
            rows.append(f'<li class="it" data-src="{esc(quote(f), quote=True)}"><span class="n">{int(it.get("index") or 0)}</span>'
                        f'<span class="t">{esc(str(it.get("title") or f))}</span><span class="d">{dur}</span>{link}</li>')
        else:
            rows.append(f'<li class="it off"><span class="n">{int(it.get("index") or 0)}</span>'
                        f'<span class="t">{esc(str(it.get("title") or ""))}</span><span class="d">not downloaded</span></li>')
    meta = []
    if uploader:
        meta.append(esc(uploader))
    meta.append(f"{sum(1 for i in items if i.get('file'))} of {len(items)} items")
    if source.startswith(("http://", "https://")):
        meta.append(_linkify(esc(source)))
    light = ("color:#1d1d1f;background:#fff", ".meta,.d,.n{color:#6e6e73}a{color:#0071e3}.it:hover{background:#0000000d}.it.on{background:#0071e322}")
    dark = ("color:#f5f5f7;background:#121214", ".meta,.d,.n{color:#a1a1a6}a{color:#2997ff}.it:hover{background:#ffffff14}.it.on{background:#2997ff33}")
    if theme == "dark":
        theme_css, scheme = f"html{{color-scheme:dark}}body{{{dark[0]}}}{dark[1]}", "dark"
    elif theme == "light":
        theme_css, scheme = f"html{{color-scheme:light}}body{{{light[0]}}}{light[1]}", "light"
    else:
        theme_css = (f"body{{{light[0]}}}{light[1]}@media(prefers-color-scheme:dark){{body{{{dark[0]}}}{dark[1]}}}")
        scheme = "light dark"
    return (
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f'<meta name="color-scheme" content="{scheme}">\n<title>{esc(title)}</title>\n<style>\n'
        "body{font:16px/1.55 system-ui,sans-serif;max-width:50rem;margin:2rem auto;padding:0 1rem}"
        "h1{font-size:1.5rem}.meta{font-size:.9rem}"
        "#p{position:sticky;top:0;z-index:1;padding:.5rem 0;background:inherit}"
        "audio{width:100%;height:3rem;border-radius:12px}"
        "video{display:block;width:100%;max-height:60vh;border-radius:12px;background:#000}"
        "ol{list-style:none;margin:0;padding:0}"
        ".it{display:flex;gap:.75rem;align-items:baseline;padding:.45rem .6rem;border-radius:8px;cursor:pointer}"
        ".it.off{opacity:.45;cursor:default}.it .t{flex:1;min-width:0;overflow-wrap:anywhere}"
        ".n{min-width:2rem;text-align:right;font-variant-numeric:tabular-nums}.d{font-size:.85rem}.pg{text-decoration:none}"
        f"{theme_css}\n</style>\n</head>\n<body>\n<h1>{esc(title)}</h1>\n"
        f'<p class="meta">{" &middot; ".join(meta)}</p>\n'
        f'<div id="p"><{tag} id="m" controls preload="metadata"></{tag}></div>\n'
        f'<ol>\n{chr(10).join(rows)}\n</ol>\n'
        '<script>(function(){var m=document.getElementById("m"),L=[].slice.call(document.querySelectorAll(".it[data-src]")),cur=-1;'
        'function go(i){if(i<0||i>=L.length)return;if(cur>=0)L[cur].classList.remove("on");cur=i;L[i].classList.add("on");'
        'm.src=L[i].dataset.src;m.play();L[i].scrollIntoView({block:"nearest"})}'
        'L.forEach(function(e,i){e.addEventListener("click",function(ev){if(ev.target.closest(".pg"))return;go(i)})});'
        'm.addEventListener("ended",function(){go(cur+1)});'
        'if(L.length){m.src=L[0].dataset.src;L[0].classList.add("on");cur=0}})();</script>\n</body>\n</html>\n')


def write_playlist_page(folder: Path, title: str, uploader: str, source: str, items: List[dict],
                        media_kind: str = "video", theme: str = "auto") -> Optional[Path]:
    """Write `<folder>/<folder name>.html` (the playlist page). Returns its path, None on a write error."""
    page = Path(folder) / (Path(folder).name + ".html")
    try:
        page.write_text(playlist_html(title, uploader, source, items, media_kind, theme), encoding="utf-8")
    except OSError:
        return None
    return page


def subtitle_to_text(raw: str) -> str:
    """Convert WebVTT/SRT text to plain text; drops timing, tags and rolling duplicates."""
    lines: List[str] = []
    for line in raw.replace("\r\n", "\n").split("\n"):
        stripped = line.strip()
        if (not stripped or stripped.startswith(("WEBVTT", "NOTE", "STYLE", "Kind:", "Language:"))
                or _TIMING.match(stripped) or stripped.isdigit()):
            continue
        text = html.unescape(_TAG.sub("", stripped)).strip()
        if text and (not lines or lines[-1] != text):
            lines.append(text)
    return "\n".join(lines) + ("\n" if lines else "")


def pick_subtitle(info: dict, langs: Iterable[str]) -> str:
    """Path of the downloaded subtitle file to use for the transcript ('' if none)."""
    found = info.get("requested_subtitles") or {}
    for lang in list(langs) + list(found):
        entry = found.get(lang)
        if entry and entry.get("filepath") and Path(entry["filepath"]).exists():
            return str(entry["filepath"])
    return ""


def write_extras(info: dict, video_path: str, want_description: bool, want_transcript: bool,
                 langs: Iterable[str], keep_subtitles: bool, media_kind: str = "video",
                 online_player: bool = False, theme: str = "auto",
                 lyrics: Optional[dict] = None) -> tuple[bool, bool]:
    """Write the requested extras next to `video_path`, with the same base name
    (`name.html`, `name.txt`) so the page's embedded player finds the media file.
    Returns (description_saved, transcript_saved)."""
    base = Path(video_path).with_suffix("")
    saved_desc = saved_tr = False
    try:
        if (want_description and has_description(info)) or (online_player and embed_url(info)):
            base.with_name(base.name + ".html").write_text(
                description_html(info, Path(video_path).name, media_kind, online_player, theme, lyrics), encoding="utf-8")
            saved_desc = True
        sub = pick_subtitle(info, langs) if want_transcript else ""
        if sub:
            text = subtitle_to_text(Path(sub).read_text(encoding="utf-8", errors="replace"))
            if text:
                base.with_name(base.name + ".txt").write_text(text, encoding="utf-8")
                saved_tr = True
        if want_transcript and not keep_subtitles:
            for entry in (info.get("requested_subtitles") or {}).values():
                path = entry.get("filepath")
                if path and Path(path).exists():
                    Path(path).unlink()
    except OSError:
        pass
    return saved_desc, saved_tr
