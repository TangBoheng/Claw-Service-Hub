# Changelog

All notable changes to Claw-Service-Hub will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Rate limiting module (`server/ratelimit.py`) for API request throttling
- Input validation module (`server/validators.py`) with request validation
- Health check endpoint (`/health`) for service monitoring
- Structured logging with `server/logging_config.py`
- SQLite-based data persistence (`server/storage.py`)
- Comprehensive test suite with pytest
- Code quality tools configuration (`ruff.toml`, `mypy.ini`)

### Changed
- Upgraded to Python 3.10+ minimum requirement
- Migrated to `pyproject.toml` for package management

### Fixed
- Fixed key manager persistence issues
- Fixed tunnel manager cleanup logic
- Fixed storage module time parsing

## [0.1.0] - 2026-03-22

### Added
- **Core Features**
  - Service registration and discovery (WebSocket + REST API)
  - Service invocation tunneling
  - Rating system
  - Key-based authentication mechanism
  
- **Infrastructure**
  - Docker support with `docker/Dockerfile`
  - Environment-based configuration (`.env.example`)
  - GitHub Actions CI/CD workflow
  
- **Testing**
  - Unit tests for key_manager, registry, tunnel, storage
  - Test fixtures and conftest configuration
  
- **Documentation**
  - API documentation (`docs/api.md`)
  - Deployment guide (`docs/deployment.md`)
  - Installation guide (`docs/installation.md`)
  - Quick start guide (`docs/quickstart.md`)

### Changed
- Migrated from `requirements.txt` to `pyproject.toml`
- Added version management with `__version__`

## [0.0.1] - 2026-03-17

### Added
- Initial release
- Basic service marketplace functionality
- Client-server architecture with WebSocket communication

---

## Version History

| Version | Date | Status |
|---------|------|--------|
| 0.1.0 | 2026-03-22 | Alpha |
| 0.0.1 | 2026-03-17 | Initial |

## Upgrade Notes

### Upgrading to 0.1.0
- Ensure Python 3.10+ is installed
- Update dependencies: `pip install -U claw-service-hub`
- Review `.env.example` for new environment variables
- Run database migration if upgrading from 0.0.1

## Deprecations

No deprecated features at this time.

## Security

For security vulnerabilities, please see [SECURITY.md](./SECURITY.md).