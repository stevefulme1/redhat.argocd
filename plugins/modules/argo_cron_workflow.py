#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: argo_cron_workflow
short_description: Manage Argo Cron Workflows
description:
  - Create, update, delete, suspend, or resume Argo Cron Workflows
  - Cron workflows run on a schedule defined by cron expressions
  - Supports check mode for validation
version_added: "0.1.0"
author:
  - Red Hat Ansible Automation Platform Team
options:
  name:
    description:
      - Name of the cron workflow
    type: str
    required: true
  namespace:
    description:
      - Kubernetes namespace where the cron workflow resides
    type: str
    required: true
  state:
    description:
      - Desired state of the cron workflow
      - C(present) ensures cron workflow exists
      - C(absent) ensures cron workflow is deleted
      - C(suspended) suspends the cron workflow schedule
      - C(resumed) resumes the cron workflow schedule
    type: str
    choices: ['present', 'absent', 'suspended', 'resumed']
    default: present
  schedule:
    description:
      - Cron expression defining when the workflow runs
      - Required when creating a new cron workflow
    type: str
    required: false
  timezone:
    description:
      - Timezone for the cron schedule
      - Defaults to UTC if not specified
    type: str
    required: false
  concurrency_policy:
    description:
      - How to handle concurrent workflow executions
      - C(Allow) - allow concurrent executions
      - C(Forbid) - skip new execution if previous is still running
      - C(Replace) - cancel previous execution and start new one
    type: str
    choices: ['Allow', 'Forbid', 'Replace']
    default: Allow
  starting_deadline_seconds:
    description:
      - Deadline in seconds for starting the workflow if it misses scheduled time
      - If exceeded, the workflow execution is skipped
    type: int
    required: false
  definition:
    description:
      - Workflow specification that will be executed on schedule
      - Required when state is present
    type: dict
    required: false
  labels:
    description:
      - Labels to apply to the cron workflow
    type: dict
    required: false
requirements:
  - requests
notes:
  - Check mode is supported
  - state=suspended and state=resumed only toggle the suspend flag
'''

EXAMPLES = r'''
- name: Create cron workflow running daily
  redhat.argocd.argo_cron_workflow:
    server_url: https://argo.example.com
    auth_token: "{{ argo_token }}"
    name: daily-backup
    namespace: argo
    state: present
    schedule: "0 2 * * *"
    timezone: America/New_York
    concurrency_policy: Forbid
    definition:
      entrypoint: backup
      templates:
        - name: backup
          container:
            image: backup-tool:latest
            command: ["/backup.sh"]
    labels:
      app: backup

- name: Suspend cron workflow
  redhat.argocd.argo_cron_workflow:
    server_url: https://argo.example.com
    auth_token: "{{ argo_token }}"
    name: daily-backup
    namespace: argo
    state: suspended
'''

RETURN = r'''
cron_workflow:
  description: The cron workflow object
  returned: when state is present, suspended, or resumed
  type: dict
  sample:
    metadata:
      name: daily-backup
      namespace: argo
    spec:
      schedule: "0 2 * * *"
      suspend: false
      workflowSpec:
        entrypoint: backup
changed:
  description: Whether the cron workflow was created, updated, deleted, suspended, or resumed
  returned: always
  type: bool
  sample: true
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.redhat.argocd.plugins.module_utils.argocd_common import (
    argocd_argument_spec,
    ArgocdClient
)


