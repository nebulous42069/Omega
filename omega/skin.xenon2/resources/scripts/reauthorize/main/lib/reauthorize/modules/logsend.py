"""Compatibility entry point: embedded ReAuthorize has no log uploader."""

def run(viewer=None):
    """Retained for older callers. Reads and sends no log data."""
    return False
