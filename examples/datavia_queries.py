"""Query Geoplace DataVIA: by USRN, near a point, and combined ASD filters."""

import os

from streetworks.datavia import DataViaClient, Layer, filters

# Basic auth (or use client_id=/client_secret= for OAuth2 server-to-server)
with DataViaClient(
    username=os.environ["DATAVIA_USER"], password=os.environ["DATAVIA_PASSWORD"]
) as dv:
    # A single street by USRN
    street = dv.street_by_usrn(4401245)
    for feature in street.get("features", []):
        print(feature["properties"]["street_descriptor"])

    # Streets within 100m of a point (EPSG:4326 lon/lat)
    nearby = dv.streets_near_point(-0.138405, 50.825181, 100)
    print(len(nearby.get("features", [])), "streets within 100m")

    # Special Engineering Difficulty lines intersecting a polygon
    ring = [(-0.140162, 50.823943), (-0.140162, 50.826413),
            (-0.136653, 50.826413), (-0.136653, 50.823943)]
    sed = dv.get_features(
        Layer.SPECIAL_DESIGNATION_LINES,
        filter_fragment=filters.and_(
            filters.intersects_polygon(ring),
            filters.property_equals("special_designation_code", 3),
        ),
    )
    print(len(sed.get("features", [])), "SED records in polygon")

    # Bulk paging over a whole layer
    for _feature in dv.iter_features(Layer.ESU_STREETS, page_size=500, max_features=1000):
        pass
