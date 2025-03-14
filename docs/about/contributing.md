# Contributing

Thank you for your interest in contributing to Pydantic2! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

Please read and follow our [Code of Conduct](https://github.com/markolofsen/pydantic2/blob/main/CODE_OF_CONDUCT.md).

## How to Contribute

There are many ways to contribute to Pydantic2:

1. **Report bugs**: If you find a bug, please report it by creating an issue on GitHub.
2. **Suggest features**: If you have an idea for a new feature, please create an issue on GitHub.
3. **Improve documentation**: If you find a mistake in the documentation or think something could be explained better, please create a pull request.
4. **Write code**: If you want to contribute code, please create a pull request.

## Development Setup

To set up a development environment:

1. Fork the repository on GitHub.
2. Clone your fork:
   ```bash
   git clone https://github.com/markolofsen/pydantic2.git
   cd pydantic2
   ```
3. Install the package in development mode:
   ```bash
   pip install -e ".[dev]"
   ```
4. Install pre-commit hooks:
   ```bash
   pre-commit install
   ```

## Pull Request Process

1. Create a new branch for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Make your changes.
3. Run the tests:
   ```bash
   pytest
   ```
4. Run the linters:
   ```bash
   black .
   flake8
   isort .
   ```
5. Commit your changes:
   ```bash
   git commit -m "Add your feature"
   ```
6. Push your changes to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```
7. Create a pull request on GitHub.

## Coding Standards

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) for code style.
- Use [Black](https://black.readthedocs.io/en/stable/) for code formatting.
- Use [isort](https://pycqa.github.io/isort/) for import sorting.
- Use [flake8](https://flake8.pycqa.org/en/latest/) for linting.
- Write docstrings for all functions, classes, and methods.
- Write tests for all new features.

## Testing

We use [pytest](https://docs.pytest.org/en/stable/) for testing. To run the tests:

```bash
pytest
```

To run the tests with coverage:

```bash
pytest --cov=src/pydantic2
```

## Documentation

We use [MkDocs](https://www.mkdocs.org/) for documentation. To build the documentation:

```bash
mkdocs build
```

To serve the documentation locally:

```bash
mkdocs serve
```

## Release Process

1. Update the version number in `setup.cfg`.
2. Update the changelog.
3. Create a new release on GitHub.
4. Build and upload the package to PyPI:
   ```bash
   python -m build
   twine upload dist/*
   ```

## Contact

If you have any questions, please contact [info@unrealos.com](mailto:info@unrealos.com).
