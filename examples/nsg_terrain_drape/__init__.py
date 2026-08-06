"""Draping the UK NSG over terrain - see README.md in this directory.

A small package, not a single script: real elevation access
(``terrain.py``, stdlib-only, module-quality - see its own docstring for
the module-boundary note this is built against) is a genuinely separate
concern from the drape itself (``drape.py``: densify, sample, emit - a
derived consumer of ``terrain.py``, deliberately never folded into it) and
from rendering (``render.py``). Run as
``python -m examples.nsg_terrain_drape.generate_drape`` from the repository
root - see the README for real examples.
"""
