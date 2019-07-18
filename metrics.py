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
"""Used to collect anonymous DeepVariant metrics."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import atexit
import functools
import json
import logging
import time
import uuid

import requests
from typing import Dict, Optional, Text

_CLEARCUT_ENDPOINT = 'https://play.googleapis.com/log'
_CLOUD_HCLS_OSS = 'CLOUD_HCLS_OSS'
_CONCORD = 'CONCORD'
_DEEP_VARIANT_RUN = 'DeepVariantRun'
_HTTP_REQUEST_TIMEOUT_SEC = 10
_PYTHON = 'PYTHON'
_VIRTUAL_HCLS_DEEPVARIANT = 'virtual.hcls.deepvariant'


def capture_exceptions(func):
  """Function decorator to capture and log any exceptions."""

  @functools.wraps(func)
  def wrapper(*args, **kwds):
    try:
      return func(*args, **kwds)
    # pylint:disable=broad-except
    except Exception as e:
      logging.error('Exception captured in %s : %s', func.__name__, e)

  return wrapper


class _ConcordEvent(object):
  """Encapsulates information representing a Concord event."""

  def __init__(self,
               event_name: Text,
               event_type: Text,
               project_number: int,
               console_type: Text,
               page_hostname: Text,
               event_metadata: Optional[Dict[Text, Text]] = None) -> None:
    self._event_name = event_name
    self._event_type = event_type
    self._project_number = project_number
    self._console_type = console_type
    self._page_hostname = page_hostname
    self._event_metadata = event_metadata or {}

  def to_json(self, **kwargs):
    """Encodes data in json."""
    event_dict = {
        'project_number': str(self._project_number),
        'event_name': self._event_name,
        'event_type': self._event_type,
        'console_type': self._console_type,
        'page_hostname': self._page_hostname,
        'event_metadata': self._event_metadata_as_kv(),
    }
    return json.dumps(event_dict, **kwargs)

  def _event_metadata_as_kv(self):
    kv_list = []
    for k, v in sorted(self._event_metadata.items()):
      kv_list.append({'key': k, 'value': str(v)})

    return kv_list


class _MetricsCollector(object):
  """A class that collects and submits metrics.

  Instances of this class share the same internal state, and thus behave the
  same all the time.
  """
  _events = []
  _session_identifier = uuid.uuid4().hex

  def add_metrics(self, project_number: int,
                  metrics_name: Text, **metrics_kw: Text) -> None:
    concord_event = _ConcordEvent(
        event_name=metrics_name,
        event_type=_DEEP_VARIANT_RUN,
        project_number=project_number,
        console_type=_CLOUD_HCLS_OSS,
        page_hostname=_VIRTUAL_HCLS_DEEPVARIANT,
        event_metadata={k: v for k, v in metrics_kw.items()})
    self._events.append(concord_event)

  def submit_metrics(self):
    """Submits all the collected metrics to Concord endpoint.

    Raises:
      HTTPError if http request doesn't succeed (status code != 200).
    """
    request_data = json.dumps(self._clearcut_request(), sort_keys=True)
    requests.post(
        url=_CLEARCUT_ENDPOINT,
        data=request_data,
        headers=None,
        timeout=_HTTP_REQUEST_TIMEOUT_SEC).raise_for_status()

  def _clearcut_request(self):
    # We dont have (or want to have) any cookies.  So, using a random ID for
    # zwieback_cookie is ok for tracking purposes.
    return {
        'client_info': {
            'client_type': _PYTHON,
        },
        'log_source_name':
            _CONCORD,
        'zwieback_cookie':
            self._session_identifier,
        'request_time_ms':
            _now_ms(),
        'log_event': [{
            'source_extension_json': e.to_json(sort_keys=True)
        } for e in self._events]
    }


def _now_ms():
  """Returns current time in milliseconds."""
  return int(round(time.time() * 1000))


def add(project_number: int, metrics_name: Text, **metrics_kw: Text) -> None:
  """Adds the given metric to the metrics to be submitted to Concord.

  Note: All metrics are submitted at exit.
  Note: Do not rely on thread safety of this method.

  Args:
    project_number(int): GCP project number.
    metrics_name(str): metrics name.
    **metrics_kw: key-values of metrics. For example, for
      metrics_name="MakeExamplesSuccess", metrics_kw can be
      duration_seconds=1000, wait_duration_seconds=100.
  """
  metrics_collector = _MetricsCollector()
  metrics_collector.add_metrics(project_number, metrics_name, **metrics_kw)


# Exceptions are captured and logged to avoid crashing callers.
@capture_exceptions
@atexit.register
def shutdown():
  """Reports all metrics that were collected."""
  metrics_collector = _MetricsCollector()
  metrics_collector.submit_metrics()
