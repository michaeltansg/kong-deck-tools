# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This repository provides tooling for Kong API Gateway configuration management. The scripts:

1. **Extract certificates** from Kong configurations into separate files, allowing templates to be safely committed to git while keeping sensitive certificate data separate
2. **Enforce consistent key ordering** across all configurations, making it easy to compare configurations across different environments (local, staging, production)

## Key Concepts

### Kong Configuration Structure

Kong configurations are YAML files with the following top-level sections:
- `_format_version`: Kong declarative config format version (currently "3.0")
- `certificates`: SSL/TLS certificates and private keys for securing API traffic
- `plugins`: Global plugins that apply across all services
- `services`: Backend services that Kong proxies to
- `upstreams`: Load balancer configurations with health checks and targets
- Each service can have nested `routes` (how clients access the service) and `plugins` (service-specific functionality)

### Configuration Hierarchy

Services -> Routes -> Plugins (at service or route level)
Upstreams -> Targets (backend servers with weights)

## Required Tools

- `deck` (Kong's declarative configuration tool)
- Python 3 with virtual environment support

## Python Environment Setup

```bash
# Create virtual environment (one-time setup)
python3 -m venv .venv

# Install dependencies
.venv/bin/pip install -r requirements.txt
```

## Repository Structure

### Files

- `templatize.py` - Extracts certificates from Kong config, creates template with placeholders, and prettifies structure
- `hydrate.py` - Reconstructs full configuration by merging template with certificate values
- `requirements.txt` - Python dependencies (ruamel.yaml for format-preserving YAML processing)
- `.gitignore` - Excludes `.venv/`, `snapshots/`, and `*.yaml` files from version control

## Certificate Management Workflow

### templatize.py - Create template from config

Splits a Kong configuration into a template and a values file:

```bash
.venv/bin/python templatize.py config.yaml
```

**Input:** `config.yaml` (full Kong configuration with certificates)

**Output:**
- `config.tmpl.yaml` - Template with Helm-style placeholders for certificates
- `config.certs.values.yaml` - Extracted certificate values (name, cert, key)

The script also prettifies the template by reordering YAML keys for consistency and readability.

### hydrate.py - Render configuration from template

Reconstructs a full Kong configuration from template and values:

```bash
.venv/bin/python hydrate.py config.tmpl.yaml
```

**Input:** `config.tmpl.yaml` (template file; values file `config.certs.values.yaml` is derived automatically)

**Output:** `config.rendered.yaml` (complete Kong configuration)

## Key Ordering

The `templatize.py` script enforces consistent key ordering to make configs:
1. **Human-readable**: Important fields (name, enabled) appear first
2. **Diff-friendly**: Consistent ordering reduces noise in git diffs
3. **Hierarchical**: Configuration objects (routes, plugins) appear after their properties

Key ordering by entity type:
- **Plugins**: name -> enabled -> config -> protocols -> tags
- **Services**: name -> enabled -> host -> port -> protocol -> timeouts -> tags -> plugins -> routes
- **Routes**: name -> hosts -> paths -> protocols -> strip_path -> preserve_host -> ... -> plugins
- **Upstreams**: name -> algorithm -> slots -> hash_* -> tags -> healthchecks -> targets
- **Consumers**: username -> custom_id -> tags

---

## Quick Reference

| Task          | Command                                                            | Description                                                         |
|---------------|--------------------------------------------------------------------|---------------------------------------------------------------------|
| Setup         | python3 -m venv .venv && .venv/bin/pip install -r requirements.txt | Install Python dependencies                                         |
| Dump          | deck gateway dump -o config.yaml                                   | Export Kong configuration to config.yaml                            |
| Templatize    | .venv/bin/python templatize.py config.yaml                         | config.yaml -> config.tmpl.yaml + config.certs.values.yaml          |
| Hydrate       | .venv/bin/python hydrate.py config.tmpl.yaml                       | config.tmpl.yaml + config.certs.values.yaml -> config.rendered.yaml |
| Check diff    | deck gateway diff config.rendered.yaml                             | Compare config.rendered.yaml with current Kong configuration        |
| Deploy        | deck gateway sync config.rendered.yaml                             | Update Kong configuration with config.rendered.yaml                 |

---
