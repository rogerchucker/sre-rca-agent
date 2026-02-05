# Contributing to RCA Agent

Thank you for your interest in contributing to RCA Agent! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for everyone.

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 20+
- [uv](https://github.com/astral-sh/uv) for Python dependency management

### Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/YOUR_ORG/rca-agent.git
   cd rca-agent
   ```

2. **Install backend dependencies**
   ```bash
   uv sync
   ```

3. **Install frontend dependencies**
   ```bash
   cd frontend
   npm install
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run the development servers**
   ```bash
   # Terminal 1: Backend
   uv run uvicorn api.main:app --reload --port 8080

   # Terminal 2: Frontend
   cd frontend && npm run dev
   ```

## How to Contribute

### Reporting Bugs

1. Check existing [issues](https://github.com/YOUR_ORG/rca-agent/issues) to avoid duplicates
2. Use the bug report template
3. Include:
   - Clear description of the issue
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, Python version, etc.)

### Suggesting Features

1. Check existing issues and discussions
2. Use the feature request template
3. Describe the use case and proposed solution

### Submitting Changes

1. **Fork the repository**

2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes**
   - Follow the code style guidelines below
   - Add tests for new functionality
   - Update documentation as needed

4. **Run tests and linting**
   ```bash
   # Backend
   uv run pytest
   uv run ruff check .
   uv run ruff format --check .

   # Frontend
   cd frontend && npm run lint
   ```

5. **Commit your changes**
   ```bash
   git commit -m "feat: add your feature description"
   ```

   Follow [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat:` new feature
   - `fix:` bug fix
   - `docs:` documentation changes
   - `refactor:` code refactoring
   - `test:` adding tests
   - `chore:` maintenance tasks

6. **Push and create a Pull Request**
   ```bash
   git push origin feature/your-feature-name
   ```

## Code Style Guidelines

### Python

- Follow PEP 8 style guidelines
- Use type hints for function signatures
- Use `ruff` for linting and formatting
- Use Pydantic models for data validation
- Keep functions focused and well-documented

```python
def process_evidence(
    evidence: list[Evidence],
    time_range: TimeRange,
) -> ProcessedEvidence:
    """Process raw evidence within the given time range.

    Args:
        evidence: List of evidence items to process
        time_range: Time window for filtering

    Returns:
        Processed and summarized evidence
    """
    ...
```

### TypeScript/React

- Use TypeScript strict mode
- Prefer functional components with hooks
- Use `interface` for object types
- Follow the existing component structure

```tsx
interface IncidentCardProps {
  incident: Incident;
  onSelect: (id: string) => void;
}

export function IncidentCard({ incident, onSelect }: IncidentCardProps) {
  // ...
}
```

### YAML Configuration

- Use `snake_case` for keys
- Include comments for complex configurations
- Validate against schemas when available

## Project Structure

```
rca-agent/
├── api/                 # FastAPI endpoints
├── core/                # Core workflow logic
│   ├── orchestrator.py  # LangGraph workflow
│   ├── models.py        # Pydantic models
│   ├── scoring.py       # Hypothesis scoring
│   └── prompts.py       # LLM prompts
├── providers/           # External service adapters
│   ├── log_store/       # Loki, CloudWatch, etc.
│   ├── vcs/             # GitHub, GitLab
│   └── deploy_tracker/  # ArgoCD, Spinnaker
├── catalog/             # Tool schemas and instances
├── kb/                  # Knowledge base configurations
├── frontend/            # Next.js + CopilotKit UI
└── tests/               # Test suites
```

## Testing

### Running Tests

```bash
# All tests
uv run pytest

# With coverage
uv run pytest --cov=core --cov=api --cov-report=html

# Specific test file
uv run pytest tests/unit/test_scoring.py

# Integration tests only
uv run pytest tests/integration/
```

### Writing Tests

- Place unit tests in `tests/unit/`
- Place integration tests in `tests/integration/`
- Use fixtures from `tests/conftest.py`
- Mock external services appropriately

## Documentation

- Update README.md for user-facing changes
- Update OUTLINE.md for architectural changes
- Add docstrings to public functions and classes
- Update API documentation for endpoint changes

## Release Process

1. Update CHANGELOG.md with changes
2. Update version in pyproject.toml
3. Create a release PR
4. After merge, tag the release

## Getting Help

- Open a [Discussion](https://github.com/YOUR_ORG/rca-agent/discussions) for questions
- Join our community chat (if available)
- Check existing documentation in `/docs`

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
