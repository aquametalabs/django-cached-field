from datetime import datetime
from django.db import models
from django.conf import settings
from django.utils.functional import curry
from django_cached_field.tasks import offload_cache_recalculation


def _flag_FIELD_as_stale(self, field=None, and_recalculate=None, commit=True):
    if and_recalculate is None:
        and_recalculate = True
        if hasattr(settings, 'CACHED_FIELD_EAGER_RECALCULATION'):
            and_recalculate = settings.CACHED_FIELD_EAGER_RECALCULATION
    if not getattr(self, field.recalculation_needed_field_name):
        setattr(self, field.recalculation_needed_field_name, True)
        kwargs = {field.recalculation_needed_field_name: True}
    else:
        kwargs = {}  # This won't trigger an actual UPDATE.
    if commit:
        type(self).objects.filter(pk=self.pk).update(**kwargs)
        if and_recalculate:
            self.trigger_cache_recalculation()
    return kwargs


def _expire_FIELD_after(self, when=None, field=None):
    setattr(self, field.expiration_field_name, when)
    type(self).objects.filter(pk=self.pk).update(**{field.expiration_field_name: when})


def _recalculate_FIELD(self, field=None, commit=True):
    val = getattr(self, field.calculation_method_name)()
    self._set_FIELD(val, field=field)
    setattr(self, field.recalculation_needed_field_name, False)
    kwargs = {field.cached_field_name: val,
              field.recalculation_needed_field_name: False}
    if field.temporal_triggers:
        expires = getattr(self, field.expiration_field_name)
        if expires and expires < datetime.now():
            setattr(self, field.expiration_field_name, None)
            kwargs[field.expiration_field_name] = None
    if commit:
        type(self).objects.filter(pk=self.pk).update(**kwargs)
    else:
        return kwargs


def _get_FIELD(self, field=None):
    val = getattr(self, field.cached_field_name)
    flag = getattr(self, field.recalculation_needed_field_name)
    if field.temporal_triggers:
        expiration = getattr(self, field.expiration_field_name)
        flag = flag or (expiration is not None and expiration < datetime.now())
    if flag is True:
        self._recalculate_FIELD(field=field)
        val = getattr(self, field.cached_field_name)
    return val


def _set_FIELD(self, val, field=None):
    setattr(self, field.cached_field_name, val)


def trigger_cache_recalculation(self):
    offload_cache_recalculation.delay(type(self)._meta.app_label, type(self)._meta.object_name, self.pk)


def ensure_class_has_cached_field_methods(cls):
    # :TODO: can this be done with a mixin?
    for func in (trigger_cache_recalculation, _set_FIELD, _get_FIELD,
                 _recalculate_FIELD, _flag_FIELD_as_stale,
                 _expire_FIELD_after):
        if not hasattr(cls, func.__name__):
            setattr(cls, func.__name__, func)


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
      * possibly recalculates automatically after a specified datetime
      * calculates its value in a user-defined calculate_FIELD(), which
        should return the value
    Init args:
      `calculation_method_name' to specify a method other than calculate_FIELD
      `cached_field_name' to specify a field name other than cached_FIELD
      `recalculation_needed_field_name' to specify a field name other than
      `temporal_triggers' to turn on expirations
        FIELD_recalculation_needed
    """

    def __init__(self, calculation_method_name=None, cached_field_name=None,
                 recalculation_needed_field_name=None, temporal_triggers=False,
                 expiration_field_name=None, *args, **kwargs):
        self.temporal_triggers = temporal_triggers
        if expiration_field_name:
            self.expiration_field_name = expiration_field_name
        if calculation_method_name:
            self.calculation_method_name = calculation_method_name
        if cached_field_name:
            self.cached_field_name = cached_field_name
        if recalculation_needed_field_name:
            self.recalculation_needed_field_name = recalculation_needed_field_name
        self.init_args_for_field = args
        self.init_kwargs_for_field = kwargs

    def contribute_to_class(self, cls, name):
        ensure_class_has_cached_field_methods(cls)
        self.name = name
        setattr(cls, 'recalculate_%s' % self.name, curry(cls._recalculate_FIELD, field=self))
        setattr(cls, self.name, property(curry(cls._get_FIELD, field=self), curry(cls._set_FIELD, field=self)))

        proper_field = (set(type(self).__bases__) - set((CachedFieldMixin,))).pop()  # :MC: ew.
        proper_field = proper_field(*self.init_args_for_field, **self.init_kwargs_for_field)
        setattr(cls, self.cached_field_name, proper_field)
        proper_field.contribute_to_class(cls, self.cached_field_name)

        flag_field = models.BooleanField(default=True)
        setattr(cls, self.recalculation_needed_field_name, flag_field)
        flag_field.contribute_to_class(cls, self.recalculation_needed_field_name)

        if self.temporal_triggers:
            setattr(cls, 'expire_%s_after' % self.name, curry(cls._expire_FIELD_after, field=self))
            expire_field = models.DateTimeField(null=True)
            setattr(cls, self.expiration_field_name, expire_field)
            expire_field.contribute_to_class(cls, self.expiration_field_name)

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

    @property
    def expiration_field_name(self):
        return '%s_expires_after' % self.name


class CachedBigIntegerField(CachedFieldMixin, models.BigIntegerField):
    pass


class CachedBooleanField(CachedFieldMixin, models.BooleanField):
    pass


class CachedCharField(CachedFieldMixin, models.CharField):
    pass


class CachedDateField(CachedFieldMixin, models.DateField):
    pass


class CachedDateTimeField(CachedFieldMixin, models.DateTimeField):
    pass


class CachedDecimalField(CachedFieldMixin, models.DecimalField):
    pass


class CachedEmailField(CachedFieldMixin, models.EmailField):
    pass


class CachedFloatField(CachedFieldMixin, models.FloatField):
    pass


class CachedIntegerField(CachedFieldMixin, models.IntegerField):
    pass


class CachedIPAddressField(CachedFieldMixin, models.IPAddressField):
    pass


class CachedNullBooleanField(CachedFieldMixin, models.NullBooleanField):
    pass


class CachedPositiveIntegerField(CachedFieldMixin, models.PositiveIntegerField):
    pass


class CachedPositiveSmallIntegerField(CachedFieldMixin, models.PositiveSmallIntegerField):
    pass


class CachedSlugField(CachedFieldMixin, models.SlugField):
    pass


class CachedSmallIntegerField(CachedFieldMixin, models.SmallIntegerField):
    pass


class CachedTextField(CachedFieldMixin, models.TextField):
    pass


class CachedTimeField(CachedFieldMixin, models.TimeField):
    pass
