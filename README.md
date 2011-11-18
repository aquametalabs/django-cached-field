# Django Cached Field

## Introduction

Using standard Django ORM and Celery, keep expensive-to-calculate
attributes up-to-date without unnecessarily bogging down your users.
You still have to do the hard work of figuring out when to invalidate
your cache, but the rest of the backend is handled transparently.

## Installation

For a manual installation, you can clone the repo and install it using python and setup.py.

    git clone git://github.com/aquameta/django-cached-field.git
    cd django-cached-field/
    python setup.py install

## Configuration

   INSTALLED_APPS += ['django_cached_field',]
   CELERY_IMPORTS += ['django_cached_field.tasks',]

## Example

In models.py:
    from django.db import models
    from django_cached_field import CachedIntegerField, ModelWithCachedFields

    class MyModel(models.Model, ModelWithCachedFields):
        a_field = CachedIntegerField(null=True)

        def calculate_a_field(self):
            return something_expensive_to_calculate

In views.py:
    @render_to("some/template.html")
    def some_view(request, my_model_id):
        my_model = MyModel.objects.get(pk=my_model_id)
        success = bool(my_model.a_field > 0)
        return locals()

    @render_to("another/template.html")
    def another_view(request):
        form = MyForm(request)
        if form.is_valid:
            form.instance.flag_a_field_as_stale()
        return locals()
