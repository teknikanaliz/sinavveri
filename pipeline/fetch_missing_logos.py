#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Eksik üniversite logoları (KKTC + yurtdışı) — resmî kaynaklardan.

universitetercih.com yalnızca Türkiye üniversitelerini kapsadığından KKTC ve
yurtdışı üniversiteler logosuz kalıyordu. KKTC logoları YÖDAK'ın (KKTC resmî
akreditasyon kurulu) resmî listesinden (300×300), yurtdışı olanlar resmî
domainlerinin favicon'undan alınır. Hepsi PNG'ye çevrilip self-host edilir.

Çıktı: assets/logos/<universiteId>.png  (ID'si olanlar)
       assets/logos/n_<normAd>.png       (ID'si olmayanlar — isim-bazlı fallback)
"""
import io
import json
import re
import urllib.request
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
LOGODIR = ROOT / "assets" / "logos"
LOGODIR.mkdir(parents=True, exist_ok=True)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

YODAK = "https://www.yodak.gov.ct.tr/images/universiteler/{}.jpg"
FAVI = "https://www.google.com/s2/favicons?domain={}&sz=256"

# universiteId → YÖDAK logo kodu (KKTC üniversiteleri, resmî YÖDAK listesi)
KKTC = {
    250548: "gu", 202542: "gau", 202959: "emu", 202952: "ydu", 202950: "lau",
    317343: "ufu", 317400: "kstu", 202951: "uku", 375111: "aku", 464048: "kau1",
    417386: "arucad", 333623: "bau-cyprus", 263352: "kau", 418550: "kibu", 240640: "akun",
}
# universiteId → resmî domain (yurtdışı; YÖDAK kapsamı dışı)
YABANCI = {
    202954: "manas.edu.kg",      # Kırgızistan-Türkiye Manas
    202953: "yesevi.edu.tr",     # Hoca Ahmet Yesevi Türk-Kazak
    301255: "ibu.edu.mk",        # Uluslararası Balkan (Üsküp)
    301253: "ius.edu.ba",        # Uluslararası Saraybosna
}
# ID'si olmayanlar → (normAd, kaynak tipi, kaynak)
NOID = [
    ("rauf denktas universitesi", "yodak", "rdu"),
    ("tiran new york universitesi", "favi", "unyt.edu.al"),
    ("azerbaycan devlet pedagoji universitesi", "favi", "adpu.edu.az"),
]


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=40).read()


def to_png(data, dest, pad=False):
    im = Image.open(io.BytesIO(data)).convert("RGBA")
    if im.width < 16:
        return False
    if pad and abs(im.width - im.height) > 4:  # kareye al (beyaz zemin)
        side = max(im.width, im.height)
        bg = Image.new("RGBA", (side, side), (255, 255, 255, 0))
        bg.paste(im, ((side - im.width) // 2, (side - im.height) // 2))
        im = bg
    im.save(dest, "PNG")
    return True


def main():
    ok = 0
    fail = []
    for uid, code in KKTC.items():
        dest = LOGODIR / f"{uid}.png"
        try:
            if to_png(fetch(YODAK.format(code)), dest):
                ok += 1
            else:
                fail.append(code)
        except Exception as e:
            fail.append(f"{code}({e})")
    for uid, dom in YABANCI.items():
        dest = LOGODIR / f"{uid}.png"
        try:
            if to_png(fetch(FAVI.format(dom)), dest):
                ok += 1
            else:
                fail.append(dom)
        except Exception as e:
            fail.append(f"{dom}({e})")
    for normad, kind, src in NOID:
        dest = LOGODIR / f"n_{normad.replace(' ', '-')}.png"
        try:
            url = YODAK.format(src) if kind == "yodak" else FAVI.format(src)
            if to_png(fetch(url), dest):
                ok += 1
            else:
                fail.append(src)
        except Exception as e:
            fail.append(f"{src}({e})")
    print(f"  → eksik logo: {ok} indirildi" + (f", başarısız: {fail}" if fail else ""))


if __name__ == "__main__":
    main()
