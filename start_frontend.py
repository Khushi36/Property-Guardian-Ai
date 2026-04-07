"""
Windows-safe startup wrapper for Streamlit.
Patches platform.version() BEFORE any imports to prevent chromadb/onnxruntime
or standard libraries from hanging on WMI queries (Windows issue with Python 3.13 + WMI service).
"""
import platform as _platform

# Monkey-patch the hanging WMI call before any other imports
_orig_version = _platform.version
def _safe_version():
    try:
        import signal
        # On Windows, signal.alarm isn't available, so just return a safe stub
        return "Windows"
    except Exception:
        return "Windows"

# Replace the slow _wmi_query by making version() return fast
_platform._wmi_query = lambda *a, **kw: (_ for _ in ()).throw(OSError("patched"))
_platform.version = lambda: "Windows"

import sys
from streamlit.web.cli import main

if __name__ == "__main__":
    sys.argv = ["streamlit", "run", "streamlit_app.py", "--server.port", "8501", "--server.address", "127.0.0.1"]
    sys.exit(main())
