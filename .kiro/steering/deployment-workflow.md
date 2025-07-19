# Deployment Workflow Guidelines

## GitHub Actions CI/CD Pipeline

### Core Workflow Structure
- Use `uv` as the Python package manager for fast dependency resolution
- Run quality checks, tests, and builds in parallel when possible
- Cache dependencies to speed up workflow execution
- Use matrix builds for multiple Python versions
- Separate CI (continuous integration) and CD (continuous deployment) concerns

### Required GitHub Actions Workflows

#### 1. Continuous Integration (.github/workflows/ci.yml)
```yaml
name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  quality:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.9", "3.10", "3.11", "3.12"]
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Install uv
      uses: astral-sh/setup-uv@v3
      with:
        version: "latest"
    
    - name: Set up Python ${{ matrix.python-version }}
      run: uv python install ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: uv sync --all-extras --dev
    
    - name: Check lock file consistency
      run: uv lock --locked
    
    - name: Run pre-commit hooks
      run: uv run pre-commit run --all-files
    
    - name: Run type checking
      run: uv run mypy
    
    - name: Check for obsolete dependencies
      run: uv run deptry .

  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.9", "3.10", "3.11", "3.12"]
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Install uv
      uses: astral-sh/setup-uv@v3
      with:
        version: "latest"
    
    - name: Set up Python ${{ matrix.python-version }}
      run: uv python install ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: uv sync --all-extras --dev
    
    - name: Run tests
      run: uv run python -m pytest --cov --cov-config=pyproject.toml --cov-report=xml
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        fail_ci_if_error: true

  docs:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Install uv
      uses: astral-sh/setup-uv@v3
      with:
        version: "latest"
    
    - name: Set up Python
      run: uv python install 3.12
    
    - name: Install dependencies
      run: uv sync --all-extras --dev
    
    - name: Test documentation build
      run: uv run mkdocs build -s
```

#### 2. Continuous Deployment (.github/workflows/cd.yml)
```yaml
name: CD

on:
  release:
    types: [published]
  workflow_dispatch:
    inputs:
      version:
        description: 'Version to release'
        required: true
        type: string

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Install uv
      uses: astral-sh/setup-uv@v3
      with:
        version: "latest"
    
    - name: Set up Python
      run: uv python install 3.12
    
    - name: Install dependencies
      run: uv sync --all-extras --dev
    
    - name: Build package
      run: uvx --from build pyproject-build --installer uv
    
    - name: Upload build artifacts
      uses: actions/upload-artifact@v4
      with:
        name: dist
        path: dist/

  publish-pypi:
    needs: build
    runs-on: ubuntu-latest
    if: github.event_name == 'release'
    environment:
      name: pypi
      url: https://pypi.org/p/summer-core
    permissions:
      id-token: write  # For trusted publishing
    
    steps:
    - name: Download build artifacts
      uses: actions/download-artifact@v4
      with:
        name: dist
        path: dist/
    
    - name: Publish to PyPI
      uses: pypa/gh-action-pypi-publish@release/v1

  publish-docs:
    needs: build
    runs-on: ubuntu-latest
    if: github.event_name == 'release'
    permissions:
      contents: read
      pages: write
      id-token: write
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Install uv
      uses: astral-sh/setup-uv@v3
      with:
        version: "latest"
    
    - name: Set up Python
      run: uv python install 3.12
    
    - name: Install dependencies
      run: uv sync --all-extras --dev
    
    - name: Build documentation
      run: uv run mkdocs build
    
    - name: Setup Pages
      uses: actions/configure-pages@v4
    
    - name: Upload Pages artifact
      uses: actions/upload-pages-artifact@v3
      with:
        path: site/
    
    - name: Deploy to GitHub Pages
      uses: actions/deploy-pages@v4
```

#### 3. Dependency Updates (.github/workflows/dependencies.yml)
```yaml
name: Update Dependencies

on:
  schedule:
    - cron: '0 0 * * 1'  # Weekly on Monday
  workflow_dispatch:

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
      with:
        token: ${{ secrets.GITHUB_TOKEN }}
    
    - name: Install uv
      uses: astral-sh/setup-uv@v3
      with:
        version: "latest"
    
    - name: Set up Python
      run: uv python install 3.12
    
    - name: Update dependencies
      run: |
        uv lock --upgrade
        uv sync --all-extras --dev
    
    - name: Run tests
      run: uv run python -m pytest
    
    - name: Create Pull Request
      uses: peter-evans/create-pull-request@v5
      with:
        token: ${{ secrets.GITHUB_TOKEN }}
        commit-message: 'chore: update dependencies'
        title: 'chore: update dependencies'
        body: 'Automated dependency update'
        branch: update-dependencies
```

## Makefile Integration

### Key Makefile Commands Mapped to CI/CD
- `make install` → Install dependencies in CI
- `make check` → Quality checks (linting, type checking, dependency analysis)
- `make test` → Run test suite with coverage
- `make build` → Build wheel package
- `make publish` → Publish to PyPI
- `make docs-test` → Test documentation build
- `make docs` → Build and serve documentation

### Local Development Workflow
```bash
# Initial setup
make install

# Before committing
make check
make test

# Build and test package
make build

# Test documentation
make docs-test
```

## Environment Configuration

### Required GitHub Secrets
- `PYPI_API_TOKEN` - For PyPI publishing (if not using trusted publishing)
- `CODECOV_TOKEN` - For code coverage reporting

### Required GitHub Environments
- `pypi` - For PyPI deployment with protection rules

### Branch Protection Rules
- Require status checks to pass before merging
- Require branches to be up to date before merging
- Require review from code owners
- Restrict pushes to main branch

## Release Process

### Automated Release
1. Create and push a git tag: `git tag v1.0.0 && git push origin v1.0.0`
2. Create GitHub release from tag
3. CD workflow automatically builds and publishes to PyPI
4. Documentation is automatically deployed to GitHub Pages

### Manual Release
1. Use workflow dispatch in GitHub Actions
2. Specify version number
3. Workflow builds and creates release artifacts

## Quality Gates

### Pre-commit Hooks
- Code formatting (black, isort)
- Linting (ruff)
- Type checking (mypy)
- Security scanning (bandit)
- Documentation checks

### CI Requirements
- All tests must pass
- Code coverage must meet threshold
- Type checking must pass
- No security vulnerabilities
- Documentation must build successfully

## Caching Strategy

### GitHub Actions Cache
- Cache uv dependencies by lock file hash
- Cache pre-commit environments
- Cache mypy cache for faster type checking

### Example Cache Configuration
```yaml
- name: Cache uv dependencies
  uses: actions/cache@v4
  with:
    path: ~/.cache/uv
    key: ${{ runner.os }}-uv-${{ hashFiles('uv.lock') }}
    restore-keys: |
      ${{ runner.os }}-uv-
```