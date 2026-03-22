# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This repository is a PyPI package (`kong-deck-tools`) that provides CLI tools for Kong API Gateway configuration management:

1. **Extract sensitive cryptographic material** (certificates, CA certificates, and keys) from Kong configurations into separate files, allowing templates to be safely committed to git while keeping sensitive data separate
2. **Enforce consistent key ordering** across all configurations, making it easy to compare configurations across different environments (local, staging, production)

## Installation

```bash
# From PyPI
pip install kong-deck-tools

# For development (from this repo)
pip install -e .
```

## CLI Commands

After installation, two commands are available:

```bash
kong-templatize config.yaml       # Extract certs, create template
kong-hydrate config.tmpl.yaml     # Render template with certs
```

## Package Structure

```
kong-deck-tools/
├── pyproject.toml              # Package metadata and entry points
├── README.md                   # PyPI documentation
├── LICENSE                     # MIT license
├── src/kong_deck_tools/        # Package source
│   ├── __init__.py
│   ├── templatize.py           # Certificate extraction & templating
│   └── hydrate.py              # Template rendering
└── requirements.txt            # Development dependencies
```

## Key Concepts

### Kong Configuration Structure

Kong configurations are YAML files with the following top-level sections:
- `_format_version`: Kong declarative config format version (currently "3.0")
- `certificates`: SSL/TLS certificates and private keys for securing API traffic
- `ca_certificates`: CA certificates for mTLS and certificate verification
- `keys`: Cryptographic keys (PEM or JWK) for signing and encryption
- `plugins`: Global plugins that apply across all services
- `services`: Backend services that Kong proxies to
- `upstreams`: Load balancer configurations with health checks and targets

### Configuration Hierarchy

Services -> Routes -> Plugins (at service or route level)
Upstreams -> Targets (backend servers with weights)

## Certificate & Key Management Workflow

### kong-templatize

Splits a Kong configuration into a template and a values file:

```bash
kong-templatize config.yaml
```

**Input:** `config.yaml` (full Kong configuration with certificates and keys)

**Output:**
- `config.tmpl.yaml` - Template with Helm-style placeholders for sensitive data
- `config.certs.values.yaml` - Extracted values (certificates, CA certificates, and keys)

**Extracted fields:**
- `certificates[].cert` and `certificates[].key` — keyed by SNI name
- `ca_certificates[].cert` — keyed by ID
- `keys[].pem.private_key`, `keys[].pem.public_key`, and `keys[].jwk` — keyed by kid

### kong-hydrate

Reconstructs a full Kong configuration from template and values:

```bash
kong-hydrate config.tmpl.yaml
```

**Input:** `config.tmpl.yaml` (template file; values file derived automatically)

**Output:** `config.rendered.yaml` (complete Kong configuration)

## Key Ordering

The `kong-templatize` command enforces consistent key ordering:
- **Plugins**: name -> enabled -> config -> protocols -> tags
- **Services**: name -> enabled -> host -> port -> protocol -> timeouts -> tags -> plugins -> routes
- **Routes**: name -> hosts -> paths -> protocols -> strip_path -> preserve_host -> ... -> plugins
- **Upstreams**: name -> algorithm -> slots -> hash_* -> tags -> healthchecks -> targets
- **Consumers**: username -> custom_id -> tags
- **CA Certificates**: id -> cert -> cert_digest -> tags
- **Keys**: name -> kid -> set -> pem -> jwk -> tags

---

## Quick Reference

| Task          | Command                              | Description                                                         |
|---------------|--------------------------------------|---------------------------------------------------------------------|
| Install       | pip install kong-deck-tools          | Install from PyPI                                                   |
| Install (dev) | pip install -e .                     | Install in development mode                                         |
| Dump          | deck gateway dump -o config.yaml     | Export Kong configuration to config.yaml                            |
| Templatize    | kong-templatize config.yaml          | config.yaml -> config.tmpl.yaml + config.certs.values.yaml          |
| Hydrate       | kong-hydrate config.tmpl.yaml        | config.tmpl.yaml + config.certs.values.yaml -> config.rendered.yaml |
| Check diff    | deck gateway diff config.rendered.yaml | Compare with current Kong configuration                           |
| Deploy        | deck gateway sync config.rendered.yaml | Update Kong configuration                                         |

---
