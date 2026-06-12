#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: argo_analysis_template
short_description: Manage Argo Analysis Templates
description:
  - Create, update, or delete Argo Analysis Templates.
  - Analysis Templates define metrics and success criteria for progressive delivery validation.
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
    description: Name of the Analysis Template.
    type: str
    required: true
  namespace:
    description: Kubernetes namespace for the Analysis Template.
    type: str
    required: true
  state:
    description: Desired state of the Analysis Template.
    type: str
    choices: [present, absent]
    default: present
  metrics:
    description: List of metrics to evaluate.
    type: list
    elements: dict
    suboptions:
      name:
        description: Metric name.
        type: str
        required: true
      provider:
        description: Metric provider configuration (prometheus, datadog, wavefront, web).
        type: dict
      success_condition:
        description: Expression that defines success.
        type: str
      failure_condition:
        description: Expression that defines failure.
        type: str
      interval:
        description: How often to run the metric (e.g., "5m").
        type: str
      count:
        description: Number of times to run the metric.
        type: int
  args:
    description: Template arguments for parameterization.
    type: list
    elements: dict
    suboptions:
      name:
        description: Argument name.
        type: str
      value:
        description: Argument value.
        type: str
author:
  - Red Hat (@redhat)
'''

EXAMPLES = r'''
- name: Create Analysis Template with Prometheus metric
  redhat.argocd.argo_analysis_template:
    server_url: https://argocd.example.com
    auth_token: "{{ argocd_token }}"
    name: success-rate
    namespace: production
    state: present
    metrics:
      - name: success-rate
        interval: 5m
        count: 10
        success_condition: result[0] >= 0.95
        failure_condition: result[0] < 0.90
        provider:
          prometheus:
            address: http://prometheus:9090
            query: |
              sum(rate(http_requests_total{status=~"2.."}[5m]))
              /
              sum(rate(http_requests_total[5m]))
    args:
      - name: service-name
        value: my-app

- name: Create web-based Analysis Template
  redhat.argocd.argo_analysis_template:
    server_url: https://argocd.example.com
    auth_token: "{{ argocd_token }}"
    name: web-check
    namespace: production
    state: present
    metrics:
      - name: web-health
        interval: 2m
        count: 5
        success_condition: "result.statusCode == 200"
        failure_condition: "result.statusCode >= 500"
        provider:
          web:
            url: https://my-app.example.com/health
            jsonPath: "{$.status}"
'''

RETURN = r'''
analysis_template:
  description: The Analysis Template resource details.
  returned: success
  type: dict
  sample:
    apiVersion: argoproj.io/v1alpha1
    kind: AnalysisTemplate
    metadata:
      name: success-rate
      namespace: production
    spec:
      metrics:
        - name: success-rate
          interval: 5m
changed:
  description: Whether the Analysis Template was modified.
  returned: always
  type: bool
  sample: true
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.redhat.argocd.plugins.module_utils.argocd_common import (
    ArgocdClient,
    argocd_argument_spec
)


def get_analysis_template(client, name, namespace):
    """Retrieve an Analysis Template resource."""
    endpoint = f"/api/v1alpha1/analysistemplates/{namespace}/{name}"
    try:
        response = client.request("GET", endpoint)
        return response if response else None
    except Exception:
        return None


def create_analysis_template(client, name, namespace, spec):
    """Create a new Analysis Template resource."""
    endpoint = f"/api/v1alpha1/analysistemplates/{namespace}"
    body = {
        "apiVersion": "argoproj.io/v1alpha1",
        "kind": "AnalysisTemplate",
        "metadata": {
            "name": name,
            "namespace": namespace
        },
        "spec": spec
    }
    return client.request("POST", endpoint, data=body)


def update_analysis_template(client, name, namespace, spec):
    """Update an existing Analysis Template resource."""
    endpoint = f"/api/v1alpha1/analysistemplates/{namespace}/{name}"
    body = {
        "apiVersion": "argoproj.io/v1alpha1",
        "kind": "AnalysisTemplate",
        "metadata": {
            "name": name,
            "namespace": namespace
        },
        "spec": spec
    }
    return client.request("PUT", endpoint, data=body)


def delete_analysis_template(client, name, namespace):
    """Delete an Analysis Template resource."""
    endpoint = f"/api/v1alpha1/analysistemplates/{namespace}/{name}"
    return client.request("DELETE", endpoint)


def build_spec(params):
    """Build Analysis Template spec from module parameters."""
    spec = {}

    if params.get('metrics'):
        spec['metrics'] = []
        for metric in params['metrics']:
            metric_def = {
                'name': metric['name']
            }

            if metric.get('provider'):
                metric_def['provider'] = metric['provider']

            if metric.get('success_condition'):
                metric_def['successCondition'] = metric['success_condition']

            if metric.get('failure_condition'):
                metric_def['failureCondition'] = metric['failure_condition']

            if metric.get('interval'):
                metric_def['interval'] = metric['interval']

            if metric.get('count') is not None:
                metric_def['count'] = metric['count']

            spec['metrics'].append(metric_def)

    if params.get('args'):
        spec['args'] = []
        for arg in params['args']:
            arg_def = {}
            if arg.get('name'):
                arg_def['name'] = arg['name']
            if arg.get('value'):
                arg_def['value'] = arg['value']
            spec['args'].append(arg_def)

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
    metric_spec = dict(
        name=dict(type='str', required=True),
        provider=dict(type='dict'),
        success_condition=dict(type='str'),
        failure_condition=dict(type='str'),
        interval=dict(type='str'),
        count=dict(type='int')
    )

    arg_spec = dict(
        name=dict(type='str'),
        value=dict(type='str')
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
        metrics=dict(type='list', elements='dict', options=metric_spec),
        args=dict(type='list', elements='dict', options=arg_spec)
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
        'analysis_template': {}
    }

    existing = get_analysis_template(client, name, namespace)

    try:
        if state == 'present':
            spec = build_spec(module.params)

            if not existing:
                if module.check_mode:
                    result['changed'] = True
                else:
                    result['analysis_template'] = create_analysis_template(client, name, namespace, spec)
                    result['changed'] = True
            else:
                if specs_differ(existing.get('spec', {}), spec):
                    if module.check_mode:
                        result['changed'] = True
                    else:
                        result['analysis_template'] = update_analysis_template(client, name, namespace, spec)
                        result['changed'] = True
                else:
                    result['analysis_template'] = existing

        elif state == 'absent':
            if existing:
                if module.check_mode:
                    result['changed'] = True
                else:
                    delete_analysis_template(client, name, namespace)
                    result['changed'] = True

    except Exception as e:
        module.fail_json(msg=f"Failed to manage analysis template: {str(e)}")

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
