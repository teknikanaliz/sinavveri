#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Üniversite tanıtım videoları — resmî YouTube kanalı + en güncel tercihiyle.

YouTube arama sonucu (ytInitialData) evomi proxy ile kazınır; her üniversite için
resmî kanal (kanal adı üniversite adıyla örtüşen) ve "tanıtım" içeren en güncel
video seçilir. Kota gerektirmez (Data API günde ~100 arama ile sınırlı).

Çıktı: data/uni_videos.json  → { "<universiteId|n_normAd>": {"id": videoId, "t": başlık, "ch": kanal} }
Anahtarlama logolarla aynı (uni_logo_html ile uyumlu).
"""
import json
import re
import urllib.request
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = DATA / "uni_videos.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def norm(s):
    s = (s or "").strip().lower().replace("i̇", "i")
    s = re.sub(r"\([^)]*\)", "", s)
    tr = {"ı": "i", "ş": "s", "ğ": "g", "ü": "u", "ö": "o", "ç": "c", "â": "a", "î": "i", "û": "u"}
    s = "".join(tr.get(c, c) for c in s)
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s)).strip()


def proxy_opener():
    url = ""
    reg = Path("/home/tekni/VS/servermimari/.secrets/REGISTRY.env")
    if reg.exists():
        for ln in reg.read_text(encoding="utf-8").splitlines():
            if ln.startswith("EVOMI_PROXY_URL="):
                url = ln.split("=", 1)[1].strip().strip('"')
    return urllib.request.build_opener(urllib.request.ProxyHandler({"http": url, "https": url})) if url else urllib.request.build_opener()


def months_ago(txt):
    """'4 yıl önce'→48, '10 ay önce'→10, '2 hafta önce'→0.5 (küçük = güncel)."""
    m = re.search(r"(\d+)\s*(yıl|ay|hafta|gün|saat|dakika)", txt or "")
    if not m:
        return 9999
    n = int(m.group(1)); u = m.group(2)
    return {"yıl": n * 12, "ay": n, "hafta": n * 0.25, "gün": 0, "saat": 0, "dakika": 0}.get(u, 9999)


def parse_results(html):
    m = re.search(r"ytInitialData\s*=\s*(\{.*?\});</script>", html, re.S) or re.search(r"var ytInitialData = (\{.*?\});", html, re.S)
    if not m:
        return []
    try:
        d = json.loads(m.group(1))
    except Exception:
        return []
    out = []

    def walk(o):
        if isinstance(o, dict):
            if "videoRenderer" in o:
                vr = o["videoRenderer"]
                out.append({
                    "id": vr.get("videoId"),
                    "title": "".join(t.get("text", "") for t in vr.get("title", {}).get("runs", [])),
                    "ch": (vr.get("ownerText", {}).get("runs", [{}]) or [{}])[0].get("text", ""),
                    "pub": vr.get("publishedTimeText", {}).get("simpleText", ""),
                })
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(d)
    return [v for v in out if v.get("id")]


def pick(results, uname):
    un = set(norm(uname).split())
    un.discard("universitesi"); un.discard("universite")
    best, best_score = None, -1
    for i, v in enumerate(results[:12]):
        chn = set(norm(v["ch"]).split())
        official = len(un & chn) >= 1 and ("universite" in v["ch"].lower() or "university" in v["ch"].lower() or len(un & chn) >= 2)
        tanit = "tanıt" in v["title"].lower() or "tanit" in norm(v["title"])
        rec = months_ago(v["pub"])
        score = 0
        if official:
            score += 100
        if tanit:
            score += 40
        score += max(0, 30 - i)          # üst sıra (alaka) bonusu
        score += max(0, 30 - rec * 0.4)  # güncellik bonusu (küçük ay = büyük bonus)
        if score > best_score:
            best, best_score = v, score
    return best


def main():
    progs = json.loads((DATA / "programs_raw.json").read_text(encoding="utf-8"))
    univ = json.loads((DATA / "universiteler.json").read_text(encoding="utf-8")) if (DATA / "universiteler.json").exists() else {}
    unis = {}
    for p in progs:
        nk = norm(p["u"])
        if nk and nk not in unis:
            unis[nk] = p["u"]
    out = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    opener = proxy_opener()
    done = 0
    for nk, uname in unis.items():
        uid = (univ.get(nk) or {}).get("id")
        key = str(uid) if uid else "n_" + nk.replace(" ", "-")
        if key in out and out[key].get("id"):
            continue
        q = urllib.parse.quote((uname.split(" (")[0] + " tanıtım filmi"))
        url = f"https://www.youtube.com/results?search_query={q}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "tr-TR,tr"})
            html = opener.open(req, timeout=40).read().decode("utf-8", "ignore")
            best = pick(parse_results(html), uname)
            if best:
                out[key] = {"id": best["id"], "t": best["title"][:90], "ch": best["ch"]}
                done += 1
        except Exception:
            pass
        if done and done % 20 == 0:
            OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
            print(f"  …{done} video bulundu")
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"  → uni_videos.json: {len(out)} üniversite için video")


if __name__ == "__main__":
    import urllib.parse
    main()
