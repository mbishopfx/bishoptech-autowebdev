from __future__ import annotations

from typing import Dict, Any, List
from openai import OpenAI
import orjson
from .openai_synth import truncate_sources


IDEAS_SYSTEM = (
    "You are a senior fullstack architect and product strategist.\n"
    "Given multi-source business context, produce:\n"
    "1) A detailed markdown report with 6-10 product/tool ideas tailored to the business.\n"
    "Each idea must include: Name, Use Case, Why It Helps (business impact), Tech Stack (frontend, backend, data, AI libs),\n"
    "Implementation Outline (steps), and SEFA integration guidance.\n"
    "2) A website audit section covering robots.txt, llm.txt, sitemap.xml with explicit improvement actions.\n"
    "Focus on realistic, implementable solutions. Be specific."
)


PITCHES_SYSTEM = (
    "You are a sales engineer. Generate 8-12 concise 'foot-in-the-door' two-to-three-line pitches.\n"
    "Each pitch should be tailored to the business, concrete, and outcome-driven.\n"
    "No fluff. Keep each to max 240 characters. Output as a markdown list."
)


def generate_ideas_markdown(api_key: str, sources: Dict[str, Any]) -> str:
    client = OpenAI(api_key=api_key)
    truncated = truncate_sources(sources)
    messages = [
        { 'role': 'system', 'content': IDEAS_SYSTEM },
        { 'role': 'user', 'content': 'Produce the report now in Markdown. Include sections: Product Ideas and Website Audit.' },
        { 'role': 'user', 'content': orjson.dumps(truncated).decode('utf-8') },
    ]
    resp = client.chat.completions.create(
        model='gpt-4o-mini',
        messages=messages,
        temperature=0.3,
    )
    return resp.choices[0].message.content or ''


def generate_pitches_markdown(api_key: str, sources: Dict[str, Any]) -> str:
    client = OpenAI(api_key=api_key)
    truncated = truncate_sources(sources)
    messages = [
        { 'role': 'system', 'content': PITCHES_SYSTEM },
        { 'role': 'user', 'content': 'Generate the pitches as a markdown list now.' },
        { 'role': 'user', 'content': orjson.dumps(truncated).decode('utf-8') },
    ]
    resp = client.chat.completions.create(
        model='gpt-4o-mini',
        messages=messages,
        temperature=0.5,
    )
    return resp.choices[0].message.content or ''


