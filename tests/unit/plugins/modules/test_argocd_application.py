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

    @pytest.fixture
    def application_spec(self):
        """Common application specification."""
        return {
            'source': {
                'repoURL': 'https://github.com/example/repo',
                'path': 'manifests',
                'targetRevision': 'HEAD',
            },
            'destination': {
                'server': 'https://kubernetes.default.svc',
                'namespace': 'default',
            },
            'project': 'default',
        }

    @patch('ansible_collections.redhat.argocd.plugins.modules.argocd_application.ArgocdClient')
    def test_create_application(self, mock_client_class, module_args, common_args, application_spec):
        """Test creating a new application."""
        # Arrange
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.get_application.return_value = None

        created_app = {
            'metadata': {'name': 'test-app'},
            'spec': application_spec,
            'status': {'sync': {'status': 'Synced'}},
        }
        mock_client.create_application.return_value = created_app

        args = common_args.copy()
        args.update({
            'name': 'test-app',
            'state': 'present',
            'spec': application_spec,
        })
        module_args(args)

        # Act
        with pytest.raises(SystemExit) as exc_info:
            argocd_application.main()

        # Assert
        assert exc_info.value.code == 0
        mock_client.get_application.assert_called_once_with('test-app')
        mock_client.create_application.assert_called_once()

    @patch('ansible_collections.redhat.argocd.plugins.modules.argocd_application.ArgocdClient')
    def test_update_application(self, mock_client_class, module_args, common_args, application_spec):
        """Test updating an existing application."""
        # Arrange
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        existing_app = {
            'metadata': {'name': 'test-app'},
            'spec': {
                'source': {
                    'repoURL': 'https://github.com/example/old-repo',
                    'path': 'old-path',
                    'targetRevision': 'main',
                },
                'destination': application_spec['destination'],
                'project': 'default',
            },
        }
        mock_client.get_application.return_value = existing_app

        updated_app = {
            'metadata': {'name': 'test-app'},
            'spec': application_spec,
        }
        mock_client.update_application.return_value = updated_app

        args = common_args.copy()
        args.update({
            'name': 'test-app',
            'state': 'present',
            'spec': application_spec,
        })
        module_args(args)

        # Act
        with pytest.raises(SystemExit) as exc_info:
            argocd_application.main()

        # Assert
        assert exc_info.value.code == 0
        mock_client.update_application.assert_called_once()

    @patch('ansible_collections.redhat.argocd.plugins.modules.argocd_application.ArgocdClient')
    def test_delete_application(self, mock_client_class, module_args, common_args, application_spec):
        """Test deleting an application."""
        # Arrange
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        existing_app = {
            'metadata': {'name': 'test-app'},
            'spec': application_spec,
        }
        mock_client.get_application.return_value = existing_app
        mock_client.delete_application.return_value = None

        args = common_args.copy()
        args.update({
            'name': 'test-app',
            'state': 'absent',
        })
        module_args(args)

        # Act
        with pytest.raises(SystemExit) as exc_info:
            argocd_application.main()

        # Assert
        assert exc_info.value.code == 0
        mock_client.delete_application.assert_called_once_with('test-app')

    @patch('ansible_collections.redhat.argocd.plugins.modules.argocd_application.ArgocdClient')
    def test_application_no_change(self, mock_client_class, module_args, common_args, application_spec):
        """Test no change when application matches desired state."""
        # Arrange
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        existing_app = {
            'metadata': {'name': 'test-app'},
            'spec': application_spec,
        }
        mock_client.get_application.return_value = existing_app

        args = common_args.copy()
        args.update({
            'name': 'test-app',
            'state': 'present',
            'spec': application_spec,
        })
        module_args(args)

        # Act
        with pytest.raises(SystemExit) as exc_info:
            argocd_application.main()

        # Assert
        assert exc_info.value.code == 0
        mock_client.create_application.assert_not_called()
        mock_client.update_application.assert_not_called()

    @patch('ansible_collections.redhat.argocd.plugins.modules.argocd_application.ArgocdClient')
    def test_check_mode_create(self, mock_client_class, module_args, common_args, application_spec):
        """Test check mode does not make API calls."""
        # Arrange
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.get_application.return_value = None

        args = common_args.copy()
        args.update({
            'name': 'test-app',
            'state': 'present',
            'spec': application_spec,
            '_ansible_check_mode': True,
        })
        module_args(args)

        # Act
        with pytest.raises(SystemExit) as exc_info:
            argocd_application.main()

        # Assert
        assert exc_info.value.code == 0
        mock_client.create_application.assert_not_called()
        mock_client.update_application.assert_not_called()
        mock_client.delete_application.assert_not_called()

    @pytest.mark.parametrize("sync_policy,expected_automated", [
        ({'automated': {'prune': True, 'selfHeal': True}}, True),
        ({'automated': None}, False),
        ({}, False),
    ])
    @patch('ansible_collections.redhat.argocd.plugins.modules.argocd_application.ArgocdClient')
    def test_sync_policy_variations(self, mock_client_class, module_args, common_args,
                                    application_spec, sync_policy, expected_automated):
        """Test different sync policy configurations."""
        # Arrange
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.get_application.return_value = None

        spec = application_spec.copy()
        spec['syncPolicy'] = sync_policy

        created_app = {
            'metadata': {'name': 'test-app'},
            'spec': spec,
        }
        mock_client.create_application.return_value = created_app

        args = common_args.copy()
        args.update({
            'name': 'test-app',
            'state': 'present',
            'spec': spec,
        })
        module_args(args)

        # Act
        with pytest.raises(SystemExit) as exc_info:
            argocd_application.main()

        # Assert
        assert exc_info.value.code == 0
        mock_client.create_application.assert_called_once()
