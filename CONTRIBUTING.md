# Contributing to Claw-Service-Hub

Thank you for your interest in contributing to Claw-Service-Hub! This document outlines the guidelines and processes for contributing to the project.

## Development Environment Setup

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/your-username/Claw-Service-Hub.git
   cd Claw-Service-Hub
   ```
3. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```
5. **Install development dependencies**:
   ```bash
   pip install black isort mypy pytest
   ```

## Code Style and Formatting

We enforce consistent code style using the following tools:

- **Black**: Code formatter (line length: 88 characters)
- **isort**: Import sorting
- **Type annotations**: All functions and methods should have type hints
- **Docstrings**: Use Google-style docstrings for public APIs

### Pre-commit hooks (Recommended)

Install pre-commit hooks to automatically format your code before committing:

```bash
pip install pre-commit
pre-commit install
```

### Manual formatting

If you prefer to format manually, run these commands before committing:

```bash
black .
isort .
mypy .  # Check type annotations
```

## Pull Request Process

1. **Create a new branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. **Write tests** for your changes (if applicable)
3. **Ensure all tests pass**:
   ```bash
   pytest
   ```
4. **Commit your changes** with clear, descriptive messages
5. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```
6. **Open a Pull Request** on GitHub
   - Provide a clear description of your changes
   - Reference any related issues
   - Ensure the PR passes all CI checks

## Code Review Guidelines

- Be respectful and constructive in your feedback
- Focus on the code, not the person
- Explain the reasoning behind suggestions
- Acknowledge good work and improvements

## Reporting Bugs

If you find a bug, please check if it has already been reported in the [Issues](https://github.com/TangBoheng/Claw-Service-Hub/issues) section. If not, create a new issue using the bug report template.

## Feature Requests

For new features or enhancements, please use the feature request template and provide as much detail as possible about the proposed functionality.

## License

By contributing to this project, you agree that your contributions will be licensed under the project's [LICENSE](LICENSE).