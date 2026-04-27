# Development Scripts

Helper scripts for development, testing, and deployment.

## Quick Start

```bash
# First-time setup
./scripts/setup.sh

# Start development server
./scripts/start.sh dev

# Run all checks before commit
./scripts/dev.sh check
```

## Available Scripts

### `verify.sh` — Verify Setup

Verify Python 3.13 setup and check dependencies.

```bash
# Check Python version and dependencies
./scripts/verify.sh
```

**Checks:**
- Python version (must be ≥3.13)
- Virtual environment exists
- Core dependencies installed
- Development dependencies installed
- Configuration files valid
- Platform detection working

Use this to troubleshoot setup issues.

---

### `setup.sh` — Initial Setup

Initialize development environment and create environment files.

**Requirements:** Python ≥3.13

```bash
# Verify Python version
python3 --version  # Must show 3.13.x or higher

# Development mode (macOS compatible, no GPU)
./scripts/setup.sh

# Production mode (with GPU support)
./scripts/setup.sh --gpu
```

**Does:**
- Verifies Python ≥3.13 is available
- Installs dependencies via `uv sync` (optionally with GPU support)
- Creates `.env.dev` from `.env.example`
- Creates `.env.prod` from `.env.example`
- Makes all scripts executable
- Verifies app imports correctly

**Configure:**
After setup, customize the environment files:
```bash
# Edit development settings
nano .env.dev

# Edit production settings (for Linux+GPU deployment)
nano .env.prod
```

---

### `start.sh` — Start Server

Start the vLLM inference server with environment-specific configuration.

```bash
# Development mode (default, macOS)
./scripts/start.sh dev

# Production mode (Linux + GPU)
./scripts/start.sh prod

# Test mode (10s timeout, debug logging)
./scripts/start.sh test
```

**Environment Files:**
- `dev` — Loads `.env.dev` (Mock vLLM, debug logging, GPU mem 0.5, batch size 32, context 2048)
- `prod` — Loads `.env.prod` (Real vLLM + CUDA, info logging, GPU mem 0.9, batch size 256, context 4096)
- `test` — Loads `.env.dev`, uses port 8001, 10s timeout

**Environment Configuration:**
Each mode loads its corresponding `.env` file:
- `.env.dev` — Development settings (macOS compatible, relaxed limits)
- `.env.prod` — Production settings (Linux+GPU, strict rate limits, full features)

Edit these files to customize model parameters, rate limits, and other settings.

**Check:**
```bash
curl http://localhost:8000/health
curl http://localhost:8000/system
```

---

### `lint.sh` — Code Quality Checks

Run Ruff linter and MyPy type checker.

```bash
# Check code quality
./scripts/lint.sh

# Auto-fix linting issues
./scripts/lint.sh --fix
```

**Checks:**
- Ruff: PEP 8, imports, complexity, bugbear rules
- MyPy: Type hints and consistency

**Config:** `pyproject.toml` → `[tool.ruff]` and `[tool.mypy]`

---

### `format.sh` — Code Formatting

Format code with Black and Ruff.

```bash
# Format all code
./scripts/format.sh
```

**Does:**
1. Runs Black formatter (100-char line length)
2. Runs Ruff autofix (imports, style fixes)

**Config:** `pyproject.toml` → `[tool.black]` and `[tool.ruff]`

---

### `test.sh` — Run Tests

Execute pytest test suite.

```bash
# Run all tests
./scripts/test.sh

# Verbose output
./scripts/test.sh -v

# Run specific test file
./scripts/test.sh tests/test_platform_detection.py

# Run tests matching pattern
./scripts/test.sh -k "startup"
```

**Config:** `pyproject.toml` → `[tool.pytest.ini_options]`

---

### `dev.sh` — Development Workflow

Complete development workflow (format → lint → test).

```bash
# Check everything (no autofix)
./scripts/dev.sh check

# Format + Lint + Test (autofix enabled)
./scripts/dev.sh all

# Run just linting
./scripts/dev.sh lint

# Run just formatting
./scripts/dev.sh format

# Run just tests
./scripts/dev.sh test
```

**Recommended:** Run before each commit:
```bash
./scripts/dev.sh check
```

---

## Development Workflow

### Initial Setup

```bash
# 1. Run setup once
./scripts/setup.sh

# 2. Customize development settings (optional)
nano .env.dev

# 3. Customize production settings (for deployment)
nano .env.prod
```

### Daily Development

```bash
# 1. Start server (loads .env.dev)
./scripts/start.sh dev

# 2. In another terminal, make code changes

# 3. Before committing
./scripts/dev.sh check

# 4. If issues, auto-fix
./scripts/format.sh

# 5. Commit and push
git add .
git commit -m "..."
```

