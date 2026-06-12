# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for argocd_project module."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import pytest
from unittest.mock import patch, MagicMock
from ansible_collections.redhat.argocd.plugins.modules import argocd_project


class TestArgocdProject:
    """Test cases for argocd_project module."""

    @patch('ansible_collections.redhat.argocd.plugins.modules.argocd_project.ArgocdClient')
    def test_create_project(self, mock_client_class, module_args, common_args):
        """Test creating a new project."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.get.return_value = None

        created_project = {
            'metadata': {'name': 'test-project'},
            'spec': {
                'description': 'Test project',
                'sourceRepos': ['https://github.com/example/*'],
                'destinations': [
                    {'server': 'https://kubernetes.default.svc', 'namespace': '*'}
                ],
            },
        }
        mock_client.post.return_value = created_project

        args = common_args.copy()
        args.update({
            'name': 'test-project',
            'state': 'present',
            'description': 'Test project',
            'source_repos': ['https://github.com/example/*'],
            'destinations': [
                {'server': 'https://kubernetes.default.svc', 'namespace': '*'}
            ],
        })
        module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            argocd_project.main()

        assert exc_info.value.code == 0
        mock_client.post.assert_called_once()

    @patch('ansible_collections.redhat.argocd.plugins.modules.argocd_project.ArgocdClient')
    def test_update_project(self, mock_client_class, module_args, common_args):
        """Test updating an existing project."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        existing_project = {
            'metadata': {'name': 'test-project'},
            'spec': {
                'description': 'Old description',
                'sourceRepos': ['https://github.com/old-repo/*'],
                'destinations': [
                    {'server': 'https://kubernetes.default.svc', 'namespace': '*'}
                ],
            },
        }
        mock_client.get.return_value = existing_project

        updated_project = {
            'metadata': {'name': 'test-project'},
            'spec': {
                'description': 'New description',
                'sourceRepos': ['https://github.com/example/*'],
                'destinations': [
                    {'server': 'https://kubernetes.default.svc', 'namespace': '*'}
                ],
            },
        }
        mock_client.put.return_value = updated_project

        args = common_args.copy()
        args.update({
            'name': 'test-project',
            'state': 'present',
            'description': 'New description',
            'source_repos': ['https://github.com/example/*'],
            'destinations': [
                {'server': 'https://kubernetes.default.svc', 'namespace': '*'}
            ],
        })
        module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            argocd_project.main()

        assert exc_info.value.code == 0
        mock_client.put.assert_called_once()

    @patch('ansible_collections.redhat.argocd.plugins.modules.argocd_project.ArgocdClient')
    def test_delete_project(self, mock_client_class, module_args, common_args):
        """Test deleting a project."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        existing_project = {
            'metadata': {'name': 'test-project'},
            'spec': {'description': 'Test project'},
        }
        mock_client.get.return_value = existing_project
        mock_client.delete.return_value = None

        args = common_args.copy()
        args.update({
            'name': 'test-project',
            'state': 'absent',
        })
        module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            argocd_project.main()

        assert exc_info.value.code == 0
        mock_client.delete.assert_called_once()

    @patch('ansible_collections.redhat.argocd.plugins.modules.argocd_project.ArgocdClient')
    def test_project_no_change(self, mock_client_class, module_args, common_args):
        """Test no change when project matches desired state."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        existing_project = {
            'metadata': {'name': 'test-project'},
            'spec': {
                'description': 'Test project',
                'sourceRepos': ['https://github.com/example/*'],
                'destinations': [
                    {'server': 'https://kubernetes.default.svc', 'namespace': '*'}
                ],
            },
        }
        mock_client.get.return_value = existing_project

        args = common_args.copy()
        args.update({
            'name': 'test-project',
            'state': 'present',
            'description': 'Test project',
            'source_repos': ['https://github.com/example/*'],
            'destinations': [
                {'server': 'https://kubernetes.default.svc', 'namespace': '*'}
            ],
        })
        module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            argocd_project.main()

        assert exc_info.value.code == 0
        mock_client.post.assert_not_called()
        mock_client.put.assert_not_called()

    @patch('ansible_collections.redhat.argocd.plugins.modules.argocd_project.ArgocdClient')
    def test_check_mode(self, mock_client_class, module_args, common_args):
        """Test check mode does not make API calls."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.get.return_value = None

        args = common_args.copy()
        args.update({
            'name': 'test-project',
            'state': 'present',
            'description': 'Test project',
            'source_repos': ['https://github.com/example/*'],
            'destinations': [
                {'server': 'https://kubernetes.default.svc', 'namespace': '*'}
            ],
            '_ansible_check_mode': True,
        })
        module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            argocd_project.main()

        assert exc_info.value.code == 0
        mock_client.post.assert_not_called()
        mock_client.put.assert_not_called()
        mock_client.delete.assert_not_called()

    @pytest.mark.parametrize("destinations,expected_count", [
        ([{'server': 'https://kubernetes.default.svc', 'namespace': 'default'}], 1),
        ([{'server': 'https://kubernetes.default.svc', 'namespace': '*'}], 1),
        ([
            {'server': 'https://cluster1.example.com', 'namespace': 'ns1'},
            {'server': 'https://cluster2.example.com', 'namespace': 'ns2'},
        ], 2),
    ])
    @patch('ansible_collections.redhat.argocd.plugins.modules.argocd_project.ArgocdClient')
    def test_multiple_destinations(self, mock_client_class, module_args, common_args,
                                   destinations, expected_count):
        """Test project with multiple destination configurations."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.get.return_value = None

        created_project = {
            'metadata': {'name': 'test-project'},
            'spec': {
                'description': 'Test project',
                'sourceRepos': ['*'],
                'destinations': destinations,
            },
        }
        mock_client.post.return_value = created_project

        args = common_args.copy()
        args.update({
            'name': 'test-project',
            'state': 'present',
            'description': 'Test project',
            'source_repos': ['*'],
            'destinations': destinations,
        })
        module_args(args)

        with pytest.raises(SystemExit) as exc_info:
            argocd_project.main()

        assert exc_info.value.code == 0
        mock_client.post.assert_called_once()
