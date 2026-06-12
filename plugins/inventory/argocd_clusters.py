# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright: (c) 2024, Red Hat (@redhat)

"""
ArgoCD clusters dynamic inventory plugin.
"""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
name: argocd_clusters
short_description: ArgoCD clusters dynamic inventory plugin
description:
  - Queries ArgoCD API to discover registered clusters
  - Creates inventory hosts for each cluster
  - Supports grouping by cluster labels, annotations, or status
version_added: "1.0.0"
author:
  - Red Hat (@redhat)
options:
  plugin:
    description:
      - Token that ensures this is a source file for the plugin
    required: true
    choices: ['redhat.argocd.argocd_clusters']
  server_url:
    description:
      - ArgoCD server URL
    required: true
    type: str
  auth_token:
    description:
      - ArgoCD authentication token
    required: true
    type: str
    env:
      - name: ARGOCD_AUTH_TOKEN
  validate_certs:
    description:
      - Whether to validate SSL certificates
    type: bool
    default: true
  group_by:
    description:
      - How to group clusters in inventory
    type: list
    elements: str
    default: []
    choices:
      - labels
      - annotations
      - status
  compose:
    description:
      - Create vars from jinja2 expressions
    type: dict
    default: {}
  groups:
    description:
      - Add hosts to group based on Jinja2 conditionals
    type: dict
    default: {}
  keyed_groups:
    description:
      - Add hosts to group based on the values of a variable
    type: list
    elements: dict
    default: []
  strict:
    description:
      - If true make invalid entries a fatal error, otherwise skip and continue
    type: bool
    default: false
requirements:
  - python >= 3.6
'''

EXAMPLES = r'''
# Full-featured inventory file (argocd.yml)
plugin: redhat.argocd.argocd_clusters
server_url: https://argocd.example.com
auth_token: "{{ lookup('env', 'ARGOCD_AUTH_TOKEN') }}"
group_by:
  - labels
  - status
compose:
  cluster_env: labels.environment | default('unknown')
groups:
  production: labels.environment == 'prod'
  development: labels.environment == 'dev'
keyed_groups:
  - key: labels.region
    prefix: region
