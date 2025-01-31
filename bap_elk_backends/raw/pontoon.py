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

from grimoire_elk.raw.elastic import ElasticOcean
from grimoire_elk.elastic_mapping import Mapping as BaseMapping


logger = logging.getLogger(__name__)


class Mapping(BaseMapping):

    @staticmethod
    def get_elastic_mappings(es_major):
        """Get Elasticsearch mapping.

        :param es_major: major version of Elasticsearch, as string
        :returns: dictionary with a key, 'items', with the mapping
        """

        mapping = """
         {
            "dynamic":true,
            "properties": {
                "data": {
                    "properties": {
                        "translation": {
                            "dynamic":false,
                            "properties": {
                                "string": {
                                    "type": "text",
                                    "index": true
                                }
                            }
                        },
                        "source": {
                            "type": "object",
                            "enabled": false
                        }
                    }
                }
            }
        }
        """

        return {"items": mapping}


class PontoonOcean(ElasticOcean):
    """Pontoon Ocean feeder"""

    mapping = Mapping

    @classmethod
    def get_perceval_params_from_url(cls, url):
        # In the url the uri and the project are included
        origin, project = url.split()
        params = [origin, '--project', project]

        return params
