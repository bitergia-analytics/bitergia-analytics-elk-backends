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

import logging

from grimoire_elk.elastic_mapping import Mapping as BaseMapping
from grimoire_elk.enriched.enrich import Enrich, metadata
from grimoirelab_toolkit.datetime import str_to_datetime
from grimoirelab_toolkit.uris import urijoin


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
               "machinery_original_analyzed": {
                    "type": "text",
                    "index": true
               },
               "original_analyzed": {
                    "type": "text",
                    "index": true
               },
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

    translation_roles = ['user', 'approved_user', 'rejected_user']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.studies = []
        self.studies.append(self.enrich_demography)

    def get_field_author(self):
        return "user"

    def get_identities(self, item):
        """ Return the identities from an item """

        item = item['data']

        users_fields = self.translation_roles

        for translation in item['history_data']:
            for field in users_fields:
                if field in translation and translation[field]:
                    user = self.get_sh_identity(translation, identity_field=field)
                    yield user

    def get_sh_identity(self, item, identity_field=None):
        identity = {}

        user = item  # by default a specific user dict is expected
        if isinstance(item, dict) and 'data' in item:
            user = item['data']['history_data']

        if not user:
            return identity

        if not user[identity_field]:
            return identity

        identity['name'] = user[identity_field]
        if '@' in user[identity_field]:
            identity['email'] = user[identity_field]
        else:
            identity['email'] = None
        identity['username'] = None
        return identity

    def get_project_repository(self, eitem):
        return eitem['origin']

    def get_field_unique_id(self):
        return "id"

    def get_review_status(self, translation):
        if translation['user'] == 'Imported':
            return 'imported'
        if translation['approved']:
            if translation['approved_user'] == translation['user']:
                return 'self-approved'
            else:
                return 'peer-approved'
        elif translation['rejected']:
            return 'rejected'
        else:
            return 'unreviewed'

    @metadata
    def enrich_translation(self, translation, item):
        eitem = {}

        self.copy_raw_fields(self.RAW_FIELDS_COPY, item, eitem)

        entity = item['data']

        # Add id info to allow different translations for same entity
        eitem['id'] = f"entity_{entity['pk']}_translation_{translation['pk']}"

        eitem['entity_pk'] = entity['pk']
        eitem['locale'] = entity['locale']
        eitem['original'] = entity['original'][:self.KEYWORD_MAX_LENGTH]
        eitem['original_analyzed'] = entity['original']
        eitem['machinery_original'] = entity['machinery_original'][:self.KEYWORD_MAX_LENGTH]
        eitem['machinery_original_analyzed'] = entity['machinery_original']
        eitem['key'] = entity['key']
        eitem['context'] = entity['context']
        eitem['path'] = entity['path']
        eitem['project_pk'] = entity['project']['pk']
        eitem['project_name'] = entity['project']['name']
        eitem['project_slug'] = entity['project']['slug']
        eitem['format'] = entity['format']
        eitem['group_comment'] = entity['group_comment']
        eitem['resource_comment'] = entity['resource_comment']
        eitem['order'] = entity['order']
        eitem['obsolete'] = entity['obsolete']
        eitem['readonly'] = entity['readonly']
        eitem['entity_date'] = str_to_datetime(entity['date_created']).isoformat()
        url = urijoin(item['origin'], entity['project']['slug'], entity['path'])
        url += f"?string={entity['pk']}"
        eitem['url'] = url

        eitem['translation_pk'] = translation['pk']
        eitem['string'] = translation['string'][:self.KEYWORD_MAX_LENGTH]
        eitem['string_analyzed'] = translation['string']
        eitem['approved'] = translation['approved']
        eitem['rejected'] = translation['rejected']
        eitem['pretranslated'] = translation['pretranslated']
        eitem['fuzzy'] = translation['fuzzy']
        eitem['errors'] = len(translation['errors'])
        eitem['warnings'] = len(translation['warnings'])
        eitem['user'] = translation['user']
        eitem['uid'] = translation['uid']
        eitem['username'] = translation['username']
        eitem['translation_date'] = str_to_datetime(translation['date']).isoformat()
        eitem['approved_user'] = translation['approved_user']
        eitem['rejected_user'] = translation['rejected_user']
        eitem['comments'] = len(translation['comments'])
        eitem['machinery_sources'] = translation['machinery_sources']
        eitem['review_status'] = self.get_review_status(translation)

        if self.sortinghat:
            eitem.update(self.get_item_sh(translation, self.translation_roles, 'date'))

        if self.prjs_map:
            eitem.update(self.get_item_project(eitem))

        self.add_repository_labels(eitem)
        self.add_metadata_filter_raw(eitem)
        eitem.update(self.get_grimoire_fields(translation['date'], "message"))

        return eitem

    def enrich_translations(self, item):
        eitems = []
        translations = item['data'].get('history_data', [])
        for translation in translations:
            rich_item_translation = self.enrich_translation(translation, item)
            eitems.append(rich_item_translation)

        return eitems

    def enrich_items(self, ocean_backend, events=False):
        items_to_enrich = []
        num_items = 0
        ins_items = 0

        for item in ocean_backend.fetch():
            eitems = self.enrich_translations(item)
            items_to_enrich.extend(eitems)

            if len(items_to_enrich) < self.elastic.max_items_bulk:
                continue

            num_items += len(items_to_enrich)
            ins_items += self.elastic.bulk_upload(items_to_enrich, self.get_field_unique_id())
            items_to_enrich = []

        if len(items_to_enrich) > 0:
            num_items += len(items_to_enrich)
            ins_items += self.elastic.bulk_upload(items_to_enrich, self.get_field_unique_id())

        if num_items != ins_items:
            missing = num_items - ins_items
            logger.error(f"{missing}/{num_items} missing items for Pontoon")
        else:
            logger.info(f"{num_items} items inserted for Pontoon")

        return num_items
