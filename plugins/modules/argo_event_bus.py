#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: argo_event_bus
short_description: Manage Argo Events EventBus
description:
  - Create, update, or delete Argo Events EventBus resources.
  - EventBus is the transport layer for events between EventSources and Sensors.
version_added: "0.1.0"
author:
  - Red Hat, Inc. (@redhat-ansible)
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
      - Name of the EventBus resource.
    type: str
    required: true
  namespace:
    description:
      - Namespace where the EventBus will be created.
    type: str
    required: true
  state:
    description:
      - Desired state of the EventBus.
    type: str
    choices:
      - present
      - absent
    default: present
  bus_type:
    description:
      - Type of event bus implementation.
    type: str
    choices:
      - nats
      - jetstream
      - kafka
    default: nats
  native:
    description:
      - Native NATS configuration.
      - Contains replicas and auth settings.
    type: dict
  exotic:
    description:
      - External event bus configuration.
      - For connecting to external NATS, Kafka, or other systems.
    type: dict
  jetstream:
    description:
      - JetStream-specific configuration.
      - Enhanced NATS with persistence and streaming.
    type: dict
'''

EXAMPLES = r'''
- name: Create native NATS EventBus
  redhat.argocd.argo_event_bus:
    server_url: https://argocd.example.com
    auth_token: "{{ argocd_token }}"
    validate_certs: true
    name: default
    namespace: argo-events
    state: present
    bus_type: nats
    native:
      replicas: 3
      auth: token

- name: Create JetStream EventBus
  redhat.argocd.argo_event_bus:
    server_url: https://argocd.example.com
    auth_token: "{{ argocd_token }}"
    validate_certs: true
    name: jetstream-bus
    namespace: argo-events
    state: present
    bus_type: jetstream
    jetstream:
      version: "2.9.0"
      replicas: 3
      persistence:
        storageClassName: standard
        accessMode: ReadWriteOnce
        volumeSize: 10Gi

- name: Create Kafka EventBus
  redhat.argocd.argo_event_bus:
    server_url: https://argocd.example.com
    auth_token: "{{ argocd_token }}"
    validate_certs: true
    name: kafka-bus
    namespace: argo-events
    state: present
    bus_type: kafka
    exotic:
      kafka:
        url: kafka-broker.example.com:9092
        topic: argo-events
        version: "3.0.0"

- name: Delete EventBus
  redhat.argocd.argo_event_bus:
    server_url: https://argocd.example.com
    auth_token: "{{ argocd_token }}"
    validate_certs: true
    name: default
    namespace: argo-events
    state: absent
    bus_type: nats
'''

RETURN = r'''
event_bus:
  description: The EventBus resource details.
  returned: success
  type: dict
  sample:
    apiVersion: argoproj.io/v1alpha1
    kind: EventBus
    metadata:
      name: default
      namespace: argo-events
    spec:
      nats:
        native:
          replicas: 3
          auth: token
changed:
  description: Whether the EventBus was changed.
  returned: always
  type: bool
  sample: true
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.redhat.argocd.plugins.module_utils.argocd_common import (
    ArgocdClient,
    argocd_argument_spec
)


def get_event_bus(client, namespace, name):
    """Retrieve an EventBus resource."""
    endpoint = f"/api/v1/namespaces/{namespace}/eventbus/{name}"
    try:
        response = client.get(endpoint)
        if response.get('status_code') == 200:
            return response.get('data')
        return None
    except Exception:
        return None


def create_event_bus(client, namespace, name, bus_type, native, exotic, jetstream):
    """Create an EventBus resource."""
    endpoint = f"/api/v1/namespaces/{namespace}/eventbus"

    spec = {}
    if bus_type == 'nats':
        spec['nats'] = {'native': native} if native else {'native': {'replicas': 3}}
    elif bus_type == 'jetstream':
        spec['jetstream'] = jetstream if jetstream else {}
    elif bus_type == 'kafka':
        spec['kafka'] = exotic.get('kafka', {}) if exotic else {}

    payload = {
        "apiVersion": "argoproj.io/v1alpha1",
        "kind": "EventBus",
        "metadata": {
            "name": name,
            "namespace": namespace
        },
        "spec": spec
    }
    response = client.post(endpoint, data=payload)
    return response.get('data')


def update_event_bus(client, namespace, name, bus_type, native, exotic, jetstream):
    """Update an EventBus resource."""
    endpoint = f"/api/v1/namespaces/{namespace}/eventbus/{name}"

    spec = {}
    if bus_type == 'nats':
        spec['nats'] = {'native': native} if native else {'native': {'replicas': 3}}
    elif bus_type == 'jetstream':
        spec['jetstream'] = jetstream if jetstream else {}
    elif bus_type == 'kafka':
        spec['kafka'] = exotic.get('kafka', {}) if exotic else {}

    payload = {
        "apiVersion": "argoproj.io/v1alpha1",
        "kind": "EventBus",
        "metadata": {
            "name": name,
            "namespace": namespace
        },
        "spec": spec
    }
    response = client.put(endpoint, data=payload)
    return response.get('data')


def delete_event_bus(client, namespace, name):
    """Delete an EventBus resource."""
    endpoint = f"/api/v1/namespaces/{namespace}/eventbus/{name}"
    response = client.delete(endpoint)
    return response.get('status_code') in [200, 204]


def event_buses_differ(existing, bus_type, native, exotic, jetstream):
    """Compare existing EventBus with desired spec."""
    if not existing:
        return True

    existing_spec = existing.get('spec', {})

    new_spec = {}
    if bus_type == 'nats':
        new_spec['nats'] = {'native': native} if native else {'native': {'replicas': 3}}
    elif bus_type == 'jetstream':
        new_spec['jetstream'] = jetstream if jetstream else {}
    elif bus_type == 'kafka':
        new_spec['kafka'] = exotic.get('kafka', {}) if exotic else {}

    return existing_spec != new_spec


def run_module():
    """Main module execution."""
    argument_spec = argocd_argument_spec()
    argument_spec.update(
        name=dict(type='str', required=True),
        namespace=dict(type='str', required=True),
        state=dict(type='str', default='present', choices=['present', 'absent']),
        bus_type=dict(type='str', default='nats', choices=['nats', 'jetstream', 'kafka']),
        native=dict(type='dict'),
        exotic=dict(type='dict'),
        jetstream=dict(type='dict')
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True
    )

    client = ArgocdClient(module)

    name = module.params['name']
    namespace = module.params['namespace']
    state = module.params['state']
    bus_type = module.params['bus_type']
    native = module.params.get('native')
    exotic = module.params.get('exotic')
    jetstream = module.params.get('jetstream')

    existing = get_event_bus(client, namespace, name)
    result = {'changed': False, 'event_bus': None}

    if state == 'present':
        if not existing:
            if module.check_mode:
                module.exit_json(changed=True, event_bus=None)
            event_bus = create_event_bus(client, namespace, name, bus_type, native, exotic, jetstream)
            result['event_bus'] = event_bus
            result['changed'] = True
        elif event_buses_differ(existing, bus_type, native, exotic, jetstream):
            if module.check_mode:
                module.exit_json(changed=True, event_bus=existing)
            event_bus = update_event_bus(client, namespace, name, bus_type, native, exotic, jetstream)
            result['event_bus'] = event_bus
            result['changed'] = True
        else:
            result['event_bus'] = existing
            result['changed'] = False
    elif state == 'absent':
        if existing:
            if module.check_mode:
                module.exit_json(changed=True, event_bus=None)
            delete_event_bus(client, namespace, name)
            result['changed'] = True
        else:
            result['changed'] = False

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
