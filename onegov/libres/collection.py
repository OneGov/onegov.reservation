from onegov.core.utils import normalize_for_url
from onegov.libres.models import Resource
from sqlalchemy import inspect
from uuid import uuid4


any_type = object()


class ResourceCollection(object):
    """ Manages a list of resources.

    """
    def __init__(self, libres_context):
        assert hasattr(libres_context, 'get_service'), """
            The ResourceCollection expected the libres_contex, not the session.
        """

        self.libres_context = libres_context
        self.session = libres_context.get_service('session_provider').session()

    def query(self):
        return self.session.query(Resource)

    def add(self, title, timezone, type=None, name=None, meta={}, content={},
            definition=None):

        # look up the right class depending on the type
        _mapper = inspect(Resource).polymorphic_map.get(type)
        resource = (_mapper and _mapper.class_ or Resource)()

        resource.id == uuid4()
        resource.name = name or normalize_for_url(title)
        resource.title = title
        resource.timezone = timezone
        resource.meta = meta
        resource.content = content
        resource.definition = definition

        self.session.add(resource)
        self.session.flush()

        return resource

    def scheduler_by_id(self, id):
        resource = self.query().filter(Resource.id == id).first()

        if resource:
            return resource.get_scheduler(self.libres_context)

    def by_id(self, id, ensure_type=any_type):
        query = self.query().filter(Resource.id == id)

        if ensure_type is not any_type:
            query = query.filter(Resource.type == type)

        return query.first()

    def by_name(self, name, ensure_type=any_type):
        query = self.query().filter(Resource.name == name)

        if ensure_type is not any_type:
            query = query.filter(Resource.type == type)

        return query.first()

    def delete(self, resource, including_reservations=False):
        scheduler = resource.get_scheduler(self.libres_context)

        if not including_reservations:
            assert not scheduler.managed_reserved_slots().first()
            assert not scheduler.managed_reservations().first()

            scheduler.managed_allocations().delete('fetch')
        else:
            scheduler.extinguish_managed_records()

        self.session.delete(resource)
        self.session.flush()
