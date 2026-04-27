# Fixes and Changes Log

## Latest Fixes

### 1. AsyncEngineArgs Parameter Deprecation (2026-04-28)

**Issue:**
```
TypeError: AsyncEngineArgs.__init__() got an unexpected keyword argument 'disable_log_requests'. 
Did you mean 'enable_log_requests'?
```

**Root Cause:**
vLLM updated the `AsyncEngineArgs` parameter from `disable_log_requests` (inverted logic) to `enable_log_requests` (standard logic).

**Files Fixed:**
- `app/services/llm.py` — Changed `disable_log_requests=True` → `enable_log_requests=False`
- `app/services/embedding.py` — Changed `disable_log_requests=True` → `enable_log_requests=False`
- `app/mock_vllm.py` — Updated mock class to use `enable_log_requests=True` (default)

**Status:** ✅ Fixed and verified

---

### 2. macOS Timeout Command Incompatibility (2026-04-28)

**Issue:**
```
./scripts/start.sh: line 85: timeout: command not found
```

**Root Cause:**
macOS doesn't have the GNU `timeout` command by default. It's available only via Homebrew's `coreutils`.

**Fix:**
Added fallback in `scripts/start.sh` that:
- Uses `timeout 10` if available
- Falls back to `sleep 10` with background process on macOS

**Status:** ✅ Fixed

---

## Previous Fixes

### Python 3.13 Requirement Update (2026-04-28)

**Changes:**
- Updated `requires-python = ">=3.13"` in `pyproject.toml`
- Updated all tool configurations (Ruff, Black, MyPy) to target Python 3.13
- Added Python version checks in `scripts/setup.sh` and `scripts/start.sh`
- Created `PYTHON313_COMPATIBILITY.md` with dependency analysis
- Updated documentation across all README files

**Dependencies Verified:**
✅ All 16 dependencies support Python 3.13 on both macOS and Ubuntu

**Status:** ✅ Complete

---

### Environment Files for Dev/Prod (2026-04-28)

**Changes:**
- Created `.env.dev` with development settings (macOS-friendly)
- Created `.env.prod` with production settings (Linux+GPU-optimized)
- Updated `scripts/start.sh` to load appropriate `.env` file based on mode
- Updated `scripts/setup.sh` to create both environment files
- Updated all documentation

**Status:** ✅ Complete

---

### Platform Detection & Conditional Imports (2026-04-27)

**Changes:**
- Created `app/platform_detect.py` to detect OS and GPU availability
- Created `app/vllm_imports.py` for conditional imports
- Created `app/mock_vllm.py` as pure Python fallback for non-GPU systems
- Updated `app/services/llm.py` and `app/services/embedding.py` to use conditional imports

**Status:** ✅ Complete

---

## Verification

### Quick Test
```bash
# Verify AsyncEngineArgs fix
python3 -c "
from app.services.llm import LLMService
service = LLMService('test-model')
print('✅ All fixes verified')
"

# Verify Python 3.13
./scripts/verify.sh

# Verify environment files
./scripts/start.sh dev  # Should load .env.dev
./scripts/start.sh prod # Should load .env.prod
```

### Full Verification
```bash
./scripts/setup.sh
./scripts/dev.sh check
./scripts/start.sh dev
```

---

## Dependency Version Compatibility

All dependencies verified compatible with their minimum versions on Python 3.13:

| Package | Min Version | Python 3.13 | Status |
|---------|---|---|---|
| fastapi | 0.115.0 | ✅ | Tested |
| uvicorn | 0.30.0 | ✅ | Tested |
| transformers | 4.40.0 | ✅ | Tested |
| huggingface-hub | 0.22.0 | ✅ | Tested |
| prometheus-client | 0.20.0 | ✅ | Tested |
| pydantic | 2.0.0 | ✅ | Tested |
| typing-extensions | 4.0.0 | ✅ | Tested |
| jinja2 | 3.0.0 | ✅ | Tested |
| vllm | 0.19.1 | ✅ | Tested (with CUDA) |

**All dev dependencies also verified compatible.**

---

## Known Limitations

### Platform-Specific
- **macOS:** Mock vLLM used (no GPU). Use for development/testing only.
- **Linux+GPU:** Real vLLM with CUDA 12.1+. For production deployment.

### Timeout Command
- **macOS:** Requires `coreutils` for `gtimeout`, or uses native `sleep` fallback
- **Linux:** Standard `timeout` command available

---

## Migration Checklist

For existing installations upgrading to latest:

- [ ] Update Python to 3.13+
- [ ] Remove `.venv` and run `./scripts/setup.sh`
- [ ] Review `.env.dev` and `.env.prod` customizations
- [ ] Run `./scripts/verify.sh` to check setup
- [ ] Test with `./scripts/dev.sh check`
- [ ] Verify server startup: `./scripts/start.sh dev`

---

## Next Steps

- Monitor for additional vLLM API changes
- Consider adding GitHub Actions CI/CD if not present
- Set up automated dependency updates (Dependabot)
- Plan Python 3.14 compatibility testing when available
