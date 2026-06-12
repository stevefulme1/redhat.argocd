# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for argocd_application module."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import pytest
from unittest.mock import patch, MagicMock
from ansible_collections.redhat.argocd.plugins.modules import argocd_application


class TestArgocdApplication:
    """Test cases for argocd_application module."""

    @patch('ansible_collections.redhat.argocd.plugins.modules.argocd_application.ArgocdClient')
    def test_create_application(self, mock_client_class, module_args, common_args):
        """Test creating a new application."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # get returns None (no existing app)
        mock_client.get.return_value = None

        created_app = {
            'metadata': {'name': 'test-app'},
            'spec': {
                'project': 'default',
                'source': {
                    'repoURL': 'https://github.com/example/repo',
                    'path': 'manifests',
                    'targetRevision': 'HEAD',
                },
                'destination': {
                    'server': 'https://kubernetes.default.svc',
                    'namespace': 'default',
                },
            },
        }
        mock_client.post.return_value = created_app

        args = common_args.copy()
        args.update({
            'name': 'test-app',
            'state': 'present',
            'project': 'default',
            'repo_url': 'https://github.com/example/repo',
            'path': 'manifests',
            'revision': 'HEAD',
            'destination_server': 'https://kubernetes.default.svc',
            'destination_namespace': 'default',
        })
        module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            argocd_application.main()

        assert exc_info.value.code == 0
        mock_client.post.assert_called_once()

    @patch('ansible_collections.redhat.argocd.plugins.modules.argocd_application.ArgocdClient')
    def test_update_application(self, mock_client_class, module_args, common_args):
        """Test updating an existing application."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        existing_app = {
            'metadata': {'name': 'test-app'},
            'spec': {
                'project': 'default',
                'source': {
                    'repoURL': 'https://github.com/example/old-repo',
                    'path': 'old-path',
                    'targetRevision': 'main',
                },
                'destination': {
                    'server': 'https://kubernetes.default.svc',
                    'namespace': 'default',
                },
            },
        }
        mock_client.get.return_value = existing_app

        updated_app = {
            'metadata': {'name': 'test-app'},
            'spec': {
                'project': 'default',
                'source': {
                    'repoURL': 'https://github.com/example/repo',
                    'path': 'manifests',
                    'targetRevision': 'HEAD',
                },
                'destination': {
                    'server': 'https://kubernetes.default.svc',
                    'namespace': 'default',
                },
            },
        }
        mock_client.put.return_value = updated_app

        args = common_args.copy()
        args.update({
            'name': 'test-app',
            'state': 'present',
            'project': 'default',
            'repo_url': 'https://github.com/example/repo',
            'path': 'manifests',
            'revision': 'HEAD',
            'destination_server': 'https://kubernetes.default.svc',
            'destination_namespace': 'default',
        })
        module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            argocd_application.main()

        assert exc_info.value.code == 0
        mock_client.put.assert_called_once()

    @patch('ansible_collections.redhat.argocd.plugins.modules.argocd_application.ArgocdClient')
    def test_delete_application(self, mock_client_class, module_args, common_args):
        """Test deleting an application."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        existing_app = {
            'metadata': {'name': 'test-app'},
            'spec': {'project': 'default'},
        }
        mock_client.get.return_value = existing_app
        mock_client.delete.return_value = None

        args = common_args.copy()
        args.update({
            'name': 'test-app',
            'state': 'absent',
        })
        module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            argocd_application.main()

        assert exc_info.value.code == 0
        mock_client.delete.assert_called_once()

    @patch('ansible_collections.redhat.argocd.plugins.modules.argocd_application.ArgocdClient')
    def test_application_no_change(self, mock_client_class, module_args, common_args):
        """Test no change when application matches desired state."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        existing_app = {
            'metadata': {'name': 'test-app'},
            'spec': {
                'project': 'default',
                'source': {
                    'repoURL': 'https://github.com/example/repo',
                    'path': 'manifests',
                    'targetRevision': 'HEAD',
                },
                'destination': {
                    'server': 'https://kubernetes.default.svc',
                    'namespace': 'default',
                },
            },
        }
        mock_client.get.return_value = existing_app

        args = common_args.copy()
        args.update({
            'name': 'test-app',
            'state': 'present',
            'project': 'default',
            'repo_url': 'https://github.com/example/repo',
            'path': 'manifests',
            'revision': 'HEAD',
            'destination_server': 'https://kubernetes.default.svc',
            'destination_namespace': 'default',
        })
        module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            argocd_application.main()

        assert exc_info.value.code == 0
        mock_client.post.assert_not_called()
        mock_client.put.assert_not_called()

    @patch('ansible_collections.redhat.argocd.plugins.modules.argocd_application.ArgocdClient')
    def test_check_mode_create(self, mock_client_class, module_args, common_args):
        """Test check mode does not make API calls."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.get.return_value = None

        args = common_args.copy()
        args.update({
            'name': 'test-app',
            'state': 'present',
            'project': 'default',
            'repo_url': 'https://github.com/example/repo',
            'path': 'manifests',
            'revision': 'HEAD',
            'destination_server': 'https://kubernetes.default.svc',
            'destination_namespace': 'default',
            '_ansible_check_mode': True,
        })
        module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            argocd_application.main()

        assert exc_info.value.code == 0
        mock_client.post.assert_not_called()
        mock_client.put.assert_not_called()
        mock_client.delete.assert_not_called()

    @patch('ansible_collections.redhat.argocd.plugins.modules.argocd_application.ArgocdClient')
    def test_create_with_sync_policy(self, mock_client_class, module_args, common_args):
        """Test creating application with sync policy."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.get.return_value = None

        created_app = {
            'metadata': {'name': 'test-app'},
            'spec': {
                'project': 'default',
                'source': {
                    'repoURL': 'https://github.com/example/repo',
                    'path': 'manifests',
                    'targetRevision': 'HEAD',
                },
                'destination': {
                    'server': 'https://kubernetes.default.svc',
                    'namespace': 'default',
                },
                'syncPolicy': {
                    'automated': {'prune': True, 'selfHeal': True},
                },
            },
        }
        mock_client.post.return_value = created_app

        args = common_args.copy()
        args.update({
            'name': 'test-app',
            'state': 'present',
            'project': 'default',
            'repo_url': 'https://github.com/example/repo',
            'path': 'manifests',
            'revision': 'HEAD',
            'destination_server': 'https://kubernetes.default.svc',
            'destination_namespace': 'default',
            'sync_policy': {
                'automated': True,
                'prune': True,
                'self_heal': True,
            },
        })
        module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            argocd_application.main()

        assert exc_info.value.code == 0
        mock_client.post.assert_called_once()
