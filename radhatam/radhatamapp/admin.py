from django.contrib import admin

# Register your models here.
from .models import Entity, Field, FunctionMeta, ArgumentMeta, DerivedFieldArgument, FieldFilter

model = [Entity, Field, FunctionMeta, ArgumentMeta,
         DerivedFieldArgument, FieldFilter]
for m in model:
    admin.site.register(m)
