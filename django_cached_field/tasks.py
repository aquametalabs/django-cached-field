from celery.decorators import task
from django.db.models import get_model
import re


recalc_needed_re = re.compile("(.*)_recalculation_needed$")
@task
def offload_cache_recalculation(app, model, obj_id, **kwargs):
    logger = offload_cache_recalculation.get_logger(**kwargs)
    model = get_model(app,model)
    try:
        obj = model.objects.get(pk=obj_id)
        for f in model._meta.fields:
            match = recalc_needed_re.search(f.name)
            if match and getattr(obj, f.name):
                basename = match.groups()[0]
                getattr(obj, "recalculate_%s" % basename)()
    except model.DoesNotExist:
        logger.info('%s.%s with pk %s does not exist.  Was offload_cache_recalculation called before initial object creation or after object deletion?' % (app, model, obj_id))
