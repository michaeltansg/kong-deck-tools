#!/usr/bin/env python3
"""
hydrate.py
Renders a Kong template file by substituting certificate values from values file.
This reverses the templatize operation.

Usage: kong-hydrate <template_file>
Example: kong-hydrate config.tmpl.yaml

Uses ruamel.yaml for format preservation to ensure lossless round-trips.
"""

import re
import sys
from io import StringIO
from pathlib import Path
from ruamel.yaml import YAML


def load_certificate_values(file_path):
    """Load certificate values from values file."""
    with open(file_path, 'r') as f:
        content = f.read()

    # Split by 'name:', 'id:', or 'kid:' but keep the delimiter
    parts = re.split(r'(?=^(?:name|id|kid): )', content, flags=re.MULTILINE)

    yaml = YAML()
    yaml.preserve_quotes = True

    certs = []
    ca_certs = []
    keys = []
    for part in parts:
        part = part.strip()
        if part:
            try:
                doc = yaml.load(StringIO(part))
                if doc and 'kid' in doc:
                    keys.append(doc)
                elif doc and 'name' in doc:
                    certs.append(doc)
                elif doc and 'id' in doc:
                    ca_certs.append(doc)
            except Exception:
                pass

    return certs, ca_certs, keys


def load_yaml(file_path):
    """Load a single YAML document with format preservation."""
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.default_flow_style = False

    with open(file_path, 'r') as f:
        return yaml.load(f)


def main():
    if len(sys.argv) < 2:
        print("Usage: kong-hydrate <template_file>")
        print("Example: kong-hydrate config.tmpl.yaml")
        sys.exit(1)

    template_file = sys.argv[1]

    # Validate input file exists
    if not Path(template_file).exists():
        print(f"Error: Template file '{template_file}' not found")
        sys.exit(1)

    # Derive basename by stripping .tmpl.yaml or .tmpl.yml extension
    basename = template_file
    for ext in ['.tmpl.yaml', '.tmpl.yml']:
        if basename.endswith(ext):
            basename = basename[:-len(ext)]
            break

    values_file = f"{basename}.certs.values.yaml"
    output_file = f"{basename}.rendered.yaml"

    if not Path(values_file).exists():
        print(f"Error: Values file '{values_file}' not found")
        sys.exit(1)

    print("Rendering Kong configuration...")
    print(f"   Template: {template_file}")
    print(f"   Values:   {values_file}")
    print("")

    # Load template
    template = load_yaml(template_file)

    # Load certificate values
    cert_values, ca_cert_values, key_values = load_certificate_values(values_file)

    # Create a mapping of SNI name to certificate data
    cert_map = {}
    for cert_doc in cert_values:
        if cert_doc and 'name' in cert_doc:
            cert_map[cert_doc['name']] = {
                'cert': cert_doc.get('cert', ''),
                'key': cert_doc.get('key', '')
            }

    # Create a mapping of ID to CA certificate data
    ca_cert_map = {}
    for ca_cert_doc in ca_cert_values:
        if ca_cert_doc and 'id' in ca_cert_doc:
            ca_cert_map[ca_cert_doc['id']] = {
                'cert': ca_cert_doc.get('cert', '')
            }

    # Create a mapping of kid to key data
    key_map = {}
    for key_doc in key_values:
        if key_doc and 'kid' in key_doc:
            key_map[key_doc['kid']] = key_doc

    # Substitute certificates in template
    if 'certificates' in template:
        for cert in template['certificates']:
            if 'snis' in cert and len(cert['snis']) > 0:
                sni_name = cert['snis'][0]['name']
                if sni_name in cert_map:
                    print(f"   Substituting certificate for: {sni_name}")
                    cert_value = cert_map[sni_name]['cert']
                    key_value = cert_map[sni_name]['key']

                    # Ensure keys end with newline to match Kong's format
                    if not key_value.endswith('\n'):
                        key_value = key_value + '\n'

                    cert['cert'] = cert_value
                    cert['key'] = key_value

    # Substitute CA certificates in template
    if 'ca_certificates' in template:
        for ca_cert in template['ca_certificates']:
            if 'id' in ca_cert:
                ca_id = ca_cert['id']
                if ca_id in ca_cert_map:
                    print(f"   Substituting CA certificate for: {ca_id}")
                    ca_cert['cert'] = ca_cert_map[ca_id]['cert']

    # Substitute keys in template
    if 'keys' in template:
        for key in template['keys']:
            if 'kid' in key:
                kid = key['kid']
                if kid in key_map:
                    print(f"   Substituting key for: {kid}")
                    key_doc = key_map[kid]
                    if 'pem' in key and 'pem' in key_doc:
                        if 'private_key' in key['pem'] and 'private_key' in key_doc['pem']:
                            key['pem']['private_key'] = key_doc['pem']['private_key']
                        if 'public_key' in key['pem'] and 'public_key' in key_doc['pem']:
                            key['pem']['public_key'] = key_doc['pem']['public_key']
                    if 'jwk' in key and 'jwk' in key_doc:
                        key['jwk'] = key_doc['jwk']

    # Write rendered output with format preservation
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.default_flow_style = False
    yaml.width = 4096  # Prevent line wrapping

    with open(output_file, 'w') as f:
        yaml.dump(template, f)

    print("")
    print("Configuration rendered successfully!")
    print(f"   Output: {output_file}")
    print("")


if __name__ == '__main__':
    main()
