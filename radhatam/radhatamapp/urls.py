"""radhatam URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from . import views

app_name = 'radhatamapp'

urlpatterns = [
    path('', views.index, name="index"),
    path('datastructure/<str:action>/<int:id>', views.datastructure, name='datastructure'),
    path('dataprep/<str:action>/<int:id>', views.dataprep, name='dataprep'),
    path('edit_fieldtype/<int:id>', views.edit_fieldtype, name='edit_fieldtype'),
    path('dataviz/<str:action>/<int:id>', views.dataviz, name='dataviz'),
    path('dataalerts/<str:action>/<int:id>', views.dataalerts, name='dataalerts'),
]
