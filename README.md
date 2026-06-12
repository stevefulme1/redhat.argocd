# Ansible Collection - redhat.argocd

[![CI](https://github.com/redhat/redhat.argocd/actions/workflows/ci.yml/badge.svg)](https://github.com/redhat/redhat.argocd/actions/workflows/ci.yml)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

Ansible modules and plugins for managing Argo CD, Argo Workflows, Argo Events, and Argo Rollouts on Kubernetes and OpenShift.

## Requirements

- Ansible core >= 2.16.0
- Python >= 3.10
- `requests >= 2.25.0`

## Installation

```bash
ansible-galaxy collection install redhat.argocd
```

Or from source:

```bash
ansible-galaxy collection build
ansible-galaxy collection install redhat-argocd-0.1.0.tar.gz
```

## Included Content

### Modules

| Module | Description |
|--------|-------------|
| `redhat.argocd.argocd_application` | Manage ArgoCD applications |
| `redhat.argocd.argocd_application_info` | Get information about ArgoCD applications |
| `redhat.argocd.argocd_application_set` | Manage ArgoCD ApplicationSets |
| `redhat.argocd.argocd_project` | Manage ArgoCD projects |
| `redhat.argocd.argocd_repository` | Manage ArgoCD repositories |
| `redhat.argocd.argocd_cluster` | Manage ArgoCD clusters |
| `redhat.argocd.argocd_sync` | Trigger ArgoCD application sync |
| `redhat.argocd.argo_workflow` | Manage Argo Workflows |
| `redhat.argocd.argo_workflow_template` | Manage Argo Workflow Templates |
| `redhat.argocd.argo_cron_workflow` | Manage Argo Cron Workflows |
| `redhat.argocd.argo_cluster_workflow_template` | Manage Argo Cluster Workflow Templates |
| `redhat.argocd.argo_event_source` | Manage Argo Events EventSources |
| `redhat.argocd.argo_sensor` | Manage Argo Events Sensors |
| `redhat.argocd.argo_event_bus` | Manage Argo Events EventBus |
| `redhat.argocd.argo_rollout` | Manage Argo Rollouts |
| `redhat.argocd.argo_analysis_template` | Manage Argo Analysis Templates |
| `redhat.argocd.argo_experiment` | Manage Argo Experiments |

### Inventory Plugins

| Plugin | Description |
|--------|-------------|
| `redhat.argocd.argocd_clusters` | Dynamic inventory from ArgoCD clusters |

### Module Utils

| Utility | Description |
|---------|-------------|
| `argocd_common` | Shared ArgoCD API client and argument spec |

## Usage

```yaml
- name: Manage ArgoCD applications
  hosts: localhost
  connection: local
  tasks:
    - name: Create an ArgoCD application
      redhat.argocd.argocd_application:
        server_url: https://argocd.example.com
        auth_token: "{{ argocd_token }}"
        name: my-app
        project: default
        repo_url: https://github.com/example/app.git
        path: manifests/
        destination_server: https://kubernetes.default.svc
        destination_namespace: my-namespace
        state: present

    - name: Sync the application
      redhat.argocd.argocd_sync:
        server_url: https://argocd.example.com
        auth_token: "{{ argocd_token }}"
        name: my-app
        wait: true
        timeout: 300
```

## Testing

```bash
# Lint
ansible-lint
yamllint .

# Sanity tests
ansible-test sanity --docker -v

# Unit tests
ansible-test units --docker -v

# Integration tests
ansible-test integration --docker -v
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

GNU General Public License v3.0 - see [LICENSE](LICENSE) for details.
