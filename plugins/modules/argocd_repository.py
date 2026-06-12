#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright: (c) 2024, Red Hat (@redhat)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: argocd_repository
short_description: Manage ArgoCD repositories
description:
  - Add, update, or remove repository credentials in ArgoCD.
  - Supports Git and Helm repositories.
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
  repo_url:
    description: Repository URL.
    type: str
    required: true
  state:
    description: Desired state of the repository.
    type: str
    choices: ['present', 'absent']
    default: 'present'
  type:
    description: Repository type.
    type: str
    choices: ['git', 'helm']
    default: 'git'
  username:
    description: Username for repository authentication.
    type: str
  password:
    description: Password for repository authentication.
    type: str
    no_log: true
  ssh_private_key:
    description: SSH private key for Git repository authentication.
    type: str
    no_log: true
  insecure:
    description: Skip server certificate verification.
    type: bool
    default: false
  name:
    description: Repository name (for Helm repositories).
    type: str
requirements:
  - "requests>=2.25.0"
author:
  - "Red Hat (@redhat)"
'''

EXAMPLES = r'''
- name: Add Git repository with HTTPS auth
  redhat.argocd.argocd_repository:
    server_url: https://argocd.example.com
    auth_token: "{{ argocd_token }}"
    repo_url: https://github.com/example/repo.git
    type: git
    username: myuser
    password: "{{ github_token }}"
    state: present

- name: Add Git repository with SSH key
  redhat.argocd.argocd_repository:
    server_url: https://argocd.example.com
    auth_token: "{{ argocd_token }}"
    repo_url: git@github.com:example/repo.git
    type: git
    ssh_private_key: "{{ lookup('file', '~/.ssh/id_rsa') }}"
    state: present

- name: Add Helm repository
  redhat.argocd.argocd_repository:
    server_url: https://argocd.example.com
    auth_token: "{{ argocd_token }}"
    repo_url: https://charts.example.com
    type: helm
    name: my-charts
    username: chartuser
    password: "{{ chart_password }}"
    state: present

- name: Add insecure repository
  redhat.argocd.argocd_repository:
    server_url: https://argocd.example.com
    auth_token: "{{ argocd_token }}"
    repo_url: https://internal-git.example.com/repo.git
    insecure: true
    state: present

- name: Remove repository
  redhat.argocd.argocd_repository:
    server_url: https://argocd.example.com
    auth_token: "{{ argocd_token }}"
    repo_url: https://github.com/example/old-repo.git
    state: absent
'''

RETURN = r'''
repository:
  description: Repository details.
  type: dict
  returned: always
  sample:
    repo: https://github.com/example/repo.git
    type: git
    name: ''
    insecure: false
changed:
  description: Whether the repository was changed.
  type: bool
  returned: always
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.redhat.argocd.plugins.module_utils.argocd_common import ArgocdClient, argocd_argument_spec


def build_repository_spec(params):
    """Build repository specification from module parameters."""
    spec = {
        'repo': params['repo_url'],
        'type': params['type']
    }

    if params.get('name'):
        spec['name'] = params['name']

    if params.get('username'):
        spec['username'] = params['username']

    if params.get('password'):
        spec['password'] = params['password']

    if params.get('ssh_private_key'):
        spec['sshPrivateKey'] = params['ssh_private_key']

    if params.get('insecure'):
        spec['insecure'] = params['insecure']

    return spec


def repositories_equal(existing, desired):
    """Compare existing and desired repository specifications."""
    if not existing:
        return False

    # Compare non-sensitive fields
    for key in ['repo', 'type', 'name', 'username', 'insecure']:
        if existing.get(key) != desired.get(key):
            return False

    # For sensitive fields (password, sshPrivateKey), we can't compare directly
    # If they're provided in desired but not in existing (masked), consider changed
    # This is conservative but safer for idempotency
    if desired.get('password') and not existing.get('password'):
        return False
    if desired.get('sshPrivateKey') and not existing.get('sshPrivateKey'):
        return False

    return True


def run_module():
    argument_spec = argocd_argument_spec()
    argument_spec.update(dict(
        repo_url=dict(type='str', required=True),
        state=dict(type='str', choices=['present', 'absent'], default='present'),
        type=dict(type='str', choices=['git', 'helm'], default='git'),
        username=dict(type='str'),
        password=dict(type='str', no_log=True),
        ssh_private_key=dict(type='str', no_log=True),
        insecure=dict(type='bool', default=False),
        name=dict(type='str')
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        mutually_exclusive=[
            ['password', 'ssh_private_key']
        ]
    )

    client = ArgocdClient(module)
    repo_url = module.params['repo_url']
    state = module.params['state']

    # Get existing repository
    # ArgoCD API returns list of repos, need to find by URL
    repos_response = client.get('/api/v1/repositories')
    existing = None
    if repos_response and 'items' in repos_response:
        for repo in repos_response['items']:
            if repo.get('repo') == repo_url:
                existing = repo
                break

    result = {
        'changed': False,
        'repository': {}
    }

    if state == 'absent':
        if existing:
            if not module.check_mode:
                # Delete uses repo URL as identifier
                client.delete(f'/api/v1/repositories/{repo_url}')
            result['changed'] = True
            result['repository'] = existing
        module.exit_json(**result)

    # State is 'present'
    desired_spec = build_repository_spec(module.params)

    if not existing:
        # Create new repository
        if not module.check_mode:
            result['repository'] = client.post('/api/v1/repositories', desired_spec)
        else:
            result['repository'] = desired_spec
        result['changed'] = True
    elif not repositories_equal(existing, desired_spec):
        # Update existing repository
        if not module.check_mode:
            result['repository'] = client.put(f'/api/v1/repositories/{repo_url}', desired_spec)
        else:
            result['repository'] = desired_spec
        result['changed'] = True
    else:
        # No changes needed
        result['repository'] = existing

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
