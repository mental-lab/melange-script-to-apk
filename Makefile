# Melange Docker Compose Packaging System
# Simple containerized build system for Melange packages

.PHONY: all build test scan dev clean help

# Default target - build packages
all: build

# Build packages using Docker Compose
build:
	@echo "Building Melange packages with Docker Compose..."
	docker-compose --profile build up --build melange-builder

# Test built packages
test:
	@echo "Testing built packages..."
	docker-compose --profile test up --build package-tester

# Scan packages for vulnerabilities
scan:
	@echo "Scanning packages for vulnerabilities..."
	docker-compose --profile scan up --build vulnerability-scanner

# Start development environment
dev:
	@echo "Starting development environment..."
	docker-compose --profile dev up --build dev-environment

# Run full pipeline (build + test + scan)
pipeline: build test scan

# Clean up build artifacts and containers
clean:
	@echo "Cleaning up build artifacts and containers..."
	docker-compose down --volumes --remove-orphans || true
	docker system prune -f --volumes || true
	rm -rf packages/ reports/ melange.yaml keys/ || true
	@echo "Cleanup complete"

# Show help
help:
	@echo "Melange APK Packaging"
	@echo ""
	@echo "Commands:"
	@echo "  make build  - Build signed APK packages"
	@echo "  make test   - Test package installation"
	@echo "  make scan   - Scan for vulnerabilities"
	@echo "  make clean  - Clean up containers and files"
	@echo ""
	@echo "Setup:"
	@echo "  1. Put your script in tools/"
	@echo "  2. Configure package-config.yaml"
	@echo "  3. Run 'make build'"
