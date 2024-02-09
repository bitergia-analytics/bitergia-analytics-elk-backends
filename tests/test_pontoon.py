#!/usr/bin/env python3
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
#     Jose Javier Merchante <jjmerchante@bitergia.com>
#

import logging
import unittest

from base import TestBaseBackend

from bap_elk_backends.enriched.pontoon import PontoonEnrich
from grimoire_elk.enriched.utils import REPO_LABELS


class TestPontoon(TestBaseBackend):
    """Test Pontoon backend"""

    connector = "pontoon"
    ocean_index = "test_" + connector
    enrich_index = "test_" + connector + "_enrich"

    def test_has_identities(self):
        """Test value of has_identities method"""

        enrich_backend = self.connectors[self.connector][2]()
        self.assertTrue(enrich_backend.has_identities())

    def test_items_to_raw(self):
        """Test whether JSON items are properly inserted into ES"""

        result = self._test_items_to_raw()
        self.assertEqual(result['items'], 5)
        self.assertEqual(result['raw'], 5)

    def test_raw_to_enrich(self):
        """Test whether the raw index is properly enriched"""

        result = self._test_raw_to_enrich()
        self.assertEqual(result['raw'], 5)
        self.assertEqual(result['enrich'], 20)

        enrich_backend = self.connectors[self.connector][2]()

        item = self.items[0]
        eitems = enrich_backend.enrich_translations(item)
        self.assertEqual(len(eitems), 4)
        eitem = eitems[0]
        self.assertEqual(eitem['origin'], 'https://pontoon.example.com/es')
        self.assertEqual(eitem['locale'], 'es')
        self.assertEqual(eitem['project_slug'], 'amo')
        self.assertEqual(eitem['id'], 'entity_280952_translation_9925882')
        self.assertEqual(eitem['entity_pk'], 280952)
        self.assertEqual(eitem['translation_pk'], 9925882)
        self.assertEqual(eitem['path'], 'LC_MESSAGES/djangojs.po')
        self.assertRegex(eitem['original'], 'Your extension has to be compatible.*')
        self.assertRegex(eitem['string'], 'Tu extensión tiene que ser compatible.*')
        self.assertTrue(eitem['approved'])
        self.assertEqual(eitem['approved_user'], 'user_approve')
        self.assertEqual(eitem['user'], 'user1')

        eitem = eitems[1]
        self.assertEqual(eitem['origin'], 'https://pontoon.example.com/es')
        self.assertEqual(eitem['locale'], 'es')
        self.assertEqual(eitem['project_slug'], 'amo')
        self.assertEqual(eitem['id'], 'entity_280952_translation_9746098')
        self.assertEqual(eitem['entity_pk'], 280952)
        self.assertEqual(eitem['translation_pk'], 9746098)
        self.assertEqual(eitem['path'], 'LC_MESSAGES/djangojs.po')
        self.assertRegex(eitem['original'], 'Your extension has to be compatible.*')
        self.assertRegex(eitem['string'], 'Tu extensión tiene que ser compatible.*.')
        self.assertFalse(eitem['approved'])
        self.assertEqual(eitem['approved_user'], '')
        self.assertEqual(eitem['user'], 'user2')

        item = self.items[1]
        eitems = enrich_backend.enrich_translations(item)
        self.assertEqual(len(eitems), 4)
        eitem = eitems[0]
        self.assertEqual(eitem['origin'], 'https://pontoon.example.com/es')
        self.assertEqual(eitem['locale'], 'es')
        self.assertEqual(eitem['project_slug'], 'amo')
        self.assertEqual(eitem['id'], 'entity_292898_translation_9925882')
        self.assertEqual(eitem['entity_pk'], 292898)
        self.assertEqual(eitem['translation_pk'], 9925882)
        self.assertEqual(eitem['path'], 'LC_MESSAGES/django.po')
        self.assertRegex(eitem['original'], 'Warning: the following manifest.*')
        self.assertRegex(eitem['string'], 'Tu extensión tiene que ser compatible.*')
        self.assertFalse(eitem['approved'])
        self.assertEqual(eitem['approved_user'], '')
        self.assertEqual(eitem['user'], 'user1')

    def test_enrich_repo_labels(self):
        """Test whether the field REPO_LABELS is present in the enriched items"""

        self._test_raw_to_enrich()
        enrich_backend = self.connectors[self.connector][2]()

        for item in self.items:
            eitems = enrich_backend.enrich_translations(item)
            for eitem in eitems:
                self.assertIn(REPO_LABELS, eitem)

    def test_raw_to_enrich_sorting_hat(self):
        """Test enrich with SortingHat"""

        result = self._test_raw_to_enrich(sortinghat=True)
        self.assertEqual(result['raw'], 5)
        self.assertEqual(result['enrich'], 20)

        enrich_backend = self.connectors[self.connector][2]()

        url = self.es_con + "/" + self.enrich_index + "/_search"
        response = enrich_backend.requests.get(url, verify=False).json()
        for hit in response['hits']['hits']:
            source = hit['_source']
            if 'author_uuid' in source:
                self.assertIn('author_domain', source)
                self.assertIn('author_gender', source)
                self.assertIn('author_gender_acc', source)
                self.assertIn('author_org_name', source)
                self.assertIn('author_bot', source)
                self.assertIn('author_multi_org_names', source)

    def test_raw_to_enrich_projects(self):
        """Test enrich with Projects"""

        result = self._test_raw_to_enrich(projects=True)
        self.assertEqual(result['raw'], 5)
        self.assertEqual(result['enrich'], 20)

    def test_refresh_identities(self):
        """Test refresh identities"""

        self._test_refresh_identities()

    def test_empty_identity(self):
        """ Test support for from value with None"""

        enricher = PontoonEnrich()

        empty_identity = {}

        item = {'data': {"history_data": {"user": None}}}

        self.assertDictEqual(empty_identity, enricher.get_sh_identity(item, "user"))

    def test_copy_raw_fields(self):
        """Test copied raw fields"""

        self._test_raw_to_enrich()
        enrich_backend = self.connectors[self.connector][2]()

        for item in self.items:
            eitems = enrich_backend.enrich_translations(item)
            for eitem in eitems:
                for attribute in enrich_backend.RAW_FIELDS_COPY:
                    if attribute in item:
                        self.assertEqual(item[attribute], eitem[attribute])
                    else:
                        self.assertIsNone(eitem[attribute])


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    unittest.main(warnings='ignore')
