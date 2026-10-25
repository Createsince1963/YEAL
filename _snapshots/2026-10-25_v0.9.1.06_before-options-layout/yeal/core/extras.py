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
    if info.get("playable_in_embed") is False:      # the owner (often label / VEVO videos) forbids embedding
        return ""
    if site.startswith("youtube") and re.fullmatch(r"[\w-]{11}", vid):
        return f"https://www.youtube-nocookie.com/embed/{vid}"
    if site == "vimeo" and vid.isdigit():
        return f"https://player.vimeo.com/video/{vid}"
    return ""


# Only one player at a time on a description page: the local <audio>/<video> and the online YouTube player
# pause each other. The iframe is controlled and observed through YouTube's postMessage API.
_SINGLE_PLAYBACK_JS = (
    '<script>(function(){'
    'function media(){return[].slice.call(document.querySelectorAll("audio,video"))}'
    'function frame(){return document.querySelector("#online iframe")}'
    'function send(o){var f=frame();if(f&&f.contentWindow){try{f.contentWindow.postMessage(JSON.stringify(o),"*")}catch(e){}}}'
    'function pauseOnline(){send({event:"command",func:"pauseVideo",args:""})}'
    'function listen(){send({event:"listening",id:1,channel:"widget"})}'
    'window.yealOnline=function(){return!!frame()};'
    'document.addEventListener("play",function(e){media().forEach(function(m){if(m!==e.target)m.pause()});pauseOnline()},true);'
    'window.addEventListener("message",function(e){var f=frame();if(!f||e.source!==f.contentWindow)return;'
    'var d=e.data;if(typeof d==="string"){try{d=JSON.parse(d)}catch(x){return}}if(!d)return;'
    'if((d.event==="onStateChange"&&d.info===1)||(d.event==="infoDelivery"&&d.info&&d.info.playerState===1))'
    'media().forEach(function(m){m.pause()})});'
    'var f=frame();if(f){f.addEventListener("load",listen);listen()}'
    '})();</script>\n')


def description_html(info: dict, media_name: str = "", media_kind: str = "video",
                     online_player: bool = False, theme: str = "auto", lyrics: Optional[dict] = None,
                     flavour: str = "server", sibling: str = "", single_playback: bool = True) -> str:
    """Standalone HTML page with the description (http(s) links clickable). When `media_name`
    is given, the file next to the page is embedded as a player (relative link: only the file name, the
    page and the media always sit in the same folder). `flavour`: "server" plays the online player when the
    page is opened over http (Yeal's local server); "file" never embeds it (works from disk, offline).
    `sibling` = file name of the other flavour in the same folder; a relative link to it is shown on top.
    `single_playback`: the local player and the online YouTube player never play at the same time."""
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
    single = bool(single_playback and embed and flavour != "file")     # only then two players can exist on the page
    single = single and "youtube" in embed          # the pause bridge is YouTube only
    if single:
        embed += "?enablejsapi=1"      # lets the page pause / observe the YouTube player
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
    if flavour == "file" and "<script>" in player:      # standalone page: no iframe script, no server hint
        i = player.index("<script>")
        j = player.index("</script>\n", i) + len("</script>\n")
        player = player[:i] + player[j:]
        player = player.replace(
            'It plays inside this page when it is opened with "Open page" in Yeal; opened from disk, the picture links to the original site.',
            "This standalone page works from disk without Yeal; the picture links to the original site.")
    nav = ""
    if sibling:
        label = "Standalone version (file, works offline)" if flavour != "file" else "Online version (needs Yeal's local server)"
        nav = f'<p class="meta"><a href="{html.escape(quote(sibling), quote=True)}">{label}</a></p>\n'
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
                'if(m){m.currentTime=t;if(!(window.yealOnline&&window.yealOnline()))m.play();m.scrollIntoView({block:"nearest"})}'
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
               'if(m){m.currentTime=s;if(!(window.yealOnline&&window.yealOnline()))m.play()}'
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
        f"<h1>{title}</h1>\n<p class=\"meta\">{' &middot; '.join(meta)}</p>\n{nav}{player}"
        f"<div>\n{body}\n</div>\n{lyr}{seek}{_SINGLE_PLAYBACK_JS if single else ''}</body>\n</html>\n")


