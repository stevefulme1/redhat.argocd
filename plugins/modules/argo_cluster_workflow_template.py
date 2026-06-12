#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: argo_cluster_workflow_template
short_description: Manage Argo Cluster Workflow Templates
description:
  - Create, update, or delete Argo Cluster Workflow Templates
  - Cluster workflow templates are cluster-scoped reusable workflow definitions
  - Can be referenced by workflows in any namespace
  - Supports check mode for validation
version_added: "0.1.0"
author:
  - Red Hat, Inc. (@redhat-ansible)
options:
  server_url:
    description:
      - URL of the ArgoCD server.
    type: str
    required: true
  auth_token:
    description:
      - Authentication token for ArgoCD API.
    type: str
    required: true
  validate_certs:
    description:
      - Whether to validate SSL certificates.
    type: bool
    default: true
  name:
    description:
      - Name of the cluster workflow template
    type: str
    required: true
  state:
    description:
      - Desired state of the cluster workflow template
      - C(present) ensures template exists
      - C(absent) ensures template is deleted
    type: str
    choices: ['present', 'absent']
    default: present
  definition:
    description:
      - Workflow template specification (spec field)
      - Required when state is present
    type: dict
    required: false
  labels:
    description:
      - Labels to apply to the cluster workflow template
    type: dict
    required: false
requirements:
  - requests
notes:
  - Check mode is supported
  - Cluster workflow templates are cluster-scoped (no namespace)
  - Requires cluster-level permissions to create/update/delete
'''

EXAMPLES = r'''
- name: Create cluster workflow template
  redhat.argocd.argo_cluster_workflow_template:
    server_url: https://argo.example.com
    auth_token: "{{ argo_token }}"
    name: shared-build-steps
    state: present
    definition:
      entrypoint: build-and-test
      templates:
        - name: build-and-test
          steps:
            - - name: checkout
                template: git-clone
            - - name: build
                template: build-binary
            - - name: test
                template: run-tests
        - name: git-clone
          container:
            image: alpine/git:latest
            command: [git, clone]
            args: ["{{inputs.parameters.repo}}"]
          inputs:
            parameters:
              - name: repo
        - name: build-binary
          container:
            image: golang:1.22
            command: [go, build]
            args: ["-o", "app", "."]
        - name: run-tests
          container:
            image: golang:1.22
            command: [go, test]
            args: ["./..."]
    labels:
      category: shared
      team: platform

- name: Delete cluster workflow template
  redhat.argocd.argo_cluster_workflow_template:
    server_url: https://argo.example.com
    auth_token: "{{ argo_token }}"
    name: deprecated-template
    state: absent
'''

RETURN = r'''
cluster_workflow_template:
  description: The cluster workflow template object
  returned: when state is present
  type: dict
  sample:
    metadata:
      name: shared-build-steps
    spec:
      entrypoint: build-and-test
      templates:
        - name: build-and-test
changed:
  description: Whether the template was created, updated, or deleted
  returned: always
  type: bool
  sample: true
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.redhat.argocd.plugins.module_utils.argocd_common import (
    argocd_argument_spec,
    ArgocdClient
)


def templates_equal(existing, desired_spec, desired_labels):
    """Compare existing template with desired state"""
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
        state=dict(type='str', choices=['present', 'absent'], default='present'),
        definition=dict(type='dict', required=False),
        labels=dict(type='dict', required=False),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_if=[
            ('state', 'present', ['definition']),
        ]
    )

    client = ArgocdClient(module)

    name = module.params['name']
    state = module.params['state']
    definition = module.params.get('definition')
    labels = module.params.get('labels')

    # Get existing template
    existing = client.get_cluster_workflow_template(name)

    if state == 'absent':
        if not existing:
            module.exit_json(changed=False, msg="Cluster workflow template already absent")

        if module.check_mode:
            module.exit_json(changed=True, msg="Would delete cluster workflow template (check mode)")

        result = client.delete_cluster_workflow_template(name)
        if result:
            module.exit_json(changed=True, msg="Cluster workflow template deleted")
        else:
            module.fail_json(msg="Failed to delete cluster workflow template")

    # state is present
    if existing:
        # Check if update is needed
        if templates_equal(existing, definition, labels):
            module.exit_json(
                changed=False,
                cluster_workflow_template=existing,
                msg="Cluster workflow template already exists with desired state"
            )

        # Update needed
        if module.check_mode:
            module.exit_json(changed=True, msg="Would update cluster workflow template (check mode)")

        # Update the template
        template_body = {
            'apiVersion': 'argoproj.io/v1alpha1',
            'kind': 'ClusterWorkflowTemplate',
            'metadata': {
                'name': name,
                'resourceVersion': existing.get('metadata', {}).get('resourceVersion')
            },
            'spec': definition
        }

        if labels:
            template_body['metadata']['labels'] = labels

        result = client.update_cluster_workflow_template(name, template_body)
        if not result:
            module.fail_json(msg="Failed to update cluster workflow template")

        module.exit_json(
            changed=True,
            cluster_workflow_template=result,
            msg="Cluster workflow template updated"
        )

    # Create new template
    if module.check_mode:
        module.exit_json(changed=True, msg="Would create cluster workflow template (check mode)")

    template_body = {
        'apiVersion': 'argoproj.io/v1alpha1',
        'kind': 'ClusterWorkflowTemplate',
        'metadata': {
            'name': name
        },
        'spec': definition
    }

    if labels:
        template_body['metadata']['labels'] = labels

    result = client.create_cluster_workflow_template(template_body)
    if not result:
        module.fail_json(msg="Failed to create cluster workflow template")

    module.exit_json(
        changed=True,
        cluster_workflow_template=result,
        msg="Cluster workflow template created"
    )


def main():
    run_module()


if __name__ == '__main__':
    main()
