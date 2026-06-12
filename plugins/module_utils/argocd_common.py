# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright: (c) 2024, Red Hat (@redhat)

"""
Common utilities for ArgoCD API interactions.
"""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import json
from ansible.module_utils.urls import open_url
from ansible.module_utils.six.moves.urllib.parse import quote, urlencode


class ArgocdClient:
    """Client for interacting with ArgoCD API."""

    def __init__(self, module):
        """
        Initialize ArgoCD client.

        Args:
            module: AnsibleModule instance with params
        """
        self.module = module
        self.server_url = module.params.get('server_url', '').rstrip('/')
        self.auth_token = module.params.get('auth_token')
        self.validate_certs = module.params.get('validate_certs', True)

        if not self.server_url:
            self.module.fail_json(msg="server_url is required")
        if not self.auth_token:
            self.module.fail_json(msg="auth_token is required")

    def _build_url(self, path):
        """
        Construct full API URL.

        Args:
            path: API path (e.g., '/api/v1/applications')

        Returns:
            str: Full URL
        """
        path = path.lstrip('/')
        return "{0}/{1}".format(self.server_url, path)

    def request(self, method, path, data=None, params=None):
        """
        Generic HTTP request to ArgoCD API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            path: API path
            data: Request body (dict, will be JSON-encoded)
            params: Query parameters (dict)

        Returns:
            dict: Parsed JSON response or None for 204
        """
        url = self._build_url(path)
        if params:
            url = "{0}?{1}".format(url, urlencode(params))

        headers = {
            'Authorization': 'Bearer {0}'.format(self.auth_token),
            'Content-Type': 'application/json',
        }

        body = None
        if data is not None:
            body = json.dumps(data)

        try:
            response = open_url(
                url,
                method=method,
                data=body,
                headers=headers,
                validate_certs=self.validate_certs,
            )

            # Handle 204 No Content
            if response.getcode() == 204:
                return None

            response_text = response.read()
            if response_text:
                return json.loads(response_text)
            return None

        except Exception as e:
            error_msg = "API request failed: {0}".format(str(e))
            # Try to extract error details from response
            if hasattr(e, 'read'):
                try:
                    error_body = e.read()
                    error_data = json.loads(error_body)
                    if 'message' in error_data:
                        error_msg = error_data['message']
                    elif 'error' in error_data:
                        error_msg = error_data['error']
                except Exception:
                    pass
            self.module.fail_json(msg=error_msg, path=path, method=method)

    def get(self, path, params=None):
        """
        Perform GET request.

        Args:
            path: API path
            params: Query parameters

        Returns:
            dict: Response data
        """
        return self.request('GET', path, params=params)

    def create(self, path, data):
        """
        Perform POST request.

        Args:
            path: API path
            data: Request body

        Returns:
            dict: Response data
        """
        return self.request('POST', path, data=data)

    def update(self, path, data):
        """
        Perform PUT request.

        Args:
            path: API path
            data: Request body

        Returns:
            dict: Response data
        """
        return self.request('PUT', path, data=data)

    def delete(self, path):
        """
        Perform DELETE request.

        Args:
            path: API path

        Returns:
            dict: Response data or None
        """
        return self.request('DELETE', path)

    def list_resources(self, path, params=None):
        """
        GET request for list endpoints.

        Args:
            path: API path
            params: Query parameters

        Returns:
            list: List of resources
        """
        result = self.get(path, params=params)
        # ArgoCD typically returns lists under 'items' key
        if isinstance(result, dict) and 'items' in result:
            return result['items']
        return result if isinstance(result, list) else []

    # ArgoCD Application methods
    def get_application(self, name, project=None):
        """
        Get ArgoCD application.

        Args:
            name: Application name
            project: Optional project name filter

        Returns:
            dict: Application data or None if not found
        """
        path = "/api/v1/applications/{0}".format(quote(name, safe=''))
        params = {}
        if project:
            params['project'] = project
        try:
            return self.get(path, params=params)
        except Exception:
            return None

    def create_application(self, data):
        """
        Create ArgoCD application.

        Args:
            data: Application specification

        Returns:
            dict: Created application
        """
        return self.create('/api/v1/applications', data)

    def update_application(self, name, data):
        """
        Update ArgoCD application.

        Args:
            name: Application name
            data: Application specification

        Returns:
            dict: Updated application
        """
        path = "/api/v1/applications/{0}".format(quote(name, safe=''))
        return self.update(path, data)

    def delete_application(self, name, cascade=True):
        """
        Delete ArgoCD application.

        Args:
            name: Application name
            cascade: Whether to cascade delete (delete app resources)

        Returns:
            dict: Response data or None
        """
        path = "/api/v1/applications/{0}".format(quote(name, safe=''))
        if cascade:
            path = "{0}?cascade=true".format(path)
        return self.delete(path)

    def sync_application(self, name, revision=None, prune=False, dry_run=False):
        """
        Sync ArgoCD application.

        Args:
            name: Application name
            revision: Target revision
            prune: Whether to prune resources
            dry_run: Whether to perform dry run

        Returns:
            dict: Sync result
        """
        path = "/api/v1/applications/{0}/sync".format(quote(name, safe=''))
        data = {
            'prune': prune,
            'dryRun': dry_run,
        }
        if revision:
            data['revision'] = revision
        return self.create(path, data)

    # ArgoCD Project methods
    def get_project(self, name):
        """
        Get ArgoCD project.

        Args:
            name: Project name

        Returns:
            dict: Project data or None if not found
        """
        path = "/api/v1/projects/{0}".format(quote(name, safe=''))
        try:
            return self.get(path)
        except Exception:
            return None

    def create_project(self, data):
        """
        Create ArgoCD project.

        Args:
            data: Project specification

        Returns:
            dict: Created project
        """
        return self.create('/api/v1/projects', data)

    def update_project(self, name, data):
        """
        Update ArgoCD project.

        Args:
            name: Project name
            data: Project specification

        Returns:
            dict: Updated project
        """
        path = "/api/v1/projects/{0}".format(quote(name, safe=''))
        return self.update(path, data)

    def delete_project(self, name):
        """
        Delete ArgoCD project.

        Args:
            name: Project name

        Returns:
            dict: Response data or None
        """
        path = "/api/v1/projects/{0}".format(quote(name, safe=''))
        return self.delete(path)

    # ArgoCD Repository methods
    def get_repository(self, repo_url):
        """
        Get ArgoCD repository.

        Args:
            repo_url: Repository URL

        Returns:
            dict: Repository data or None if not found
        """
        path = "/api/v1/repositories/{0}".format(quote(repo_url, safe=''))
        try:
            return self.get(path)
        except Exception:
            return None

    def create_repository(self, data):
        """
        Create ArgoCD repository.

        Args:
            data: Repository specification

        Returns:
            dict: Created repository
        """
        return self.create('/api/v1/repositories', data)

    def delete_repository(self, repo_url):
        """
        Delete ArgoCD repository.

        Args:
            repo_url: Repository URL

        Returns:
            dict: Response data or None
        """
        path = "/api/v1/repositories/{0}".format(quote(repo_url, safe=''))
        return self.delete(path)

    # ArgoCD Cluster methods
    def get_cluster(self, server):
        """
        Get ArgoCD cluster.

        Args:
            server: Cluster server URL

        Returns:
            dict: Cluster data or None if not found
        """
        path = "/api/v1/clusters/{0}".format(quote(server, safe=''))
        try:
            return self.get(path)
        except Exception:
            return None

    def create_cluster(self, data):
        """
        Create ArgoCD cluster.

        Args:
            data: Cluster specification

        Returns:
            dict: Created cluster
        """
        return self.create('/api/v1/clusters', data)

    def delete_cluster(self, server):
        """
        Delete ArgoCD cluster.

        Args:
            server: Cluster server URL

        Returns:
            dict: Response data or None
        """
        path = "/api/v1/clusters/{0}".format(quote(server, safe=''))
        return self.delete(path)

    # Argo Workflows methods (Kubernetes API)
    def get_workflow(self, namespace, name):
        """
        Get Argo Workflow.

        Args:
            namespace: Workflow namespace
            name: Workflow name

        Returns:
            dict: Workflow data or None if not found
        """
        path = "/apis/argoproj.io/v1alpha1/namespaces/{0}/workflows/{1}".format(
            quote(namespace, safe=''), quote(name, safe='')
        )
        try:
            return self.get(path)
        except Exception:
            return None

    def create_workflow(self, namespace, data):
        """
        Create Argo Workflow.

        Args:
            namespace: Workflow namespace
            data: Workflow specification

        Returns:
            dict: Created workflow
        """
        path = "/apis/argoproj.io/v1alpha1/namespaces/{0}/workflows".format(
            quote(namespace, safe='')
        )
        return self.create(path, data)

    def delete_workflow(self, namespace, name):
        """
        Delete Argo Workflow.

        Args:
            namespace: Workflow namespace
            name: Workflow name

        Returns:
            dict: Response data or None
        """
        path = "/apis/argoproj.io/v1alpha1/namespaces/{0}/workflows/{1}".format(
            quote(namespace, safe=''), quote(name, safe='')
        )
        return self.delete(path)

    def get_workflow_template(self, namespace, name):
        """
        Get Argo WorkflowTemplate.

        Args:
            namespace: Template namespace
            name: Template name

        Returns:
            dict: Template data or None if not found
        """
        path = "/apis/argoproj.io/v1alpha1/namespaces/{0}/workflowtemplates/{1}".format(
            quote(namespace, safe=''), quote(name, safe='')
        )
        try:
            return self.get(path)
        except Exception:
            return None

    def create_workflow_template(self, namespace, data):
        """
        Create Argo WorkflowTemplate.

        Args:
            namespace: Template namespace
            data: Template specification

        Returns:
            dict: Created template
        """
        path = "/apis/argoproj.io/v1alpha1/namespaces/{0}/workflowtemplates".format(
            quote(namespace, safe='')
        )
        return self.create(path, data)

    def delete_workflow_template(self, namespace, name):
        """
        Delete Argo WorkflowTemplate.

        Args:
            namespace: Template namespace
            name: Template name

        Returns:
            dict: Response data or None
        """
        path = "/apis/argoproj.io/v1alpha1/namespaces/{0}/workflowtemplates/{1}".format(
            quote(namespace, safe=''), quote(name, safe='')
        )
        return self.delete(path)

    def get_cron_workflow(self, namespace, name):
        """
        Get Argo CronWorkflow.

        Args:
            namespace: CronWorkflow namespace
            name: CronWorkflow name

        Returns:
            dict: CronWorkflow data or None if not found
        """
        path = "/apis/argoproj.io/v1alpha1/namespaces/{0}/cronworkflows/{1}".format(
            quote(namespace, safe=''), quote(name, safe='')
        )
        try:
            return self.get(path)
        except Exception:
            return None

    def create_cron_workflow(self, namespace, data):
        """
        Create Argo CronWorkflow.

        Args:
            namespace: CronWorkflow namespace
            data: CronWorkflow specification

        Returns:
            dict: Created CronWorkflow
        """
        path = "/apis/argoproj.io/v1alpha1/namespaces/{0}/cronworkflows".format(
            quote(namespace, safe='')
        )
        return self.create(path, data)

    def delete_cron_workflow(self, namespace, name):
        """
        Delete Argo CronWorkflow.

        Args:
            namespace: CronWorkflow namespace
            name: CronWorkflow name

        Returns:
            dict: Response data or None
        """
        path = "/apis/argoproj.io/v1alpha1/namespaces/{0}/cronworkflows/{1}".format(
            quote(namespace, safe=''), quote(name, safe='')
        )
        return self.delete(path)

    def get_cluster_workflow_template(self, name):
        """
        Get Argo ClusterWorkflowTemplate.

        Args:
            name: Template name

        Returns:
            dict: Template data or None if not found
        """
        path = "/apis/argoproj.io/v1alpha1/clusterworkflowtemplates/{0}".format(
            quote(name, safe='')
        )
        try:
            return self.get(path)
        except Exception:
            return None

    def create_cluster_workflow_template(self, data):
        """
        Create Argo ClusterWorkflowTemplate.

        Args:
            data: Template specification

        Returns:
            dict: Created template
        """
        return self.create('/apis/argoproj.io/v1alpha1/clusterworkflowtemplates', data)

    def delete_cluster_workflow_template(self, name):
        """
        Delete Argo ClusterWorkflowTemplate.

        Args:
            name: Template name

        Returns:
            dict: Response data or None
        """
        path = "/apis/argoproj.io/v1alpha1/clusterworkflowtemplates/{0}".format(
            quote(name, safe='')
        )
        return self.delete(path)

    # Argo Events methods
    def get_event_source(self, namespace, name):
        """
        Get Argo EventSource.

        Args:
            namespace: EventSource namespace
            name: EventSource name

        Returns:
            dict: EventSource data or None if not found
        """
        path = "/apis/argoproj.io/v1alpha1/namespaces/{0}/eventsources/{1}".format(
            quote(namespace, safe=''), quote(name, safe='')
        )
        try:
            return self.get(path)
        except Exception:
            return None

    def create_event_source(self, namespace, data):
        """
        Create Argo EventSource.

        Args:
            namespace: EventSource namespace
            data: EventSource specification

        Returns:
            dict: Created EventSource
        """
        path = "/apis/argoproj.io/v1alpha1/namespaces/{0}/eventsources".format(
            quote(namespace, safe='')
        )
        return self.create(path, data)

    def delete_event_source(self, namespace, name):
        """
        Delete Argo EventSource.

        Args:
            namespace: EventSource namespace
            name: EventSource name

        Returns:
            dict: Response data or None
        """
        path = "/apis/argoproj.io/v1alpha1/namespaces/{0}/eventsources/{1}".format(
            quote(namespace, safe=''), quote(name, safe='')
        )
        return self.delete(path)

    def get_sensor(self, namespace, name):
        """
        Get Argo Sensor.

        Args:
            namespace: Sensor namespace
            name: Sensor name

        Returns:
            dict: Sensor data or None if not found
        """
        path = "/apis/argoproj.io/v1alpha1/namespaces/{0}/sensors/{1}".format(
            quote(namespace, safe=''), quote(name, safe='')
        )
        try:
            return self.get(path)
        except Exception:
            return None

    def create_sensor(self, namespace, data):
        """
        Create Argo Sensor.

        Args:
            namespace: Sensor namespace
            data: Sensor specification

        Returns:
            dict: Created Sensor
        """
        path = "/apis/argoproj.io/v1alpha1/namespaces/{0}/sensors".format(
            quote(namespace, safe='')
        )
        return self.create(path, data)

    def delete_sensor(self, namespace, name):
        """
        Delete Argo Sensor.

        Args:
            namespace: Sensor namespace
            name: Sensor name

        Returns:
            dict: Response data or None
        """
        path = "/apis/argoproj.io/v1alpha1/namespaces/{0}/sensors/{1}".format(
            quote(namespace, safe=''), quote(name, safe='')
        )
        return self.delete(path)

    def get_event_bus(self, namespace, name):
        """
        Get Argo EventBus.

        Args:
            namespace: EventBus namespace
            name: EventBus name

        Returns:
            dict: EventBus data or None if not found
        """
        path = "/apis/argoproj.io/v1alpha1/namespaces/{0}/eventbus/{1}".format(
            quote(namespace, safe=''), quote(name, safe='')
        )
        try:
            return self.get(path)
        except Exception:
            return None

    def create_event_bus(self, namespace, data):
        """
        Create Argo EventBus.

        Args:
            namespace: EventBus namespace
            data: EventBus specification

        Returns:
            dict: Created EventBus
        """
        path = "/apis/argoproj.io/v1alpha1/namespaces/{0}/eventbus".format(
            quote(namespace, safe='')
        )
        return self.create(path, data)

    def delete_event_bus(self, namespace, name):
        """
        Delete Argo EventBus.

        Args:
            namespace: EventBus namespace
            name: EventBus name

        Returns:
            dict: Response data or None
        """
        path = "/apis/argoproj.io/v1alpha1/namespaces/{0}/eventbus/{1}".format(
            quote(namespace, safe=''), quote(name, safe='')
        )
        return self.delete(path)

    # Argo Rollouts methods
    def get_rollout(self, namespace, name):
        """
        Get Argo Rollout.

        Args:
            namespace: Rollout namespace
            name: Rollout name

        Returns:
            dict: Rollout data or None if not found
        """
        path = "/apis/argoproj.io/v1alpha1/namespaces/{0}/rollouts/{1}".format(
            quote(namespace, safe=''), quote(name, safe='')
        )
        try:
            return self.get(path)
        except Exception:
            return None

    def create_rollout(self, namespace, data):
        """
        Create Argo Rollout.

        Args:
            namespace: Rollout namespace
            data: Rollout specification

        Returns:
            dict: Created Rollout
        """
        path = "/apis/argoproj.io/v1alpha1/namespaces/{0}/rollouts".format(
            quote(namespace, safe='')
        )
        return self.create(path, data)

    def delete_rollout(self, namespace, name):
        """
        Delete Argo Rollout.

        Args:
            namespace: Rollout namespace
            name: Rollout name

        Returns:
            dict: Response data or None
        """
        path = "/apis/argoproj.io/v1alpha1/namespaces/{0}/rollouts/{1}".format(
            quote(namespace, safe=''), quote(name, safe='')
        )
        return self.delete(path)

    def get_analysis_template(self, namespace, name):
        """
        Get Argo AnalysisTemplate.

        Args:
            namespace: Template namespace
            name: Template name

        Returns:
            dict: Template data or None if not found
        """
        path = "/apis/argoproj.io/v1alpha1/namespaces/{0}/analysistemplates/{1}".format(
            quote(namespace, safe=''), quote(name, safe='')
        )
        try:
            return self.get(path)
        except Exception:
            return None

    def create_analysis_template(self, namespace, data):
        """
        Create Argo AnalysisTemplate.

        Args:
            namespace: Template namespace
            data: Template specification

        Returns:
            dict: Created template
        """
        path = "/apis/argoproj.io/v1alpha1/namespaces/{0}/analysistemplates".format(
            quote(namespace, safe='')
        )
        return self.create(path, data)

    def delete_analysis_template(self, namespace, name):
        """
        Delete Argo AnalysisTemplate.

        Args:
            namespace: Template namespace
            name: Template name

        Returns:
            dict: Response data or None
        """
        path = "/apis/argoproj.io/v1alpha1/namespaces/{0}/analysistemplates/{1}".format(
            quote(namespace, safe=''), quote(name, safe='')
        )
        return self.delete(path)

    def get_experiment(self, namespace, name):
        """
        Get Argo Experiment.

        Args:
            namespace: Experiment namespace
            name: Experiment name

        Returns:
            dict: Experiment data or None if not found
        """
        path = "/apis/argoproj.io/v1alpha1/namespaces/{0}/experiments/{1}".format(
            quote(namespace, safe=''), quote(name, safe='')
        )
        try:
            return self.get(path)
        except Exception:
            return None

    def create_experiment(self, namespace, data):
        """
        Create Argo Experiment.

        Args:
            namespace: Experiment namespace
            data: Experiment specification

        Returns:
            dict: Created Experiment
        """
        path = "/apis/argoproj.io/v1alpha1/namespaces/{0}/experiments".format(
            quote(namespace, safe='')
        )
        return self.create(path, data)

    def delete_experiment(self, namespace, name):
        """
        Delete Argo Experiment.

        Args:
            namespace: Experiment namespace
            name: Experiment name

        Returns:
            dict: Response data or None
        """
        path = "/apis/argoproj.io/v1alpha1/namespaces/{0}/experiments/{1}".format(
            quote(namespace, safe=''), quote(name, safe='')
        )
        return self.delete(path)


def argocd_argument_spec():
    """
    Return common ArgoCD argument spec for modules.

    Returns:
        dict: Argument specification
    """
    return dict(
        server_url=dict(type='str', required=True),
        auth_token=dict(type='str', required=True, no_log=True),
        validate_certs=dict(type='bool', default=True),
    )
