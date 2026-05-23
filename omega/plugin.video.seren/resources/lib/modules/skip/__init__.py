"""Unified skip module for intro/recap/credits/preview segments.

Sources:
- AniSkip + Anime-Skip — anime episodes only (MAL / AniList ids)
- TheIntroDB — movies and TV episodes (TMDB / IMDb ids)

Supports four segment types:
- intro    — opening / theme / show titles
- recap    — "Previously on…" segment
- credits  — end credits (anime: ED outro)
- preview  — next-episode teaser

Use SkipHandler from skip_handler.py as the entry point.
"""
