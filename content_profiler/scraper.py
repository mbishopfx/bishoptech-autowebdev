from __future__ import annotations

from typing import List, Dict
from urllib.parse import urlparse
import tldextract
from bs4 import BeautifulSoup
import trafilatura
from .http import get_text


def normalize_url(url: str) -> str:
    # Ensure scheme and strip fragments
    parsed = urlparse(url)
    scheme = parsed.scheme or 'https'
    netloc = parsed.netloc
    path = parsed.path.rstrip('/')
    return f"{scheme}://{netloc}{path}"


def extract_domain(url: str) -> str:
    ext = tldextract.extract(url)
    return '.'.join(part for part in [ext.domain, ext.suffix] if part)


def extract_links(html: str, base_url: str) -> List[str]:
    soup = BeautifulSoup(html, 'lxml')
    links = []
    for a in soup.select('a[href]'):
        href = a['href']
        if href.startswith('#') or href.startswith('mailto:') or href.startswith('tel:'):
            continue
        if href.startswith('http'):
            links.append(href)
        elif href.startswith('/'):
            parsed = urlparse(base_url)
            links.append(f"{parsed.scheme}://{parsed.netloc}{href}")
    return list(dict.fromkeys(links))


def extract_text(url: str) -> Dict[str, str | list[str]]:
    url = normalize_url(url)
    raw = get_text(url)
    text = trafilatura.extract(raw, include_comments=False, include_tables=False) or ''
    links = extract_links(raw, url)
    return { 'url': url, 'text': text.strip(), 'links': links }


