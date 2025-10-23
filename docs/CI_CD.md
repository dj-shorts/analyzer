# CI/CD Pipeline Documentation

Complete guide for Continuous Integration and Continuous Deployment pipelines using GitHub Actions.

## 🎯 Overview

The CI/CD pipeline consists of:
- **Code Quality**: Linting and formatting checks
- **Testing**: Automated test execution
- **Security**: Vulnerability scanning
- **Docker**: Image building and publishing
- **Performance**: Regression detection

## 📊 Pipeline Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   GitHub Actions                         │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐│
│  │   Lint   │  │   Test   │  │ Security │  │ Docker ││
│  │          │  │          │  │          │  │        ││
│  │ • ruff   │  │ • pytest │  │ • bandit │  │ • build││
│  │ • black  │  │ • coverage│  │ • safety │  │ • push ││
│  │ • mypy   │  │ • 3.11/12│  │ • trivy  │  │ • scan ││
│  └──────────┘  └──────────┘  └──────────┘  └────────┘│
│                                                          │
│  Status: ✅ Pass | ❌ Fail | ⚠️ Warning                 │
└─────────────────────────────────────────────────────────┘
```

## 🚀 Workflows

### 1. CI Workflow (`.github/workflows/ci.yml`)

**Triggers:**
- Push to `main` or `release/*` branches
- Pull requests to `main` or `release/*`

**Jobs:**

#### Lint Job
```yaml
- Checkout code
- Setup Python 3.11
- Install uv
- Run ruff (linter)
- Run black (formatter)
- Run mypy (type checker)
```

**Tools:**
- `ruff`: Fast Python linter
- `black`: Code formatter
- `mypy`: Static type checker

#### Test Job
```yaml
- Checkout code
- Setup Python (matrix: 3.11, 3.12)
- Install system deps (ffmpeg)
- Install Python deps
- Run pytest with coverage
- Upload to Codecov
```

**Coverage Target**: 80%+

#### Docker Job
```yaml
- Checkout code
- Setup Docker Buildx
- Build image
- Test image (run --help)
```

### 2. Security Workflow (`.github/workflows/security.yml`)

**Triggers:**
- Push to `main` or `release/*`
- Pull requests
- Weekly schedule (Sunday 00:00)

**Jobs:**

#### Bandit (Security Linter)
Scans Python code for security issues:
- SQL injection
- Command injection
- Hardcoded passwords
- Insecure random
- etc.

#### Safety (Dependency Vulnerabilities)
Checks dependencies for known vulnerabilities:
- CVE database lookup
- Security advisories
- Dependency tree analysis

#### Trivy (Docker Image Scan)
Scans Docker images for vulnerabilities:
- OS packages
- Python packages
- Config issues
- Secrets detection

### 3. Docker Publish Workflow (`.github/workflows/docker-publish.yml`)

**Triggers:**
- Push to `main` branch
- Version tags (`v*`)
- Release published

**Jobs:**

#### Build and Push
```yaml
- Checkout code
- Setup Docker Buildx
- Login to ghcr.io
- Extract metadata (tags, labels)
- Build and push image
- Scan published image
```

**Registry**: GitHub Container Registry (ghcr.io)

**Tags:**
- `main`: Latest from main branch
- `v1.2.3`: Version tag
- `v1.2`: Major.minor
- `v1`: Major version
- `sha-abc123`: Commit SHA

## ⚙️ Configuration

### Ruff Configuration (`.ruff.toml`)

```toml
target-version = "py311"
line-length = 88

[lint]
select = ["E", "W", "F", "I", "C", "B", "UP"]
ignore = ["E501", "B008", "C901"]
```

### Bandit Configuration (`.bandit`)

```ini
[bandit]
exclude_dirs = ["/tests", "/.venv"]
skips = ["B101", "B601"]
level = "LOW"
severity = "LOW"
```

### pytest Configuration (`pyproject.toml`)

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
addopts = "-v --cov=src --cov-report=term"
```

## 📊 Status Badges

Add to `README.md`:

```markdown
[![CI](https://github.com/dj-shorts/analyzer/actions/workflows/ci.yml/badge.svg)](https://github.com/dj-shorts/analyzer/actions/workflows/ci.yml)
[![Security](https://github.com/dj-shorts/analyzer/actions/workflows/security.yml/badge.svg)](https://github.com/dj-shorts/analyzer/actions/workflows/security.yml)
[![Docker](https://github.com/dj-shorts/analyzer/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/dj-shorts/analyzer/actions/workflows/docker-publish.yml)
[![codecov](https://codecov.io/gh/dj-shorts/analyzer/branch/main/graph/badge.svg)](https://codecov.io/gh/dj-shorts/analyzer)
```

## 🔧 Local Testing

### Run Linters Locally

```bash
# Ruff
uv run ruff check src/ tests/

# Black
uv run black --check src/ tests/

# Mypy
uv run mypy src/
```

### Run Tests Locally

```bash
# All tests
uv run pytest -v

# With coverage
uv run pytest --cov=src --cov-report=html

# Specific test file
uv run pytest tests/test_analyzer.py -v
```

### Run Security Scans Locally

```bash
# Bandit
pip install bandit
bandit -r src/

# Safety
pip install safety
safety check

# Trivy (requires Docker)
docker build -t dj-shorts/analyzer:test .
trivy image dj-shorts/analyzer:test
```

## 🐛 Troubleshooting

### Lint Failures

**Problem**: Ruff or Black fails
```bash
# Fix automatically
uv run ruff check --fix src/
uv run black src/
```

**Problem**: Mypy type errors
```bash
# Add type hints or ignore
# type: ignore
```

### Test Failures

**Problem**: Tests fail in CI but pass locally
```bash
# Check Python version
python --version  # Must be 3.11+

# Check system deps
which ffmpeg

# Run with same flags as CI
uv run pytest -v --cov=src
```

### Docker Build Failures

**Problem**: Build fails
```bash
# Clear Docker cache
docker builder prune -af

# Build with no cache
docker build --no-cache -t dj-shorts/analyzer:test .
```

### Security Scan Failures

**Problem**: High severity vulnerability found
```bash
# Update dependency
uv add package@latest

# Or pin to safe version
uv add "package>=1.2.3,<2.0.0"
```

## 🔒 Secrets Management

### GitHub Secrets

Required secrets (Settings → Secrets):
- `CODECOV_TOKEN`: For coverage upload
- `GITHUB_TOKEN`: Auto-provided for Docker registry

Optional secrets:
- `TESTSPRITE_API_KEY`: For test reporting
- `SLACK_WEBHOOK`: For notifications

### Adding Secrets

```bash
# Via CLI
gh secret set SECRET_NAME

# Or via web UI
# Settings → Secrets → New repository secret
```

## 📈 Performance Optimization

### Caching

All workflows use caching:
- **pip cache**: Python packages
- **Docker cache**: Build layers
- **GitHub cache**: Between runs

### Parallel Jobs

Tests run in parallel:
- Python 3.11 and 3.12 simultaneously
- Multiple test files in parallel

### Artifacts

Failed test artifacts retained for 30 days:
- Coverage reports
- Security scan results
- Test logs

## 🔄 Branch Protection

Recommended branch protection for `main`:

```yaml
Require status checks to pass:
  - lint
  - test (3.11)
  - test (3.12)
  - docker

Require pull request reviews: 1

Dismiss stale approvals: yes

Require linear history: yes

Include administrators: yes
```

## 📊 Monitoring

### Workflow Monitoring

```bash
# List recent runs
gh run list

# View specific run
gh run view <run-id>

# Watch live
gh run watch

# Re-run failed
gh run rerun <run-id>
```

### Metrics to Track

- **Build Success Rate**: % of passing builds
- **Test Coverage**: Line/branch coverage
- **Build Duration**: Time to complete
- **Security Issues**: Count by severity

## 🚀 Advanced Usage

### Matrix Testing

Test multiple configurations:

```yaml
strategy:
  matrix:
    python-version: ['3.11', '3.12']
    os: [ubuntu-latest, macos-latest]
```

### Conditional Jobs

Skip jobs based on conditions:

```yaml
if: github.event_name == 'pull_request'
```

### Manual Triggers

Add manual workflow dispatch:

```yaml
on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Environment to deploy'
        required: true
        default: 'staging'
```

## 🔗 Integration

### Codecov

Configure in `codecov.yml`:

```yaml
coverage:
  status:
    project:
      default:
        target: 80%
```

### TestSprite

Add to test job:

```yaml
- name: Run tests with TestSprite
  env:
    TESTSPRITE_API_KEY: ${{ secrets.TESTSPRITE_API_KEY }}
    TESTSPRITE_ENABLED: true
  run: uv run pytest -v
```

### Notifications

Add Slack notifications:

```yaml
- name: Notify Slack
  if: failure()
  uses: slackapi/slack-github-action@v1
  with:
    webhook: ${{ secrets.SLACK_WEBHOOK }}
```

## 📚 References

- [GitHub Actions Docs](https://docs.github.com/actions)
- [Ruff Documentation](https://beta.ruff.rs/)
- [pytest Documentation](https://docs.pytest.org/)
- [Trivy Documentation](https://aquasecurity.github.io/trivy/)
- [Bandit Documentation](https://bandit.readthedocs.io/)

## 🔗 Related Documentation

- [Testing Guide](./TESTSPRITE.md) - Test reporting
- [Docker Guide](./DOCKER.md) - Container usage
- [Security](../README.md#security) - Security best practices


