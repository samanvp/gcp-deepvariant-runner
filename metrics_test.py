# Copyright 2019 Google LLC.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from this
#    software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
"""Tests for metrics.py.

To run the tests, first activate virtualenv and install required packages:
$ virtualenv venv
$ . venv/bin/activate
$ pip install mock requests

Then run:
$ python metrics_test.py
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import json
import unittest

import metrics
import mock


# This is to test if all metrics collector instances share same session
# identifier. Mocks '_session_identifier' on import.
@mock.patch('metrics._MetricsCollector._session_identifier', 'abcd')
class MetricsCollectorTest(unittest.TestCase):
  """Tests for MetricsCollector class."""

  def setUp(self):
    super(MetricsCollectorTest, self).setUp()
    # 'metrics_collector' has class attributes, clear them before each test.
    metrics._MetricsCollector()._events[:] = []

  @mock.patch('requests.post')
  @mock.patch('time.time', return_value=1234)
  def test_submit_metrics(self, unused_mock_time, mock_requests_post):
    metrics.add(
        123,
        'test-metrics-1',
        attribute_1=1,
        attribute_2='string-1',
        attribute_3=True)
    metrics.add(
        123,
        'test-metrics-2',
        attribute_1=2,
        attribute_2='string-2',
        attribute_3=True)
    metrics._MetricsCollector().submit_metrics()

    mock_requests_post.assert_called_with(
        data=json.dumps(
            {
                'zwieback_cookie': 'abcd',
                'request_time_ms': 1234000,
                'log_source_name': 'CONCORD',
                'log_event': [
                    {
                        'source_extension_json':
                            json.dumps(
                                {
                                    'console_type': 'CLOUD_HCLS_OSS',
                                    'event_metadata': [
                                        {
                                            'key': 'attribute_1',
                                            'value': '1'
                                        },
                                        {
                                            'key': 'attribute_2',
                                            'value': 'string-1'
                                        },
                                        {
                                            'key': 'attribute_3',
                                            'value': 'True'
                                        }
                                    ],
                                    'event_name': 'test-metrics-1',
                                    'event_type': 'DeepVariantRun',
                                    'page_hostname': 'virtual.hcls.deepvariant',
                                    'project_number': '123'
                                },
                                sort_keys=True)
                    },
                    {
                        'source_extension_json':
                            json.dumps({
                                'console_type': 'CLOUD_HCLS_OSS',
                                'event_metadata': [
                                    {
                                        'key': 'attribute_1',
                                        'value': '2'
                                    },
                                    {
                                        'key': 'attribute_2',
                                        'value': 'string-2'
                                    },
                                    {
                                        'key': 'attribute_3',
                                        'value': 'True'
                                    }
                                ],
                                'event_name': 'test-metrics-2',
                                'event_type': 'DeepVariantRun',
                                'page_hostname': 'virtual.hcls.deepvariant',
                                'project_number': '123'
                            },
                                       sort_keys=True)
                    }
                ],
                'client_info': {
                    'client_type': 'PYTHON'
                }
            },
            sort_keys=True),
        headers=None,
        timeout=10,
        url=metrics._CLEARCUT_ENDPOINT)

  @mock.patch('requests.post')
  @mock.patch('time.time', side_effect=(1234, 1235))
  def test_two_metrics_collector(self, unused_mock_time, mock_requests_post):
    first_metric_collector = metrics._MetricsCollector()
    second_metric_collector = metrics._MetricsCollector()

    first_metric_collector.add_metrics(123, 'test-metrics-1', attribute_1=1)
    second_metric_collector.add_metrics(123, 'test-metrics-2', attribute_2=2)
    metrics.add(123, 'test-metrics-3', attribute_3=3)

    def expected_post_data(request_time_ms):
      template = {
          'zwieback_cookie': 'abcd',
          'log_source_name': 'CONCORD',
          'log_event': [
              {
                  'source_extension_json':
                      json.dumps({
                          'console_type': 'CLOUD_HCLS_OSS',
                          'event_metadata': [{
                              'key': 'attribute_1',
                              'value': '1'
                          }],
                          'event_name': 'test-metrics-1',
                          'event_type': 'DeepVariantRun',
                          'page_hostname': 'virtual.hcls.deepvariant',
                          'project_number': '123'
                      },
                                 sort_keys=True)
              },
              {
                  'source_extension_json':
                      json.dumps({
                          'console_type': 'CLOUD_HCLS_OSS',
                          'event_metadata': [{
                              'key': 'attribute_2',
                              'value': '2'
                          }],
                          'event_name': 'test-metrics-2',
                          'event_type': 'DeepVariantRun',
                          'page_hostname': 'virtual.hcls.deepvariant',
                          'project_number': '123'
                      },
                                 sort_keys=True)
              },
              {
                  'source_extension_json':
                      json.dumps({
                          'console_type': 'CLOUD_HCLS_OSS',
                          'event_metadata': [{
                              'key': 'attribute_3',
                              'value': '3'
                          }],
                          'event_name': 'test-metrics-3',
                          'event_type': 'DeepVariantRun',
                          'page_hostname': 'virtual.hcls.deepvariant',
                          'project_number': '123'
                      },
                                 sort_keys=True)
              }
          ],
          'client_info': {
              'client_type': 'PYTHON'
          }
      }
      template.update({'request_time_ms': request_time_ms})
      return json.dumps(template, sort_keys=True)

    first_metric_collector.submit_metrics()
    mock_requests_post.assert_called_with(
        data=expected_post_data(1234000),
        headers=None,
        timeout=10,
        url=metrics._CLEARCUT_ENDPOINT)

    second_metric_collector.submit_metrics()
    mock_requests_post.assert_called_with(
        data=expected_post_data(1235000),
        headers=None,
        timeout=10,
        url=metrics._CLEARCUT_ENDPOINT)


if __name__ == '__main__':
  unittest.main()
