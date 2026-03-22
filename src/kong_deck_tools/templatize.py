#!/usr/bin/env python3
"""
templatize.py
Splits Kong configuration into template and values files, then prettifies.
This creates diff-friendly, Helm-ready configuration files.

Usage: kong-templatize <config_file>
Example: kong-templatize config.yaml
"""

import sys
from pathlib import Path
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap


# Key ordering definitions for each entity type
PLUGIN_KEY_ORDER = ['name', 'enabled', 'config', 'protocols', 'tags']
SERVICE_KEY_ORDER = ['name', 'enabled', 'host', 'port', 'protocol',
                     'connect_timeout', 'read_timeout', 'write_timeout',
                     'retries', 'tags']
SERVICE_TRAILING_KEYS = ['plugins', 'routes']
ROUTE_KEY_ORDER = ['name', 'hosts', 'paths', 'protocols', 'strip_path',
                   'preserve_host', 'https_redirect_status_code', 'path_handling',
                   'regex_priority', 'request_buffering', 'response_buffering', 'tags']
ROUTE_TRAILING_KEYS = ['plugins']
UPSTREAM_KEY_ORDER = ['name', 'algorithm', 'slots', 'hash_on', 'hash_fallback',
                      'hash_on_cookie_path', 'use_srv_name', 'tags']
UPSTREAM_TRAILING_KEYS = ['healthchecks', 'targets']
TARGET_KEY_ORDER = ['target', 'weight', 'tags']
CONSUMER_KEY_ORDER = ['username', 'custom_id', 'tags']
CA_CERTIFICATE_KEY_ORDER = ['id', 'cert', 'cert_digest', 'tags']
KEY_KEY_ORDER = ['name', 'kid', 'set', 'pem', 'jwk', 'tags']


def reorder_keys(obj, key_order, trailing_keys=None):
    """Reorder keys in a CommentedMap according to specified order."""
    if not isinstance(obj, dict):
        return obj

    trailing_keys = trailing_keys or []
    ordered = CommentedMap()

    # First, add keys in specified order
    for key in key_order:
        if key in obj:
            ordered[key] = obj[key]

    # Then add remaining keys (except trailing ones)
    all_specified = set(key_order) | set(trailing_keys)
    for key in obj:
        if key not in all_specified:
            ordered[key] = obj[key]

    # Finally add trailing keys
    for key in trailing_keys:
        if key in obj:
            ordered[key] = obj[key]

    return ordered


def reorder_plugins(plugins):
    """Reorder keys in plugin configurations."""
    if not plugins:
        return plugins
    return [reorder_keys(p, PLUGIN_KEY_ORDER) for p in plugins]


def reorder_routes(routes):
    """Reorder keys in route configurations."""
    if not routes:
        return routes
    result = []
    for route in routes:
        ordered = reorder_keys(route, ROUTE_KEY_ORDER, ROUTE_TRAILING_KEYS)
        if 'plugins' in ordered:
            ordered['plugins'] = reorder_plugins(ordered['plugins'])
        result.append(ordered)
    return result


def reorder_services(services):
    """Reorder keys in service configurations."""
    if not services:
        return services
    result = []
    for service in services:
        ordered = reorder_keys(service, SERVICE_KEY_ORDER, SERVICE_TRAILING_KEYS)
        if 'plugins' in ordered:
            ordered['plugins'] = reorder_plugins(ordered['plugins'])
        if 'routes' in ordered:
            ordered['routes'] = reorder_routes(ordered['routes'])
        result.append(ordered)
    return result


def reorder_targets(targets):
    """Reorder keys in target configurations."""
    if not targets:
        return targets
    return [reorder_keys(t, TARGET_KEY_ORDER) for t in targets]


def reorder_upstreams(upstreams):
    """Reorder keys in upstream configurations."""
    if not upstreams:
        return upstreams
    result = []
    for upstream in upstreams:
        ordered = reorder_keys(upstream, UPSTREAM_KEY_ORDER, UPSTREAM_TRAILING_KEYS)
        if 'targets' in ordered:
            ordered['targets'] = reorder_targets(ordered['targets'])
        result.append(ordered)
    return result


def reorder_consumers(consumers):
    """Reorder keys in consumer configurations."""
    if not consumers:
        return consumers
    return [reorder_keys(c, CONSUMER_KEY_ORDER) for c in consumers]


def reorder_ca_certificates(ca_certificates):
    """Reorder keys in CA certificate configurations."""
    if not ca_certificates:
        return ca_certificates
    return [reorder_keys(c, CA_CERTIFICATE_KEY_ORDER) for c in ca_certificates]


def reorder_keys_entities(keys):
    """Reorder keys in key configurations."""
    if not keys:
        return keys
    return [reorder_keys(k, KEY_KEY_ORDER) for k in keys]


def prettify_config(config):
    """Prettify the entire configuration by reordering keys."""
    if 'plugins' in config:
        config['plugins'] = reorder_plugins(config['plugins'])
    if 'services' in config:
        config['services'] = reorder_services(config['services'])
    if 'upstreams' in config:
        config['upstreams'] = reorder_upstreams(config['upstreams'])
    if 'consumers' in config:
        config['consumers'] = reorder_consumers(config['consumers'])
    if 'ca_certificates' in config:
        config['ca_certificates'] = reorder_ca_certificates(config['ca_certificates'])
    if 'keys' in config:
        config['keys'] = reorder_keys_entities(config['keys'])
    return config


