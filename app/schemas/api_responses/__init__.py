"""Schemas for raw external API responses."""
from __future__ import annotations

from app.schemas.api_responses.geonames import GeoNamesCity, GeoNamesResponse
from app.schemas.api_responses.google_sv import GoogleSVLocation, GoogleSVMetadata
from app.schemas.api_responses.mapillary import MapillaryImage
from app.schemas.api_responses.open_meteo import OpenMeteoResponse
from app.schemas.api_responses.owm import OWMResponse
from app.schemas.api_responses.restcountries import RestCountry
from app.schemas.api_responses.wiki import WikiExtract

__all__ = [
    "GeoNamesResponse",
    "GeoNamesCity",
    "GoogleSVMetadata",
    "GoogleSVLocation",
    "OWMResponse",
    "OpenMeteoResponse",
    "WikiExtract",
    "RestCountry",
    "MapillaryImage",
]