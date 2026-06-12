# Contributing to redhat.argocd

Thank you for your interest in contributing to this collection.

## Development Setup

1. Fork and clone the repository:

   ```bash
   git clone https://github.com/<your-username>/redhat.argocd.git
   cd redhat.argocd
   ```

2. Install development dependencies:

   ```bash
   pip install ansible-core ansible-lint yamllint pytest pytest-mock requests
   ```

3. Set up the collection path:

   ```bash
   mkdir -p ansible_collections/redhat
   ln -s "$(pwd)" ansible_collections/redhat/argocd
   ```

## Testing

Run all checks before submitting a pull request:

```bash
# Linting
yamllint .
ansible-lint

# Sanity tests
ansible-test sanity --docker -v

# Unit tests
ansible-test units --docker -v

# Integration tests (requires ArgoCD instance)
ansible-test integration --docker -v
```

## Pull Request Guidelines

- Each PR should address a single concern (bug fix, feature, documentation).
- Include unit tests for new modules and features.
- Update CHANGELOG.md with a summary of changes.
- Follow conventional commit format for commit messages.
- Ensure all CI checks pass before requesting review.

## Module Development

Every module must include:

- GPL-3.0 header
- `DOCUMENTATION`, `EXAMPLES`, and `RETURN` blocks matching `argument_spec`
- Check mode support via `supports_check_mode=True`
- Idempotent operations (get existing state, compare, modify only if needed)
- Proper error handling with `module.fail_json()`

Use `argocd_argument_spec()` from `module_utils.argocd_common` for shared parameters.

## Code Style

- Follow PEP 8 for Python code.
- Use `snake_case` for module names and parameters.
- Do not use FQCN self-references within the collection.

## Reporting Issues

Open an issue on GitHub with:

- Ansible version (`ansible --version`)
- Collection version
- Steps to reproduce
- Expected and actual behavior
