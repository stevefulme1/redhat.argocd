# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for argocd_sync module."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import pytest
from unittest.mock import patch, MagicMock, call
from ansible_collections.redhat.argocd.plugins.modules import argocd_sync


class TestArgocdSync:
    """Test cases for argocd_sync module."""

    @patch('ansible_collections.redhat.argocd.plugins.modules.argocd_sync.ArgocdClient')
    @patch('ansible_collections.redhat.argocd.plugins.modules.argocd_sync.time.sleep')
    def test_sync_application(self, mock_sleep, mock_client_class, module_args, common_args):
        """Test syncing an application."""
        # Arrange
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        sync_result = {
            'status': 'Succeeded',
            'message': 'Sync operation completed',
        }
        mock_client.sync_application.return_value = sync_result

        args = common_args.copy()
        args.update({
            'name': 'test-app',
            'revision': 'HEAD',
            'prune': False,
            'dry_run': False,
            'wait': False,
        })
        module_args(args)

        # Act
        with pytest.raises(SystemExit) as exc_info:
            argocd_sync.main()

        # Assert
        assert exc_info.value.code == 0
        mock_client.sync_application.assert_called_once_with(
            name='test-app',
            revision='HEAD',
            prune=False,
            dry_run=False,
        )
        mock_sleep.assert_not_called()

    @patch('ansible_collections.redhat.argocd.plugins.modules.argocd_sync.ArgocdClient')
    @patch('ansible_collections.redhat.argocd.plugins.modules.argocd_sync.time.sleep')
    def test_sync_with_wait(self, mock_sleep, mock_client_class, module_args, common_args):
        """Test syncing with wait for completion."""
        # Arrange
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        sync_result = {
            'status': 'Running',
            'message': 'Sync in progress',
        }
        mock_client.sync_application.return_value = sync_result

        # Simulate sync status progression
        mock_client.get_application_sync_status.side_effect = [
            {'status': 'Syncing', 'health': {'status': 'Progressing'}},
            {'status': 'Syncing', 'health': {'status': 'Progressing'}},
            {'status': 'Synced', 'health': {'status': 'Healthy'}},
        ]

        args = common_args.copy()
        args.update({
            'name': 'test-app',
            'revision': 'main',
            'wait': True,
            'wait_timeout': 300,
            'prune': True,
            'dry_run': False,
        })
        module_args(args)

        # Act
        with pytest.raises(SystemExit) as exc_info:
            argocd_sync.main()

        # Assert
        assert exc_info.value.code == 0
        mock_client.sync_application.assert_called_once()
        assert mock_client.get_application_sync_status.call_count == 3
        assert mock_sleep.call_count == 2

    @patch('ansible_collections.redhat.argocd.plugins.modules.argocd_sync.ArgocdClient')
    def test_sync_dry_run(self, mock_client_class, module_args, common_args):
        """Test sync with dry_run enabled."""
        # Arrange
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        dry_run_result = {
            'status': 'DryRun',
            'message': 'Dry run completed',
            'resources': ['deployment/app', 'service/app'],
        }
        mock_client.sync_application.return_value = dry_run_result

        args = common_args.copy()
        args.update({
            'name': 'test-app',
            'revision': 'feature-branch',
            'dry_run': True,
            'prune': False,
            'wait': False,
        })
        module_args(args)

        # Act
        with pytest.raises(SystemExit) as exc_info:
            argocd_sync.main()

        # Assert
        assert exc_info.value.code == 0
        mock_client.sync_application.assert_called_once_with(
            name='test-app',
            revision='feature-branch',
            prune=False,
            dry_run=True,
        )

    @patch('ansible_collections.redhat.argocd.plugins.modules.argocd_sync.ArgocdClient')
    def test_check_mode(self, mock_client_class, module_args, common_args):
        """Test check mode does not perform sync."""
        # Arrange
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        args = common_args.copy()
        args.update({
            'name': 'test-app',
            'revision': 'HEAD',
            'prune': False,
            'dry_run': False,
            'wait': False,
            '_ansible_check_mode': True,
        })
        module_args(args)

        # Act
        with pytest.raises(SystemExit) as exc_info:
            argocd_sync.main()

        # Assert
        assert exc_info.value.code == 0
        mock_client.sync_application.assert_not_called()
        mock_client.get_application_sync_status.assert_not_called()

    @pytest.mark.parametrize("prune,expected_prune", [
        (True, True),
        (False, False),
    ])
    @patch('ansible_collections.redhat.argocd.plugins.modules.argocd_sync.ArgocdClient')
    def test_sync_with_prune_variations(self, mock_client_class, module_args, common_args,
                                       prune, expected_prune):
        """Test sync with different prune settings."""
        # Arrange
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        sync_result = {'status': 'Succeeded'}
        mock_client.sync_application.return_value = sync_result

        args = common_args.copy()
        args.update({
            'name': 'test-app',
            'revision': 'HEAD',
            'prune': prune,
            'dry_run': False,
            'wait': False,
        })
        module_args(args)

        # Act
        with pytest.raises(SystemExit) as exc_info:
            argocd_sync.main()

        # Assert
        assert exc_info.value.code == 0
        mock_client.sync_application.assert_called_once_with(
            name='test-app',
            revision='HEAD',
            prune=expected_prune,
            dry_run=False,
        )

    @patch('ansible_collections.redhat.argocd.plugins.modules.argocd_sync.ArgocdClient')
    @patch('ansible_collections.redhat.argocd.plugins.modules.argocd_sync.time.sleep')
    @patch('ansible_collections.redhat.argocd.plugins.modules.argocd_sync.time.time')
    def test_sync_wait_timeout(self, mock_time, mock_sleep, mock_client_class, module_args, common_args):
        """Test sync wait timeout handling."""
        # Arrange
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        sync_result = {'status': 'Running'}
        mock_client.sync_application.return_value = sync_result

        # Simulate timeout by making time progress faster than sync completes
        mock_time.side_effect = [0, 10, 20, 30, 40, 50, 60, 70]

        mock_client.get_application_sync_status.return_value = {
            'status': 'Syncing',
            'health': {'status': 'Progressing'},
        }

        args = common_args.copy()
        args.update({
            'name': 'test-app',
            'revision': 'HEAD',
            'wait': True,
            'wait_timeout': 60,
            'prune': False,
            'dry_run': False,
        })
        module_args(args)

        # Act
        with pytest.raises(SystemExit) as exc_info:
            argocd_sync.main()

        # Assert
        # Module should fail on timeout
        assert exc_info.value.code != 0

    @patch('ansible_collections.redhat.argocd.plugins.modules.argocd_sync.ArgocdClient')
    def test_sync_with_resources(self, mock_client_class, module_args, common_args):
        """Test sync with specific resources."""
        # Arrange
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        sync_result = {'status': 'Succeeded'}
        mock_client.sync_application.return_value = sync_result

        args = common_args.copy()
        args.update({
            'name': 'test-app',
            'revision': 'HEAD',
            'resources': [
                {'kind': 'Deployment', 'name': 'app'},
                {'kind': 'Service', 'name': 'app'},
            ],
            'prune': False,
            'dry_run': False,
            'wait': False,
        })
        module_args(args)

        # Act
        with pytest.raises(SystemExit) as exc_info:
            argocd_sync.main()

        # Assert
        assert exc_info.value.code == 0
        mock_client.sync_application.assert_called_once()
