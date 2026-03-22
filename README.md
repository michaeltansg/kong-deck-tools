# kong-deck-tools

Kong API Gateway configuration tools for certificate management and cross-environment comparison.

## Overview

This package provides CLI tools for managing Kong API Gateway configurations:

1. **Extract sensitive cryptographic material** (certificates, CA certificates, and keys) from Kong configurations into separate files, allowing templates to be safely committed to git while keeping sensitive data separate
2. **Enforce consistent key ordering** across all configurations, making it easy to compare configurations across different environments (local, staging, production)

## Installation

```bash
pip install kong-deck-tools
```

## Usage

### kong-templatize

Splits a Kong configuration into a template and a values file:

```bash
kong-templatize config.yaml
```

**Input:** `config.yaml` (full Kong configuration with certificates and keys)

**Output:**
- `config.tmpl.yaml` - Template with Helm-style placeholders for sensitive data
- `config.certs.values.yaml` - Extracted values (certificates, CA certificates, and keys)

Extracts the following sensitive fields:
- `certificates[].cert` and `certificates[].key` — keyed by SNI name
- `ca_certificates[].cert` — keyed by ID
- `keys[].pem.private_key`, `keys[].pem.public_key`, and `keys[].jwk` — keyed by kid

The script also prettifies the template by reordering YAML keys for consistency and readability.

### kong-hydrate

Reconstructs a full Kong configuration from template and values:

```bash
kong-hydrate config.tmpl.yaml
```

**Input:** `config.tmpl.yaml` (template file; values file `config.certs.values.yaml` is derived automatically)

**Output:** `config.rendered.yaml` (complete Kong configuration)

## Workflow with Kong deck

```bash
# 1. Export current Kong configuration
deck gateway dump -o config.yaml

# 2. Extract certificates and create template
kong-templatize config.yaml

# 3. Commit template to git (certificates stay separate)
git add config.tmpl.yaml
git commit -m "Update Kong configuration"

# 4. Before deploying, hydrate the template with certificates
kong-hydrate config.tmpl.yaml

# 5. Compare with current Kong state
deck gateway diff config.rendered.yaml

# 6. Apply changes
deck gateway sync config.rendered.yaml
```

## Key Ordering

The `kong-templatize` command enforces consistent key ordering to make configs:
- **Human-readable**: Important fields (name, enabled) appear first
- **Diff-friendly**: Consistent ordering reduces noise in git diffs
- **Hierarchical**: Configuration objects (routes, plugins) appear after their properties

Key ordering by entity type:
- **Plugins**: name -> enabled -> config -> protocols -> tags
- **Services**: name -> enabled -> host -> port -> protocol -> timeouts -> tags -> plugins -> routes
- **Routes**: name -> hosts -> paths -> protocols -> strip_path -> preserve_host -> ... -> plugins
- **Upstreams**: name -> algorithm -> slots -> hash_* -> tags -> healthchecks -> targets
- **Consumers**: username -> custom_id -> tags
- **CA Certificates**: id -> cert -> cert_digest -> tags
- **Keys**: name -> kid -> set -> pem -> jwk -> tags

## Requirements

- Python 3.8+
- Kong deck CLI (for dumping/syncing configurations)

## Development

### Install in development mode

```bash
git clone https://github.com/michaeltan/kong-deck-tools.git
cd kong-deck-tools
pip install -e .
```

### Publishing to PyPI

```bash
# Install uv (if not already installed)
brew install uv

# Clean previous build artifacts, rebuild, and publish
rm -rf dist/ && uv build && uv publish --token $PYPI_TOKEN
```

To get a PyPI API token, visit https://pypi.org/manage/account/token/

## License

MIT
