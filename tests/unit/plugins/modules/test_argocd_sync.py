# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for argocd_sync module."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import pytest
from unittest.mock import patch, MagicMock
from ansible_collections.redhat.argocd.plugins.modules import argocd_sync


class TestArgocdSync:
    """Test cases for argocd_sync module."""

    @patch('ansible_collections.redhat.argocd.plugins.modules.argocd_sync.ArgocdClient')
    def test_sync_application(self, mock_client_class, module_args, common_args):
        """Test syncing an application."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Application exists and is out of sync
        existing_app = {
            'metadata': {'name': 'test-app'},
            'status': {
                'sync': {'status': 'OutOfSync'},
                'health': {'status': 'Healthy'},
            },
        }
        mock_client.get_application.return_value = existing_app

        sync_result = {
            'status': {
                'sync': {'status': 'Synced'},
                'operationState': {
                    'phase': 'Succeeded',
                    'message': 'Sync operation completed',
                },
            },
        }
        mock_client.sync_application.return_value = sync_result

        args = common_args.copy()
        args.update({
            'name': 'test-app',
            'prune': False,
            'dry_run': False,
            'force': False,
            'strategy': 'apply',
            'wait': False,
            'timeout': 300,
        })
        module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            argocd_sync.main()

        assert exc_info.value.code == 0
        mock_client.sync_application.assert_called_once()

    @patch('ansible_collections.redhat.argocd.plugins.modules.argocd_sync.time.sleep')
    @patch('ansible_collections.redhat.argocd.plugins.modules.argocd_sync.time.time')
    @patch('ansible_collections.redhat.argocd.plugins.modules.argocd_sync.ArgocdClient')
    def test_sync_with_wait(self, mock_client_class, mock_time, mock_sleep, module_args, common_args):
        """Test syncing with wait for completion."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # First call: initial check - app out of sync
        # Subsequent calls: wait_for_sync polling
        existing_app = {
            'metadata': {'name': 'test-app'},
            'status': {
                'sync': {'status': 'OutOfSync'},
                'health': {'status': 'Healthy'},
            },
        }

        syncing_app = {
            'metadata': {'name': 'test-app'},
            'status': {
                'sync': {'status': 'Syncing'},
                'operationState': {'phase': 'Running'},
            },
        }

        synced_app = {
            'metadata': {'name': 'test-app'},
            'status': {
                'sync': {'status': 'Synced'},
                'operationState': {'phase': 'Succeeded'},
            },
        }

        mock_client.get_application.side_effect = [
            existing_app,   # initial check
            syncing_app,    # wait poll 1
            syncing_app,    # wait poll 2
            synced_app,     # wait poll 3 - done
        ]

        sync_result = {
            'status': {
                'sync': {'status': 'Syncing'},
                'operationState': {'phase': 'Running'},
            },
        }
        mock_client.sync_application.return_value = sync_result

        # time.time() returns increasing values within timeout
        mock_time.side_effect = [0, 5, 10, 15, 20]

        args = common_args.copy()
        args.update({
            'name': 'test-app',
            'wait': True,
            'timeout': 300,
            'prune': True,
            'dry_run': False,
            'force': False,
            'strategy': 'apply',
        })
        module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            argocd_sync.main()

        assert exc_info.value.code == 0
        mock_client.sync_application.assert_called_once()

    @patch('ansible_collections.redhat.argocd.plugins.modules.argocd_sync.ArgocdClient')
    def test_sync_dry_run(self, mock_client_class, module_args, common_args):
        """Test sync with dry_run enabled."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        existing_app = {
            'metadata': {'name': 'test-app'},
            'status': {
                'sync': {'status': 'OutOfSync'},
                'health': {'status': 'Healthy'},
            },
        }

        # For dry_run, get_application is called twice: once to check, once after sync
        updated_app = {
            'metadata': {'name': 'test-app'},
            'status': {
                'sync': {'status': 'OutOfSync'},
                'operationState': {'phase': 'Succeeded', 'message': 'Dry run completed'},
            },
        }
        mock_client.get_application.side_effect = [existing_app, updated_app]

        dry_run_result = {
            'status': {
                'sync': {'status': 'OutOfSync'},
                'operationState': {'phase': 'Succeeded'},
            },
        }
        mock_client.sync_application.return_value = dry_run_result

        args = common_args.copy()
        args.update({
            'name': 'test-app',
            'dry_run': True,
            'prune': False,
            'force': False,
            'strategy': 'apply',
            'wait': False,
            'timeout': 300,
        })
        module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            argocd_sync.main()

        assert exc_info.value.code == 0
        mock_client.sync_application.assert_called_once()

    @patch('ansible_collections.redhat.argocd.plugins.modules.argocd_sync.ArgocdClient')
    def test_check_mode(self, mock_client_class, module_args, common_args):
        """Test check mode does not perform sync."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        existing_app = {
            'metadata': {'name': 'test-app'},
            'status': {
                'sync': {'status': 'OutOfSync'},
                'health': {'status': 'Healthy'},
            },
        }
        mock_client.get_application.return_value = existing_app

        args = common_args.copy()
        args.update({
            'name': 'test-app',
            'prune': False,
            'dry_run': False,
            'force': False,
            'strategy': 'apply',
            'wait': False,
            'timeout': 300,
            '_ansible_check_mode': True,
        })
        module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            argocd_sync.main()

        assert exc_info.value.code == 0
        mock_client.sync_application.assert_not_called()

    @pytest.mark.parametrize("prune,expected_prune", [
        (True, True),
        (False, False),
    ])
    @patch('ansible_collections.redhat.argocd.plugins.modules.argocd_sync.ArgocdClient')
    def test_sync_with_prune_variations(self, mock_client_class,
                                        module_args, common_args,
                                        prune, expected_prune):
        """Test sync with different prune settings."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        existing_app = {
            'metadata': {'name': 'test-app'},
            'status': {
                'sync': {'status': 'OutOfSync'},
                'health': {'status': 'Healthy'},
            },
        }

        updated_app = {
            'metadata': {'name': 'test-app'},
            'status': {
                'sync': {'status': 'Synced'},
                'operationState': {'phase': 'Succeeded'},
            },
        }
        mock_client.get_application.side_effect = [existing_app, updated_app]

        sync_result = {
            'status': {
                'sync': {'status': 'Synced'},
                'operationState': {'phase': 'Succeeded'},
            },
        }
        mock_client.sync_application.return_value = sync_result

        args = common_args.copy()
        args.update({
            'name': 'test-app',
            'prune': prune,
            'dry_run': False,
            'force': False,
            'strategy': 'apply',
            'wait': False,
            'timeout': 300,
        })
        module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            argocd_sync.main()

        assert exc_info.value.code == 0
        mock_client.sync_application.assert_called_once()

    @patch('ansible_collections.redhat.argocd.plugins.modules.argocd_sync.time.sleep')
    @patch('ansible_collections.redhat.argocd.plugins.modules.argocd_sync.time.time')
    @patch('ansible_collections.redhat.argocd.plugins.modules.argocd_sync.ArgocdClient')
    def test_sync_wait_timeout(self, mock_client_class, mock_time, mock_sleep, module_args, common_args):
        """Test sync wait timeout handling."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        existing_app = {
            'metadata': {'name': 'test-app'},
            'status': {
                'sync': {'status': 'OutOfSync'},
                'health': {'status': 'Healthy'},
            },
        }

        syncing_app = {
            'metadata': {'name': 'test-app'},
            'status': {
                'sync': {'status': 'Syncing'},
                'operationState': {'phase': 'Running'},
            },
        }

        # Initial check returns existing_app, then syncing_app during wait
        mock_client.get_application.side_effect = [existing_app] + [syncing_app] * 20

        sync_result = {
            'status': {
                'sync': {'status': 'Syncing'},
                'operationState': {'phase': 'Running'},
            },
        }
        mock_client.sync_application.return_value = sync_result

        # Simulate timeout: time exceeds the 60s timeout
        mock_time.side_effect = [0, 10, 20, 30, 40, 50, 60, 70, 80]

        args = common_args.copy()
        args.update({
            'name': 'test-app',
            'wait': True,
            'timeout': 60,
            'prune': False,
            'dry_run': False,
            'force': False,
            'strategy': 'apply',
        })
        module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            argocd_sync.main()

        # Module should fail on timeout
        assert exc_info.value.code != 0

    @patch('ansible_collections.redhat.argocd.plugins.modules.argocd_sync.ArgocdClient')
    def test_already_synced_no_force(self, mock_client_class, module_args, common_args):
        """Test that already-synced app without force returns no change."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        synced_app = {
            'metadata': {'name': 'test-app'},
            'status': {
                'sync': {'status': 'Synced'},
                'health': {'status': 'Healthy'},
            },
        }
        mock_client.get_application.return_value = synced_app

        args = common_args.copy()
        args.update({
            'name': 'test-app',
            'prune': False,
            'dry_run': False,
            'force': False,
            'strategy': 'apply',
            'wait': False,
            'timeout': 300,
        })
        module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            argocd_sync.main()

        assert exc_info.value.code == 0
        mock_client.sync_application.assert_not_called()
