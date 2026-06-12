#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: argo_workflow_template
short_description: Manage Argo Workflow Templates
description:
  - Create, update, or delete Argo Workflow Templates
  - Workflow templates are reusable workflow definitions
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
      - Name of the workflow template
    type: str
    required: true
  namespace:
    description:
      - Kubernetes namespace where the workflow template resides
    type: str
    required: true
  state:
    description:
      - Desired state of the workflow template
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
      - Labels to apply to the workflow template
    type: dict
    required: false
requirements:
  - requests
notes:
  - Check mode is supported
  - Templates can be referenced by workflows for reuse
'''

EXAMPLES = r'''
- name: Create workflow template
  redhat.argocd.argo_workflow_template:
    server_url: https://argo.example.com
    auth_token: "{{ argo_token }}"
    name: common-steps
    namespace: argo
    state: present
    definition:
      entrypoint: main
      templates:
        - name: main
          steps:
            - - name: checkout
                template: git-clone
            - - name: build
                template: build-image
        - name: git-clone
          container:
            image: alpine/git
            command: [git, clone]
            args: ["https://github.com/example/repo.git"]
        - name: build-image
          container:
            image: gcr.io/kaniko-project/executor
            args: ["--context=/workspace", "--dockerfile=Dockerfile"]
    labels:
      category: cicd

- name: Delete workflow template
  redhat.argocd.argo_workflow_template:
    server_url: https://argo.example.com
    auth_token: "{{ argo_token }}"
    name: old-template
    namespace: argo
    state: absent
'''

RETURN = r'''
workflow_template:
  description: The workflow template object
  returned: when state is present
  type: dict
  sample:
    metadata:
      name: common-steps
      namespace: argo
    spec:
      entrypoint: main
      templates:
        - name: main
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
        namespace=dict(type='str', required=True),
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
    namespace = module.params['namespace']
    state = module.params['state']
    definition = module.params.get('definition')
    labels = module.params.get('labels')

    # Get existing template
    existing = client.get_workflow_template(namespace, name)

    if state == 'absent':
        if not existing:
            module.exit_json(changed=False, msg="Workflow template already absent")

        if module.check_mode:
            module.exit_json(changed=True, msg="Would delete workflow template (check mode)")

        result = client.delete_workflow_template(namespace, name)
        if result:
            module.exit_json(changed=True, msg="Workflow template deleted")
        else:
            module.fail_json(msg="Failed to delete workflow template")

    # state is present
    if existing:
        # Check if update is needed
        if templates_equal(existing, definition, labels):
            module.exit_json(
                changed=False,
                workflow_template=existing,
                msg="Workflow template already exists with desired state"
            )

        # Update needed
        if module.check_mode:
            module.exit_json(changed=True, msg="Would update workflow template (check mode)")

        # Update the template
        template_body = {
            'apiVersion': 'argoproj.io/v1alpha1',
            'kind': 'WorkflowTemplate',
            'metadata': {
                'name': name,
                'namespace': namespace,
                'resourceVersion': existing.get('metadata', {}).get('resourceVersion')
            },
            'spec': definition
        }

        if labels:
            template_body['metadata']['labels'] = labels

        result = client.update_workflow_template(name, namespace, template_body)
        if not result:
            module.fail_json(msg="Failed to update workflow template")

        module.exit_json(
            changed=True,
            workflow_template=result,
            msg="Workflow template updated"
        )

    # Create new template
    if module.check_mode:
        module.exit_json(changed=True, msg="Would create workflow template (check mode)")

    template_body = {
        'apiVersion': 'argoproj.io/v1alpha1',
        'kind': 'WorkflowTemplate',
        'metadata': {
            'name': name,
            'namespace': namespace
        },
        'spec': definition
    }

    if labels:
        template_body['metadata']['labels'] = labels

    result = client.create_workflow_template(namespace, template_body)
    if not result:
        module.fail_json(msg="Failed to create workflow template")

    module.exit_json(
        changed=True,
        workflow_template=result,
        msg="Workflow template created"
    )


def main():
    run_module()


if __name__ == '__main__':
    main()
