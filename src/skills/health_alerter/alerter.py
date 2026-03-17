# ============================================================
# skills/health_alerter/alerter.py — Proactive Health Alerting
# Auto-alert when CPU/mem/disk/Ollama hits critical
# ============================================================
import threading, time
import psutil
from settings import settings as config
from skills.logger import log_audit, log_app

class HealthAlerter:
    def __init__(self, notify_fn=None, check_interval=120):
        self._notify = notify_fn
        self._interval = check_interval
        self._running = False
        self._alerted = set()

    def start(self):
        self._running = True
        t = threading.Thread(target=self._loop, daemon=True, name="health-alerter")
        t.start()
        log_app("Health alerter started")

    def stop(self): self._running = False

    def _loop(self):
        while self._running:
            time.sleep(self._interval)
            if not self._running: break
            try: self._check()
            except Exception as e: log_app(f"Health alert error: {e}")

    def _check(self):
        alerts = []
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage(config.BASE_DIR).percent

        if cpu > 90 and "cpu" not in self._alerted:
            alerts.append(f"🔴 CPU at {cpu:.0f}% — consider stopping heavy tasks")
            self._alerted.add("cpu")
        elif cpu < 70: self._alerted.discard("cpu")

        if mem > 85 and "mem" not in self._alerted:
            alerts.append(f"🔴 Memory at {mem:.0f}% — free up resources")
            self._alerted.add("mem")
        elif mem < 70: self._alerted.discard("mem")

        if disk > 90 and "disk" not in self._alerted:
            alerts.append(f"🔴 Disk at {disk:.0f}% — clean up files or old backups")
            self._alerted.add("disk")
        elif disk < 80: self._alerted.discard("disk")

        if alerts and self._notify:
            from core.resource_governor import get_governor
            gov = get_governor()
            
            remediation_report = ""
            if any("🔴" in a for a in alerts):
                # Trigger active remediation if anything is critical
                remediation_report = gov.remediate_stress()
            
            msg = "<b>⚠️ Health Alert & Auto-Remediation</b>\n\n" + "\n".join(alerts)
            if remediation_report:
                msg += f"\n\n<b>🛡️ Action Taken:</b>\n{remediation_report}"
                
            log_audit("HEALTH", msg)
            self._notify(msg)