def playlist_html(title: str, uploader: str, source: str, items: List[dict],
                  media_kind: str = "video", theme: str = "auto") -> str:
    """Standalone page for a downloaded playlist (a different layout than the single-video page).
    Video: sticky player on top, a grid of thumbnail tiles below. Audio: cover header with Play/Shuffle and a
    track list with covers, the player bar stays at the top. A click plays that file (relative links, so the page
    works from the playlist folder), the next entry follows automatically. A filter box searches the titles.
    items: [{index, title, duration, file, page, thumb}] - `file` '' = not downloaded (greyed out),
    `page` = the entry's own description page, `thumb` = https thumbnail address (optional)."""
    esc = html.escape
    audio = media_kind == "audio"
    tag = "audio" if audio else "video"

    def thumb_of(it: dict) -> str:
        t = str(it.get("thumb") or "")
        return t if t.startswith("https://") else ""

    rows = []
    for it in items:
        f = str(it.get("file") or "")
        page = str(it.get("page") or "")
        dur = esc(str(it.get("duration") or ""))
        ttl = esc(str(it.get("title") or f))
        n = int(it.get("index") or 0)
        th = thumb_of(it)
        img = (f'<img src="{esc(th, quote=True)}" alt="" loading="lazy" referrerpolicy="no-referrer" '
               'onerror="this.style.visibility=\'hidden\'">') if th else ""
        link = f'<a class="pg" href="{esc(quote(page), quote=True)}" title="Description">&#9432;</a>' if page else ""
        if f:
            rows.append(f'<li class="it" data-src="{esc(quote(f), quote=True)}" data-t="{esc(ttl.lower(), quote=True)}">'
                        f'<span class="n">{n}</span><span class="c">{img}<i class="d">{dur}</i></span>'
                        f'<span class="t">{ttl}</span>{link}</li>')
        else:
            rows.append(f'<li class="it off" data-t="{esc(ttl.lower(), quote=True)}"><span class="n">{n}</span>'
                        f'<span class="c">{img}</span><span class="t">{ttl}</span><span class="x">not downloaded</span></li>')
    got = sum(1 for i in items if i.get("file"))
    meta = []
    if uploader:
        meta.append(esc(uploader))
    meta.append(f"{got} of {len(items)} items")
    if source.startswith(("http://", "https://")):
        meta.append(_linkify(esc(source)))
    cover = next((thumb_of(i) for i in items if thumb_of(i)), "")
    cover_html = (f'<img class="cv" src="{esc(cover, quote=True)}" alt="" referrerpolicy="no-referrer" '
                  'onerror="this.style.display=\'none\'">') if (audio and cover) else ""
    light = ("color:#1d1d1f;background:#fff", ".meta,.d,.n,.x{color:#6e6e73}a{color:#0071e3}.it:hover{background:#0000000d}"
             ".it.on{background:#0071e322}.c{background:#e5e5ea}input,button{background:#f2f2f7;color:#1d1d1f}")
    dark = ("color:#f5f5f7;background:#121214", ".meta,.d,.n,.x{color:#a1a1a6}a{color:#2997ff}.it:hover{background:#ffffff14}"
            ".it.on{background:#2997ff33}.c{background:#2c2c2e}input,button{background:#2c2c2e;color:#f5f5f7}")
    if theme == "dark":
        theme_css, scheme = f"html{{color-scheme:dark}}body{{{dark[0]}}}{dark[1]}", "dark"
    elif theme == "light":
        theme_css, scheme = f"html{{color-scheme:light}}body{{{light[0]}}}{light[1]}", "light"
    else:
        theme_css = (f"body{{{light[0]}}}{light[1]}@media(prefers-color-scheme:dark){{body{{{dark[0]}}}{dark[1]}}}")
        scheme = "light dark"
    layout = (
        # audio: list rows with small square covers
        "ol.a{display:block}.a .it{display:flex;gap:.75rem;align-items:center;padding:.4rem .6rem}"
        ".a .c{width:3rem;height:3rem;flex:none}.a .c i{display:none}.a .t{flex:1;min-width:0;overflow-wrap:anywhere}"
        ".a .n{min-width:2rem;text-align:right}"
        ".hd{display:flex;gap:1.25rem;align-items:flex-end;margin-bottom:.5rem}.cv{width:9rem;height:9rem;object-fit:cover;border-radius:14px}"
        if audio else
        # video: grid of 16:9 tiles
        "ol.v{display:grid;grid-template-columns:repeat(auto-fill,minmax(14rem,1fr));gap:1rem}"
        ".v .it{display:flex;flex-direction:column;gap:.4rem;padding:.4rem}.v .c{aspect-ratio:16/9;width:100%}"
        ".v .c i{position:absolute;right:.4rem;bottom:.4rem;background:#000b;color:#fff;border-radius:5px;padding:0 .35rem;font-style:normal}"
        ".v .n{position:absolute;left:.4rem;top:.4rem;z-index:1;background:#000b;color:#fff;border-radius:5px;padding:0 .35rem;min-width:0}"
        ".v .it{position:relative}.v .t{font-size:.95rem;line-height:1.3;max-height:2.6em;overflow:hidden}"
    )
    return (
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f'<meta name="color-scheme" content="{scheme}">\n<title>{esc(title)}</title>\n<style>\n'
        f"body{{font:16px/1.5 system-ui,sans-serif;max-width:{'50rem' if audio else '72rem'};margin:1.5rem auto;padding:0 1rem}}"
        "h1{font-size:1.5rem;margin:.2rem 0}.meta{font-size:.9rem;margin:.2rem 0}"
        "#p{position:sticky;top:0;z-index:2;padding:.5rem 0;background:inherit}"
        "audio{width:100%;height:3rem;border-radius:12px}"
        "video{display:block;width:100%;max-height:55vh;border-radius:12px;background:#000}"
        ".bar{display:flex;gap:.5rem;margin:.6rem 0 1rem;flex-wrap:wrap}"
        "input,button{border:0;border-radius:10px;padding:.5rem .8rem;font:inherit}input{flex:1;min-width:10rem}button{cursor:pointer}"
        "ol{list-style:none;margin:0;padding:0}.it{border-radius:10px;cursor:pointer}"
        ".c{position:relative;border-radius:8px;overflow:hidden;display:block}.c img{width:100%;height:100%;object-fit:cover;display:block}"
        ".it.off{opacity:.45;cursor:default}.d,.x{font-size:.85rem}.n{font-variant-numeric:tabular-nums}.pg{text-decoration:none}"
        f"{layout}{theme_css}\n</style>\n</head>\n<body>\n"
        f'<div class="hd">{cover_html}<div><h1>{esc(title)}</h1>\n<p class="meta">{" &middot; ".join(meta)}</p></div></div>\n'
        f'<div id="p"><{tag} id="m" controls preload="metadata"></{tag}></div>\n'
        '<div class="bar"><button id="all" type="button">&#9654; Play all</button><button id="shuf" type="button">&#128256; Shuffle</button>'
        '<input id="q" type="search" placeholder="Filter titles" aria-label="Filter titles"></div>\n'
        f'<ol class="{"a" if audio else "v"}" id="l">\n{chr(10).join(rows)}\n</ol>\n'
        '<script>(function(){var m=document.getElementById("m"),L=[].slice.call(document.querySelectorAll(".it[data-src]")),cur=-1,order=null;'
        'function vis(e){return e.style.display!=="none"}'
        'function go(i){if(i<0||i>=L.length)return;if(cur>=0)L[cur].classList.remove("on");cur=i;L[i].classList.add("on");'
        'm.src=L[i].dataset.src;m.play();L[i].scrollIntoView({block:"nearest"})}'
        'function next(){var a=order||L.map(function(_,i){return i});var p=a.indexOf(cur);'
        'for(var k=p+1;k<a.length;k++){if(vis(L[a[k]])){go(a[k]);return}}}'
        'L.forEach(function(e,i){e.addEventListener("click",function(ev){if(ev.target.closest(".pg"))return;go(i)})});'
        'm.addEventListener("ended",next);'
        'document.getElementById("all").onclick=function(){order=null;var f=L.findIndex(vis);if(f>=0)go(f)};'
        'document.getElementById("shuf").onclick=function(){order=L.map(function(_,i){return i}).sort(function(){return Math.random()-.5});'
        'var f=order.find(function(i){return vis(L[i])});if(f!==undefined)go(f)};'
        'document.getElementById("q").oninput=function(){var s=this.value.toLowerCase();'
        '[].slice.call(document.querySelectorAll("#l .it")).forEach(function(e){e.style.display=e.dataset.t.indexOf(s)<0?"none":""})};'
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
                 lyrics: Optional[dict] = None, html_create: str = "both",
                 single_playback: bool = True) -> tuple[bool, bool]:
    """Write the requested extras next to `video_path`, with the same base name
    (`name.html`, `name.txt`) so the page's embedded player finds the media file.
    Returns (description_saved, transcript_saved)."""
    base = Path(video_path).with_suffix("")
    saved_desc = saved_tr = False
    try:
        if (want_description and has_description(info)) or (online_player and embed_url(info)):
            name = Path(video_path).name          # links are always the bare file name (same folder)
            main = base.with_name(base.name + ".html")
            alt = base.with_name(base.name + ".file.html")
            two = html_create == "both" and bool(online_player and embed_url(info))   # a 2nd page only differs by the embed
            flavour = "file" if html_create == "file" else "server"
            main.write_text(description_html(info, name, media_kind, online_player, theme, lyrics, flavour,
                                             alt.name if two else "", single_playback), encoding="utf-8")
            if two:
                alt.write_text(description_html(info, name, media_kind, online_player, theme, lyrics, "file",
                                                main.name, single_playback), encoding="utf-8")
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


