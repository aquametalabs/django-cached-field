Django Cached Field
===================

Introduction
------------

Using Django ORM and Celery, cache expensive-to-calculate attributes.

Installation
------------

You can make things easy on yourself::

    pip install django-cached-field

Or, for a manual installation, you can clone the repo and install it
using python and setup.py::

    git clone git://github.com/aquameta/django-cached-field.git
    cd django-cached-field/
    python setup.py install

Tested with django 1.3.1, celery 2.3.1, and django-celery 2.3.3, but I
would entertain other minimums if someone was willing to test them.

Configuration
-------------

Two settings changes are pretty much required for things to work: make
sure it's a registered app, make sure celery sees its tasks file::

   INSTALLED_APPS += ['django_cached_field',]
   CELERY_IMPORTS += ['django_cached_field.tasks',]

One change is optional: whether recalculation should happen when
flagged as stale (default) or be left to the next time the attribute
is accessed. This is useful for optimizing testing environments where
you don't care that your cached values are invalid or that the expense
of calculation is applied to a user. Note that, in this situation, you
wouldn't need celery. ::

   CACHED_FIELD_EAGER_RECALCULATION = True # or False for testing environments

This is a global option, so individual exceptions should instead be
handled by passing the ``and_recalculate`` argument to the
``flag_FIELD_as_stale`` call.

Example
-------

Say you have a CTO who believes everything belongs in the database and
a slow method on one of your models::

    class Lamppost(models.Model):
        # ...
        @property
        def slow_full_name(self):
            ackermann(5, 2)
            return 'The %s %s of %s' % (self.weight, self.first_name, self.country)

Ugh; too slow. Let's cache that (but not with, say, a dedicated
caching system). We'll want a few tools. `Celery
<http://celeryproject.org/>` with `django-celery
<http://github.com/ask/django-celery>` will need to be set up and
humming along smoothly. Then we'll add in our cached field and rename
our method appropriately::

    from django_cached_field import CachedIntegerField

    class Lamppost(models.Model):
        # ...
        slow_full_name = CachedTextField(null=True)

        def calculate_slow_full_name(self):
            ackermann(5, 2)
            return 'The %s %s of %s' % (self.weight, self.first_name, self.country)

(Yeah, ``calculate_*`` is just a convention. I clearly haven't given
up the rails ghost, but you can pass in your own method name with
``calculation_method_name``.)

Next, migrate your db schema to include the new cached field using
south, or roll your own. Note that at least two fields will be added
to this table, ``cached_slow_full_name`` of type *text*,
``slow_full_name_recalculation_needed`` of type *boolean*, probably
defaulting to true, and possibly ``slow_full_name_expires_after`` of
type *datetime*, if we pass ``temporal_triggers=True`` into the field
declaration (more on that later).

Already that's kinda better. ``lamppost.slow_full_name`` may take a
while the first time it gets called for a given record, but from then
on, it'll be nigh instant. Of course, at this point, it will never
change after that first call.

The remaining important piece of the puzzle is to invalidate our cache
using ``flag_slow_full_name_as_stale``. It is probably changed in some
views.py (this example code could be more clever about noticing if the
relevant values are updated)::

    @render_to('lamppost/edit.html')
    def edit(request, lamppost_id):
        lamppost = Lamppost.objects.get(pk=lamppost_id)
        if request.METHOD == 'POST':
            form = LamppostForm(request.POST)
            if form.is_valid():
                form.save()
                form.instance.flag_slow_full_name_as_stale()
                return HttpResponseRedirect(
                    reverse('lamppost_view', args=(lamppost.pk,)))
        else:
            form = LamppostForm()
        return {'form': form, 'lamppost': lamppost}

**This is the hardest part as the developer.** Caching requires you
hunt down every place the value could be changed and calling that
``flag_slow_full_name_as_stale`` method. Is country assigned a random
new value every morning at cron'o'clock? That flag had best be stale
by cron'o'one. Do you calculate weight based on the sum of all
associated pigeons? Hook into the pigeons landing. And takeoff. And
everything that changes an individual pigeon's weight. As Abraham
Lincoln said, "There are only two hard problems in programming:
naming, cache invalidation and off-by-one errors."

One possible invalidation scheme you might want to use is expiration
dates. We know the pigeons on our lamppost are going to die and turn
into ghosts, right::

    class Pigeon(models.Model):
        death_day = models.DateField()

        def die(self):
            self.weight = 0
            self.save()

And rather than bother the pigeon-death-handling system, we'll take
note of their death as they land::

    class Lamppost(models.Model):
        #...
        def notice_pigeon_landing(self, pigeon):
            earliest = self.pigeon_set.all().aggregate(
                models.Min('death_date'))['death_date']
            self.expire_slow_full_name_after(earliest)

Or maybe you only want the cache to ever be valid for 30 minutes, lest
**They** have too easy a time of tracking your thoughts. So, yeah, you
get the idea.

Caveats
-------

* Race condition if you flag a field as stale in a db transaction that takes longer to complete than the celery job takes to be called (so commit your transactions before invalidating the cache).
* All ORM methods (e.g. ``order_by``, ``filter``) can only access this field through ``cached_FIELD``.
* ``recalculate_FIELD`` uses ``.update(cached_FIELD=`` to set the value. Don't expect ``.save`` to be called.
* ``flag_FIELD_as_stale`` uses ``.update``, as well.
* This may break if you try to add this mixin to a field class that multiply-inherits (I'm currently grabbing an arbitrary, non-CachedFieldMixin class and making the real field with it).
* The FIELD_recalculation_needed field is accessed by regex in at least one place, so problems will result from user fields that match the same pattern.

TODO
----

* Figure out if we can turn temporal_triggers into a celery job that happens once at the given time.
* All my tests are in the project I pulled this out of, but based on models therein. I don't have experience making tests for standalone django libraries. Someone wanna point me to a tutorial?
* Recalculation task will not adapt to recalculation_needed_field_name option
* Replace use of _recalculation_needed regex with class-level registry of cached fields.
* Fix race condition with https://github.com/davehughes/django-transaction-signals ?
* Or maybe with https://github.com/chrisdoble/django-celery-transactions ?
