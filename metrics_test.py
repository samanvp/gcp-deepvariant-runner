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
from metrics import _CLEARCUT_ENDPOINT as CLEARCUT_ENDPOINT
from metrics import _MetricsCollector as MetricsCollector
import mock


# This is to test if all metrics collector instances share same session
# identifier. Mocks '_shared_session_identifier' on import.
@mock.patch('metrics._MetricsCollector._shared_session_identifier', 'abcd')
class MetricsCollectorTest(unittest.TestCase):
  """Tests for MetricsCollector class."""

  def _clear_metrics_collector(self):
    # 'metrics_collector' is a singleton. Remove any shared state before
    # starting next test.
    MetricsCollector()._events[:] = []

  @mock.patch('requests.post')
  @mock.patch('time.time', return_value=1234)
  def test_submit_metrics(self, unused_mock_time, mock_requests_post):
    self._clear_metrics_collector()
    metrics_collector = MetricsCollector()

    metrics_collector.add_metrics(
        123,
        'test-metrics-1',
        attribute_1=1,
        attribute_2='string-1',
        attribute_3=True)
    metrics_collector.add_metrics(
        123,
        'test-metrics-2',
        attribute_1=2,
        attribute_2='string-2',
        attribute_3=True)
    metrics_collector.submit_metrics()

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
                                    'console_type': 'CLOUD_HCLS',
                                    'event_metadata': [{
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
                                                       }],
                                    'event_name': 'test-metrics-1',
                                    'event_type': 'DeepVariantRun',
                                    'page_hostname': 'virtual.chc.deepvariant',
                                    'project_number': 123
                                },
                                sort_keys=True)
                    },
                    {
                        'source_extension_json':
                            json.dumps({
                                'console_type': 'CLOUD_HCLS',
                                'event_metadata': [{
                                    'key': 'attribute_1',
                                    'value': '2'
                                }, {
                                    'key': 'attribute_2',
                                    'value': 'string-2'
                                }, {
                                    'key': 'attribute_3',
                                    'value': 'True'
                                }],
                                'event_name': 'test-metrics-2',
                                'event_type': 'DeepVariantRun',
                                'page_hostname': 'virtual.chc.deepvariant',
                                'project_number': 123
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
        url=CLEARCUT_ENDPOINT)

  @mock.patch('requests.post')
  @mock.patch('time.time', side_effect=(1234, 1235))
  def test_two_metrics_collector(self, unused_mock_time, mock_requests_post):
    self._clear_metrics_collector()
    first_metric_collector = MetricsCollector()
    second_metric_collector = MetricsCollector()

    first_metric_collector.add_metrics(123, 'test-metrics-1', attribute_1=1)
    second_metric_collector.add_metrics(123, 'test-metrics-2', attribute_2=2)

    def expected_post_data(request_time_ms):
      template = {
          'zwieback_cookie': 'abcd',
          'log_source_name': 'CONCORD',
          'log_event': [{
              'source_extension_json':
                  json.dumps({
                      'console_type': 'CLOUD_HCLS',
                      'event_metadata': [{
                          'key': 'attribute_1',
                          'value': '1'
                      }],
                      'event_name': 'test-metrics-1',
                      'event_type': 'DeepVariantRun',
                      'page_hostname': 'virtual.chc.deepvariant',
                      'project_number': 123
                  },
                             sort_keys=True)
          },
                        {
                            'source_extension_json':
                                json.dumps({
                                    'console_type': 'CLOUD_HCLS',
                                    'event_metadata': [{
                                        'key': 'attribute_2',
                                        'value': '2'
                                    }],
                                    'event_name': 'test-metrics-2',
                                    'event_type': 'DeepVariantRun',
                                    'page_hostname': 'virtual.chc.deepvariant',
                                    'project_number': 123
                                },
                                           sort_keys=True)
                        }],
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
        url=CLEARCUT_ENDPOINT)

    second_metric_collector.submit_metrics()
    mock_requests_post.assert_called_with(
        data=expected_post_data(1235000),
        headers=None,
        timeout=10,
        url=CLEARCUT_ENDPOINT)


if __name__ == '__main__':
  unittest.main()
