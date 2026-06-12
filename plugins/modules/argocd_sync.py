#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: argocd_sync
short_description: Trigger ArgoCD application sync
description:
  - Trigger synchronization of an ArgoCD application
  - Optionally wait for sync to complete
  - Supports check mode for dry-run validation
version_added: "0.1.0"
author:
  - Red Hat Ansible Automation Platform Team
options:
  name:
    description:
      - Name of the ArgoCD application to sync
    type: str
    required: true
  revision:
    description:
      - Git revision to sync to (commit SHA, branch, or tag)
      - If not specified, syncs to the revision defined in the application
    type: str
    required: false
  prune:
    description:
      - Whether to delete resources that are no longer tracked in git
    type: bool
    default: false
  dry_run:
    description:
      - Perform a dry-run sync without actually applying changes
    type: bool
    default: false
  force:
    description:
      - Force sync even if application is already in sync
    type: bool
    default: false
  strategy:
    description:
      - Sync strategy to use
    type: str
    choices: ['apply', 'hook']
    default: apply
  timeout:
    description:
      - Maximum time in seconds to wait for sync to complete
      - Only applies when wait is true
    type: int
    default: 300
  wait:
    description:
      - Wait for sync operation to complete before returning
    type: bool
    default: true
requirements:
  - requests
notes:
  - Check mode is supported
'''

EXAMPLES = r'''
- name: Sync application to latest revision
  redhat.argocd.argocd_sync:
    server_url: https://argocd.example.com
    auth_token: "{{ argocd_token }}"
    name: my-app
    wait: true
    timeout: 600

- name: Force sync with prune and specific revision
  redhat.argocd.argocd_sync:
    server_url: https://argocd.example.com
    auth_token: "{{ argocd_token }}"
    name: production-app
    revision: v1.2.3
    prune: true
    force: true
    strategy: hook
    validate_certs: false
'''

RETURN = r'''
sync_result:
  description: Details of the sync operation
  returned: success
  type: dict
  sample:
    operation_state:
      phase: Succeeded
      message: "successfully synced (all tasks run)"
      started_at: "2026-06-12T10:00:00Z"
      finished_at: "2026-06-12T10:02:30Z"
    sync:
      revision: abc123def456
      status: Synced
status:
  description: Final sync status
  returned: success
  type: str
  sample: Synced
changed:
  description: Whether the sync operation changed the application state
  returned: always
  type: bool
  sample: true
'''

import time
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.redhat.argocd.plugins.module_utils.argocd_common import (
    argocd_argument_spec,
    ArgocdClient
)


def wait_for_sync(client, app_name, timeout):
    """Wait for sync operation to complete"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        app = client.get_application(app_name)
        if not app:
            return None, "Application not found"

        operation_state = app.get('status', {}).get('operationState', {})
        phase = operation_state.get('phase', '')

        if phase in ['Succeeded', 'Failed', 'Error']:
            return app, phase

        time.sleep(5)

    return None, "Timeout"


def run_module():
    argument_spec = argocd_argument_spec()
    argument_spec.update(
        name=dict(type='str', required=True),
        revision=dict(type='str', required=False),
        prune=dict(type='bool', default=False),
        dry_run=dict(type='bool', default=False),
        force=dict(type='bool', default=False),
        strategy=dict(type='str', choices=['apply', 'hook'], default='apply'),
        timeout=dict(type='int', default=300),
        wait=dict(type='bool', default=True),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True
    )

    client = ArgocdClient(module)

    name = module.params['name']
    revision = module.params.get('revision')
    prune = module.params['prune']
    dry_run = module.params['dry_run']
    force = module.params['force']
    strategy = module.params['strategy']
    timeout = module.params['timeout']
    wait = module.params['wait']

    # Get current application state
    app = client.get_application(name)
    if not app:
        module.fail_json(msg=f"Application {name} not found")

    # Check if already in sync
    sync_status = app.get('status', {}).get('sync', {}).get('status', '')
    if sync_status == 'Synced' and not force:
        module.exit_json(
            changed=False,
            sync_result=app.get('status', {}),
            status=sync_status,
            msg="Application already in sync"
        )

    if module.check_mode:
        module.exit_json(
            changed=True,
            msg="Would trigger sync operation (check mode)"
        )

    # Trigger sync
    sync_request = {
        'prune': prune,
        'dryRun': dry_run,
        'strategy': {'apply': {} if strategy == 'apply' else {'hook': {}}}
    }
    if revision:
        sync_request['revision'] = revision

    result = client.sync_application(name, sync_request)
    if not result:
        module.fail_json(msg="Failed to trigger sync operation")

    changed = True
    final_status = 'Syncing'

    # Wait for sync to complete if requested
    if wait and not dry_run:
        final_app, phase = wait_for_sync(client, name, timeout)
        if final_app:
            result = final_app.get('status', {})
            final_status = result.get('sync', {}).get('status', phase)
            if phase == 'Failed' or phase == 'Error':
                module.fail_json(
                    msg=f"Sync operation failed: {phase}",
                    sync_result=result,
                    status=final_status
                )
        else:
            module.fail_json(
                msg=f"Sync operation did not complete within {timeout} seconds: {phase}",
                sync_result=result,
                status=final_status
            )
    else:
        # Get updated status without waiting
        updated_app = client.get_application(name)
        if updated_app:
            result = updated_app.get('status', {})
            final_status = result.get('sync', {}).get('status', 'Syncing')

    module.exit_json(
        changed=changed,
        sync_result=result,
        status=final_status
    )


def main():
    run_module()


if __name__ == '__main__':
    main()
