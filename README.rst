Django Cached Field
===================

Introduction
------------

Using Django ORM and Celery, keep expensive-to-calculate attributes
up-to-date.

Example
-------

Say you have a slow method on one of your models::

    class Lamppost(models.Model):

        @property
        def slow_full_name(self):
            sleep(30)
            return 'The %s %s of %s' % (self.weight, self.first_name, self.country)

Ugh; too slow. Let's cache that. We'll want a few tools. `Celery
<http://celeryproject.org/>` with `django-celery
<http://github.com/ask/django-celery>` will need to be set up and
humming along smoothly. Then we'll add in our cached field and rename
our method appropriately::

    from django_cached_field import CachedIntegerField, ModelWithCachedFields

    class Lamppost(models.Model, ModelWithCachedFields):
        slow_full_name = CachedTextField(null=True)

        def calculate_slow_full_name(self):
            sleep(30)
            return 'The %s %s of %s' % (self.weight, self.first_name, self.country)

(Yeah, ``calculate_`` is just a convention. I clearly haven't given up
the rails ghost...)

Next, migrate your db schema to include the new cached field using
south, or roll your own. Note that two fields will be added to this
table, ``cached_slow_full_name`` of type *text* and
``slow_full_name_recalculation_needed`` of type *boolean*, probably
defaulting to true.

Already that's kinda better. ``lamppost.slow_full_name`` may take 30
seconds the first time it gets called for a given record, but from
then on, it'll be nigh instant. Of course, at this point, it will
never change after that first call.

The remaining important piece of the puzzle is to invalidate our
cache. Thoses constituent fields are probably changed in some views.py
(this could be more clever about noticing if the relevant values are
updated)::

    @render_to("lamppost/edit.html")
    def edit(request, lamppost_id):
        lamppost = Lamppost.objects.get(pk=lamppost_id)
        if request.METHOD == 'POST':
            form = LamppostForm(request.POST)
            if form.is_valid():
                form.save()
                form.instance.flag_slow_full_name_as_stale()
        else:
            form = LamppostForm()
        return {'form': form, 'lamppost': lamppost}

**This is the hardest part as the developer!** Caching requires you
hunt down every place the value could be changed and calling that
``flag_slow_full_name_as_stale`` method. Is country assigned a random
new value every morning at cron'o'clock? That flag had best be stale
by cron'o'one. Do you calculate weight based on the sum of all
associated pigeons? Hook into the pigeons landing. And takeoff. And
everything that changes an individual pigeon's weight. As Abraham
Lincolc said, "There are only two hard problems in programming:
naming, cache invalidation and off-by-one errors."

Installation
------------

You can make things easy on yourself::

    pip install django-cached-field

Or, for a manual installation, you can clone the repo and install it using python and setup.py::

    git clone git://github.com/aquameta/django-cached-field.git
    cd django-cached-field/
    python setup.py install

Tested with django 1.3.1, celery 2.3.1, django-celery 2.3.3.

Configuration
-------------

Two settings changes are pretty much required for things to work: make
sure it's a registered app, make sure celery sees its tasks file::

   INSTALLED_APPS += ['django_cached_field',]
   CELERY_IMPORTS += ['django_cached_field.tasks',]

One change is optional: whether recalculation should happen when
flagged as stale (default) or be left to the next time the attribute
is accessed. This is useful for testing environments where you don't
care that your cached values are invalid. Note that in this situation,
you wouldn't need celery. ::

   CACHED_FIELD_EAGER_RECALCULATION = True # or False for testing environments

This is a global option, so individual exceptions should instead be
handled by passing the *and_recalculate* argument to the
*flag_FIELD_as_stale* call.

Caveats
-------

* Race condition if you flag a field as stale in a db transaction that takes longer to complete than the celery job takes to be called.

TODO
----

* All my tests are in the project I pulled this out of, but based on models therein. I don't have experience making tests for standalone django libraries. Someone wanna point me to a tutorial?
* Argument-passed, custom-named calculat/flag/&c.-methods are stubbed in, but not done.
* I should probably make sure I'm covering all the field types, not just the ones I've ever cared about.
* The docs are a lie: do the south integration.
