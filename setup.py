from setuptools import setup, find_packages
import sys, os

version = '0.1'


setup(name='django-cached-field',
      version=version,
      description="Cached fields on Django ORM for expensive-to-calculate data",
      long_description="""Cached fields on Django ORM for expensive-to-calculate data""",
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
          # -*- Extra requirements: -*-
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
