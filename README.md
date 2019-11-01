## Start new Django project.

```sh
$ django-admin startproject map-app & cd map-app
```

## Start new Django app.

```sh
python manage.py startapp somerville
```

## Create, activate, and populate new virtualenv.

```sh
virtualenv venv
. venv/bin/activate
pip install -r requirements.txt
```

## Set up new PostGIS database.

```sh
$ psql -h localhost -U postgres
```

```sql
postgres=# CREATE DATABASE postgis_db;
postgres=# \connect postgis_db;
postgres=# CREATE EXTENSION postgis;

postgres=# CREATE USER postgis_user WITH PASSWORD 'postgis_pass';

postgres=# ALTER ROLE postgis_user SET client_encoding TO 'utf8';
postgres=# ALTER ROLE postgis_user SET default_transaction_isolation TO 'read committed';
postgres=# ALTER ROLE postgis_user SET timezone TO 'EST';

postgres=# GRANT ALL PRIVILEGES ON DATABASE postgis_db TO postgis_user;
```

## Configure settings.

### Modify installed apps.

```py
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',
    'somerville',
]
```

### Set up database connection.

Here, we set up Django to expect a PostGIS database we've set up on our `localhost`.

```py
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'postgis_db',
        'USER': 'postgis_user',
        'USER': 'postgis_user',
        'PASSWORD': 'postgis_pass',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

## Build a data loader.

### Examine spatial data.

```sh
$ ogrinfo -so somerville/data/Neighborhoods.shp Neighborhoods

INFO: Open of `somerville/data/Neighborhoods.shp'
      using driver `ESRI Shapefile' successful.

Layer name: Neighborhoods
Metadata:
  DBF_DATE_LAST_UPDATE=2017-04-11
Geometry: Polygon
Feature Count: 19
Extent: (754845.775343, 2961071.219847) - (771656.760094, 2977608.500093)
Layer SRS WKT:
PROJCS["NAD83 / Massachusetts Mainland (ftUS)",
    GEOGCS["NAD83",
        DATUM["North_American_Datum_1983",
            SPHEROID["GRS 1980",6378137,298.257222101,
                AUTHORITY["EPSG","7019"]],
            TOWGS84[0,0,0,0,0,0,0],
            AUTHORITY["EPSG","6269"]],
        PRIMEM["Greenwich",0,
            AUTHORITY["EPSG","8901"]],
        UNIT["degree",0.0174532925199433,
            AUTHORITY["EPSG","9122"]],
        AUTHORITY["EPSG","4269"]],
    PROJECTION["Lambert_Conformal_Conic_2SP"],
    PARAMETER["standard_parallel_1",42.68333333333333],
    PARAMETER["standard_parallel_2",41.71666666666667],
    PARAMETER["latitude_of_origin",41],
    PARAMETER["central_meridian",-71.5],
    PARAMETER["false_easting",656166.667],
    PARAMETER["false_northing",2460625],
    UNIT["US survey foot",0.3048006096012192,
        AUTHORITY["EPSG","9003"]],
    AXIS["X",EAST],
    AXIS["Y",NORTH],
    AUTHORITY["EPSG","2249"]]
OBJECTID: Integer64 (10.0)
NBHD: String (50.0)
SHAPE_Leng: Real (19.11)
SHAPE_Area: Real (19.11)
```

We're mostly interested in the lines reading `Geometry: Polygon` and the four lines describing the fields (e.g., `OBJECTID: Integer64 (10.0)`).

### Create a Model

Now, open `somerville/models.py` - you'll have to replace the first line to use spatial data models.

```py
from django.contrib.gis.db import models

# Create your models here.
class Neigh(models.Model):
    oid = models.IntegerField('ObjectID')
    name = models.CharField('Neighborhood Name', max_length=50)
    area = models.FloatField('Shape Area')
    length = models.FloatField('Shape Length')

    # Geometry with MA State Plane spatial reference.
    geom = models.PolygonField(srid=4326)

    # Returns the string representation of the model.
    def __str__(self):
        return self.name
