# Django Cached Field

## Introduction

## Installation

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

