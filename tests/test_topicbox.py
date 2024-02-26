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

from bap_elk_backends.enriched.topicbox import TopicboxEnrich
from grimoire_elk.enriched.utils import REPO_LABELS


class TestTopicbox(TestBaseBackend):
    """Test Topicbox backend"""

    connector = "topicbox"
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
        self.assertEqual(result['enrich'], 5)

        enrich_backend = self.connectors[self.connector][2]()

        item = self.items[0]
        eitem = enrich_backend.get_rich_item(item)
        self.assertEqual(eitem['origin'], 'https://example.com/groups/test_group')
        self.assertEqual(eitem['Subject'], 'Subject 1')
        self.assertEqual(eitem['Message-ID'], 'item1@topicbox.com')
        self.assertEqual(eitem['topicbox_message_id'], 'Mtest1')
        self.assertEqual(eitem['root'], False)
        self.assertEqual(eitem['thread'], 'thread1')
        self.assertEqual(eitem['thread_url'], 'https://example.com/groups/test_group/thread1')
        self.assertEqual(eitem['url'], 'https://example.com/groups/test_group/thread1-Mtest1')

        item = self.items[1]
        eitem = enrich_backend.get_rich_item(item)
        self.assertEqual(eitem['origin'], 'https://example.com/groups/test_group')
        self.assertEqual(eitem['Subject'], 'Subject 2')
        self.assertEqual(eitem['Message-ID'], 'item2@topicbox.com')
        self.assertEqual(eitem['topicbox_message_id'], 'Mtest2')
        self.assertEqual(eitem['root'], False)
        self.assertEqual(eitem['thread'], 'Thread2')
        self.assertEqual(eitem['thread_url'], 'https://example.com/groups/test_group/Thread2')
        self.assertEqual(eitem['url'], 'https://example.com/groups/test_group/Thread2-Mtest2')

        item = self.items[2]
        eitem = enrich_backend.get_rich_item(item)
        self.assertEqual(eitem['origin'], 'https://example.com/groups/test_group')
        self.assertEqual(eitem['Subject'], 'Subject 3')
        self.assertEqual(eitem['Message-ID'], 'item3@topicbox.com')
        self.assertEqual(eitem['topicbox_message_id'], 'Mtest3')
        self.assertEqual(eitem['root'], False)
        self.assertEqual(eitem['thread'], 'Thread3')
        self.assertEqual(eitem['thread_url'], 'https://example.com/groups/test_group/Thread3')
        self.assertEqual(eitem['url'], 'https://example.com/groups/test_group/Thread3-Mtest3')

        item = self.items[3]
        eitem = enrich_backend.get_rich_item(item)
        self.assertEqual(eitem['origin'], 'https://example.com/groups/test_group')
        self.assertEqual(eitem['Subject'], 'Subject 4')
        self.assertEqual(eitem['Message-ID'], 'item4@topicbox.com')
        self.assertEqual(eitem['topicbox_message_id'], 'Mtest4')
        self.assertEqual(eitem['root'], True)
        self.assertEqual(eitem['thread'], 'Thread3')
        self.assertEqual(eitem['thread_url'], 'https://example.com/groups/test_group/Thread3')
        self.assertEqual(eitem['url'], 'https://example.com/groups/test_group/Thread3-Mtest4')

        item = self.items[4]
        eitem = enrich_backend.get_rich_item(item)
        self.assertEqual(eitem['origin'], 'https://example.com/groups/test_group')
        self.assertEqual(eitem['Subject'], 'Subject 5')
        self.assertEqual(eitem['Message-ID'], 'item5@topicbox.com')
        self.assertEqual(eitem['topicbox_message_id'], 'Mtest5')
        self.assertEqual(eitem['root'], True)
        self.assertEqual(eitem['thread'], 'Thread3')
        self.assertEqual(eitem['thread_url'], 'https://example.com/groups/test_group/Thread3')
        self.assertEqual(eitem['url'], 'https://example.com/groups/test_group/Thread3-Mtest5')

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
        self.assertEqual(result['raw'], 5)
        self.assertEqual(result['enrich'], 5)

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
        self.assertEqual(result['enrich'], 5)

    def test_refresh_identities(self):
        """Test refresh identities"""

        self._test_refresh_identities()

    def test_empty_identity(self):
        """ Test support for from value with None"""

        enricher = TopicboxEnrich()

        empty_identity = {f: None for f in ['email', 'name', 'username']}

        item = {'data': {"author": None}}

        self.assertDictEqual(empty_identity, enricher.get_sh_identity(item, "author"))

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


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    unittest.main(warnings='ignore')
