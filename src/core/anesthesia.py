"""
core/anesthesia.py
============================================================
The 'Anesthesia' layer for ASURA.
Prevents background daemons (Curiosity, Self-Healing) from running
while the Surgeon is modifying their core logic.
"""

import os
import time
from settings import settings as config
from skills.logger import log_audit

ANESTHESIA_LOCK = os.path.join(config.DATA_DIR, ".anesthesia")


def is_under_anesthesia() -> bool:
    """Checks if a surgical operation is currently in progress."""
    return os.path.exists(ANESTHESIA_LOCK)


def wait_for_consciousness(timeout: int = 300):
    """Wait for the anesthesia to wear off."""
    start = time.time()
    while is_under_anesthesia():
        if time.time() - start > timeout:
            break
        time.sleep(5)


class Anesthesia:
    """
    Context manager to pause system daemons during surgery.
    """
    def __enter__(self):
        log_audit("SURGEON", "Administering anesthesia... (pausing daemons)")
        os.makedirs(os.path.dirname(ANESTHESIA_LOCK), exist_ok=True)
        with open(ANESTHESIA_LOCK, "w") as f:
            f.write(str(time.time()))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        log_audit("SURGEON", "Surgery complete. Daemons waking up...")
        if os.path.exists(ANESTHESIA_LOCK):
            os.remove(ANESTHESIA_LOCK)
