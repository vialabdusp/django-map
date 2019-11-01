import os
from django.contrib.gis.utils import LayerMapping
from .models import Neigh

# Map shapefile fields onto model fields.
somer_mapping = {
    # Key is model field, value is shapefile field.
    'oid' : 'OBJECTID',
    'name' : 'NBHD',
    'area' : 'SHAPE_Area',
    'length' : 'SHAPE_Leng',
    'geom' : 'POLYGON',
}

def run(filename, verbose=True):
    somer_shp = os.path.abspath(
        os.path.join(os.path.dirname(__file__), 'data', filename),
    )
    lm = LayerMapping(Neigh, somer_shp, somer_mapping, transform=True)
    lm.save(strict=True, verbose=verbose)