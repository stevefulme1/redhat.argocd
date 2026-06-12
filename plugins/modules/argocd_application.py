#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright: (c) 2024, Red Hat (@redhat)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: argocd_application
short_description: Manage ArgoCD applications
description:
  - Create, update, or delete ArgoCD applications.
  - Supports idempotent operations with check mode.
version_added: "0.1.0"
options:
  server_url:
    description: URL of the ArgoCD server.
    type: str
    required: true
  auth_token:
    description: Authentication token for ArgoCD API.
    type: str
    required: true
    no_log: true
  validate_certs:
    description: Whether to validate SSL certificates.
    type: bool
    default: true
  name:
    description: Name of the application.
    type: str
    required: true
  project:
    description: ArgoCD project name.
    type: str
    default: "default"
  state:
    description: Desired state of the application.
    type: str
    choices: ['present', 'absent']
    default: 'present'
  repo_url:
    description: Git repository URL.
    type: str
  revision:
    description: Git revision (branch, tag, or commit SHA).
    type: str
    default: 'HEAD'
  path:
    description: Path within the repository.
    type: str
  destination_server:
    description: Kubernetes cluster API server URL.
    type: str
  destination_namespace:
    description: Target namespace for the application.
    type: str
  helm_values:
    description: Helm values to override.
    type: dict
  sync_policy:
    description: Sync policy configuration.
    type: dict
    suboptions:
      automated:
        description: Enable automated sync.
        type: bool
      prune:
        description: Prune resources during sync.
        type: bool
      self_heal:
        description: Enable self-healing.
        type: bool
  auto_sync:
    description: Enable automated synchronization (deprecated, use sync_policy.automated).
    type: bool
    default: false
requirements:
  - "requests>=2.25.0"
author:
  - "Red Hat (@redhat)"
'''

EXAMPLES = r'''
- name: Create ArgoCD application
  redhat.argocd.argocd_application:
    server_url: https://argocd.example.com
    auth_token: "{{ argocd_token }}"
    name: my-app
    project: default
    repo_url: https://github.com/example/app.git
    revision: main
    path: manifests
    destination_server: https://kubernetes.default.svc
    destination_namespace: production
    state: present

- name: Create application with Helm values
  redhat.argocd.argocd_application:
    server_url: https://argocd.example.com
    auth_token: "{{ argocd_token }}"
    name: helm-app
    repo_url: https://charts.example.com
    path: my-chart
    destination_server: https://kubernetes.default.svc
    destination_namespace: default
    helm_values:
      replicaCount: 3
      image:
        tag: v1.2.3

- name: Create application with auto-sync
  redhat.argocd.argocd_application:
    server_url: https://argocd.example.com
    auth_token: "{{ argocd_token }}"
    name: auto-app
    repo_url: https://github.com/example/app.git
    path: k8s
    destination_server: https://kubernetes.default.svc
    destination_namespace: staging
    sync_policy:
      automated: true
      prune: true
      self_heal: true

- name: Delete ArgoCD application
  redhat.argocd.argocd_application:
    server_url: https://argocd.example.com
    auth_token: "{{ argocd_token }}"
    name: my-app
    state: absent
'''

RETURN = r'''
application:
  description: Application details.
  type: dict
  returned: always
  sample:
    metadata:
      name: my-app
    spec:
      project: default
      source:
        repoURL: https://github.com/example/app.git
        targetRevision: main
        path: manifests
      destination:
        server: https://kubernetes.default.svc
        namespace: production
changed:
  description: Whether the application was changed.
  type: bool
  returned: always
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.redhat.argocd.plugins.module_utils.argocd_common import ArgocdClient, argocd_argument_spec


def build_application_spec(params):
    """Build application specification from module parameters."""
    spec = {
        'project': params['project'],
        'source': {},
        'destination': {}
    }

    if params.get('repo_url'):
        spec['source']['repoURL'] = params['repo_url']
    if params.get('revision'):
        spec['source']['targetRevision'] = params['revision']
    if params.get('path'):
        spec['source']['path'] = params['path']
    if params.get('helm_values'):
        spec['source']['helm'] = {'values': params['helm_values']}

    if params.get('destination_server'):
        spec['destination']['server'] = params['destination_server']
    if params.get('destination_namespace'):
        spec['destination']['namespace'] = params['destination_namespace']

    # Handle sync policy
    sync_policy = params.get('sync_policy', {})
    if sync_policy or params.get('auto_sync'):
        policy = {}
        if sync_policy.get('automated') or params.get('auto_sync'):
            policy['automated'] = {}
            if sync_policy.get('prune'):
                policy['automated']['prune'] = True
            if sync_policy.get('self_heal'):
                policy['automated']['selfHeal'] = True
        spec['syncPolicy'] = policy

    return spec


def applications_equal(existing, desired):
    """Compare existing and desired application specifications."""
    if not existing:
        return False

    existing_spec = existing.get('spec', {})

    # Compare project
    if existing_spec.get('project') != desired.get('project'):
        return False

    # Compare source
    existing_source = existing_spec.get('source', {})
    desired_source = desired.get('source', {})
    for key in ['repoURL', 'targetRevision', 'path']:
        if existing_source.get(key) != desired_source.get(key):
            return False

    # Compare destination
    existing_dest = existing_spec.get('destination', {})
    desired_dest = desired.get('destination', {})
    for key in ['server', 'namespace']:
        if existing_dest.get(key) != desired_dest.get(key):
            return False

    # Compare sync policy
    existing_policy = existing_spec.get('syncPolicy', {})
    desired_policy = desired.get('syncPolicy', {})
    if bool(existing_policy) != bool(desired_policy):
        return False

    return True


def run_module():
    argument_spec = argocd_argument_spec()
    argument_spec.update(dict(
        name=dict(type='str', required=True),
        project=dict(type='str', default='default'),
        state=dict(type='str', choices=['present', 'absent'], default='present'),
        repo_url=dict(type='str'),
        revision=dict(type='str', default='HEAD'),
        path=dict(type='str'),
        destination_server=dict(type='str'),
        destination_namespace=dict(type='str'),
        helm_values=dict(type='dict'),
        sync_policy=dict(type='dict'),
        auto_sync=dict(type='bool', default=False)
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_if=[
            ('state', 'present', ['repo_url', 'destination_server', 'destination_namespace'])
        ]
    )

    client = ArgocdClient(module)
    name = module.params['name']
    state = module.params['state']

    # Get existing application
    existing = client.get(f'/api/v1/applications/{name}')

    result = {
        'changed': False,
        'application': {}
    }

    if state == 'absent':
        if existing:
            if not module.check_mode:
                client.delete(f'/api/v1/applications/{name}')
            result['changed'] = True
            result['application'] = existing
        module.exit_json(**result)

    # State is 'present'
    desired_spec = build_application_spec(module.params)

    if not existing:
        # Create new application
        payload = {
            'metadata': {'name': name},
            'spec': desired_spec
        }
        if not module.check_mode:
            result['application'] = client.post('/api/v1/applications', payload)
        else:
            result['application'] = payload
        result['changed'] = True
    elif not applications_equal(existing, desired_spec):
        # Update existing application
        payload = existing.copy()
        payload['spec'] = desired_spec
        if not module.check_mode:
            result['application'] = client.put(f'/api/v1/applications/{name}', payload)
        else:
            result['application'] = payload
        result['changed'] = True
    else:
        # No changes needed
        result['application'] = existing

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
