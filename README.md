# Passbolt LDAPS Certificate Bundler

A tool for retrieving and configuring LDAPS certificates for Passbolt. Automatically retrieves and formats certificate chains from LDAPS servers, handling both standard and self-signed certificates.

## Features

- Retrieves complete certificate chains from LDAPS servers
- Handles self-signed certificates commonly used in internal LDAP servers
- Validates certificate chain integrity
- Supports both PEM and DER output formats
- Provides detailed debugging information
- Compatible with Passbolt's LDAPS configuration requirements

## Requirements

### System Requirements
- [OpenSSL](https://www.openssl.org/) command-line tool
  - Usually available as package `openssl` in most Linux distributions and package managers
  - The script uses `openssl s_client` to establish an SSL/TLS connection and retrieve the certificate chain
- Python 3.11 or higher
  - Required for running the tool
  - On Debian/Ubuntu, you may need to install the following additional packages:
    ```bash
    sudo apt-get install python3-venv python3-pip build-essential libssl-dev libffi-dev python3-dev
    ```
- Pip (Python package installer)
  - The setup script will attempt to install pip if it is missing, but it is recommended to install it beforehand

### Python Package Requirements
- cryptography package (installed automatically in the virtual environment)

## Setup

The tool uses a Python virtual environment to manage dependencies. To set up:

1. Make the setup script executable:
```shell
chmod +x setup_python_env.sh
```

2. Run the setup script:
- This will create a virtual environment and install all required dependencies. The script will exit when complete.
```shell
./setup_python_env.sh
```

👉 After setup completes, you need to activate the virtual environment once per shell session before running the tool:
```shell
source venv/bin/activate
```

## Usage

### Basic Usage

1. First, activate the virtual environment in your shell:
```shell
source venv/bin/activate
```

2. Run the script with your LDAPS server:
```shell
python3 ldaps_cert_chain_retriever.py --server your.ldaps.server
```

3. When you're done, you can deactivate the virtual environment:
```shell
deactivate
```

### Saving the Certificate Bundle

To save the certificate bundle to a file:
```shell
python3 ldaps_cert_chain_retriever.py --server your.ldaps.server > ldaps_bundle.crt
```

### Testing

Test the tool using the test mode:
```shell
python3 ldaps_cert_chain_retriever.py --test --debug
```

The test mode will try multiple test servers and show detailed connection information if --debug is enabled.

## Certificate Installation

### Standard Installation

After obtaining the certificate bundle:

1. Copy the certificate to the appropriate location:
```shell
sudo cp ldaps_bundle.crt /etc/ssl/certs/
```

2. Set proper permissions:
```shell
sudo chown root:root /etc/ssl/certs/ldaps_bundle.crt
sudo chmod 644 /etc/ssl/certs/ldaps_bundle.crt
```

3. Configure your LDAP client to use the certificate by editing `/etc/ldap/ldap.conf`:
```
TLS_CACERT /etc/ssl/certs/ldaps_bundle.crt
```

## Passbolt Integration

Passbolt can be configured to use the LDAPS certificate in two ways:

### 1. Using passbolt.php (Recommended)

Add the following configuration to your `config/passbolt.php`:

```php
return [
    'passbolt' => [
        'plugins' => [
            'directorySync' => [
                'security' => [
                    'sslCustomOptions' => [
                        'enabled' => true,
                        'verifyPeer' => true,
                        'cadir' => '/etc/ssl/certs',
                        'cafile' => '/etc/ssl/certs/ldaps_bundle.crt',
                    ],
                ],
            ],
        ],
    ],
];
```

### 2. Using Environment Variables

```shell
# Enable custom SSL options
export PASSBOLT_PLUGINS_DIRECTORY_SYNC_SECURITY_SSL_CUSTOM_OPTIONS_ENABLED=true

# Enable peer verification
export PASSBOLT_PLUGINS_DIRECTORY_SYNC_SECURITY_SSL_CUSTOM_OPTIONS_VERIFY_PEER=true

# Set the CA directory (where system certificates are stored)
export PASSBOLT_PLUGINS_DIRECTORY_SYNC_SECURITY_SSL_CUSTOM_OPTIONS_CADIR=/etc/ssl/certs

# Set the path to your LDAPS certificate bundle
export PASSBOLT_PLUGINS_DIRECTORY_SYNC_SECURITY_SSL_CUSTOM_OPTIONS_CAFILE=/etc/ssl/certs/ldaps_bundle.crt
```

> **Note**: 
> - Environment variables must be in uppercase
> - Paths should be absolute
> - Use either the `ldap.conf` method or the Passbolt configuration method, not both

## Docker-Specific Installation

If you're running Passbolt in Docker, you'll need to:

1. **Get the Certificate Bundle**:
```shell
python3 ldaps_cert_chain_retriever.py --server your.ldaps.server > ldaps_bundle.crt
```

2. **Choose an Installation Method**:

   a. **Using Volume Mount (Recommended)**:
   ```shell
   # Add to your docker-compose.yml
   volumes:
     - ./ldaps_bundle.crt:/etc/ssl/certs/ldaps_bundle.crt:ro
   ```

   b. **Using Environment Variables**:
   ```shell
   # Add to your docker-compose.yml
   environment:
     - PASSBOLT_PLUGINS_DIRECTORY_SYNC_SECURITY_SSL_CUSTOM_OPTIONS_ENABLED=true
     - PASSBOLT_PLUGINS_DIRECTORY_SYNC_SECURITY_SSL_CUSTOM_OPTIONS_VERIFY_PEER=true
     - PASSBOLT_PLUGINS_DIRECTORY_SYNC_SECURITY_SSL_CUSTOM_OPTIONS_CADIR=/etc/ssl/certs
     - PASSBOLT_PLUGINS_DIRECTORY_SYNC_SECURITY_SSL_CUSTOM_OPTIONS_CAFILE=/etc/ssl/certs/ldaps_bundle.crt
   ```

3. **Restart the Container**:
```shell
docker-compose restart passbolt
```

> **Note**: 
> - The volume mount method is recommended as it persists across container recreations
> - Keep your certificate bundle in version control (if appropriate) or a secure location
> - Update the certificate bundle when it expires or is renewed
> - Consider using Docker secrets for production environments

## Running the Tool in a Dedicated Container

You can also build and run this tool in a fully isolated container (without installing Python or dependencies on your host).

A sample `Dockerfile` is provided in the repository.

### Build the container:

```shell
docker build -t ldaps-cert-tool .
```

### Run the tool:

```shell
docker run --rm ldaps-cert-tool --server your.ldaps.server --debug
```

### Save the certificate bundle to a file:

```shell
docker run --rm -v $(pwd):/out ldaps-cert-tool --server your.ldaps.server --output /out/ldaps_bundle.crt
```

- The output bundle will appear in your current directory as `ldaps_bundle.crt`.
- You can then use it with Passbolt as described above.


## Using the Makefile (optional convenience)

A `Makefile` is provided to simplify common operations:

```
make build                   # Build the Docker image
make run SERVER=your.ldaps.server  # Run the tool interactively (prints certs to stdout)
make save SERVER=your.ldaps.server # Save the certificate bundle to ./ldaps_bundle.crt
make test                    # Run unit tests inside the container
make help                    # Show help
```

### Build the container:

```shell
make build
```

### Run the tool:

```shell
make run SERVER=your.ldaps.server
```

### Save the certificate bundle to a file:

```shell
make save SERVER=your.ldaps.server
```

- The output bundle will appear in your current directory as `ldaps_bundle.crt`.
- You can then use it with Passbolt as described above.

### Run unit tests:

```shell
make test
```

## Advanced Debugging

### Using ldapsearch

For additional debugging, you can use the `ldapsearch` command (from the ldap-utils package):

> **Important**: When testing with Passbolt, execute ldapsearch as the web user, not as root:
> - Debian/Ubuntu: `www-data`
> - openSUSE: `wwwrun`
> - RHEL-based: `nginx`

Example command:
```shell
sudo su -s /bin/bash -c 'ldapsearch -x -D "username" -W -H ldaps://your_ldap_host -b "dc=domain,dc=ext" -d 9' www-data
```

### Common Issues

1. **Certificate Chain Issues**
   - Use debug mode to verify the complete certificate chain
   - Ensure all intermediate certificates are included
   - Verify the certificate is properly chained for OpenLDAP

2. **Permission Issues**
   - Verify the web user has read access to the certificate
   - Check SELinux contexts if applicable
   - Ensure proper ownership and permissions (644)

3. **Connection Issues**
   - Verify LDAPS port (636) is accessible
   - Check firewall rules
   - Test with debug mode for detailed connection information
   - Verify DNS resolution for the LDAP server

4. **Passbolt-Specific Issues**
   - Ensure the certificate is trusted by the Passbolt instance
   - Verify the certificate configuration in passbolt.php
   - Check web server user permissions
   - Verify LDAP connection parameters in Passbolt

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

## License

This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License (AGPL) as published by the Free Software Foundation version 3.

The name "Passbolt" is a registered trademark of Passbolt SA, and Passbolt SA hereby declines to grant a trademark license to "Passbolt" pursuant to the GNU Affero General Public License version 3 Section 7(e), without a separate agreement with Passbolt SA.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program. If not, see [GNU Affero General Public License v3](https://www.gnu.org/licenses/agpl-3.0.html).
