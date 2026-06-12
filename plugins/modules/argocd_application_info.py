#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright: (c) 2024, Red Hat (@redhat)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: argocd_application_info
short_description: Get information about ArgoCD applications
description:
  - Retrieve information about one or all ArgoCD applications.
  - This is a read-only module that does not modify state.
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
    description:
      - Name of a specific application to retrieve.
      - If not provided, all applications will be returned.
    type: str
  project:
    description:
      - Filter applications by project name.
      - Only used when name is not specified.
    type: str
requirements:
  - "requests>=2.25.0"
author:
  - "Red Hat (@redhat)"
'''

EXAMPLES = r'''
- name: Get information about a specific application
  redhat.argocd.argocd_application_info:
    server_url: https://argocd.example.com
    auth_token: "{{ argocd_token }}"
    name: my-app
  register: app_info

- name: Get all applications
  redhat.argocd.argocd_application_info:
    server_url: https://argocd.example.com
    auth_token: "{{ argocd_token }}"
  register: all_apps

- name: Get applications in a specific project
  redhat.argocd.argocd_application_info:
    server_url: https://argocd.example.com
    auth_token: "{{ argocd_token }}"
    project: production
  register: prod_apps

- name: Display application sync status
  redhat.argocd.argocd_application_info:
    server_url: https://argocd.example.com
    auth_token: "{{ argocd_token }}"
    name: my-app
  register: result
- debug:
    msg: "App {{ result.applications[0].metadata.name }} is {{ result.applications[0].status.sync.status }}"
'''

RETURN = r'''
applications:
  description: List of application details.
  type: list
  returned: always
  elements: dict
  sample:
    - metadata:
        name: my-app
        namespace: argocd
      spec:
        project: default
        source:
          repoURL: https://github.com/example/app.git
          targetRevision: main
          path: manifests
        destination:
          server: https://kubernetes.default.svc
          namespace: production
      status:
        sync:
          status: Synced
        health:
          status: Healthy
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.redhat.argocd.plugins.module_utils.argocd_common import ArgocdClient, argocd_argument_spec


def run_module():
    argument_spec = argocd_argument_spec()
    argument_spec.update(dict(
        name=dict(type='str'),
        project=dict(type='str')
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True
    )

    client = ArgocdClient(module)
    name = module.params.get('name')
    project = module.params.get('project')

    result = {
        'changed': False,
        'applications': []
    }

    if name:
        # Get specific application
        app = client.get(f'/api/v1/applications/{name}')
        if app:
            result['applications'] = [app]
    else:
        # Get all applications
        response = client.get('/api/v1/applications')
        if response and 'items' in response:
            apps = response['items']
            # Filter by project if specified
            if project:
                apps = [app for app in apps if app.get('spec', {}).get('project') == project]
            result['applications'] = apps
        else:
            result['applications'] = []

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
