from typing import Optional
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


class HttpError(Exception):
    pass


@retry(reraise=True, stop=stop_after_attempt(4), wait=wait_exponential(multiplier=0.5, min=1, max=8), retry=retry_if_exception_type(HttpError))
def get_json(url: str, params: Optional[dict] = None, headers: Optional[dict] = None) -> dict:
    resp = requests.get(url, params=params, headers=headers, timeout=20)
    if resp.status_code >= 500:
        raise HttpError(f"{resp.status_code}: {resp.text[:200]}")
    resp.raise_for_status()
    return resp.json()


@retry(reraise=True, stop=stop_after_attempt(4), wait=wait_exponential(multiplier=0.5, min=1, max=8), retry=retry_if_exception_type(HttpError))
def get_text(url: str, headers: Optional[dict] = None) -> str:
    resp = requests.get(url, headers=headers, timeout=20)
    if resp.status_code >= 500:
        raise HttpError(f"{resp.status_code}: {resp.text[:200]}")
    resp.raise_for_status()
    return resp.text


