# -*- coding: utf-8 -*-
#
# Copyright (C) 2024 Bitergia
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#   Jose Javier Merchante <jjmerchante@bitergia.com>
#

import datetime
import logging

from grimoire_elk.elastic import ElasticSearch
from grimoire_elk.elastic_mapping import Mapping as BaseMapping
from grimoire_elk.enriched.enrich import Enrich
from grimoire_elk.enriched.utils import anonymize_url
from grimoirelab_toolkit.datetime import str_to_datetime
from grimoirelab_toolkit.uris import urijoin


HEADER_JSON = {'Content-Type': 'application/json'}


logger = logging.getLogger(__name__)


class Mapping(BaseMapping):

    @staticmethod
    def get_elastic_mappings(es_major):
        """Get Elasticsearch mapping.

        :param es_major: major version of Elasticsearch, as string
        :returns:        dictionary with a key, 'items', with the mapping
        """

        mapping = """
        {
            "properties": {
               "translation_string_analyzed": {
                    "type": "text",
                    "index": true
               },
               "id": {
                    "type": "keyword"
               },
               "locale": {
                    "type": "keyword"
               }
            }
        }
        """

        return {"items": mapping}


class PontoonEnrich(Enrich):

    mapping = Mapping

    action_roles = ['user']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.studies = []
        self.studies.append(self.enrich_demography)
        self.studies.append(self.enrich_latest_translation_status)

    def get_field_author(self):
        return "user"

    def get_identities(self, item):
        """ Return the identities from an item """

        user = self.get_sh_identity(item, identity_field='user')
        return [user]

    def get_sh_identity(self, item, identity_field=None):
        identity = {}

        user = item  # by default a specific user dict is expected
        if isinstance(item, dict) and 'data' in item:
            user = item['data'][identity_field]
        elif isinstance(item, dict) and identity_field in item:
            user = item[identity_field]

        if not user:
            return identity

        identity['name'] = user['name']
        if '@' in user['name']:
            identity['email'] = user['name']
        else:
            identity['email'] = None
        identity['username'] = None
        return identity

    def get_project_repository(self, eitem):
        return eitem['origin']

    def get_field_unique_id(self):
        return "uuid"

    def get_rich_item(self, item):
        eitem = {}
        self.copy_raw_fields(self.RAW_FIELDS_COPY, item, eitem)

        action = item['data']

        eitem['id'] = action['id']

        eitem['type'] = action['type']
        eitem['date'] = str_to_datetime(action['date']).isoformat()

        eitem['user_name'] = action['user']['name']
        eitem['system_user'] = action['user']['system_user']
        eitem['user_pk'] = action['user']['pk']

        eitem['entity_pk'] = action['entity']['pk']
        eitem['entity_key'] = action['entity']['key']

        eitem['locale'] = action['locale']['code']
        eitem['locale_name'] = action['locale']['name']

        eitem['resource_pk'] = action['resource']['pk']
        eitem['resource_path'] = action['resource']['path']
        eitem['resource_format'] = action['resource']['format']

        eitem['translation_pk'] = action['translation']['pk']
        eitem['translation_string'] = action['translation']['string'][:self.KEYWORD_MAX_LENGTH]
        eitem['translation_string_analyzed'] = action['translation']['string']
        eitem['translation_errors'] = len(action['translation']['errors'])
        eitem['translation_warnings'] = len(action['translation']['warnings'])
        eitem['translation_approved'] = action['translation']['approved']
        eitem['translation_rejected'] = action['translation']['rejected']
        eitem['translation_pretranslated'] = action['translation']['pretranslated']
        eitem['translation_fuzzy'] = action['translation']['fuzzy']

        eitem['project_pk'] = action['project']['pk']
        eitem['project_name'] = action['project']['name']
        eitem['project_slug'] = action['project']['slug']

        origin = "/".join(item['origin'].split('/')[:-1])
        url = urijoin(origin,
                      action['locale']['code'],
                      action['project']['slug'],
                      action['resource']['path'])
        url += f"?string={action['entity']['pk']}"
        eitem['url'] = url

        eitem['entity_uid'] = f"{eitem['project_slug']}:{eitem['locale']}:{eitem['entity_pk']}"

        if self.sortinghat:
            eitem.update(self.get_item_sh(action, self.action_roles, 'date'))

        if self.prjs_map:
            eitem.update(self.get_item_project(eitem))

        self.add_repository_labels(eitem)
        self.add_metadata_filter_raw(eitem)
        eitem.update(self.get_grimoire_fields(action['date'], "action"))

        return eitem

    def enrich_latest_translation_status(self, ocean_backend, enrich_backend, out_index,
                                         alias="pontoon_latest_translation_status"):
        """Identify the last translation action for each entity-locale pair and store it with the current status."""

        es_out = ElasticSearch(enrich_backend.elastic.url, out_index)
        es_out.add_alias(alias)

        logger.info(f"[pontoon] Latest translation status study starting. "
                    f"Input: {anonymize_url(enrich_backend.elastic.index_url)} "
                    f"Output: {anonymize_url(es_out.index_url)}")

        from_date = es_out.get_last_date(field="date")

        items = self._get_latest_translation_per_entity_uid(from_date)

        chunk = []
        total = 0
        for item in items:
            item['status'] = self._get_translation_status(item)
            chunk.append(item)
            total += 1

            if len(chunk) >= 100:
                es_out.bulk_upload(chunk, field_id='entity_uid')
                chunk = []

        if chunk:
            es_out.bulk_upload(chunk, field_id='entity_uid')

        logger.info(f"[pontoon] Latest translation status study processed {total} entities")

        logger.info("[pontoon] Latest translation status study ends.")

    def _get_latest_translation_per_entity_uid(self, from_date=None):
        """Get the latest translation action for each entity_uid.

        Iterates over the most recent action for each entity_uid. When multiple actions exist
        at the same time, the accepted action is preferred (sorted by type).

        If from_date is provided, only actions from that date onward are considered.
        """
        query = {
            "size": 0,
            "aggs": {
                "by_entity_uid": {
                    "composite": {
                        "size": 1000,
                        "sources": [
                            {"entity_uid": {"terms": {"field": "entity_uid"}}}
                        ]
                    },
                    "aggs": {
                        "latest_action": {
                            "top_hits": {
                                "size": 1,
                                "sort": [
                                    {"date": {"order": "desc"}},
                                    {"type": {"order": "asc"}}
                                ],
                            }
                        }
                    }
                }
            }
        }

        if from_date:
            query['query'] = {
                "range": {
                    "date": {
                        "gte": from_date.isoformat() if isinstance(from_date, datetime.datetime) else from_date
                    }
                }
            }

        while True:
            response = self.requests.post(self.elastic.index_url + "/_search", json=query,
                                          headers=HEADER_JSON, verify=False)
            if not response.ok:
                logger.error(f"[pontoon] Latest translation status study. "
                             f"Error fetching latest translations: {response.status_code} - {response.text}")
                break

            data = response.json()
            buckets = data['aggregations']['by_entity_uid']['buckets']
            for bucket in buckets:
                latest_action = bucket['latest_action']['hits']['hits'][0]['_source']
                yield latest_action

            if 'after_key' in data['aggregations']['by_entity_uid']:
                query['aggs']['by_entity_uid']['composite']['after'] = \
                    data['aggregations']['by_entity_uid']['after_key']
            else:
                break

    @staticmethod
    def _get_translation_status(item):
        """Determine the translation status of an entity based on the action item."""

        status = "Pending"
        if item['type'] == "translation:rejected":
            status = "Rejected"
        elif item['type'] == "translation:approved":
            status = "Approved"
        elif item['type'] == "translation:created":
            if item['translation_approved']:
                if item['system_user']:
                    status = "Imported"
                else:
                    status = "Approved"

        return status
