"""Compatibility module forwarding to app.services.offer_parser."""

from app.services.offer_parser import fallback_parser, parse_offer_text

__all__ = ["parse_offer_text", "fallback_parser"]
