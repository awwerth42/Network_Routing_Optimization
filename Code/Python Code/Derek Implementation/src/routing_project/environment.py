"""Machine and runtime environment capture.

The term-project deliverables require the report to state the characteristics of
the computer used to generate results. This module records those details next to
the experiment output so the numbers in the report can always be traced back to
the machine that produced them.
"""

from __future__ import annotations

import json
import os
import platform
import sys
from pathlib import Path


def _total_memory_gb() -> float | None:
    """Best-effort physical RAM lookup using only the standard library."""

    # Windows: GlobalMemoryStatusEx via ctypes.
    if sys.platform == "win32":
        try:
            import ctypes

            class MemoryStatusEx(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = MemoryStatusEx()
            status.dwLength = ctypes.sizeof(MemoryStatusEx)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return round(status.ullTotalPhys / (1024**3), 2)
        except Exception:
            return None
        return None

    # POSIX: sysconf pages.
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        return round((pages * page_size) / (1024**3), 2)
    except (ValueError, OSError, AttributeError):
        return None


def describe_environment() -> dict[str, object]:
    """Return a JSON-serializable description of the current machine."""

    return {
        "os": f"{platform.system()} {platform.release()}",
        "os_version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor() or "unknown",
        "logical_cpus": os.cpu_count(),
        "total_memory_gb": _total_memory_gb(),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
    }


def format_environment(details: dict[str, object] | None = None) -> str:
    """Render the environment as Markdown bullets for the report."""

    details = details or describe_environment()
    memory = details.get("total_memory_gb")
    memory_text = f"{memory} GB" if memory else "unavailable"
    return "\n".join(
        [
            f"- Operating system: {details.get('os')} ({details.get('machine')})",
            f"- Processor: {details.get('processor')}",
            f"- Logical CPUs: {details.get('logical_cpus')}",
            f"- Physical memory: {memory_text}",
            f"- Python: {details.get('python_implementation')} {details.get('python_version')}",
        ]
    )


def write_environment(output_path: Path) -> Path:
    """Write the environment description to ``output_path`` as JSON."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(describe_environment(), indent=2) + "\n", encoding="utf-8")
    return output_path
