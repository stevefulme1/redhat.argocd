#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright: (c) 2024, Red Hat (@redhat)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: argocd_project
short_description: Manage ArgoCD projects
description:
  - Create, update, or delete ArgoCD projects.
  - Projects provide logical grouping and access control for applications.
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
  validate_certs:
    description: Whether to validate SSL certificates.
    type: bool
    default: true
  name:
    description: Name of the project.
    type: str
    required: true
  state:
    description: Desired state of the project.
    type: str
    choices: ['present', 'absent']
    default: 'present'
  description:
    description: Project description.
    type: str
  source_repos:
    description:
      - List of source repository URLs allowed for this project.
      - Use '*' to allow all repositories.
    type: list
    elements: str
  destinations:
    description:
      - List of allowed deployment destinations.
      - Each destination specifies a server and namespace.
    type: list
    elements: dict
    suboptions:
      server:
        description: Kubernetes API server URL.
        type: str
        required: true
      namespace:
        description: Target namespace (use '*' for all namespaces).
        type: str
        required: true
  cluster_resource_whitelist:
    description:
      - List of cluster-scoped resources allowed for this project.
      - Each entry specifies group and kind.
    type: list
    elements: dict
    suboptions:
      group:
        description: API group (use '*' for all groups).
        type: str
      kind:
        description: Resource kind (use '*' for all kinds).
        type: str
  namespace_resource_blacklist:
    description:
      - List of namespace-scoped resources denied for this project.
      - Each entry specifies group and kind.
    type: list
    elements: dict
    suboptions:
      group:
        description: API group.
        type: str
      kind:
        description: Resource kind.
        type: str
requirements:
  - "requests>=2.25.0"
author:
  - "Red Hat (@redhat)"
'''

EXAMPLES = r'''
- name: Create ArgoCD project
  redhat.argocd.argocd_project:
    server_url: https://argocd.example.com
    auth_token: "{{ argocd_token }}"
    name: production
    description: Production applications
    source_repos:
      - https://github.com/example/prod-apps.git
      - https://charts.example.com
    destinations:
      - server: https://kubernetes.default.svc
        namespace: prod-*
      - server: https://prod.k8s.local
        namespace: '*'
    state: present

- name: Create project with resource restrictions
  redhat.argocd.argocd_project:
    server_url: https://argocd.example.com
    auth_token: "{{ argocd_token }}"
    name: restricted
    source_repos:
      - '*'
    destinations:
      - server: https://kubernetes.default.svc
        namespace: restricted
    cluster_resource_whitelist:
      - group: ''
        kind: Namespace
    namespace_resource_blacklist:
      - group: ''
        kind: ResourceQuota

- name: Delete ArgoCD project
  redhat.argocd.argocd_project:
    server_url: https://argocd.example.com
    auth_token: "{{ argocd_token }}"
    name: old-project
    state: absent
'''

RETURN = r'''
project:
  description: Project details.
  type: dict
  returned: always
  sample:
    metadata:
      name: production
    spec:
      description: Production applications
      sourceRepos:
        - https://github.com/example/prod-apps.git
      destinations:
        - server: https://kubernetes.default.svc
          namespace: prod-*
changed:
  description: Whether the project was changed.
  type: bool
  returned: always
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.redhat.argocd.plugins.module_utils.argocd_common import ArgocdClient, argocd_argument_spec


def build_project_spec(params):
    """Build project specification from module parameters."""
    spec = {}

    if params.get('description'):
        spec['description'] = params['description']

    if params.get('source_repos'):
        spec['sourceRepos'] = params['source_repos']

    if params.get('destinations'):
        spec['destinations'] = params['destinations']

    if params.get('cluster_resource_whitelist'):
        spec['clusterResourceWhitelist'] = params['cluster_resource_whitelist']

    if params.get('namespace_resource_blacklist'):
        spec['namespaceResourceBlacklist'] = params['namespace_resource_blacklist']

    return spec


def projects_equal(existing, desired):
    """Compare existing and desired project specifications."""
    if not existing:
        return False

    existing_spec = existing.get('spec', {})

    # Compare description
    if existing_spec.get('description') != desired.get('description'):
        return False

    # Compare source repos
    existing_repos = set(existing_spec.get('sourceRepos', []))
    desired_repos = set(desired.get('sourceRepos', []))
    if existing_repos != desired_repos:
        return False

    # Compare destinations
    if existing_spec.get('destinations') != desired.get('destinations'):
        return False

    # Compare resource lists
    if existing_spec.get('clusterResourceWhitelist') != desired.get('clusterResourceWhitelist'):
        return False
    if existing_spec.get('namespaceResourceBlacklist') != desired.get('namespaceResourceBlacklist'):
        return False

    return True


def run_module():
    argument_spec = argocd_argument_spec()
    argument_spec.update(dict(
        name=dict(type='str', required=True),
        state=dict(type='str', choices=['present', 'absent'], default='present'),
        description=dict(type='str'),
        source_repos=dict(type='list', elements='str'),
        destinations=dict(type='list', elements='dict'),
        cluster_resource_whitelist=dict(type='list', elements='dict'),
        namespace_resource_blacklist=dict(type='list', elements='dict')
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True
    )

    client = ArgocdClient(module)
    name = module.params['name']
    state = module.params['state']

    # Get existing project
    existing = client.get(f'/api/v1/projects/{name}')

    result = {
        'changed': False,
        'project': {}
    }

    if state == 'absent':
        if existing:
            if not module.check_mode:
                client.delete(f'/api/v1/projects/{name}')
            result['changed'] = True
            result['project'] = existing
        module.exit_json(**result)

    # State is 'present'
    desired_spec = build_project_spec(module.params)

    if not existing:
        # Create new project
        payload = {
            'metadata': {'name': name},
            'spec': desired_spec
        }
        if not module.check_mode:
            result['project'] = client.post('/api/v1/projects', payload)
        else:
            result['project'] = payload
        result['changed'] = True
    elif not projects_equal(existing, desired_spec):
        # Update existing project
        payload = existing.copy()
        payload['spec'] = desired_spec
        if not module.check_mode:
            result['project'] = client.put(f'/api/v1/projects/{name}', payload)
        else:
            result['project'] = payload
        result['changed'] = True
    else:
        # No changes needed
        result['project'] = existing

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
