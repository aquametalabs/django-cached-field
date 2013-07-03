from setuptools import setup, find_packages
import sys, os

version = '1.2.3'

setup(name='django-cached-field',
      version=version,
      description="Celery-deferred, cached fields on Django ORM for expensive-to-calculate data",
      long_description="""Celery-deferred, cached fields on Django ORM for expensive-to-calculate data""",
      classifiers=[],  # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='django caching',
      author='Martin Chase',
      author_email='outofculture@gmail.com',
      url='https://github.com/aquameta/django-cached-field',
      license='BSD',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
        'django>=1.3.1',
        'celery>=3.0',
        'django-celery>=3.0',
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
