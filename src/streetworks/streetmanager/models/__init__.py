"""Generated Street Manager Pydantic models, namespaced by API version.

Once generated (see ``scripts/generate_models.py``), models live at e.g.
``streetworks.streetmanager.models.v6.work`` and can be used to validate
payloads from the corresponding client methods::

    from streetworks.streetmanager.models.v6.work import WorkResponse

    work = WorkResponse.model_validate(sm.work.get_work("TSR123"))

Models are generated from the official DfT swagger specifications and are
committed to the repository, so installing from PyPI includes them. To
regenerate after a DfT release::

    pip install -e ".[gen]"
    python scripts/generate_models.py --version v6 --from-dir specs/streetmanager/v6
"""