### Full Quality Check (Before Pushing)

```bash
# Complete check with auto-fix
./scripts/dev.sh all

# Or run individually:
./scripts/format.sh    # Auto-fix code style
./scripts/lint.sh      # Check for errors
./scripts/test.sh -v   # Run all tests

# Production deployment check (in Linux+GPU environment)
./scripts/start.sh prod  # Verify production mode works
```

---

## Linting Rules

### Ruff Linter

**Selected Rules:**
- `E`, `W` — PEP 8 errors and warnings
- `F` — Pyflakes (undefined names, unused imports)
- `I` — isort (import sorting)
- `UP` — pyupgrade (modern Python syntax)
- `B` — flake8-bugbear (error detection)
- `C4` — comprehension checks
- `ARG` — unused arguments
- `ASYNC` — async/await issues
- `C90` — McCabe complexity (max 10)

**Exceptions:**
- `__init__.py`: Allow unused imports (F401)
- `tests/*`: Allow unused test arguments (ARG001)
- `E501`: Line length (handled by Black)
- `W503`: Line breaks before operators

**Config:** `pyproject.toml` → `[tool.ruff.lint]`

---

### Black Formatter

**Settings:**
- Line length: 100 characters
- Target: Python 3.13+
- Single quotes where possible (standard)

**Config:** `pyproject.toml` → `[tool.black]`

---

### MyPy Type Checking

**Level:** `check_untyped_defs` (medium strictness)

**Ignores:**
- `vllm.*` — GPU library (no types)
- `transformers.*` — Third-party (no types)
- `huggingface_hub.*` — Third-party
- `prometheus_client.*` — Third-party

**Config:** `pyproject.toml` → `[tool.mypy]`

---

## Environment Variables

Configuration is loaded from environment files:

**Development (.env.dev):**
```bash
CHAT_MODEL              # Model name (default: Qwen/Qwen2.5-7B-Instruct-AWQ)
CHAT_GPU_MEM_UTIL=0.5   # GPU memory utilization (development)
CHAT_MAX_NUM_SEQS=32    # Max concurrent sequences (development)
CHAT_MAX_MODEL_LEN=2048 # Smaller context window for faster testing
LOG_LEVEL=debug         # Verbose logging
```

**Production (.env.prod):**
```bash
CHAT_GPU_MEM_UTIL=0.9   # High GPU memory utilization
CHAT_MAX_NUM_SEQS=256   # Higher batch for throughput
CHAT_MAX_MODEL_LEN=4096 # Full context window
CHAT_DTYPE=bfloat16     # Mixed precision for speed
LOG_LEVEL=info          # Standard logging
EMBEDDING_MODEL         # Optional embedding model
RATE_LIMIT_*            # Strict rate limits
```

Edit `.env.dev` and `.env.prod` to customize settings for your environment.

---

## Troubleshooting

### "Virtual environment not found"

```bash
# Setup first
./scripts/setup.sh
```

### Lint errors won't go away

```bash
# Auto-fix issues
./scripts/format.sh

# Then check again
./scripts/lint.sh
```

### Tests fail but locally work

```bash
# Clear cache and run again
rm -rf .pytest_cache __pycache__
./scripts/test.sh -v
```

### Scripts not executable

```bash
# Make executable
chmod +x scripts/*.sh
```

---

## Continuous Integration

### GitHub Actions

```yaml
- name: Setup
  run: ./scripts/setup.sh

- name: Lint
  run: ./scripts/lint.sh

- name: Format Check
  run: ./scripts/format.sh --check

- name: Tests
  run: ./scripts/test.sh -v
```

---

## Quick Reference

| Task | Command |
|------|---------|
| Verify setup | `./scripts/verify.sh` |
| First-time setup | `./scripts/setup.sh` |
| Customize dev config | `nano .env.dev` |
| Customize prod config | `nano .env.prod` |
| Start dev server | `./scripts/start.sh dev` |
| Start prod server | `./scripts/start.sh prod` |
| Format code | `./scripts/format.sh` |
| Lint code | `./scripts/lint.sh` |
| Run tests | `./scripts/test.sh -v` |
| Pre-commit check | `./scripts/dev.sh check` |
| Full workflow | `./scripts/dev.sh all` |

---

## Adding New Scripts

1. Create `scripts/newscript.sh`
2. Start with shebang: `#!/usr/bin/env bash`
3. Add: `set -euo pipefail`
4. Make executable: `chmod +x scripts/newscript.sh`
5. Document in this README