'''

from ansible.plugins.inventory import BaseInventoryPlugin, Constructable
from ansible.errors import AnsibleError
from ansible.module_utils.urls import open_url
import json


class InventoryModule(BaseInventoryPlugin, Constructable):
    """ArgoCD clusters dynamic inventory plugin."""

    NAME = 'redhat.argocd.argocd_clusters'

    def verify_file(self, path):
        """
        Verify that the source file is valid for this plugin.

        Args:
            path: Path to inventory source file

        Returns:
            bool: True if valid
        """
        valid = False
        if super(InventoryModule, self).verify_file(path):
            # Check if file contains 'plugin: redhat.argocd.argocd_clusters'
            if path.endswith(('argocd.yml', 'argocd.yaml', 'argocd_clusters.yml', 'argocd_clusters.yaml')):
                valid = True
        return valid

    def parse(self, inventory, loader, path, cache=True):
        """
        Parse inventory source and populate inventory.

        Args:
            inventory: Inventory object to populate
            loader: DataLoader instance
            path: Path to inventory source file
            cache: Whether to use cache
        """
        super(InventoryModule, self).parse(inventory, loader, path, cache)

        # Read and validate config
        self._read_config_data(path)

        # Get plugin configuration
        server_url = self.get_option('server_url')
        auth_token = self.get_option('auth_token')
        validate_certs = self.get_option('validate_certs')
        group_by = self.get_option('group_by') or []
        strict = self.get_option('strict')

        if not server_url:
            raise AnsibleError("server_url is required")
        if not auth_token:
            raise AnsibleError("auth_token is required")

        # Fetch clusters from ArgoCD
        try:
            clusters = self._fetch_clusters(server_url, auth_token, validate_certs)
        except Exception as e:
            raise AnsibleError("Failed to fetch clusters from ArgoCD: {0}".format(str(e)))

        # Populate inventory
        for cluster in clusters:
            self._populate_cluster(cluster, group_by, strict)

    def _fetch_clusters(self, server_url, auth_token, validate_certs):
        """
        Fetch clusters from ArgoCD API.

        Args:
            server_url: ArgoCD server URL
            auth_token: Authentication token
            validate_certs: Whether to validate SSL certificates

        Returns:
            list: List of cluster dictionaries
        """
        url = "{0}/api/v1/clusters".format(server_url.rstrip('/'))

        headers = {
            'Authorization': 'Bearer {0}'.format(auth_token),
            'Content-Type': 'application/json',
        }

        try:
            response = open_url(
                url,
                method='GET',
                headers=headers,
                validate_certs=validate_certs,
            )

            response_text = response.read()
            data = json.loads(response_text)

            # ArgoCD returns clusters under 'items' key
            if isinstance(data, dict) and 'items' in data:
                return data['items']
            elif isinstance(data, list):
                return data
            else:
                raise AnsibleError("Unexpected response format from ArgoCD API")

        except Exception as e:
            raise AnsibleError("API request failed: {0}".format(str(e)))

    def _populate_cluster(self, cluster, group_by, strict):
        """
        Add cluster to inventory.

        Args:
            cluster: Cluster dictionary from API
            group_by: List of grouping strategies
            strict: Whether to fail on errors
        """
        # Extract cluster metadata
        cluster_name = cluster.get('name', 'unknown')
        cluster_server = cluster.get('server', '')
        cluster_labels = cluster.get('labels', {})
        cluster_annotations = cluster.get('annotations', {})
        cluster_info = cluster.get('info', {})
        connection_state = cluster.get('connectionState', {})

        # Use server URL as hostname if name is not available
        if not cluster_name or cluster_name == 'unknown':
            cluster_name = cluster_server.replace('https://', '').replace('http://', '').replace('/', '_')

        # Add host to inventory
        self.inventory.add_host(cluster_name)

        # Set host variables
        self.inventory.set_variable(cluster_name, 'ansible_host', cluster_server)
        self.inventory.set_variable(cluster_name, 'argocd_cluster_name', cluster.get('name', ''))
        self.inventory.set_variable(cluster_name, 'argocd_server', cluster_server)
        self.inventory.set_variable(cluster_name, 'argocd_labels', cluster_labels)
        self.inventory.set_variable(cluster_name, 'argocd_annotations', cluster_annotations)
        self.inventory.set_variable(cluster_name, 'argocd_info', cluster_info)
        self.inventory.set_variable(cluster_name, 'argocd_connection_state', connection_state)

        # Set cluster version and platform info if available
        if cluster_info:
            server_version = cluster_info.get('serverVersion', '')
            platform = cluster_info.get('platform', '')
            if server_version:
                self.inventory.set_variable(cluster_name, 'kubernetes_version', server_version)
            if platform:
                self.inventory.set_variable(cluster_name, 'kubernetes_platform', platform)

        # Group by labels
        if 'labels' in group_by and cluster_labels:
            for key, value in cluster_labels.items():
                group_name = "label_{0}_{1}".format(
                    self._sanitize_group_name(key),
                    self._sanitize_group_name(value)
                )
                self.inventory.add_group(group_name)
                self.inventory.add_child(group_name, cluster_name)

        # Group by annotations
        if 'annotations' in group_by and cluster_annotations:
            for key, value in cluster_annotations.items():
                group_name = "annotation_{0}_{1}".format(
                    self._sanitize_group_name(key),
                    self._sanitize_group_name(value)
                )
                self.inventory.add_group(group_name)
                self.inventory.add_child(group_name, cluster_name)

        # Group by connection status
        if 'status' in group_by and connection_state:
            status = connection_state.get('status', 'unknown')
            group_name = "status_{0}".format(self._sanitize_group_name(status))
            self.inventory.add_group(group_name)
            self.inventory.add_child(group_name, cluster_name)

        # Use constructed features (compose, groups, keyed_groups)
        self._set_composite_vars(
            self.get_option('compose'),
            self.inventory.get_host(cluster_name).get_vars(),
            cluster_name,
            strict
        )

        self._add_host_to_composed_groups(
            self.get_option('groups'),
            {},
            cluster_name,
            strict
        )

        self._add_host_to_keyed_groups(
            self.get_option('keyed_groups'),
            {},
            cluster_name,
            strict
        )

    def _sanitize_group_name(self, name):
        """
        Sanitize group name to be valid for Ansible.

        Args:
            name: Original group name

        Returns:
            str: Sanitized group name
        """
        # Replace invalid characters with underscores
        sanitized = str(name).lower()
        sanitized = ''.join(c if c.isalnum() or c == '_' else '_' for c in sanitized)
        # Remove leading/trailing underscores
        sanitized = sanitized.strip('_')
        # Ensure it doesn't start with a digit
        if sanitized and sanitized[0].isdigit():
            sanitized = 'cluster_' + sanitized
        return sanitized or 'unknown'
