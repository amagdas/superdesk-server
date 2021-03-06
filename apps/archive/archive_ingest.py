# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

"""
Created on May 23, 2014

@author: Ioan v. Pocol
"""

import superdesk

from eve.utils import config
from apps.archive.common import insert_into_versions, remove_unwanted, set_original_creator
from apps.tasks import send_to

from superdesk.errors import SuperdeskApiError, InvalidStateTransitionError
from superdesk.utc import utcnow
from superdesk.resource import Resource
from superdesk.services import BaseService
from .archive import SOURCE as ARCHIVE
from superdesk.workflow import is_workflow_state_transition_valid
from apps.content import LINKED_IN_PACKAGES, PACKAGE
STATE_FETCHED = 'fetched'


class ArchiveIngestResource(Resource):
    resource_methods = ['POST']
    item_methods = []
    schema = {
        'guid': {'type': 'string', 'required': True},
        'desk': Resource.rel('desks', False, nullable=True)
    }
    privileges = {'POST': 'ingest_move'}


class ArchiveIngestService(BaseService):

    def create(self, docs, **kwargs):
        for doc in docs:
            ingest_doc = superdesk.get_resource_service('ingest').find_one(req=None, _id=doc.get('guid'))
            if not ingest_doc:
                msg = 'Fail to found ingest item with guid: %s' % doc.get('guid')
                raise SuperdeskApiError.notFoundError(msg)

            if not is_workflow_state_transition_valid('fetch_as_from_ingest', ingest_doc[config.CONTENT_STATE]):
                raise InvalidStateTransitionError()

            archived = utcnow()
            superdesk.get_resource_service('ingest').patch(ingest_doc.get('_id'), {'archived': archived})
            doc['archived'] = archived

            archived_doc = superdesk.get_resource_service(ARCHIVE).find_one(req=None, _id=doc.get('guid'))
            if not archived_doc:
                dest_doc = dict(ingest_doc)
                dest_doc[config.VERSION] = 1
                send_to(dest_doc, doc.get('desk'))
                dest_doc[config.CONTENT_STATE] = STATE_FETCHED
                remove_unwanted(dest_doc)
                for ref in [ref for group in dest_doc.get('groups', [])
                            for ref in group.get('refs', []) if 'residRef' in ref]:
                    ref['location'] = ARCHIVE
                    ref['guid'] = ref['residRef']

                set_original_creator(dest_doc)
                if doc.get(PACKAGE):
                    links = dest_doc.get(LINKED_IN_PACKAGES, [])
                    links.append({PACKAGE: doc.get(PACKAGE)})
                    dest_doc[LINKED_IN_PACKAGES] = links
                superdesk.get_resource_service(ARCHIVE).post([dest_doc])
                insert_into_versions(dest_doc.get('guid'))
                desk = doc.get('desk')
                refs = [{'guid': ref.get('residRef'), 'desk': desk, PACKAGE: dest_doc.get('_id')}
                        for group in dest_doc.get('groups', [])
                        for ref in group.get('refs', []) if 'residRef' in ref]
                if refs:
                    self.create(refs)
            else:
                if doc.get(PACKAGE):
                    links = archived_doc.get(LINKED_IN_PACKAGES, [])
                    links.append({PACKAGE: doc.get(PACKAGE)})
                    superdesk.get_resource_service(ARCHIVE).patch(archived_doc.get('_id'), {LINKED_IN_PACKAGES: links})

        return [doc.get('guid') for doc in docs]


superdesk.workflow_state(STATE_FETCHED)

superdesk.workflow_action(
    name='fetch_as_from_ingest',
    include_states=['ingested'],
    privileges=['archive', 'ingest_move']
)

superdesk.workflow_state('routed')
superdesk.workflow_action(
    name='route',
    include_states=['ingested']
)