```

Each line corresponds to a new field in our data table, each of which matches a column in our shapefile. Note that the data types must match!

Now you can make and run migrations - basically, Django's way of managing changes to data models. Frameworks like Django are appealing exactly because they're able to manage and track changes to large, sophisticated databases without ever interacting with these databases directly.

```py
python manage.py makemigrations
python manage.py migrate
```

## Use the LayerMapping Utility to Load Data

Create a new file, `somerville/load.py`.

```py
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
```

Here, we tell Django how to map Shapefile fields onto the model we built in `models.py`. There are many reasons to use a formal loader script like this: it contains a lot of built-in validator functionality so that data loaded into your database lines up with the Django models. It also automatically reprojects spatial data into the CRS listed in the `geom` field (in this case, EPSG:4326, WGS 84 - we use this projection because it's the only one supported by the GeoJSON spec).

## Load the Neighborhoods data.

```sh
python manage.py shell
```

```py
>>> from somerville import load
>>> load.run('Neighborhoods.shp')
Saved: North Point
Saved: Boynton Yards
Saved: Twin City
Saved: Brickbottom
Saved: Duck Village
Saved: Inner Belt
Saved: Union Square
Saved: East Somerville
Saved: Porter Square
Saved: Spring Hill
Saved: Assembly Square
Saved: Ten Hills
Saved: Magoun Square
Saved: Winter Hill
Saved: Ball Square
Saved: Davis Square
Saved: Powder House Square
Saved: Teele Square
Saved: Hillside
>>> quit()
```

## Build a View

In `somerville/views.py`, we're going to create a view that presents all features stored in our PostGIS database as a GeoJSON file. To do this, we use django's stock serializer which can display results of what is ultimately a (hidden) SQL query as a GeoJSON.

```py
from django.shortcuts import render
from django.views import generic
from django.core.serializers import serialize

# Import Neigh model.
from .models import Neigh

class IndexView(generic.ListView):
    model = Neigh
    template_name = 'index.html'
    context_object_name = 'neigh'

    def get_queryset(self):
        return serialize('geojson', 
            Neigh.objects.all(),
            geometry_field='geom',
            fields=('name',),
        )
```

Let's wire up this view to our Django app! In `map_app/urls.py`, let's make some changes and create a new `urlpattern`.

```python
from django.contrib import admin
from django.urls import path, include
from somerville import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.IndexView.as_view(), name='index'),
]
```

Note that you're importing views from your Somerville app - this is the file we just created! and configuring a urlpattern such that when the root path is loaded (`''` - in other words `localhost:8000/`), it loads the IndexView from somerville.views. 

## Build a Template

Last step! We need to tell Django what to render in the browser using a template. Note that in the above view, we reference a template that doesn't yet exist (`index.html`). Let's change that! Create a folder called `templates` in your somerville app folder and create a new `index.html file`.

```html
<!DOCTYPE html>
<html lang="en" style="padding: 0;margin: 0;width:100%;height: 100%;">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="ie=edge">
    <title>Sample Map</title>
</head>
<body style="padding: 0;margin: 0; width:100%;height: 100%;">
    {{neigh}}
</body>
</html>
```

Simple HTML with some simple styling... except for that {{neigh}}, huh? That's Django's way of referencing variables and querysets - the results of model views! Run the server like so and you should see the text of a GeoJSON file filling your page when you load `localhost:8000`.

```py
python manage.py runserver
```

Let's pop that GeoJSON into a Leaflet map... this should be familiar.

```html
<!DOCTYPE html>
<html lang="en" style="padding: 0;margin: 0;width:100%;height: 100%;">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="ie=edge">
    <title>Sample Map</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.5.1/dist/leaflet.css"
    integrity="sha512-xwE/Az9zrjBIphAcBb3F6JVqxf46+CDLwfLMHloNu6KEQCAWi6HcDUbeOfBIptF7tcCzusKFjFw2yuvEpDL9wQ=="
    crossorigin=""/>
    <script src="https://unpkg.com/leaflet@1.5.1/dist/leaflet.js"
    integrity="sha512-GffPMF3RvMeYyc1LWMHtK8EbPv0iNZ8/oTtHPx9/cc2ILxQ+u905qIwdpULaqDkyBKgOaB57QTMg7ztg8Jm2Og=="
    crossorigin=""></script>

</head>
<body style="padding: 0;margin: 0; width:100%;height: 100%;">
    <div id="map" style="width:100%;height: 100%;"></div>
    <script>
        var map = L.map('map').setView([42.3876, -71.0995], 13);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(map);

        L.geoJSON({{neigh|safe}}).bindPopup(function (layer) {
            return layer.feature.properties.name;
        }).addTo(map);
    </script>
</body>
</html>
```

Note that you need to use {{neigh|safe}}, which turns some safeties off - because we loaded this data into our database, we know it's clean and doesn't contain any SQL injections or any of the things from which Django is trying to protect us. Load that page and see your Django web map app whirring happily!