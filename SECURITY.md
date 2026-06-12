# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |

## Reporting a Vulnerability

If you discover a security vulnerability in this collection, please report it
responsibly.

**Do not open a public GitHub issue for security vulnerabilities.**

Instead, please send an email to secalert@redhat.com with the following
information:

- A description of the vulnerability
- Steps to reproduce the issue
- Affected versions
- Any potential impact

You should receive a response within 48 hours acknowledging your report. We
will work with you to understand the scope and develop a fix.

## Security Considerations

This collection communicates with ArgoCD, Argo Workflows, Argo Events, and
Argo Rollouts APIs. When using these modules:

- Store API tokens in Ansible Vault or an external secrets manager.
- Use `no_log: true` for parameters containing credentials (already configured
  in all modules for `auth_token`, `password`, and `ssh_private_key`).
- Enable TLS certificate validation (`validate_certs: true`) in production.
- Follow the principle of least privilege when creating API tokens.
- Review ArgoCD RBAC policies to limit token scope.

## Disclosure Policy

We follow coordinated disclosure. Once a fix is available, we will publish a
security advisory and release a patched version.
