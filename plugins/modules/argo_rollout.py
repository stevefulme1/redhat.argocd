#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: argo_rollout
short_description: Manage Argo Rollouts
description:
  - Create, update, delete, pause, resume, promote, or abort Argo Rollouts.
  - Provides progressive delivery capabilities for Kubernetes workloads.
version_added: "0.1.0"
options:
  server_url:
    description: Argo CD server URL.
    type: str
    required: true
  auth_token:
    description: Argo CD authentication token.
    type: str
    required: true
    no_log: true
  validate_certs:
    description: Whether to validate SSL certificates.
    type: bool
    default: true
  name:
    description: Name of the Rollout resource.
    type: str
    required: true
  namespace:
    description: Kubernetes namespace for the Rollout.
    type: str
    required: true
  state:
    description: Desired state of the Rollout.
    type: str
    choices: [present, absent, paused, resumed, promoted, aborted]
    default: present
  replicas:
    description: Number of desired pod replicas.
    type: int
  image:
    description: Container image to deploy.
    type: str
  strategy:
    description: Deployment strategy configuration.
    type: dict
    suboptions:
      canary:
        description: Canary deployment strategy.
        type: dict
      blueGreen:
        description: Blue-green deployment strategy.
        type: dict
  selector:
    description: Label selector for pods.
    type: dict
  template:
    description: Pod template specification.
    type: dict
author:
  - Red Hat (@redhat)
'''

EXAMPLES = r'''
- name: Create canary rollout
  redhat.argocd.argo_rollout:
    server_url: https://argocd.example.com
    auth_token: "{{ argocd_token }}"
    name: my-app
    namespace: production
    state: present
    replicas: 3
    image: my-app:v2.0
    selector:
      app: my-app
    template:
      metadata:
        labels:
          app: my-app
      spec:
        containers:
          - name: my-app
            image: my-app:v2.0
            ports:
              - containerPort: 8080
    strategy:
      canary:
        steps:
          - setWeight: 20
          - pause: {duration: 5m}
          - setWeight: 40
          - pause: {duration: 5m}
          - setWeight: 60
          - pause: {duration: 5m}
          - setWeight: 80
          - pause: {duration: 5m}

- name: Create blue-green rollout
  redhat.argocd.argo_rollout:
    server_url: https://argocd.example.com
    auth_token: "{{ argocd_token }}"
    name: web-app
    namespace: production
    state: present
    replicas: 5
    image: web-app:v3.0
    selector:
      app: web-app
    template:
      metadata:
        labels:
          app: web-app
      spec:
        containers:
          - name: web-app
            image: web-app:v3.0
    strategy:
      blueGreen:
        activeService: web-app-active
        previewService: web-app-preview
        autoPromotionEnabled: false

- name: Promote rollout to stable
  redhat.argocd.argo_rollout:
    server_url: https://argocd.example.com
    auth_token: "{{ argocd_token }}"
    name: my-app
    namespace: production
    state: promoted
'''

RETURN = r'''
rollout:
  description: The Rollout resource details.
  returned: success
  type: dict
  sample:
    apiVersion: argoproj.io/v1alpha1
    kind: Rollout
    metadata:
      name: my-app
      namespace: production
    spec:
      replicas: 3
      selector:
        matchLabels:
          app: my-app
changed:
  description: Whether the Rollout was modified.
  returned: always
  type: bool
  sample: true
status:
  description: Current status of the Rollout operation.
  returned: success
  type: str
  sample: "promoted"
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.redhat.argocd.plugins.module_utils.argocd_common import (
    ArgocdClient,
    argocd_argument_spec
)


def get_rollout(client, name, namespace):
    """Retrieve a Rollout resource."""
    endpoint = f"/api/v1alpha1/rollouts/{namespace}/{name}"
    try:
        response = client.request("GET", endpoint)
        return response if response else None
    except Exception:
        return None


def create_rollout(client, name, namespace, spec):
    """Create a new Rollout resource."""
    endpoint = f"/api/v1alpha1/rollouts/{namespace}"
    body = {
        "apiVersion": "argoproj.io/v1alpha1",
        "kind": "Rollout",
        "metadata": {
            "name": name,
            "namespace": namespace
        },
        "spec": spec
    }
    return client.request("POST", endpoint, data=body)


