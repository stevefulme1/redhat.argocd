#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: argo_experiment
short_description: Manage Argo Experiments
description:
  - Create, update, or delete Argo Experiments.
  - Experiments enable A/B testing and canary analysis with multiple template variations.
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
  validate_certs:
    description: Whether to validate SSL certificates.
    type: bool
    default: true
  name:
    description: Name of the Experiment resource.
    type: str
    required: true
  namespace:
    description: Kubernetes namespace for the Experiment.
    type: str
    required: true
  state:
    description: Desired state of the Experiment.
    type: str
    choices: [present, absent]
    default: present
  duration:
    description: How long the experiment should run (e.g., "1h", "30m").
    type: str
  templates:
    description: List of template variations to test.
    type: list
    elements: dict
    suboptions:
      name:
        description: Template variation name.
        type: str
      spec_ref:
        description: Reference to ReplicaSet or Rollout spec.
        type: str
      replicas:
        description: Number of replicas for this template.
        type: int
  analyses:
    description: List of analyses to run during the experiment.
    type: list
    elements: dict
    suboptions:
      name:
        description: Analysis name.
        type: str
      template_name:
        description: AnalysisTemplate name to use.
        type: str
      args:
        description: Arguments to pass to the analysis.
        type: list
        elements: dict
author:
  - Red Hat (@redhat)
'''

EXAMPLES = r'''
- name: Create experiment with two variants
  redhat.argocd.argo_experiment:
    server_url: https://argocd.example.com
    auth_token: "{{ argocd_token }}"
    name: my-app-experiment
    namespace: production
    state: present
    duration: "1h"
    templates:
      - name: baseline
        spec_ref: my-app-stable
        replicas: 1
      - name: canary
        spec_ref: my-app-canary
        replicas: 1
    analyses:
      - name: success-rate
        template_name: success-rate
        args:
          - name: service-name
            value: my-app-canary

- name: Create experiment with custom analysis
  redhat.argocd.argo_experiment:
    server_url: https://argocd.example.com
    auth_token: "{{ argocd_token }}"
    name: web-app-ab-test
    namespace: production
    state: present
    duration: "30m"
    templates:
      - name: control
        spec_ref: web-app-v1
        replicas: 2
      - name: treatment
        spec_ref: web-app-v2
        replicas: 2
    analyses:
      - name: web-metrics
        template_name: web-check
        args:
          - name: baseline-url
            value: http://web-app-v1:8080
          - name: canary-url
            value: http://web-app-v2:8080
'''

RETURN = r'''
experiment:
  description: The Experiment resource details.
  returned: success
  type: dict
  sample:
    apiVersion: argoproj.io/v1alpha1
    kind: Experiment
    metadata:
      name: my-app-experiment
      namespace: production
    spec:
      duration: 1h
      templates:
        - name: baseline
changed:
  description: Whether the Experiment was modified.
  returned: always
  type: bool
  sample: true
status:
  description: Current status of the Experiment.
  returned: success
  type: str
  sample: "running"
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.redhat.argocd.plugins.module_utils.argocd_common import (
    ArgocdClient,
    argocd_argument_spec
)


def get_experiment(client, name, namespace):
    """Retrieve an Experiment resource."""
    endpoint = f"/api/v1alpha1/experiments/{namespace}/{name}"
    try:
        response = client.request("GET", endpoint)
        return response if response else None
    except Exception:
        return None


def create_experiment(client, name, namespace, spec):
    """Create a new Experiment resource."""
    endpoint = f"/api/v1alpha1/experiments/{namespace}"
    body = {
        "apiVersion": "argoproj.io/v1alpha1",
        "kind": "Experiment",
        "metadata": {
            "name": name,
            "namespace": namespace
        },
        "spec": spec
    }
    return client.request("POST", endpoint, data=body)


def update_experiment(client, name, namespace, spec):
    """Update an existing Experiment resource."""
    endpoint = f"/api/v1alpha1/experiments/{namespace}/{name}"
    body = {
        "apiVersion": "argoproj.io/v1alpha1",
        "kind": "Experiment",
        "metadata": {
            "name": name,
            "namespace": namespace
        },
        "spec": spec
    }
    return client.request("PUT", endpoint, data=body)


def delete_experiment(client, name, namespace):
    """Delete an Experiment resource."""
    endpoint = f"/api/v1alpha1/experiments/{namespace}/{name}"
    return client.request("DELETE", endpoint)


def build_spec(params):
    """Build Experiment spec from module parameters."""
    spec = {}

    if params.get('duration'):
        spec['duration'] = params['duration']

    if params.get('templates'):
        spec['templates'] = []
        for template in params['templates']:
            template_def = {}

            if template.get('name'):
                template_def['name'] = template['name']

            if template.get('spec_ref'):
                template_def['specRef'] = template['spec_ref']

            if template.get('replicas') is not None:
                template_def['replicas'] = template['replicas']

            spec['templates'].append(template_def)

    if params.get('analyses'):
        spec['analyses'] = []
        for analysis in params['analyses']:
            analysis_def = {}

            if analysis.get('name'):
                analysis_def['name'] = analysis['name']

            if analysis.get('template_name'):
                analysis_def['templateName'] = analysis['template_name']

            if analysis.get('args'):
                analysis_def['args'] = analysis['args']

            spec['analyses'].append(analysis_def)

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
    template_spec = dict(
        name=dict(type='str'),
        spec_ref=dict(type='str'),
        replicas=dict(type='int')
    )

    analysis_spec = dict(
        name=dict(type='str'),
        template_name=dict(type='str'),
        args=dict(type='list', elements='dict')
    )

    module_args = argocd_argument_spec()
    module_args.update(
        name=dict(type='str', required=True),
        namespace=dict(type='str', required=True),
        state=dict(
            type='str',
            choices=['present', 'absent'],
            default='present'
        ),
        duration=dict(type='str'),
        templates=dict(type='list', elements='dict', options=template_spec),
        analyses=dict(type='list', elements='dict', options=analysis_spec)
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
        'experiment': {},
        'status': ''
    }

    existing = get_experiment(client, name, namespace)

    try:
        if state == 'present':
            spec = build_spec(module.params)

            if not existing:
                if module.check_mode:
                    result['changed'] = True
                    result['status'] = 'would create'
                else:
                    result['experiment'] = create_experiment(client, name, namespace, spec)
                    result['changed'] = True
                    result['status'] = 'created'
            else:
                if specs_differ(existing.get('spec', {}), spec):
                    if module.check_mode:
                        result['changed'] = True
                        result['status'] = 'would update'
                    else:
                        result['experiment'] = update_experiment(client, name, namespace, spec)
                        result['changed'] = True
                        result['status'] = 'updated'
                else:
                    result['experiment'] = existing
                    result['status'] = 'unchanged'

        elif state == 'absent':
            if existing:
                if module.check_mode:
                    result['changed'] = True
                    result['status'] = 'would delete'
                else:
                    delete_experiment(client, name, namespace)
                    result['changed'] = True
                    result['status'] = 'deleted'
            else:
                result['status'] = 'already absent'

    except Exception as e:
        module.fail_json(msg=f"Failed to manage experiment: {str(e)}")

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