def cron_workflows_equal(existing, desired_spec, desired_labels, schedule, timezone, concurrency_policy, starting_deadline_seconds):
    """Compare existing cron workflow with desired state"""
    existing_spec = existing.get('spec', {})

    if schedule and existing_spec.get('schedule') != schedule:
        return False

    if timezone and existing_spec.get('timezone') != timezone:
        return False

    if concurrency_policy and existing_spec.get('concurrencyPolicy') != concurrency_policy:
        return False

    if starting_deadline_seconds is not None:
        if existing_spec.get('startingDeadlineSeconds') != starting_deadline_seconds:
            return False

    if desired_spec:
        existing_workflow_spec = existing_spec.get('workflowSpec', {})
        if existing_workflow_spec != desired_spec:
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
        state=dict(type='str', choices=['present', 'absent', 'suspended', 'resumed'], default='present'),
        schedule=dict(type='str', required=False),
        timezone=dict(type='str', required=False),
        concurrency_policy=dict(type='str', choices=['Allow', 'Forbid', 'Replace'], default='Allow'),
        starting_deadline_seconds=dict(type='int', required=False),
        definition=dict(type='dict', required=False),
        labels=dict(type='dict', required=False),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_if=[
            ('state', 'present', ['schedule', 'definition']),
        ]
    )

    client = ArgocdClient(module)

    name = module.params['name']
    namespace = module.params['namespace']
    state = module.params['state']
    schedule = module.params.get('schedule')
    timezone = module.params.get('timezone')
    concurrency_policy = module.params['concurrency_policy']
    starting_deadline_seconds = module.params.get('starting_deadline_seconds')
    definition = module.params.get('definition')
    labels = module.params.get('labels')

    # Get existing cron workflow
    existing = client.get_cron_workflow(name, namespace)

    if state == 'absent':
        if not existing:
            module.exit_json(changed=False, msg="Cron workflow already absent")

        if module.check_mode:
            module.exit_json(changed=True, msg="Would delete cron workflow (check mode)")

        result = client.delete_cron_workflow(name, namespace)
        if result:
            module.exit_json(changed=True, msg="Cron workflow deleted")
        else:
            module.fail_json(msg="Failed to delete cron workflow")

    # Handle suspend/resume
    if state in ['suspended', 'resumed']:
        if not existing:
            module.fail_json(msg=f"Cannot {state} non-existent cron workflow")

        current_suspend = existing.get('spec', {}).get('suspend', False)
        desired_suspend = (state == 'suspended')

        if current_suspend == desired_suspend:
            module.exit_json(
                changed=False,
                cron_workflow=existing,
                msg=f"Cron workflow already {state}"
            )

        if module.check_mode:
            module.exit_json(changed=True, msg=f"Would {state.replace('ed', 'e')} cron workflow (check mode)")

        # Update suspend field
        existing['spec']['suspend'] = desired_suspend
        result = client.update_cron_workflow(name, namespace, existing)
        if not result:
            module.fail_json(msg=f"Failed to {state.replace('ed', 'e')} cron workflow")

        module.exit_json(
            changed=True,
            cron_workflow=result,
            msg=f"Cron workflow {state}"
        )

    # state is present
    if existing:
        # Check if update is needed
        if cron_workflows_equal(existing, definition, labels, schedule, timezone, concurrency_policy, starting_deadline_seconds):
            module.exit_json(
                changed=False,
                cron_workflow=existing,
                msg="Cron workflow already exists with desired state"
            )

        # Update needed
        if module.check_mode:
            module.exit_json(changed=True, msg="Would update cron workflow (check mode)")

        # Build updated spec
        cron_spec = {
            'schedule': schedule,
            'concurrencyPolicy': concurrency_policy,
            'workflowSpec': definition
        }

        if timezone:
            cron_spec['timezone'] = timezone

        if starting_deadline_seconds is not None:
            cron_spec['startingDeadlineSeconds'] = starting_deadline_seconds

        # Preserve suspend state if not explicitly changing it
        if 'suspend' in existing.get('spec', {}):
            cron_spec['suspend'] = existing['spec']['suspend']

        cron_body = {
            'apiVersion': 'argoproj.io/v1alpha1',
            'kind': 'CronWorkflow',
            'metadata': {
                'name': name,
                'namespace': namespace,
                'resourceVersion': existing.get('metadata', {}).get('resourceVersion')
            },
            'spec': cron_spec
        }

        if labels:
            cron_body['metadata']['labels'] = labels

        result = client.update_cron_workflow(name, namespace, cron_body)
        if not result:
            module.fail_json(msg="Failed to update cron workflow")

        module.exit_json(
            changed=True,
            cron_workflow=result,
            msg="Cron workflow updated"
        )

    # Create new cron workflow
    if module.check_mode:
        module.exit_json(changed=True, msg="Would create cron workflow (check mode)")

    cron_spec = {
        'schedule': schedule,
        'concurrencyPolicy': concurrency_policy,
        'workflowSpec': definition
    }

    if timezone:
        cron_spec['timezone'] = timezone

    if starting_deadline_seconds is not None:
        cron_spec['startingDeadlineSeconds'] = starting_deadline_seconds

    cron_body = {
        'apiVersion': 'argoproj.io/v1alpha1',
        'kind': 'CronWorkflow',
        'metadata': {
            'name': name,
            'namespace': namespace
        },
        'spec': cron_spec
    }

    if labels:
        cron_body['metadata']['labels'] = labels

    result = client.create_cron_workflow(namespace, cron_body)
    if not result:
        module.fail_json(msg="Failed to create cron workflow")

    module.exit_json(
        changed=True,
        cron_workflow=result,
        msg="Cron workflow created"
    )


def main():
    run_module()


if __name__ == '__main__':
    main()
