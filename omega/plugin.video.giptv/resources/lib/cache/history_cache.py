import threading
import queue
import xbmc


from resources.lib.manager.history_manager import add_item


_write_queue = queue.Queue()
_shutdown_event = threading.Event()  # NEW


def _writer_loop():
    monitor = xbmc.Monitor()

    while not _shutdown_event.is_set() and not monitor.abortRequested():
        try:
            task = _write_queue.get(timeout=0.1)

        except queue.Empty:
            continue

        # Shutdown signal
        if task is None:
            break

        # Process task
        try:
            add_item(**task)
        except Exception:
            pass

    # Final drain (optional)
    while not _write_queue.empty():
        try:
            task = _write_queue.get_nowait()
            if task is None:
                break
            add_item(**task)
        except:  # noqa: E722
            break


# Start background writer
_writer_thread = threading.Thread(target=_writer_loop, daemon=True)
_writer_thread.start()


def enqueue_write(task_dict):
    """Queue a write request safely."""
    if not _shutdown_event.is_set():
        _write_queue.put(task_dict)


def shutdown_writer():
    """Called during Kodi shutdown to cleanly stop the thread."""
    _shutdown_event.set()
    _write_queue.put(None)  # wake the thread
