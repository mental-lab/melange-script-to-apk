# Melange APK Packaging

Package your scripts as signed APK packages using Docker Compose.

## Quick Start

**1. Add your script:**
```bash
cp your-script.sh tools/
```

**2. Configure package:**
```yaml
# package-config.yaml
name: my-tool
version: 1.0.0
description: "My deployment tool"
script: my-script.sh
language: bash
```

**3. Build package:**
```bash
make build
```

**4. Results:**
- Signed APK packages in `packages/`
- RSA signing keys in `keys/`

## Commands

- `make build` - Build signed APK packages
- `make test` - Test package installation  
- `make clean` - Clean up containers and files
- `make help` - Show all commands

## Why APK Packages?

**Problem**: ISVs ship tarballs with manual instructions that customers execute incorrectly

**Solution**: Professional signed packages with automated installation

- **Security**: Cryptographically signed
- **Reliability**: No manual installation steps
- **Professional**: Enterprise-grade packaging
- **Simple**: Single command builds

## Requirements

- Docker and Docker Compose
- Your script in `tools/` directory
- Configured `package-config.yaml`

## Configuration Options

```yaml
name: package-name          # Required
version: 1.0.0             # Required  
description: "Description"  # Required
script: script-name.sh     # Required
language: bash             # bash, python, go
dependencies: [bash, curl] # Optional
systemd_service: false    # Optional
```

## Templates

- **bash**: Shell scripts, deployment tools
- **python**: Applications, data processing  
- **go**: High-performance utilities

## Security

- RSA-4096 package signing
- Vulnerability scanning with Grype
- Minimal Chainguard base images
- SBOM generation for compliance

