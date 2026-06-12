# -*- coding: utf-8 -*-
# Copyright: (c) 2026, Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Pytest configuration and fixtures for unit tests."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import pytest
from unittest.mock import MagicMock, patch
from ansible.module_utils import basic
from ansible.module_utils.common.text.converters import to_bytes
import json


@pytest.fixture
def module_args():
    """Fixture that patches AnsibleModule to capture module arguments."""
    def set_module_args(args):
        """Prepare arguments for AnsibleModule instantiation."""
        if '_ansible_remote_tmp' not in args:
            args['_ansible_remote_tmp'] = '/tmp'
        if '_ansible_keep_remote_files' not in args:
            args['_ansible_keep_remote_files'] = False

        args = json.dumps({'ANSIBLE_MODULE_ARGS': args})
        basic._ANSIBLE_ARGS = to_bytes(args)

    return set_module_args


@pytest.fixture
def mock_client():
    """Fixture that returns a mock ArgocdClient instance."""
    client = MagicMock()
    client.get_application = MagicMock()
    client.create_application = MagicMock()
    client.update_application = MagicMock()
    client.delete_application = MagicMock()
    client.get_project = MagicMock()
    client.create_project = MagicMock()
    client.update_project = MagicMock()
    client.delete_project = MagicMock()
    client.sync_application = MagicMock()
    client.get_application_sync_status = MagicMock()
    return client


@pytest.fixture
def common_args():
    """Fixture providing common module arguments."""
    return {
        'server_url': 'https://argocd.example.com',
        'auth_token': 'test-token-12345',
        'validate_certs': True,
    }
