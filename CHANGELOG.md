# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.1.0] - 2026-02-07

### Added
- **Caching System**: In-memory caching with TTL support for GitHub API calls
- **Rate Limiting**: SlowAPI integration with configurable limits (default: 10/minute)
- **Structured Logging**: JSON-formatted logs for production monitoring
- **WebSocket Support**: Real-time analysis progress updates via WebSocket
- **Code Quality Analysis**: Automated code quality metrics and scoring
- **Comparative Analysis**: Compare multiple repositories across tech stack, architecture, and complexity
- **Comprehensive Testing**: pytest-based test suite with fixtures and mocks
- **CI/CD Pipeline**: GitHub Actions workflow for automated testing
- **Development Dependencies**: Separate requirements-dev.txt for development tools
- **Documentation**: ARCHITECTURE.md, DEPLOYMENT.md, and CONTRIBUTING.md

### Changed
- GitHub service now uses caching to reduce API calls
- Main application includes rate limiting middleware
- Health check endpoint now reports all available features
- API routes reorganized with new comparative and code quality endpoints

### Fixed
- Foreign key constraint error when creating analysis sessions (added flush before session creation)

## [3.0.0] - 2026-02-05

### Added
- Split table architecture for normalized data storage
- Production-ready async flow with proper session management
- Background task processing for repository analysis
- Single Gemini API call per repository
- Comprehensive error handling and logging
- Mock fallback for Gemini service

### Changed
- Migrated from monolithic JSON storage to split tables
- Improved database schema with proper foreign keys
- Enhanced file filtering with priority system

## [2.0.0] - 2026-01-15

### Added
- FastAPI backend with async SQLAlchemy
- GitHub API integration
- Gemini LLM integration
- Q&A functionality
- SQLite database storage

## [1.0.0] - 2026-01-01

### Added
- Initial release
- Basic repository analysis
- Simple file fetching
