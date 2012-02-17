from django.db import models
from django.conf import settings
from django.utils.functional import curry
from django_cached_field.tasks import offload_cache_recalculation


class ModelWithCachedFields(object):

    def _flag_FIELD_as_stale(self, field=None, and_recalculate=None, commit=True):
        if and_recalculate is None:
            try:
                and_recalculate = settings.CACHED_FIELD_EAGER_RECALCULATION
            except AttributeError:
                and_recalculate = True
        if not getattr(self, field.recalculation_needed_field_name):
            setattr(self, field.recalculation_needed_field_name, True)
            kwargs = {field.recalculation_needed_field_name: True}
            if commit:
                type(self).objects.filter(pk=self.pk).update(**kwargs)
                if and_recalculate:
                    self.trigger_cache_recalculation()
            else:
                return kwargs
        return {}

    def _recalculate_FIELD(self, field=None, commit=True):
        val = getattr(self, field.calculation_method_name)()
        self._set_FIELD(val, field=field)
        setattr(self, field.recalculation_needed_field_name, False)
        kwargs = {field.cached_field_name: val,
                  field.recalculation_needed_field_name: False}
        if commit:
            type(self).objects.filter(pk=self.pk).update(**kwargs)
        else:
            return kwargs

    def _get_FIELD(self, field=None):
        val = getattr(self, field.cached_field_name)
        flag = getattr(self, field.recalculation_needed_field_name)
        if val is None or flag is True:
            self._recalculate_FIELD(field=field)
            val = getattr(self, field.cached_field_name)
        return val

    def _set_FIELD(self, val, field=None):
        setattr(self, field.cached_field_name, val)

    def trigger_cache_recalculation(self):
        offload_cache_recalculation.delay(type(self)._meta.app_label, type(self)._meta.object_name, self.pk)


class CachedFieldMixin(object):
    """Include this when you want to make a field that:
      * accesses its value with @property FIELD
      * stores its value on the db-level in cached_FIELD
      * keeps a boolean on the db-level: FIELD_recalculation_needed
      * sets above to True with flag_FIELD_as_stale()
      * flag_FIELD_as_stale also queues a delayed
        offload_cache_recalculation if and_recalculate is set to True
        (the default).
      * performs recalculation with recalculate_FIELD()
      * accepts `commit' flag to recalculate_FIELD and
        flag_FIELD_as_stale that, if false, prevents calling
        .update or .trigger_cache_recalculation
      * recalculates automatically if FIELD is accessed and
        cached_FIELD is None or FIELD_recalculation_needed is True
      * calculates its value in a user-defined calculate_FIELD(), which
        should return the value
    Eventual future init args:
      `calculation_method_name' to specify a method other than calculate_FIELD
      `cached_field_name' to specify a field name other than cached_FIELD
      `recalculation_needed_field_name' to specify a field name other than
        FIELD_recalculation_needed
    """

    def __init__(self, *args, **kwargs):
        self.init_kwargs_for_field = kwargs

    def contribute_to_class(self, cls, name):
        self.name = name
        setattr(cls, 'recalculate_%s' % self.name, curry(cls._recalculate_FIELD, field=self))
        setattr(cls, self.name, property(curry(cls._get_FIELD, field=self), curry(cls._set_FIELD, field=self)))

        proper_field = (set(type(self).__bases__) - set((CachedFieldMixin,))).pop() #:MC: ew.
        proper_field = proper_field(**self.init_kwargs_for_field)
        setattr(cls, self.cached_field_name, proper_field)
        proper_field.contribute_to_class(cls, self.cached_field_name)

        flag_field = models.BooleanField(default=False)
        setattr(cls, self.recalculation_needed_field_name, flag_field)
        flag_field.contribute_to_class(cls, self.recalculation_needed_field_name)

        setattr(cls, 'flag_%s_as_stale' % self.name, curry(cls._flag_FIELD_as_stale, field=self))

    @property
    def cached_field_name(self):
        return 'cached_%s' % self.name

    @property
    def recalculation_needed_field_name(self):
        return '%s_recalculation_needed' % self.name

    @property
    def calculation_method_name(self):
        return 'calculate_%s' % self.name

class CachedIntegerField(CachedFieldMixin, models.IntegerField):
    pass
class CachedFloatField(CachedFieldMixin, models.FloatField):
    pass
class CachedCharField(CachedFieldMixin, models.CharField):
    pass
class CachedBooleanField(CachedFieldMixin, models.BooleanField):
    pass
class CachedDecimalField(CachedFieldMixin, models.DecimalField):
    pass
class CachedDateField(CachedFieldMixin, models.DateField):
    pass
