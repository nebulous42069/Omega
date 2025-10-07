# -*- coding: utf-8 -*-
"""
Lightweight Diggz Wallpapers source for plugin.video.4kwallpapers

This scrapes a public Internet Archive directory listing and returns
categories (subfolders) and image files. Kept dependency-free to fit
within the addon's footprint.
"""
from urllib.request import Request, urlopen
from urllib.parse import urljoin
import re
import time

BASE = "https://ia601602.us.archive.org/6/items/tr049_20230511/WALLPAPERS/"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")

IMG_EXTS = (".jpg", ".jpeg", ".png", ".webp")

def _fetch(url, timeout=30):
    req = Request(url, headers={"User-Agent": UA})
    with urlopen(req, timeout=timeout) as resp:
        data = resp.read()
    # Directory pages are simple HTML; force utf-8 with fallback
    try:
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return data.decode("latin-1", errors="ignore")

def list_categories():
    """Return a list of dicts: {'title','href'} for each subfolder under BASE."""
    html = _fetch(BASE)
    # naive directory parser; IA directory listings are predictable
    links = re.findall(r'href="([^"]+)">([^<]+)</a>', html)
    items = []
    for href, label in links:
        if not href.endswith("/"):
            continue
        if href.startswith("../"):
            continue
        # Normalize title
        title = label.strip().strip("/")
        items.append({"title": title, "href": href})
    # Stable sort by title
    items.sort(key=lambda x: x["title"].lower())
    return items

def list_images(category_href):
    """Return list of dicts: {'title','img','thumb'} within a category folder."""
    cat_url = urljoin(BASE, category_href)
    html = _fetch(cat_url)
    links = re.findall(r'href="([^"]+)">([^<]+)</a>', html)
    items = []
    for href, label in links:
        name = label.strip()
        if name.endswith("/") or not any(name.lower().endswith(e) for e in IMG_EXTS):
            continue
        img_url = urljoin(cat_url, href)
        # Derive a clean title
        base = name.rsplit(".", 1)[0]
        items.append({"title": base, "img": img_url, "thumb": img_url})
    # Prefer natural sort by title
    def _key(s):
        return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s["title"])]
    items.sort(key=_key)
    return items