def update_rollout(client, name, namespace, spec):
    """Update an existing Rollout resource."""
    endpoint = f"/api/v1alpha1/rollouts/{namespace}/{name}"
    body = {
        "apiVersion": "argoproj.io/v1alpha1",
        "kind": "Rollout",
        "metadata": {
            "name": name,
            "namespace": namespace
        },
        "spec": spec
    }
    return client.request("PUT", endpoint, data=body)


def delete_rollout(client, name, namespace):
    """Delete a Rollout resource."""
    endpoint = f"/api/v1alpha1/rollouts/{namespace}/{name}"
    return client.request("DELETE", endpoint)


def patch_rollout_status(client, name, namespace, action):
    """Patch Rollout status for pause/resume/promote/abort."""
    endpoint = f"/api/v1alpha1/rollouts/{namespace}/{name}/{action}"
    return client.request("PUT", endpoint)


def build_spec(params):
    """Build Rollout spec from module parameters."""
    spec = {}

    if params.get('replicas') is not None:
        spec['replicas'] = params['replicas']

    if params.get('selector'):
        spec['selector'] = {
            'matchLabels': params['selector']
        }

    if params.get('template'):
        spec['template'] = params['template']
        if params.get('image') and 'spec' in spec['template'] and 'containers' in spec['template']['spec']:
            for container in spec['template']['spec']['containers']:
                container['image'] = params['image']

    if params.get('strategy'):
        spec['strategy'] = params['strategy']

    return spec


def specs_differ(existing_spec, desired_spec):
    """Compare existing and desired specs for changes."""
    for key in desired_spec:
        if key not in existing_spec:
            return True
        if existing_spec[key] != desired_spec[key]:
            return True
    return False


def run_module():
    module_args = argocd_argument_spec()
    module_args.update(
        name=dict(type='str', required=True),
        namespace=dict(type='str', required=True),
        state=dict(
            type='str',
            choices=['present', 'absent', 'paused', 'resumed', 'promoted', 'aborted'],
            default='present'
        ),
        replicas=dict(type='int'),
        image=dict(type='str'),
        strategy=dict(type='dict'),
        selector=dict(type='dict'),
        template=dict(type='dict')
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    client = ArgocdClient(module)

    name = module.params['name']
    namespace = module.params['namespace']
    state = module.params['state']

    result = {
        'changed': False,
        'rollout': {},
        'status': ''
    }

    existing = get_rollout(client, name, namespace)

    try:
        if state == 'present':
            spec = build_spec(module.params)

            if not existing:
                if module.check_mode:
                    result['changed'] = True
                    result['status'] = 'would create'
                else:
                    result['rollout'] = create_rollout(client, name, namespace, spec)
                    result['changed'] = True
                    result['status'] = 'created'
            else:
                if specs_differ(existing.get('spec', {}), spec):
                    if module.check_mode:
                        result['changed'] = True
                        result['status'] = 'would update'
                    else:
                        result['rollout'] = update_rollout(client, name, namespace, spec)
                        result['changed'] = True
                        result['status'] = 'updated'
                else:
                    result['rollout'] = existing
                    result['status'] = 'unchanged'

        elif state == 'absent':
            if existing:
                if module.check_mode:
                    result['changed'] = True
                    result['status'] = 'would delete'
                else:
                    delete_rollout(client, name, namespace)
                    result['changed'] = True
                    result['status'] = 'deleted'
            else:
                result['status'] = 'already absent'

        elif state in ['paused', 'resumed', 'promoted', 'aborted']:
            if not existing:
                module.fail_json(msg=f"Rollout {name} does not exist in namespace {namespace}")

            if module.check_mode:
                result['changed'] = True
                result['status'] = f'would {state}'
            else:
                result['rollout'] = patch_rollout_status(client, name, namespace, state)
                result['changed'] = True
                result['status'] = state

    except Exception as e:
        module.fail_json(msg=f"Failed to manage rollout: {str(e)}")

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
