#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: argo_sensor
short_description: Manage Argo Events Sensors
description:
  - Create, update, or delete Argo Events Sensor resources.
  - Sensors define a set of event dependencies and triggers to execute.
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
      - Name of the Sensor resource.
    type: str
    required: true
  namespace:
    description:
      - Namespace where the Sensor will be created.
    type: str
    required: true
  state:
    description:
      - Desired state of the Sensor.
    type: str
    choices:
      - present
      - absent
    default: present
  dependencies:
    description:
      - List of event dependencies for the Sensor.
      - Each dependency should contain name, event_source_name, and event_name.
    type: list
    elements: dict
  triggers:
    description:
      - List of triggers to execute when dependencies are met.
      - Each trigger contains a template with name, conditions, and trigger specifications.
    type: list
    elements: dict
'''

EXAMPLES = r'''
- name: Create Argo Events Sensor with workflow trigger
  redhat.argocd.argo_sensor:
    server_url: https://argocd.example.com
    auth_token: "{{ argocd_token }}"
    validate_certs: true
    name: webhook-sensor
    namespace: argo-events
    state: present
    dependencies:
      - name: webhook-dep
        event_source_name: webhook-example
        event_name: example
    triggers:
      - template:
          name: webhook-workflow-trigger
          conditions: webhook-dep
          argoWorkflow:
            operation: submit
            source:
              resource:
                apiVersion: argoproj.io/v1alpha1
                kind: Workflow
                metadata:
                  generateName: webhook-workflow-
                spec:
                  entrypoint: main
                  templates:
                    - name: main
                      container:
                        image: alpine:latest
                        command: [echo, "Event received"]

- name: Create Sensor with HTTP trigger
  redhat.argocd.argo_sensor:
    server_url: https://argocd.example.com
    auth_token: "{{ argocd_token }}"
    validate_certs: true
    name: http-sensor
    namespace: argo-events
    state: present
    dependencies:
      - name: kafka-dep
        event_source_name: kafka-example
        event_name: example
    triggers:
      - template:
          name: http-trigger
          conditions: kafka-dep
          http:
            url: https://webhook.example.com/notify
            method: POST
            payload:
              - src:
                  dependencyName: kafka-dep
                  dataKey: body
                dest: message

- name: Delete Sensor
  redhat.argocd.argo_sensor:
    server_url: https://argocd.example.com
    auth_token: "{{ argocd_token }}"
    validate_certs: true
    name: webhook-sensor
    namespace: argo-events
    state: absent
'''

RETURN = r'''
sensor:
  description: The Sensor resource details.
  returned: success
  type: dict
  sample:
    apiVersion: argoproj.io/v1alpha1
    kind: Sensor
    metadata:
      name: webhook-sensor
      namespace: argo-events
    spec:
      dependencies:
        - name: webhook-dep
          eventSourceName: webhook-example
          eventName: example
      triggers:
        - template:
            name: webhook-workflow-trigger
            conditions: webhook-dep
changed:
  description: Whether the Sensor was changed.
  returned: always
  type: bool
  sample: true
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.redhat.argocd.plugins.module_utils.argocd_common import (
    ArgocdClient,
    argocd_argument_spec
)


def get_sensor(client, namespace, name):
    """Retrieve a Sensor resource."""
    endpoint = f"/api/v1/namespaces/{namespace}/sensors/{name}"
    try:
        response = client.get(endpoint)
        if response.get('status_code') == 200:
            return response.get('data')
        return None
    except Exception:
        return None


def create_sensor(client, namespace, name, dependencies, triggers):
    """Create a Sensor resource."""
    endpoint = f"/api/v1/namespaces/{namespace}/sensors"

    formatted_dependencies = []
    for dep in dependencies:
        formatted_dependencies.append({
            "name": dep.get('name'),
            "eventSourceName": dep.get('event_source_name'),
            "eventName": dep.get('event_name')
        })

    payload = {
        "apiVersion": "argoproj.io/v1alpha1",
        "kind": "Sensor",
        "metadata": {
            "name": name,
            "namespace": namespace
        },
        "spec": {
            "dependencies": formatted_dependencies,
            "triggers": triggers
        }
    }
    response = client.post(endpoint, data=payload)
    return response.get('data')


def update_sensor(client, namespace, name, dependencies, triggers):
    """Update a Sensor resource."""
    endpoint = f"/api/v1/namespaces/{namespace}/sensors/{name}"

    formatted_dependencies = []
    for dep in dependencies:
        formatted_dependencies.append({
            "name": dep.get('name'),
            "eventSourceName": dep.get('event_source_name'),
            "eventName": dep.get('event_name')
        })

    payload = {
        "apiVersion": "argoproj.io/v1alpha1",
        "kind": "Sensor",
        "metadata": {
            "name": name,
            "namespace": namespace
        },
        "spec": {
            "dependencies": formatted_dependencies,
            "triggers": triggers
        }
    }
    response = client.put(endpoint, data=payload)
    return response.get('data')


def delete_sensor(client, namespace, name):
    """Delete a Sensor resource."""
    endpoint = f"/api/v1/namespaces/{namespace}/sensors/{name}"
    response = client.delete(endpoint)
    return response.get('status_code') in [200, 204]


def sensors_differ(existing, dependencies, triggers):
    """Compare existing Sensor with desired spec."""
    if not existing:
        return True

    existing_spec = existing.get('spec', {})

    formatted_dependencies = []
    for dep in dependencies:
        formatted_dependencies.append({
            "name": dep.get('name'),
            "eventSourceName": dep.get('event_source_name'),
            "eventName": dep.get('event_name')
        })

    new_spec = {
        "dependencies": formatted_dependencies,
        "triggers": triggers
    }

    return existing_spec != new_spec


def run_module():
    """Main module execution."""
    argument_spec = argocd_argument_spec()
    argument_spec.update(
        name=dict(type='str', required=True),
        namespace=dict(type='str', required=True),
        state=dict(type='str', default='present', choices=['present', 'absent']),
        dependencies=dict(type='list', elements='dict'),
        triggers=dict(type='list', elements='dict')
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_if=[
            ('state', 'present', ['dependencies', 'triggers'])
        ]
    )

    client = ArgocdClient(module)

    name = module.params['name']
    namespace = module.params['namespace']
    state = module.params['state']
    dependencies = module.params.get('dependencies', [])
    triggers = module.params.get('triggers', [])

    existing = get_sensor(client, namespace, name)
    result = {'changed': False, 'sensor': None}

    if state == 'present':
        if not existing:
            if module.check_mode:
                module.exit_json(changed=True, sensor=None)
            sensor = create_sensor(client, namespace, name, dependencies, triggers)
            result['sensor'] = sensor
            result['changed'] = True
        elif sensors_differ(existing, dependencies, triggers):
            if module.check_mode:
                module.exit_json(changed=True, sensor=existing)
            sensor = update_sensor(client, namespace, name, dependencies, triggers)
            result['sensor'] = sensor
            result['changed'] = True
        else:
            result['sensor'] = existing
            result['changed'] = False
    elif state == 'absent':
        if existing:
            if module.check_mode:
                module.exit_json(changed=True, sensor=None)
            delete_sensor(client, namespace, name)
            result['changed'] = True
        else:
            result['changed'] = False

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
