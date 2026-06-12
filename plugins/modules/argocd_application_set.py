#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright: (c) 2024, Red Hat (@redhat)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: argocd_application_set
short_description: Manage ArgoCD ApplicationSets
description:
  - Create, update, or delete ArgoCD ApplicationSets.
  - ApplicationSets use generators to create multiple applications from templates.
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
    description: Name of the ApplicationSet.
    type: str
    required: true
  state:
    description: Desired state of the ApplicationSet.
    type: str
    choices: ['present', 'absent']
    default: 'present'
  namespace:
    description: Namespace for the ApplicationSet resource.
    type: str
    default: 'argocd'
  generators:
    description:
      - List of generators for the ApplicationSet.
      - Each generator produces parameters for the template.
    type: list
    elements: dict
  template:
    description:
      - Application template specification.
      - Uses Go template syntax with generator parameters.
    type: dict
  sync_policy:
    description: Sync policy for generated applications.
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
requirements:
  - "requests>=2.25.0"
author:
  - "Red Hat (@redhat)"
'''

EXAMPLES = r'''
- name: Create ApplicationSet with list generator
  redhat.argocd.argocd_application_set:
    server_url: https://argocd.example.com
    auth_token: "{{ argocd_token }}"
    name: my-appset
    namespace: argocd
    generators:
      - list:
          elements:
            - cluster: prod
              url: https://prod.k8s.local
            - cluster: staging
              url: https://staging.k8s.local
    template:
      metadata:
        name: "{{cluster}}-app"
      spec:
        project: default
        source:
          repoURL: https://github.com/example/app.git
          targetRevision: main
          path: manifests
        destination:
          server: "{{url}}"
          namespace: default
    state: present

- name: Create ApplicationSet with git generator
  redhat.argocd.argocd_application_set:
    server_url: https://argocd.example.com
    auth_token: "{{ argocd_token }}"
    name: git-appset
    generators:
      - git:
          repoURL: https://github.com/example/apps.git
          revision: main
          directories:
            - path: "apps/*"
    template:
      metadata:
        name: "{{path.basename}}"
      spec:
        project: default
        source:
          repoURL: https://github.com/example/apps.git
          targetRevision: main
          path: "{{path}}"
        destination:
          server: https://kubernetes.default.svc
          namespace: "{{path.basename}}"

- name: Delete ApplicationSet
  redhat.argocd.argocd_application_set:
    server_url: https://argocd.example.com
    auth_token: "{{ argocd_token }}"
    name: my-appset
    state: absent
'''

RETURN = r'''
application_set:
  description: ApplicationSet details.
  type: dict
  returned: always
  sample:
    apiVersion: argoproj.io/v1alpha1
    kind: ApplicationSet
    metadata:
      name: my-appset
      namespace: argocd
    spec:
      generators:
        - list:
            elements:
              - cluster: prod
      template:
        metadata:
          name: "{{cluster}}-app"
        spec:
          project: default
changed:
  description: Whether the ApplicationSet was changed.
  type: bool
  returned: always
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.redhat.argocd.plugins.module_utils.argocd_common import ArgocdClient, argocd_argument_spec


def build_applicationset_spec(params):
    """Build ApplicationSet specification from module parameters."""
    spec = {}

    if params.get('generators'):
        spec['generators'] = params['generators']

    if params.get('template'):
        spec['template'] = params['template']

    # Handle sync policy
    sync_policy = params.get('sync_policy', {})
    if sync_policy:
        policy = {}
        if sync_policy.get('automated'):
            policy['automated'] = {}
            if sync_policy.get('prune'):
                policy['automated']['prune'] = True
            if sync_policy.get('self_heal'):
                policy['automated']['selfHeal'] = True
        if 'template' in spec and 'spec' in spec['template']:
            spec['template']['spec']['syncPolicy'] = policy

    return spec


def applicationsets_equal(existing, desired):
    """Compare existing and desired ApplicationSet specifications."""
    if not existing:
        return False

    existing_spec = existing.get('spec', {})

    # Compare generators
    if existing_spec.get('generators') != desired.get('generators'):
        return False

    # Compare template
    if existing_spec.get('template') != desired.get('template'):
        return False

    return True


def run_module():
    argument_spec = argocd_argument_spec()
    argument_spec.update(dict(
        name=dict(type='str', required=True),
        state=dict(type='str', choices=['present', 'absent'], default='present'),
        namespace=dict(type='str', default='argocd'),
        generators=dict(type='list', elements='dict'),
        template=dict(type='dict'),
        sync_policy=dict(type='dict')
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_if=[
            ('state', 'present', ['generators', 'template'])
        ]
    )

    client = ArgocdClient(module)
    name = module.params['name']
    namespace = module.params['namespace']
    state = module.params['state']

    # ApplicationSets are Kubernetes CRDs, accessed via /api/v1/applicationsets
    endpoint = f'/api/v1/applicationsets/{namespace}/{name}'

    # Get existing ApplicationSet
    existing = client.get(endpoint)

    result = {
        'changed': False,
        'application_set': {}
    }

    if state == 'absent':
        if existing:
            if not module.check_mode:
                client.delete(endpoint)
            result['changed'] = True
            result['application_set'] = existing
        module.exit_json(**result)

    # State is 'present'
    desired_spec = build_applicationset_spec(module.params)

    if not existing:
        # Create new ApplicationSet
        payload = {
            'apiVersion': 'argoproj.io/v1alpha1',
            'kind': 'ApplicationSet',
            'metadata': {
                'name': name,
                'namespace': namespace
            },
            'spec': desired_spec
        }
        if not module.check_mode:
            result['application_set'] = client.post('/api/v1/applicationsets', payload)
        else:
            result['application_set'] = payload
        result['changed'] = True
    elif not applicationsets_equal(existing, desired_spec):
        # Update existing ApplicationSet
        payload = existing.copy()
        payload['spec'] = desired_spec
        if not module.check_mode:
            result['application_set'] = client.put(endpoint, payload)
        else:
            result['application_set'] = payload
        result['changed'] = True
    else:
        # No changes needed
        result['application_set'] = existing

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
