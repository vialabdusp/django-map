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