def _mmss(seconds) -> str:
    try:
        s = int(seconds or 0)
    except (TypeError, ValueError):
        return ""
    return "%d:%02d:%02d" % (s // 3600, s % 3600 // 60, s % 60) if s >= 3600 else "%d:%02d" % (s // 60, s % 60)


def tidal_linklist_html(info: dict) -> str:
    """Standalone page with the tracks of a Tidal playlist / album / mix as links to Tidal (TIDAL DIY, 0.9.1).
    Nothing is downloaded: every title opens on tidal.com (or in the TIDAL app). info: the dict of
    core.tidal_api (title, subtitle, cover, url, duration, items=[track dicts])."""
    esc = html.escape
    items = [it for it in info.get("items") or [] if isinstance(it, dict)]
    title = esc(str(info.get("title") or "TIDAL"))
    by = esc(str(info.get("subtitle") or ""))
    url = str(info.get("url") or "")
    cover = str(info.get("coverLarge") or info.get("cover") or "")
    total = sum(int(it.get("duration") or 0) for it in items) or int(info.get("duration") or 0)
    rows = []
    for n, it in enumerate(items, 1):
        link = str(it.get("url") or "")
        if not link.startswith("https://"):
            continue
        img = str(it.get("cover") or "")
        pic = (f'<img src="{esc(img, quote=True)}" alt="" loading="lazy" referrerpolicy="no-referrer">'
               if img.startswith("https://") else "")
        ttl = esc(str(it.get("title") or ""))
        art = esc(str(it.get("subtitle") or ""))
        alb = esc(str(it.get("album") or ""))
        rows.append(f'<li data-t="{esc((str(it.get("title") or "") + " " + str(it.get("subtitle") or "")).lower(), quote=True)}">'
                    f'<span class="n">{n}</span><span class="c">{pic}</span>'
                    f'<a class="t" href="{esc(link, quote=True)}" target="_blank" rel="noopener noreferrer">{ttl}'
                    f'<small>{art}{" &middot; " + alb if alb else ""}</small></a>'
                    f'<span class="d">{esc(_mmss(it.get("duration")))}</span></li>')
    head_img = (f'<img class="cv" src="{esc(cover, quote=True)}" alt="" referrerpolicy="no-referrer">'
                if cover.startswith("https://") else "")
    open_btn = (f'<a class="btn" href="{esc(url, quote=True)}" target="_blank" rel="noopener noreferrer">Open in TIDAL</a>'
                if url.startswith("https://") else "")
    meta = " &middot; ".join(x for x in (by, f"{len(rows)} titles", esc(_mmss(total)) if total else "") if x)
    return ("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
            "<meta name=\"color-scheme\" content=\"light dark\">\n"
            f"<title>{title}</title>\n<style>\n"
            "body{font:15px/1.45 system-ui,sans-serif;max-width:56rem;margin:1.5rem auto;padding:0 1rem;color:#1d1d1f;background:#fff}"
            "h1{font-size:1.5rem;margin:.2rem 0}.meta,small,.d,.n{color:#6e6e73}.hd{display:flex;gap:1.25rem;align-items:flex-end;margin-bottom:1rem}"
            ".cv{width:8rem;height:8rem;object-fit:cover;border-radius:12px}.bar{display:flex;gap:.5rem;flex-wrap:wrap;margin:.6rem 0 1rem}"
            "input,button,.btn{border:0;border-radius:10px;padding:.5rem .8rem;font:inherit;background:#f2f2f7;color:#1d1d1f;text-decoration:none;cursor:pointer}"
            "input{flex:1;min-width:10rem;cursor:text}ol{list-style:none;margin:0;padding:0}"
            "li{display:flex;gap:.75rem;align-items:center;padding:.35rem .5rem;border-radius:10px}li:hover{background:#0000000d}"
            ".n{min-width:2rem;text-align:right;font-variant-numeric:tabular-nums}.c{width:2.6rem;height:2.6rem;flex:none;border-radius:6px;overflow:hidden;background:#e5e5ea}"
            ".c img{width:100%;height:100%;object-fit:cover}.t{flex:1;min-width:0;color:inherit;text-decoration:none;overflow-wrap:anywhere}"
            ".t small{display:block;font-size:.85rem}.d{font-variant-numeric:tabular-nums}a.t:hover{color:#0071e3}"
            "@media(prefers-color-scheme:dark){body{color:#f5f5f7;background:#121214}.meta,small,.d,.n{color:#a1a1a6}"
            "input,button,.btn{background:#2c2c2e;color:#f5f5f7}li:hover{background:#ffffff14}.c{background:#2c2c2e}a.t:hover{color:#2997ff}}\n"
            "</style>\n</head>\n<body>\n"
            f"<div class=\"hd\">{head_img}<div><h1>{title}</h1><p class=\"meta\">{meta}</p></div></div>\n"
            f"<div class=\"bar\">{open_btn}<button id=\"cp\" type=\"button\">Copy all links</button>"
            "<input id=\"q\" type=\"search\" placeholder=\"Filter titles\" aria-label=\"Filter titles\"></div>\n"
            "<ol id=\"l\">\n" + "\n".join(rows) + "\n</ol>\n"
            "<script>(function(){var L=[].slice.call(document.querySelectorAll('#l li'));"
            "document.getElementById('q').oninput=function(){var s=this.value.toLowerCase();"
            "L.forEach(function(e){e.style.display=e.dataset.t.indexOf(s)<0?'none':''})};"
            "document.getElementById('cp').onclick=function(){var t=L.filter(function(e){return e.style.display!=='none'})"
            ".map(function(e){return e.querySelector('a').href}).join('\\n');"
            "if(navigator.clipboard)navigator.clipboard.writeText(t);this.textContent='Copied'}})();</script>\n"
            "<p class=\"meta\">Saved by Yeal. Playing needs a TIDAL account.</p>\n</body>\n</html>\n")


def write_tidal_linklist(folder: Path, info: dict) -> Optional[Path]:
    """Write `<folder>/<title>.html`; an existing file is never replaced (' (2)', ' (3)' ... is added)."""
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", str(info.get("title") or "TIDAL")).strip(" .")[:120] or "TIDAL"
    folder = Path(folder)
    try:
        folder.mkdir(parents=True, exist_ok=True)
        page = folder / (name + ".html")
        n = 2
        while page.exists():
            page = folder / ("%s (%d).html" % (name, n))
            n += 1
        page.write_text(tidal_linklist_html(info), encoding="utf-8")
    except OSError:
        return None
    return page
