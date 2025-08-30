import os
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass
class AppConfig:
    openai_api_key: str
    google_api_key: str
    google_cse_id: str
    pagespeed_api_key: str | None = None
    places_api_key: str | None = None


def load_config() -> AppConfig:
    load_dotenv()
    openai_api_key = os.getenv('OPENAI_API_KEY')
    google_api_key = os.getenv('GOOGLE_API_KEY')
    google_cse_id = os.getenv('GOOGLE_CSE_ID')
    pagespeed_api_key = os.getenv('GOOGLE_PAGESPEED_API_KEY', google_api_key)
    places_api_key = os.getenv('GOOGLE_PLACES_API_KEY', google_api_key)

    if not openai_api_key:
        raise RuntimeError('OPENAI_API_KEY is required')
    if not google_api_key:
        raise RuntimeError('GOOGLE_API_KEY is required')
    if not google_cse_id:
        raise RuntimeError('GOOGLE_CSE_ID is required')

    return AppConfig(
        openai_api_key=openai_api_key,
        google_api_key=google_api_key,
        google_cse_id=google_cse_id,
        pagespeed_api_key=pagespeed_api_key,
        places_api_key=places_api_key,
    )


