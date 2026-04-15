"""
Global cuDNN runtime guard.

Keeps CUDA available but disables cuDNN when the installed runtime is known
to be incompatible (missing cudnnGetLibConfig), which otherwise crashes
Conv layers with Windows Error 127.
"""

from __future__ import annotations

import ctypes
import glob
import logging
import os
import site

logger = logging.getLogger("qace.cudnn")


def _prime_nvidia_cuda_dll_paths() -> list[str]:
    """Add venv CUDA/cuDNN wheel bin folders to DLL search path (Windows)."""
    if os.name != "nt":
        return []

    roots = site.getsitepackages() + [site.getusersitepackages()]
    patterns = [
        ("nvidia", "cudnn", "bin"),
        ("nvidia", "cublas", "bin"),
        ("nvidia", "cuda_nvrtc", "bin"),
        ("nvidia", "cuda_runtime", "bin"),
    ]
    bins: list[str] = []
    for root in roots:
        for pat in patterns:
            bins.extend(glob.glob(os.path.join(root, *pat)))
    bins = [p for p in bins if os.path.isdir(p)]

    # Prepend to PATH so dependent DLL lookup resolves these first.
    if bins:
        os.environ["PATH"] = os.pathsep.join(bins + [os.environ.get("PATH", "")])

    for path in bins:
        try:
            os.add_dll_directory(path)
        except Exception:
            pass

    return bins


def _env_true(name: str) -> bool:
    value = os.environ.get(name, "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _should_disable_cudnn_windows() -> bool:
    if _env_true("QACE_FORCE_ENABLE_CUDNN"):
        return False
    if _env_true("QACE_FORCE_DISABLE_CUDNN"):
        return True
    if os.name != "nt":
        return False

    bins = _prime_nvidia_cuda_dll_paths()

    dll = None
    if bins:
        for b in bins:
            candidate = os.path.join(b, "cudnn64_9.dll")
            if os.path.exists(candidate):
                try:
                    dll = ctypes.WinDLL(candidate)
                    break
                except OSError:
                    continue

    if dll is None:
        try:
            dll = ctypes.WinDLL("cudnn64_9.dll")
        except OSError:
            # If cuDNN isn't on PATH, don't force-disable globally.
            return False

    try:
        dll.cudnnGetVersion.restype = ctypes.c_size_t
        version = int(dll.cudnnGetVersion())
        # 9.2.x => 902xx. Versions below 9.2 are missing symbols used by some ops.
        return version < 90200
    except Exception:
        return not hasattr(dll, "cudnnGetLibConfig")


def apply_global_cudnn_guard() -> None:
    """Disable cuDNN globally only when runtime compatibility requires it."""
    _prime_nvidia_cuda_dll_paths()

    try:
        import torch
    except Exception:
        return

    if not torch.cuda.is_available():
        return

    if _should_disable_cudnn_windows():
        torch.backends.cudnn.enabled = False
        logger.warning("Global cuDNN guard active: disabled cuDNN (CUDA remains enabled)")
    else:
        logger.info("Global cuDNN guard: cuDNN left enabled")
