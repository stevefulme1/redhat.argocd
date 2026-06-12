#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: argo_workflow
short_description: Manage Argo Workflows
description:
  - Create, delete, or submit Argo Workflows
  - Manage workflow lifecycle in specified namespace
  - Supports check mode for validation
version_added: "0.1.0"
author:
  - Red Hat Ansible Automation Platform Team
options:
  name:
    description:
      - Name of the workflow
    type: str
    required: true
  namespace:
    description:
      - Kubernetes namespace where the workflow resides
    type: str
    required: true
  state:
    description:
      - Desired state of the workflow
      - C(present) ensures workflow exists
      - C(absent) ensures workflow is deleted
      - C(submitted) creates and starts the workflow
    type: str
    choices: ['present', 'absent', 'submitted']
    default: present
  definition:
    description:
      - Workflow specification (spec field)
      - Required when state is present or submitted
    type: dict
    required: false
  labels:
    description:
      - Labels to apply to the workflow
    type: dict
    required: false
  wait:
    description:
      - Wait for workflow to complete when state is submitted
    type: bool
    default: false
  timeout:
    description:
      - Maximum time in seconds to wait for workflow completion
      - Only applies when wait is true
    type: int
    default: 600
requirements:
  - requests
notes:
  - Check mode is supported
  - state=submitted will create and immediately start the workflow
'''

EXAMPLES = r'''
- name: Create a workflow
  redhat.argocd.argo_workflow:
    server_url: https://argo.example.com
    auth_token: "{{ argo_token }}"
    name: hello-world
    namespace: argo
    state: present
    definition:
      entrypoint: whalesay
      templates:
        - name: whalesay
          container:
            image: docker/whalesay
            command: [cowsay]
            args: ["hello world"]
    labels:
      app: demo

- name: Submit and wait for workflow completion
  redhat.argocd.argo_workflow:
    server_url: https://argo.example.com
    auth_token: "{{ argo_token }}"
    name: data-processing
    namespace: workflows
    state: submitted
    wait: true
    timeout: 1800
    definition:
      entrypoint: process-data
      templates:
        - name: process-data
          script:
            image: python:3.11
            command: [python]
            source: |
              print("Processing data...")
'''

RETURN = r'''
workflow:
  description: The workflow object
  returned: success
  type: dict
  sample:
    metadata:
      name: hello-world
      namespace: argo
    spec:
      entrypoint: whalesay
    status:
      phase: Succeeded
changed:
  description: Whether the workflow was created, updated, or deleted
  returned: always
  type: bool
  sample: true
status:
  description: Current workflow status
  returned: when workflow exists
  type: str
  sample: Succeeded
'''

import time
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.redhat.argocd.plugins.module_utils.argocd_common import (
    argocd_argument_spec,
    ArgocdClient
)


def wait_for_workflow(client, name, namespace, timeout):
    """Wait for workflow to complete"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        workflow = client.get_workflow(namespace, name)
        if not workflow:
            return None, "Workflow not found"

        phase = workflow.get('status', {}).get('phase', '')
        if phase in ['Succeeded', 'Failed', 'Error']:
            return workflow, phase

        time.sleep(5)

    return None, "Timeout"


def workflows_equal(existing, desired_spec, desired_labels):
    """Compare existing workflow with desired state"""
    if desired_spec:
        existing_spec = existing.get('spec', {})
        if existing_spec != desired_spec:
            return False

    if desired_labels:
        existing_labels = existing.get('metadata', {}).get('labels', {})
        for key, value in desired_labels.items():
            if existing_labels.get(key) != value:
                return False

    return True


def run_module():
    argument_spec = argocd_argument_spec()
    argument_spec.update(
        name=dict(type='str', required=True),
        namespace=dict(type='str', required=True),
        state=dict(type='str', choices=['present', 'absent', 'submitted'], default='present'),
        definition=dict(type='dict', required=False),
        labels=dict(type='dict', required=False),
        wait=dict(type='bool', default=False),
        timeout=dict(type='int', default=600),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_if=[
            ('state', 'present', ['definition']),
            ('state', 'submitted', ['definition']),
        ]
    )

    client = ArgocdClient(module)

    name = module.params['name']
    namespace = module.params['namespace']
    state = module.params['state']
    definition = module.params.get('definition')
    labels = module.params.get('labels')
    wait = module.params['wait']
    timeout = module.params['timeout']

    # Get existing workflow
    existing = client.get_workflow(namespace, name)

    if state == 'absent':
        if not existing:
            module.exit_json(changed=False, msg="Workflow already absent")

        if module.check_mode:
            module.exit_json(changed=True, msg="Would delete workflow (check mode)")

        result = client.delete_workflow(namespace, name)
        if result:
            module.exit_json(changed=True, msg="Workflow deleted")
        else:
            module.fail_json(msg="Failed to delete workflow")

    # state is present or submitted
    if existing:
        # Check if update is needed
        if workflows_equal(existing, definition, labels):
            workflow_status = existing.get('status', {}).get('phase', 'Unknown')
            module.exit_json(
                changed=False,
                workflow=existing,
                status=workflow_status,
                msg="Workflow already exists with desired state"
            )

        # Workflow exists but needs update - delete and recreate
        if module.check_mode:
            module.exit_json(changed=True, msg="Would update workflow (check mode)")

        client.delete_workflow(namespace, name)

    # Create workflow
    if module.check_mode:
        module.exit_json(changed=True, msg="Would create workflow (check mode)")

    workflow_body = {
        'apiVersion': 'argoproj.io/v1alpha1',
        'kind': 'Workflow',
        'metadata': {
            'name': name,
            'namespace': namespace
        },
        'spec': definition
    }

    if labels:
        workflow_body['metadata']['labels'] = labels

    if state == 'submitted':
        result = client.submit_workflow(namespace, workflow_body)
    else:
        result = client.create_workflow(namespace, workflow_body)

    if not result:
        module.fail_json(msg="Failed to create workflow")

    changed = True
    workflow_status = result.get('status', {}).get('phase', 'Pending')

    # Wait for completion if requested
    if state == 'submitted' and wait:
        final_workflow, phase = wait_for_workflow(client, name, namespace, timeout)
        if final_workflow:
            result = final_workflow
            workflow_status = phase
            if phase in ['Failed', 'Error']:
                module.fail_json(
                    msg=f"Workflow failed: {phase}",
                    workflow=result,
                    status=workflow_status
                )
        else:
            module.fail_json(
                msg=f"Workflow did not complete within {timeout} seconds",
                workflow=result,
                status=workflow_status
            )

    module.exit_json(
        changed=changed,
        workflow=result,
        status=workflow_status
    )


def main():
    run_module()


if __name__ == '__main__':
    main()
