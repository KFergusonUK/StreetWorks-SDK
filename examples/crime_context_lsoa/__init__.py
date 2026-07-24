"""Worksite-keyed, LSOA-level crime context - see README.md in this directory.

A small package (not a single script, unlike the neighbourhood-level
example it succeeds) because it genuinely spans several concerns: police
CSV ingestion (``ingest``), ONS population/boundary (``ons``), worksite
geometry (``worksite``), and rate/shrinkage/banding (``stats``), tied
together by ``report``. Run as ``python -m examples.crime_context_lsoa.report``
from the repository root - see the README for real examples.
"""
