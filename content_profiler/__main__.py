import argparse
from .pipeline import run_pipeline
from .config import load_config
from .google_clients import GoogleClients
from .ideator import generate_ideas_markdown, generate_pitches_markdown
from .scraper import extract_text
from .bulk import run_bulk
import orjson
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description='Content Profiler')
    parser.add_argument('--query', required=True, help='Client name/business or relevant query')
    parser.add_argument('--out', default='outputs', help='Output base directory')
    parser.add_argument('--ideas', action='store_true', help='Also generate product ideas/audit/pitches markdown')
    parser.add_argument('--bulk', action='store_true', help='Bulk mode: treat --query as "<zip>|<genre>" and run 20 profiles')
    args = parser.parse_args()

    if args.bulk:
        try:
            zip_code, genre = [x.strip() for x in args.query.split('|', 1)]
        except ValueError:
            raise SystemExit('In bulk mode, --query must be "<zip>|<genre>" e.g., "78701|dentist"')
        results = run_bulk(zip_code, genre, args.out)
        print('Bulk complete. Results:')
        for r in results:
            print('-', r['query'], '->', r['outDir'])
        return

    result = run_pipeline(args.query, args.out)
    print('Wrote outputs to:', result['outDir'])
    if result.get('primaryUrl'):
        print('Primary URL:', result['primaryUrl'])
    print('Pages scraped:', result.get('pagesScraped'))

    if args.ideas:
        # Load sources for ideation
        base = Path(result['outDir'])
        sources = orjson.loads((base / 'sources.json').read_bytes())
        cfg = load_config()
        print('Generating product ideas and audit markdown...')
        ideas_md = generate_ideas_markdown(cfg.openai_api_key, sources)
        (base / 'ideas.md').write_text(ideas_md, encoding='utf-8')
        print('Generating short sales pitches...')
        pitches_md = generate_pitches_markdown(cfg.openai_api_key, sources)
        (base / 'pitches.md').write_text(pitches_md, encoding='utf-8')
        print('Ideas and pitches written.')


if __name__ == '__main__':
    main()


