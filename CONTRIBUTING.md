# Contributing to Payment Gateway Backend

Thank you for your interest in contributing to the Payment Gateway Backend! We welcome pull requests, feature suggestions, and bug reports.

## Code Style & Formatting
This project strictly enforces PEP 8 guidelines and Clean Architecture principles. Before submitting a PR, make sure your code passes formatting and lint checks:

```bash
make format
make lint
make test
```

## Pull Request Guidelines
1. Fork the repository and create your branch from `main`.
2. Follow the standard directory layout (`apps/<domain>/domain|services|repositories|views`).
3. Ensure all new functions have docstrings and typing annotations.
4. Include tests covering new feature logic or bug fixes (>90% test coverage target).
5. Pass pre-commit hooks before committing: `pre-commit run --all-files`.
6. Fill out the PR template completely when submitting.
