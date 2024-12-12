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
import time
import unittest

from base import TestBaseBackend

from bap_elk_backends.enriched.pontoon import PontoonEnrich
from grimoire_elk.enriched.utils import REPO_LABELS
from grimoire_elk.enriched.enrich import (logger,
                                          anonymize_url)


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
        self.assertEqual(result['items'], 4)
        self.assertEqual(result['raw'], 4)

    def test_raw_to_enrich(self):
        """Test whether the raw index is properly enriched"""

        result = self._test_raw_to_enrich()
        self.assertEqual(result['raw'], 4)
        self.assertEqual(result['enrich'], 4)

        enrich_backend = self.connectors[self.connector][2]()

        item = self.items[0]
        eitem = enrich_backend.get_rich_item(item)
        self.assertEqual(eitem['origin'], 'https://pontoon.mozilla.org/p1')
        self.assertEqual(eitem['id'], 'action:p1:el:86261:2018965:translation:approved')
        self.assertEqual(eitem['type'], 'translation:approved')
        self.assertEqual(eitem['date'], '2016-11-17T09:31:04.768000+00:00')
        self.assertEqual(eitem['user_name'], 'User 1')
        self.assertEqual(eitem['user_pk'], 1)
        self.assertEqual(eitem['entity_pk'], 86261)
        self.assertEqual(eitem['locale'], 'el')
        self.assertEqual(eitem['resource_path'], 'mail/chrome/messenger/messengercompose/composeMsgs.properties')
        self.assertEqual(eitem['translation_string'], 'Sample string')
        self.assertEqual(eitem['translation_pk'], 2018965)
        self.assertEqual(eitem['project_slug'], 'p1')
        self.assertEqual(eitem['url'], 'https://pontoon.mozilla.org/el/p1/'
                                       'mail/chrome/messenger/messengercompose/composeMsgs.properties?string=86261')

        item = self.items[1]
        eitem = enrich_backend.get_rich_item(item)
        self.assertEqual(eitem['origin'], 'https://pontoon.mozilla.org/p1')
        self.assertEqual(eitem['id'], 'action:p1:el:83090:2470935:translation:created')
        self.assertEqual(eitem['type'], 'translation:created')
        self.assertEqual(eitem['date'], '2016-11-17T09:38:22.129000+00:00')
        self.assertEqual(eitem['user_name'], 'User 1')
        self.assertEqual(eitem['user_pk'], 1)
        self.assertEqual(eitem['entity_pk'], 83090)
        self.assertEqual(eitem['locale'], 'el')
        self.assertEqual(eitem['resource_path'], 'mail/chrome/messenger/messenger.properties')
        self.assertEqual(eitem['translation_string'], 'Sample string 2')
        self.assertEqual(eitem['translation_pk'], 2470935)
        self.assertEqual(eitem['project_slug'], 'p1')
        self.assertEqual(eitem['url'], 'https://pontoon.mozilla.org/el/p1/'
                                       'mail/chrome/messenger/messenger.properties?string=83090')

        item = self.items[2]
        eitem = enrich_backend.get_rich_item(item)
        self.assertEqual(eitem['origin'], 'https://pontoon.mozilla.org/p1')
        self.assertEqual(eitem['id'], 'action:p1:el:83140:2016834:translation:approved')
        self.assertEqual(eitem['type'], 'translation:approved')
        self.assertEqual(eitem['date'], '2016-11-17T09:39:34.077000+00:00')
        self.assertEqual(eitem['user_name'], 'User 1')
        self.assertEqual(eitem['user_pk'], 1)
        self.assertEqual(eitem['entity_pk'], 83140)
        self.assertEqual(eitem['locale'], 'el')
        self.assertEqual(eitem['resource_path'], 'mail/chrome/messenger/messenger.properties')
        self.assertEqual(eitem['translation_string'], 'NTLM')
        self.assertEqual(eitem['translation_pk'], 2016834)
        self.assertEqual(eitem['project_slug'], 'p1')
        self.assertEqual(eitem['url'], 'https://pontoon.mozilla.org/el/p1/'
                                       'mail/chrome/messenger/messenger.properties?string=83140')

        item = self.items[3]
        eitem = enrich_backend.get_rich_item(item)
        self.assertEqual(eitem['origin'], 'https://pontoon.mozilla.org/p1')
        self.assertEqual(eitem['id'], 'action:p1:el:85470:2016743:translation:approved')
        self.assertEqual(eitem['type'], 'translation:approved')
        self.assertEqual(eitem['date'], '2016-11-17T08:46:23.174000+00:00')
        self.assertEqual(eitem['user_name'], 'User 1')
        self.assertEqual(eitem['user_pk'], 1)
        self.assertEqual(eitem['entity_pk'], 85470)
        self.assertEqual(eitem['locale'], 'el')
        self.assertEqual(eitem['resource_path'], 'mail/chrome/messenger/messenger.dtd')
        self.assertEqual(eitem['translation_string'], 'Sample string 3')
        self.assertEqual(eitem['translation_pk'], 2016743)
        self.assertEqual(eitem['project_slug'], 'p1')
        self.assertEqual(eitem['url'],
                         'https://pontoon.mozilla.org/el/p1/mail/chrome/messenger/messenger.dtd?string=85470')

    def test_enrich_repo_labels(self):
        """Test whether the field REPO_LABELS is present in the enriched items"""

        self._test_raw_to_enrich()
        enrich_backend = self.connectors[self.connector][2]()

        for item in self.items:
            eitem = enrich_backend.get_rich_item(item)
            self.assertIn(REPO_LABELS, eitem)

    def test_raw_to_enrich_sorting_hat(self):
        """Test enrich with SortingHat"""

        result = self._test_raw_to_enrich(sortinghat=True)
        self.assertEqual(result['raw'], 4)
        self.assertEqual(result['enrich'], 4)

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
        self.assertEqual(result['raw'], 4)
        self.assertEqual(result['enrich'], 4)

    def test_refresh_identities(self):
        """Test refresh identities"""

        self._test_refresh_identities()

    def test_empty_identity(self):
        """ Test support for from value with None"""

        enricher = PontoonEnrich()

        empty_identity = {}

        item = {'data': {"user": None}}

        self.assertDictEqual(empty_identity, enricher.get_sh_identity(item, "user"))

    def test_copy_raw_fields(self):
        """Test copied raw fields"""

        self._test_raw_to_enrich()
        enrich_backend = self.connectors[self.connector][2]()

        for item in self.items:
            eitem = enrich_backend.get_rich_item(item)
            for attribute in enrich_backend.RAW_FIELDS_COPY:
                if attribute in item:
                    self.assertEqual(item[attribute], eitem[attribute])
                else:
                    self.assertIsNone(eitem[attribute])

    def test_demography_study(self):
        """ Test that the demography study works correctly """

        alias = 'demographics'
        study, ocean_backend, enrich_backend = self._test_study('enrich_demography')

        with self.assertLogs(logger, level='INFO') as cm:
            if study.__name__ == "enrich_demography":
                study(ocean_backend, enrich_backend, alias)

            self.assertEqual(cm.output[0], 'INFO:grimoire_elk.enriched.enrich:[pontoon] Demography '
                                           'starting study %s/test_pontoon_enrich'
                             % anonymize_url(self.es_con))
            self.assertEqual(cm.output[-1], 'INFO:grimoire_elk.enriched.enrich:[pontoon] Demography '
                                            'end %s/test_pontoon_enrich'
                             % anonymize_url(self.es_con))

        time.sleep(5)  # HACK: Wait until pontoon enrich index has been written
        items = [item for item in enrich_backend.fetch()]
        self.assertEqual(len(items), 4)
        for item in items:
            self.assertTrue('demography_min_date' in item.keys())
            self.assertTrue('demography_max_date' in item.keys())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    unittest.main(warnings='ignore')
