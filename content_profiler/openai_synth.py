from __future__ import annotations

from typing import Any, Dict
import orjson
from openai import OpenAI


SYSTEM_PROMPT = (
    "You are an expert business analyst creating comprehensive content profiles for LLM chatbot training. \n"
    "Analyze multi-source data to produce detailed, factual business intelligence. \n"
    "Return strict JSON with keys: organization, services, faqs, voice, meta, products, team, policies, locations. \n"
    "- organization: { name, legalName?, description, phone?, email?, url, address?, hours?, social?:[], yearEstablished?, certifications?:[] } \n"
    "- services: array of { name, summary, details, bullets:[], benefits:[], pricing?, duration?, schemaServiceType? } \n"
    "- products: array of { name, description, category, features?:[], pricing? } \n"
    "- team: array of { name?, role?, bio?, specialties?:[] } \n"
    "- faqs: array of { q, a, category? } \n"
    "- policies: { payment?, cancellation?, privacy?, terms? } \n"
    "- locations: array of { name?, address?, phone?, hours?, services?:[] } \n"
    "- voice: { tone, brandTraits:[], readingLevel, personality, communicationStyle } \n"
    "- meta: { homepageTitle, homepageDescription, primaryKeywords:[], secondaryKeywords?:[], targetAudience?:[] } \n"
    "Extract maximum detail from provided sources. Use only factual information; if unknown, omit or use null."
)


def truncate_sources(sources: Dict[str, Any], max_chars: int = 50000) -> Dict[str, Any]:
    """Truncate scraped content to avoid token limits"""
    truncated = sources.copy()
    
    # Limit scraped pages content
    if 'scraped' in truncated:
        for page in truncated['scraped']:
            if 'text' in page and len(page['text']) > 8000:
                page['text'] = page['text'][:8000] + '... [truncated]'
    
    # Limit CSE snippets
    if 'cse' in truncated:
        for item in truncated['cse']:
            if 'snippet' in item and len(item['snippet']) > 500:
                item['snippet'] = item['snippet'][:500] + '...'
    
    # Remove large nested data that's not essential
    if 'pagespeed' in truncated:
        if isinstance(truncated['pagespeed'], dict) and 'lighthouseResult' in truncated['pagespeed']:
            truncated['pagespeed'] = {'summary': 'PageSpeed data available but truncated for processing'}
    
    return truncated


def synthesize_profile(api_key: str, sources: Dict[str, Any]) -> Dict[str, Any]:
    client = OpenAI(api_key=api_key)
    truncated_sources = truncate_sources(sources)
    
    messages = [
        { 'role': 'system', 'content': SYSTEM_PROMPT },
        { 'role': 'user', 'content': 'Compile a content profile from these sources. Respond with JSON only.' },
        { 'role': 'user', 'content': orjson.dumps(truncated_sources).decode('utf-8') },
    ]

    resp = client.chat.completions.create(
        model='gpt-4o-mini',
        messages=messages,
        temperature=0.2,
        response_format={ 'type': 'json_object' },
    )
    content = resp.choices[0].message.content
    return orjson.loads(content) if content else {}


