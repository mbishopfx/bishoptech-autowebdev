from __future__ import annotations

from typing import List, Dict, Any, Tuple
from .config import load_config
from .google_clients import GoogleClients
from .pipeline import run_pipeline
from pathlib import Path
import orjson
from .ideator import generate_ideas_markdown, generate_pitches_markdown
import time


def find_businesses(zip_code: str, genre: str, target_count: int = 20) -> List[Dict[str, Any]]:
    cfg = load_config()
    clients = GoogleClients(api_key=cfg.google_api_key, cse_id=cfg.google_cse_id, pagespeed_key=cfg.pagespeed_api_key, places_key=cfg.places_api_key)

    # Geocode ZIP
    geo = clients.geocode_address(zip_code)
    results = geo.get('results') or []
    if not results:
        raise RuntimeError(f'Could not geocode {zip_code}')
    loc = results[0]['geometry']['location']
    lat, lng = loc['lat'], loc['lng']

    businesses: List[Dict[str, Any]] = []
    radius = 5000  # 5km start
    pagetoken = None
    tried_radii = 0

    # Expand radius until we get target_count (cap at ~100km)
    while len(businesses) < target_count and radius <= 100000 and tried_radii < 6:
        data = clients.places_nearby(lat, lng, radius, keyword=genre)
        items = data.get('results') or []
        for it in items:
            if 'place_id' in it:
                businesses.append(it)
                if len(businesses) >= target_count:
                    break
        # Handle next page if available
        pagetoken = data.get('next_page_token')
        while pagetoken and len(businesses) < target_count:
            time.sleep(2)
            data = clients.places_nearby(lat, lng, radius, keyword=genre, pagetoken=pagetoken)
            items = data.get('results') or []
            for it in items:
                if 'place_id' in it:
                    businesses.append(it)
                    if len(businesses) >= target_count:
                        break
            pagetoken = data.get('next_page_token')
        radius = int(radius * 2)
        tried_radii += 1

    # Deduplicate by place_id
    seen = set()
    unique: List[Dict[str, Any]] = []
    for b in businesses:
        pid = b.get('place_id')
        if pid and pid not in seen:
            seen.add(pid)
            unique.append(b)
    return unique[:target_count]


def run_bulk(zip_code: str, genre: str, out_base: str) -> List[Dict[str, Any]]:
    cfg = load_config()
    clients = GoogleClients(api_key=cfg.google_api_key, cse_id=cfg.google_cse_id, pagespeed_key=cfg.pagespeed_api_key, places_key=cfg.places_api_key)
    found = find_businesses(zip_code, genre, target_count=20)
    results: List[Dict[str, Any]] = []
    print(f"Found {len(found)} candidates. Running profiling...")
    for idx, biz in enumerate(found, start=1):
        name = biz.get('name') or genre
        vicinity = biz.get('vicinity') or biz.get('formatted_address') or ''
        query = f"{name} {vicinity}"
        print(f"[{idx}/{len(found)}] Profiling: {query}")
        try:
            res = run_pipeline(query, out_base)
            # enrich summary from profile.json
            base = Path(res['outDir'])
            name = ''
            phone = ''
            website = ''
            try:
                prof = orjson.loads((base / 'profile.json').read_bytes())
                org = prof.get('organization', {})
                name = org.get('name') or ''
                phone = org.get('phone') or ''
                website = org.get('url') or ''
            except Exception:
                pass
            # generate ideas & pitches for each business
            sources = {}
            try:
                sources = orjson.loads((base / 'sources.json').read_bytes())
                ideas_md = generate_ideas_markdown(cfg.openai_api_key, sources)
                (base / 'ideas.md').write_text(ideas_md, encoding='utf-8')
                pitches_md = generate_pitches_markdown(cfg.openai_api_key, sources)
                (base / 'pitches.md').write_text(pitches_md, encoding='utf-8')
            except Exception as e:
                print(f"Ideas/Pitches generation failed for {query}: {e}")

            results.append({'query': query, 'outDir': res['outDir'], 'name': name, 'phone': phone, 'website': website})
        except Exception as e:
            print(f"Failed: {query} -> {e}")
            continue
        time.sleep(1)
    return results


