from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, Any, List
import orjson

from .config import load_config
from .google_clients import GoogleClients
from .scraper import extract_text, extract_domain
from .openai_synth import synthesize_profile, render_markdown_outputs, generate_training_data


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return re.sub(r'-+', '-', text).strip('-')


def run_pipeline(query: str, out_dir: str) -> Dict[str, Any]:
    cfg = load_config()
    clients = GoogleClients(
        api_key=cfg.google_api_key, cse_id=cfg.google_cse_id,
        pagespeed_key=cfg.pagespeed_api_key, places_key=cfg.places_api_key
    )

    cse_items = clients.search(query, num=8)
    primary_url = None
    if cse_items:
        # Prefer official domain by choosing the first non-social domain
        for item in cse_items:
            link = item.get('link')
            dom = extract_domain(link) if link else ''
            if dom and not any(s in dom for s in ['facebook.com','instagram.com','linkedin.com','x.com','twitter.com','yelp.com']):
                primary_url = link
                break
        primary_url = primary_url or cse_items[0].get('link')

    # Places API calls with error handling
    places = {}
    place_details = {}
    try:
        places = clients.places_text_search(query)
        place = (places.get('results') or [None])[0]
        if place and 'place_id' in place:
            place_details = clients.place_details(place['place_id'])
    except Exception as e:
        print(f"Places API failed (skipping): {e}")
        places = {'error': str(e)}

    # Comprehensive scraping of primary site
    scraped_pages: List[Dict[str, Any]] = []
    social_profiles: List[Dict[str, Any]] = []
    
    if primary_url:
        print(f"Scraping primary site: {primary_url}")
        first = extract_text(primary_url)
        scraped_pages.append(first)
        
        # Extract and categorize all links
        internal_links = []
        social_links = []
        
        for link in first.get('links', []):
            link_domain = extract_domain(link)
            primary_domain = extract_domain(primary_url)
            
            if link_domain == primary_domain:
                internal_links.append(link)
            elif any(social in link_domain for social in ['facebook.com', 'instagram.com', 'linkedin.com', 'twitter.com', 'x.com', 'youtube.com', 'tiktok.com']):
                social_links.append(link)
        
        # Scrape up to 12 internal pages for comprehensive coverage
        print(f"Found {len(internal_links)} internal links, scraping top 12...")
        for link in internal_links[:12]:
            try:
                page_data = extract_text(link)
                scraped_pages.append(page_data)
                print(f"Scraped: {link}")
            except Exception as e:
                print(f"Failed to scrape {link}: {e}")
                continue
            if len(scraped_pages) >= 12:
                break
        
        # Extract basic info from social profiles (no full scraping to respect ToS)
        print(f"Found {len(social_links)} social profiles")
        for social_link in social_links[:5]:
            try:
                social_data = {'url': social_link, 'platform': extract_domain(social_link)}
                social_profiles.append(social_data)
            except Exception:
                continue

    # PageSpeed for the primary URL (optional, can timeout)
    psi = {}
    if primary_url:
        try:
            psi = clients.pagespeed(primary_url)
        except Exception as e:
            print(f"PageSpeed API failed (skipping): {e}")
            psi = {'error': str(e)}

    sources = {
        'query': query,
        'cse': cse_items,
        'primaryUrl': primary_url,
        'places': places,
        'placeDetails': place_details,
        'pagespeed': psi,
        'scraped': scraped_pages,
        'socialProfiles': social_profiles,
        'scrapingStats': {
            'totalPagesScraped': len(scraped_pages),
            'socialProfilesFound': len(social_profiles),
        }
    }

    print("Synthesizing comprehensive profile with OpenAI...")
    profile = synthesize_profile(cfg.openai_api_key, sources)
    md = render_markdown_outputs(profile)
    training_data = generate_training_data(profile, sources)

    # Write outputs
    base = Path(out_dir) / slugify(profile.get('organization', {}).get('name') or query)
    (base / 'content').mkdir(parents=True, exist_ok=True)
    (base / 'jsonld').mkdir(parents=True, exist_ok=True)

    (base / 'sources.json').write_bytes(orjson.dumps(sources, option=orjson.OPT_INDENT_2))
    (base / 'profile.json').write_bytes(orjson.dumps(profile, option=orjson.OPT_INDENT_2))
    (base / 'training.json').write_bytes(orjson.dumps(training_data, option=orjson.OPT_INDENT_2))
    
    for name, body in md.items():
        (base / 'content' / name).write_text(body, encoding='utf-8')

    # Draft org JSON-LD
    org = profile.get('organization', {})
    org_graph = {
        '@context': 'https://schema.org',
        '@graph': [
            {
                '@type': 'Organization',
                '@id': f"{org.get('url','').rstrip('/') or primary_url.rstrip('/') if primary_url else ''}#organization",
                'name': org.get('name'),
                'url': org.get('url') or primary_url,
                'telephone': org.get('phone'),
                'description': org.get('description'),
                'sameAs': org.get('social') or [],
                'address': org.get('address') or None,
                'openingHoursSpecification': org.get('hours') or None,
            }
        ]
    }
    (base / 'jsonld' / 'organization.jsonld').write_bytes(orjson.dumps(org_graph, option=orjson.OPT_INDENT_2))

    print(f"✅ Generated comprehensive profile!")
    print(f"📁 Output directory: {base}")
    print(f"📄 Profile: profile.json")
    print(f"🤖 Training data: training.json")
    print(f"📝 Content files: {len(md)} markdown files")
    print(f"🔗 Schema markup: jsonld/organization.jsonld")
    
    return {
        'outDir': str(base),
        'primaryUrl': primary_url,
        'pagesScraped': len(scraped_pages),
        'socialProfilesFound': len(social_profiles),
        'trainingQAPairs': len(training_data.get('qa_pairs', [])),
        'contentFiles': len(md),
    }