def generate_training_data(profile: Dict[str, Any], sources: Dict[str, Any]) -> Dict[str, Any]:
    """Generate comprehensive training data for LLM chatbot training"""
    org = profile.get('organization', {})
    services = profile.get('services', [])
    faqs = profile.get('faqs', [])
    team = profile.get('team', [])
    products = profile.get('products', [])
    policies = profile.get('policies', {})
    
    # Base knowledge for context
    context = {
        'business_name': org.get('name'),
        'business_description': org.get('description'),
        'services': [s.get('name') for s in services],
        'contact_info': {
            'phone': org.get('phone'),
            'email': org.get('email'),
            'address': org.get('address'),
            'website': org.get('url')
        },
        'social_media': org.get('social', []),
        'scraped_pages_count': sources.get('scrapingStats', {}).get('totalPagesScraped', 0)
    }
    
    # Generate Q&A pairs for training
    qa_pairs = []
    
    # FAQ-based Q&As
    for faq in faqs:
        qa_pairs.append({
            'question': faq.get('q'),
            'answer': faq.get('a'),
            'category': faq.get('category', 'general'),
            'context_needed': ['business_info']
        })
    
    # Service-based Q&As
    for service in services:
        qa_pairs.extend([
            {
                'question': f"What is {service.get('name')}?",
                'answer': service.get('summary', ''),
                'category': 'services',
                'context_needed': ['services', 'business_info']
            },
            {
                'question': f"What are the benefits of {service.get('name')}?",
                'answer': '. '.join(service.get('benefits', [])),
                'category': 'services',
                'context_needed': ['services']
            }
        ])
    
    # Contact/booking Q&As
    if org.get('phone'):
        qa_pairs.append({
            'question': "How can I contact you?",
            'answer': f"You can reach us at {org.get('phone')} or visit our website at {org.get('url', '')}",
            'category': 'contact',
            'context_needed': ['contact_info']
        })
    
    # Location Q&As
    if org.get('address'):
        qa_pairs.append({
            'question': "Where are you located?",
            'answer': f"We're located at {org.get('address')}",
            'category': 'location',
            'context_needed': ['contact_info']
        })
    
    # Team Q&As
    for member in team:
        if member.get('name') and member.get('bio'):
            qa_pairs.append({
                'question': f"Tell me about {member.get('name')}",
                'answer': member.get('bio'),
                'category': 'team',
                'context_needed': ['team_info']
            })
    
    return {
        'context': context,
        'qa_pairs': qa_pairs,
        'training_instructions': {
            'personality': profile.get('voice', {}),
            'response_guidelines': [
                'Always be helpful and professional',
                'Use information only from the provided context',
                'If unsure, direct to contact information',
                'Match the business tone and voice'
            ]
        },
        'embeddings_data': [
            {'text': org.get('description', ''), 'metadata': {'type': 'business_description'}},
            *[{'text': s.get('summary', ''), 'metadata': {'type': 'service', 'service_name': s.get('name')}} for s in services],
            *[{'text': f.get('a', ''), 'metadata': {'type': 'faq', 'question': f.get('q')}} for f in faqs]
        ]
    }


def render_markdown_outputs(profile: Dict[str, Any]) -> Dict[str, str]:
    org = profile.get('organization', {})
    services = profile.get('services', [])
    faqs = profile.get('faqs', [])
    voice = profile.get('voice', {})
    team = profile.get('team', [])
    products = profile.get('products', [])

    about = f"# About {org.get('name','')}\n\n{org.get('description','')}\n"
    
    # Enhanced services with more detail
    services_md = "# Services\n\n" + "\n\n".join([
        f"## {s.get('name','')}\n\n{s.get('summary','')}\n\n" +
        (f"### Details\n{s.get('details','')}\n\n" if s.get('details') else '') +
        ("### Key Features:\n- " + "\n- ".join((s.get('bullets') or [])) + "\n\n" if s.get('bullets') else '') +
        ("### Benefits:\n- " + "\n- ".join((s.get('benefits') or [])) + "\n\n" if s.get('benefits') else '') +
        (f"**Duration:** {s.get('duration')}\n\n" if s.get('duration') else '') +
        (f"**Pricing:** {s.get('pricing')}\n\n" if s.get('pricing') else '')
        for s in services
    ])
    
    faqs_md = "# Frequently Asked Questions\n\n" + "\n\n".join([
        f"### {f.get('q','')}\n\n{f.get('a','')}"
        for f in faqs
    ])
    
    hero_md = f"# {voice.get('tone','Professional').title()} {org.get('name','')}\n\n{org.get('description','')}\n"
    
    # Team page if team data exists
    team_md = ""
    if team:
        team_md = "# Our Team\n\n" + "\n\n".join([
            f"## {member.get('name','')}\n**{member.get('role','')}**\n\n{member.get('bio','')}\n\n" +
            ("**Specialties:** " + ", ".join(member.get('specialties', [])) + "\n\n" if member.get('specialties') else '')
            for member in team
        ])
    
    # Products page if products exist
    products_md = ""
    if products:
        products_md = "# Products\n\n" + "\n\n".join([
            f"## {p.get('name','')}\n\n{p.get('description','')}\n\n" +
            ("**Category:** " + p.get('category','') + "\n\n" if p.get('category') else '') +
            ("**Features:**\n- " + "\n- ".join(p.get('features', [])) + "\n\n" if p.get('features') else '') +
            (f"**Pricing:** {p.get('pricing')}\n\n" if p.get('pricing') else '')
            for p in products
        ])

    outputs = {
        'about.md': about,
        'services.md': services_md,
        'faqs.md': faqs_md,
        'homepage-hero.md': hero_md,
    }
    
    if team_md:
        outputs['team.md'] = team_md
    if products_md:
        outputs['products.md'] = products_md
        
    return outputs


