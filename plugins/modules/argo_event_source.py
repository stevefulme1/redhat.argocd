#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: argo_event_source
short_description: Manage Argo Events EventSources
description:
  - Create, update, or delete Argo Events EventSource resources.
  - EventSources define the source of events that trigger workflows.
version_added: "0.1.0"
author:
  - Red Hat Ansible Automation Platform Team
options:
  server_url:
    description:
      - The URL of the Argo CD server.
    type: str
    required: true
  auth_token:
    description:
      - Authentication token for the Argo CD server.
    type: str
    required: true
  validate_certs:
    description:
      - Whether to validate SSL certificates.
    type: bool
    default: true
  name:
    description:
      - Name of the EventSource resource.
    type: str
    required: true
  namespace:
    description:
      - Namespace where the EventSource will be created.
    type: str
    required: true
  state:
    description:
      - Desired state of the EventSource.
    type: str
    choices:
      - present
      - absent
    default: present
  event_source_type:
    description:
      - Type of event source.
    type: str
    required: true
    choices:
      - webhook
      - calendar
      - resource
      - file
      - sns
      - sqs
      - kafka
      - amqp
      - nats
      - mqtt
      - redis
      - github
      - gitlab
      - slack
      - stripe
      - emitter
      - minio
      - nsq
      - pulsar
      - generic
  spec:
    description:
      - The EventSource specification.
      - Required when state is present.
    type: dict
'''

EXAMPLES = r'''
- name: Create webhook EventSource
  redhat.argocd.argo_event_source:
    server_url: https://argocd.example.com
    auth_token: "{{ argocd_token }}"
    validate_certs: true
    name: webhook-example
    namespace: argo-events
    state: present
    event_source_type: webhook
    spec:
      webhook:
        example:
          port: "12000"
          endpoint: /example
          method: POST

- name: Create Kafka EventSource
  redhat.argocd.argo_event_source:
    server_url: https://argocd.example.com
    auth_token: "{{ argocd_token }}"
    validate_certs: true
    name: kafka-example
    namespace: argo-events
    state: present
    event_source_type: kafka
    spec:
      kafka:
        example:
          url: kafka-broker.example.com:9092
          topic: events
          partition: "0"
          consumerGroup:
            groupName: argo-events-group

- name: Delete EventSource
  redhat.argocd.argo_event_source:
    server_url: https://argocd.example.com
    auth_token: "{{ argocd_token }}"
    validate_certs: true
    name: webhook-example
    namespace: argo-events
    state: absent
    event_source_type: webhook
'''

RETURN = r'''
event_source:
  description: The EventSource resource details.
  returned: success
  type: dict
  sample:
    apiVersion: argoproj.io/v1alpha1
    kind: EventSource
    metadata:
      name: webhook-example
      namespace: argo-events
    spec:
      webhook:
        example:
          port: "12000"
          endpoint: /example
          method: POST
changed:
  description: Whether the EventSource was changed.
  returned: always
  type: bool
  sample: true
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.redhat.argocd.plugins.module_utils.argocd_common import (
    ArgocdClient,
    argocd_argument_spec
)


def get_event_source(client, namespace, name):
    """Retrieve an EventSource resource."""
    endpoint = f"/api/v1/namespaces/{namespace}/eventsources/{name}"
    try:
        response = client.get(endpoint)
        if response.get('status_code') == 200:
            return response.get('data')
        return None
    except Exception:
        return None


def create_event_source(client, namespace, name, event_source_type, spec):
    """Create an EventSource resource."""
    endpoint = f"/api/v1/namespaces/{namespace}/eventsources"
    payload = {
        "apiVersion": "argoproj.io/v1alpha1",
        "kind": "EventSource",
        "metadata": {
            "name": name,
            "namespace": namespace
        },
        "spec": {
            event_source_type: spec.get(event_source_type, spec)
        }
    }
    response = client.post(endpoint, data=payload)
    return response.get('data')


def update_event_source(client, namespace, name, event_source_type, spec):
    """Update an EventSource resource."""
    endpoint = f"/api/v1/namespaces/{namespace}/eventsources/{name}"
    payload = {
        "apiVersion": "argoproj.io/v1alpha1",
        "kind": "EventSource",
        "metadata": {
            "name": name,
            "namespace": namespace
        },
        "spec": {
            event_source_type: spec.get(event_source_type, spec)
        }
    }
    response = client.put(endpoint, data=payload)
    return response.get('data')


def delete_event_source(client, namespace, name):
    """Delete an EventSource resource."""
    endpoint = f"/api/v1/namespaces/{namespace}/eventsources/{name}"
    response = client.delete(endpoint)
    return response.get('status_code') in [200, 204]


def event_sources_differ(existing, event_source_type, spec):
    """Compare existing EventSource with desired spec."""
    if not existing:
        return True
    existing_spec = existing.get('spec', {})
    new_spec = {event_source_type: spec.get(event_source_type, spec)}
    return existing_spec != new_spec


def run_module():
    """Main module execution."""
    argument_spec = argocd_argument_spec()
    argument_spec.update(
        name=dict(type='str', required=True),
        namespace=dict(type='str', required=True),
        state=dict(type='str', default='present', choices=['present', 'absent']),
        event_source_type=dict(
            type='str',
            required=True,
            choices=[
                'webhook', 'calendar', 'resource', 'file', 'sns', 'sqs',
                'kafka', 'amqp', 'nats', 'mqtt', 'redis', 'github',
                'gitlab', 'slack', 'stripe', 'emitter', 'minio', 'nsq',
                'pulsar', 'generic'
            ]
        ),
        spec=dict(type='dict')
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_if=[
            ('state', 'present', ['spec'])
        ]
    )

    client = ArgocdClient(module)

    name = module.params['name']
    namespace = module.params['namespace']
    state = module.params['state']
    event_source_type = module.params['event_source_type']
    spec = module.params.get('spec', {})

    existing = get_event_source(client, namespace, name)
    changed = False
    result = {'changed': False, 'event_source': None}

    if state == 'present':
        if not existing:
            if module.check_mode:
                module.exit_json(changed=True, event_source=None)
            event_source = create_event_source(client, namespace, name, event_source_type, spec)
            result['event_source'] = event_source
            result['changed'] = True
        elif event_sources_differ(existing, event_source_type, spec):
            if module.check_mode:
                module.exit_json(changed=True, event_source=existing)
            event_source = update_event_source(client, namespace, name, event_source_type, spec)
            result['event_source'] = event_source
            result['changed'] = True
        else:
            result['event_source'] = existing
            result['changed'] = False
    elif state == 'absent':
        if existing:
            if module.check_mode:
                module.exit_json(changed=True, event_source=None)
            delete_event_source(client, namespace, name)
            result['changed'] = True
        else:
            result['changed'] = False

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
