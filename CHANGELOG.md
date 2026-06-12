# Changelog

All notable changes to this collection will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this collection adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - Unreleased

### Added

- `argocd_application` module for managing ArgoCD applications.
- `argocd_application_info` module for retrieving ArgoCD application information.
- `argocd_application_set` module for managing ArgoCD ApplicationSets.
- `argocd_project` module for managing ArgoCD projects.
- `argocd_repository` module for managing ArgoCD repositories.
- `argocd_cluster` module for managing ArgoCD clusters.
- `argocd_sync` module for triggering ArgoCD application sync.
- `argo_workflow` module for managing Argo Workflows.
- `argo_workflow_template` module for managing Argo Workflow Templates.
- `argo_cron_workflow` module for managing Argo Cron Workflows.
- `argo_cluster_workflow_template` module for managing Argo Cluster Workflow Templates.
- `argo_event_source` module for managing Argo Events EventSources.
- `argo_sensor` module for managing Argo Events Sensors.
- `argo_event_bus` module for managing Argo Events EventBus.
- `argo_rollout` module for managing Argo Rollouts.
- `argo_analysis_template` module for managing Argo Analysis Templates.
- `argo_experiment` module for managing Argo Experiments.
- `argocd_clusters` dynamic inventory plugin.
- `argocd_common` module utility with shared ArgoCD API client.
- CI pipeline with lint, sanity, unit, and integration tests.
- Matrix testing across Python 3.10-3.12 and ansible-core 2.16-2.18.