def extract_certificates(config):
    """Extract certificates from config into a list of certificate values."""
    certs = []
    if 'certificates' in config and config['certificates']:
        for cert in config['certificates']:
            if 'snis' in cert and cert['snis']:
                cert_entry = CommentedMap()
                cert_entry['name'] = cert['snis'][0]['name']
                cert_entry['cert'] = cert.get('cert', '')
                cert_entry['key'] = cert.get('key', '')
                certs.append(cert_entry)
    return certs


def extract_ca_certificates(config):
    """Extract CA certificates from config into a list of CA certificate values."""
    ca_certs = []
    if 'ca_certificates' in config and config['ca_certificates']:
        for ca_cert in config['ca_certificates']:
            if 'id' in ca_cert:
                ca_cert_entry = CommentedMap()
                ca_cert_entry['id'] = ca_cert['id']
                ca_cert_entry['cert'] = ca_cert.get('cert', '')
                ca_certs.append(ca_cert_entry)
    return ca_certs


def extract_keys(config):
    """Extract keys from config into a list of key values."""
    keys = []
    if 'keys' in config and config['keys']:
        for key in config['keys']:
            if 'kid' in key:
                key_entry = CommentedMap()
                key_entry['kid'] = key['kid']
                if 'pem' in key and key['pem']:
                    pem_entry = CommentedMap()
                    if 'private_key' in key['pem']:
                        pem_entry['private_key'] = key['pem']['private_key']
                    if 'public_key' in key['pem']:
                        pem_entry['public_key'] = key['pem']['public_key']
                    key_entry['pem'] = pem_entry
                if 'jwk' in key:
                    key_entry['jwk'] = key['jwk']
                keys.append(key_entry)
    return keys


def create_template(config):
    """Create template by replacing certificate values with Helm placeholders."""
    if 'certificates' in config and config['certificates']:
        for cert in config['certificates']:
            cert['cert'] = "{{ .Values.certificates[.snis[0].name].cert }}"
            cert['key'] = "{{ .Values.certificates[.snis[0].name].key }}"
    if 'ca_certificates' in config and config['ca_certificates']:
        for ca_cert in config['ca_certificates']:
            ca_cert['cert'] = "{{ .Values.ca_certificates[.id].cert }}"
    if 'keys' in config and config['keys']:
        for key in config['keys']:
            if 'pem' in key and key['pem']:
                if 'private_key' in key['pem']:
                    key['pem']['private_key'] = "{{ .Values.keys[.kid].pem.private_key }}"
                if 'public_key' in key['pem']:
                    key['pem']['public_key'] = "{{ .Values.keys[.kid].pem.public_key }}"
            if 'jwk' in key:
                key['jwk'] = "{{ .Values.keys[.kid].jwk }}"
    return config


def main():
    if len(sys.argv) < 2:
        print("Usage: kong-templatize <config_file>")
        print("Example: kong-templatize config.yaml")
        sys.exit(1)

    input_file = sys.argv[1]

    # Validate input file exists
    input_path = Path(input_file)
    if not input_path.exists():
        print(f"Error: Input file '{input_file}' not found")
        sys.exit(1)

    # Extract basename (remove .yaml or .yml extension)
    basename = input_file
    for ext in ['.yaml', '.yml']:
        if basename.endswith(ext):
            basename = basename[:-len(ext)]
            break

    # Define output files
    template_file = f"{basename}.tmpl.yaml"
    values_file = f"{basename}.certs.values.yaml"

    print(f"Processing Kong configuration: {input_file}")
    print("")

    # Initialize YAML parser
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.default_flow_style = False
    yaml.width = 4096  # Prevent line wrapping

    # Load input configuration
    with open(input_file, 'r') as f:
        config = yaml.load(f)

    # Step 1: Extract certificates to values file
    print("Extracting certificates to values file...")
    certs = extract_certificates(config)
    ca_certs = extract_ca_certificates(config)
    keys = extract_keys(config)

    if certs or ca_certs or keys:
        with open(values_file, 'w') as f:
            for cert in certs:
                yaml.dump(cert, f)
            for ca_cert in ca_certs:
                yaml.dump(ca_cert, f)
            for key in keys:
                yaml.dump(key, f)
        if certs:
            print(f"   Certificates extracted to: {values_file}")
        if ca_certs:
            print(f"   CA certificates extracted to: {values_file}")
        if keys:
            print(f"   Keys extracted to: {values_file}")
    else:
        print("   No certificates or keys found")
        # Create empty values file
        with open(values_file, 'w') as f:
            pass

    # Step 2: Create template with Helm placeholders
    print("Creating template with Helm placeholders...")
    template = create_template(config)
    print(f"   Template created: {template_file}")
    print("")

    # Step 3: Prettify the template file with key reordering
    print("Prettifying template structure...")
    template = prettify_config(template)

    # Write template file
    with open(template_file, 'w') as f:
        yaml.dump(template, f)

    print("")
    print("Kong configuration processed successfully!")
    print("")
    print("Files created:")
    print(f"   Template: {template_file}")
    print(f"   Values:   {values_file}")
    print("")


if __name__ == '__main__':
    main()
