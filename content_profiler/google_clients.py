from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Dict
from .http import get_json


@dataclass
class GoogleClients:
    api_key: str
    cse_id: str
    pagespeed_key: str | None = None
    places_key: str | None = None

    def search(self, query: str, num: int = 5) -> List[Dict[str, Any]]:
        url = 'https://www.googleapis.com/customsearch/v1'
        data = get_json(url, params={'key': self.api_key, 'cx': self.cse_id, 'q': query, 'num': num})
        return data.get('items', [])

    def pagespeed(self, url_to_test: str, strategy: str = 'DESKTOP') -> Dict[str, Any]:
        key = self.pagespeed_key or self.api_key
        url = 'https://www.googleapis.com/pagespeedonline/v5/runPagespeed'
        return get_json(url, params={'url': url_to_test, 'key': key, 'strategy': strategy})

    def places_text_search(self, query: str) -> Dict[str, Any]:
        key = self.places_key or self.api_key
        url = 'https://maps.googleapis.com/maps/api/place/textsearch/json'
        return get_json(url, params={'key': key, 'query': query})

    def place_details(self, place_id: str, fields: str = 'name,formatted_address,geometry,opening_hours,website,formatted_phone_number,types,rating,user_ratings_total') -> Dict[str, Any]:
        key = self.places_key or self.api_key
        url = 'https://maps.googleapis.com/maps/api/place/details/json'
        return get_json(url, params={'key': key, 'place_id': place_id, 'fields': fields})

    def geocode_address(self, address: str) -> Dict[str, Any]:
        key = self.places_key or self.api_key
        url = 'https://maps.googleapis.com/maps/api/geocode/json'
        return get_json(url, params={'key': key, 'address': address})

    def places_nearby(self, lat: float, lng: float, radius_m: int, keyword: str | None = None, type_: str | None = None, pagetoken: str | None = None) -> Dict[str, Any]:
        key = self.places_key or self.api_key
        url = 'https://maps.googleapis.com/maps/api/place/nearbysearch/json'
        params: Dict[str, Any] = {'key': key, 'location': f'{lat},{lng}', 'radius': radius_m}
        if keyword:
            params['keyword'] = keyword
        if type_:
            params['type'] = type_
        if pagetoken:
            params['pagetoken'] = pagetoken
        return get_json(url, params=params)


