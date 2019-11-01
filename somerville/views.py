from django.shortcuts import render
from django.views import generic
from django.core.serializers import serialize

# Create your views here.
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