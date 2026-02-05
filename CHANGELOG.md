# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial open source release
- Next.js 16 frontend with CopilotKit integration
- Conversational AI-powered incident investigation
- LangGraph-based RCA workflow orchestrator
- Multi-provider evidence collection (Loki, CloudWatch, GitHub, ArgoCD)
- Hypothesis generation and confidence scoring
- Knowledge base configuration via YAML
- Real-time streaming responses via AG-UI protocol
- Docker and docker-compose support

### Changed
- Migrated frontend from SvelteKit to Next.js 16 with App Router
- Upgraded to React 19
- Upgraded CopilotKit to v1.51

### Fixed
- CopilotKit agent registration with runtime sync

## [0.1.0] - 2024-XX-XX

### Added
- Core RCA workflow with LangGraph
- Evidence collection from temporal sources
- Knowledge base loader for static YAML configuration
- Hypothesis ranking with hybrid scoring
- FastAPI backend with webhook support
- Provider adapters for logs, deployments, and VCS
- Unit and integration test suites

---

## Release Notes Format

### Added
New features and capabilities

### Changed
Changes to existing functionality

### Deprecated
Features that will be removed in future versions

### Removed
Features that have been removed

### Fixed
Bug fixes

### Security
Security-related changes
