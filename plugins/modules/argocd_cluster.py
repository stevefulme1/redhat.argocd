#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright: (c) 2024, Red Hat (@redhat)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: argocd_cluster
short_description: Manage ArgoCD clusters
description:
  - Register, update, or remove Kubernetes clusters in ArgoCD.
  - Clusters are deployment targets for ArgoCD applications.
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
  validate_certs:
    description: Whether to validate SSL certificates.
    type: bool
    default: true
  name:
    description: Cluster name (friendly identifier).
    type: str
    required: true
  server:
    description: Kubernetes API server URL.
    type: str
    required: true
  state:
    description: Desired state of the cluster.
    type: str
    choices: ['present', 'absent']
    default: 'present'
  config:
    description: Cluster connection configuration.
    type: dict
    suboptions:
      bearer_token:
        description: Bearer token for authentication.
        type: str
      tls_client_config:
        description: TLS configuration.
        type: dict
        suboptions:
          insecure:
            description: Skip TLS verification.
            type: bool
          ca_data:
            description: Base64-encoded CA certificate.
            type: str
          cert_data:
            description: Base64-encoded client certificate.
            type: str
          key_data:
            description: Base64-encoded client key.
            type: str
  namespaces:
    description:
      - List of namespaces allowed for deployment.
      - Empty list means all namespaces.
    type: list
    elements: str
  shard:
    description: Shard number for cluster assignment.
    type: int
requirements:
  - "requests>=2.25.0"
author:
  - "Red Hat (@redhat)"
'''

EXAMPLES = r'''
- name: Register cluster with bearer token
  redhat.argocd.argocd_cluster:
    server_url: https://argocd.example.com
    auth_token: "{{ argocd_token }}"
    name: production
    server: https://prod.k8s.example.com
    config:
      bearer_token: "{{ k8s_token }}"
      tls_client_config:
        insecure: false
        ca_data: "{{ ca_cert_base64 }}"
    state: present

- name: Register cluster with namespace restrictions
  redhat.argocd.argocd_cluster:
    server_url: https://argocd.example.com
    auth_token: "{{ argocd_token }}"
    name: staging
    server: https://staging.k8s.example.com
    config:
      bearer_token: "{{ k8s_token }}"
    namespaces:
      - staging
      - staging-apps
    state: present

- name: Register in-cluster
  redhat.argocd.argocd_cluster:
    server_url: https://argocd.example.com
    auth_token: "{{ argocd_token }}"
    name: in-cluster
    server: https://kubernetes.default.svc
    config:
      bearer_token: "{{ serviceaccount_token }}"
      tls_client_config:
        insecure: true
    state: present

- name: Remove cluster
  redhat.argocd.argocd_cluster:
    server_url: https://argocd.example.com
    auth_token: "{{ argocd_token }}"
    name: old-cluster
    server: https://old.k8s.example.com
    state: absent
'''

RETURN = r'''
cluster:
  description: Cluster details.
  type: dict
  returned: always
  sample:
    name: production
    server: https://prod.k8s.example.com
    namespaces:
      - prod
      - prod-apps
    config:
      tlsClientConfig:
        insecure: false
changed:
  description: Whether the cluster was changed.
  type: bool
  returned: always
'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.redhat.argocd.plugins.module_utils.argocd_common import ArgocdClient, argocd_argument_spec


def build_cluster_spec(params):
    """Build cluster specification from module parameters."""
    spec = {
        'name': params['name'],
        'server': params['server']
    }

    if params.get('config'):
        config = {}
        if params['config'].get('bearer_token'):
            config['bearerToken'] = params['config']['bearer_token']

        if params['config'].get('tls_client_config'):
            tls_config = {}
            tls = params['config']['tls_client_config']
            if tls.get('insecure') is not None:
                tls_config['insecure'] = tls['insecure']
            if tls.get('ca_data'):
                tls_config['caData'] = tls['ca_data']
            if tls.get('cert_data'):
                tls_config['certData'] = tls['cert_data']
            if tls.get('key_data'):
                tls_config['keyData'] = tls['key_data']
            if tls_config:
                config['tlsClientConfig'] = tls_config

        if config:
            spec['config'] = config

    if params.get('namespaces'):
        spec['namespaces'] = params['namespaces']

    if params.get('shard') is not None:
        spec['shard'] = params['shard']

    return spec


def clusters_equal(existing, desired):
    """Compare existing and desired cluster specifications."""
    if not existing:
        return False

    # Compare basic fields
    for key in ['name', 'server', 'namespaces', 'shard']:
        if existing.get(key) != desired.get(key):
            return False

    # Compare config (excluding sensitive fields which may be masked)
    existing_config = existing.get('config', {})
    desired_config = desired.get('config', {})

    # Compare TLS config
    existing_tls = existing_config.get('tlsClientConfig', {})
    desired_tls = desired_config.get('tlsClientConfig', {})
    for key in ['insecure', 'caData', 'certData']:
        if existing_tls.get(key) != desired_tls.get(key):
            return False

    # For bearer token and key data, can't compare if masked
    # Conservative approach: if desired has value but existing doesn't, consider changed
    if desired_config.get('bearerToken') and not existing_config.get('bearerToken'):
        return False
    if desired_tls.get('keyData') and not existing_tls.get('keyData'):
        return False

    return True


def run_module():
    argument_spec = argocd_argument_spec()
    argument_spec.update(dict(
        name=dict(type='str', required=True),
        server=dict(type='str', required=True),
        state=dict(type='str', choices=['present', 'absent'], default='present'),
        config=dict(type='dict'),
        namespaces=dict(type='list', elements='str'),
        shard=dict(type='int')
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True
    )

    client = ArgocdClient(module)
    name = module.params['name']
    server = module.params['server']
    state = module.params['state']

    # Get existing cluster
    # ArgoCD API returns list of clusters, need to find by server URL
    clusters_response = client.get('/api/v1/clusters')
    existing = None
    if clusters_response and 'items' in clusters_response:
        for cluster in clusters_response['items']:
            if cluster.get('server') == server:
                existing = cluster
                break

    result = {
        'changed': False,
        'cluster': {}
    }

    if state == 'absent':
        if existing:
            if not module.check_mode:
                # Delete uses server URL as identifier
                client.delete(f'/api/v1/clusters/{server}')
            result['changed'] = True
            result['cluster'] = existing
        module.exit_json(**result)

    # State is 'present'
    desired_spec = build_cluster_spec(module.params)

    if not existing:
        # Create new cluster
        if not module.check_mode:
            result['cluster'] = client.post('/api/v1/clusters', desired_spec)
        else:
            result['cluster'] = desired_spec
        result['changed'] = True
    elif not clusters_equal(existing, desired_spec):
        # Update existing cluster
        payload = existing.copy()
        payload.update(desired_spec)
        if not module.check_mode:
            result['cluster'] = client.put(f'/api/v1/clusters/{server}', payload)
        else:
            result['cluster'] = payload
        result['changed'] = True
    else:
        # No changes needed
        result['cluster'] = existing

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
