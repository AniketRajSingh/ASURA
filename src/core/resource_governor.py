# ============================================================
# core/resource_governor.py — Resource Governor
# Prevents overloading Ollama, CPU, memory, disk.
# All AI operations must check with the governor first.
# ============================================================

import time
import os
import json
import threading
import requests
import psutil
from datetime import datetime
from settings import settings as config
from skills.logger import log_audit, log_app


class ResourceGovernor:
    """
    Central resource management — monitors system health and
    throttles AI operations to prevent overload.

    Every LLM call, shell execution, or heavy operation
    should call governor.acquire() first and governor.release() after.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self._lock = threading.Lock()
        self._active_llm_calls = 0
        self._max_concurrent_llm = 2  # max parallel Ollama requests
        self._llm_semaphore = threading.Semaphore(self._max_concurrent_llm)

        # Thresholds (Relaxed to 90% to prevent false positives)
        self.cpu_threshold = 90.0      # percent
        self.memory_threshold = 90.0   # percent
        self.disk_threshold = 95.0     # percent
        self.ollama_queue_max = 3      # max queued Ollama requests

        # Panic Hard-Stops (Safety Plan)
        self.panic_disk_gb = 2.0       # shutdown if disk < 2GB free
        self.panic_cpu_sustained = 180 # seconds at 100% before panic
        self._cpu_100_start = 0

        # Stats
        self._total_requests = 0
        self._throttled_requests = 0
        self._rejected_requests = 0

        # Backoff state
        self._backoff_until = 0
        self._backoff_multiplier = 1
        self._stress_mode = False
        self._last_remediation = 0
        
        # LLM Usage Tracking
        self._usage_file = os.path.join(config.DATA_DIR, "llm_usage.json")
        self._usage = self._load_usage()
        
        # Start background stats logger
        threading.Thread(target=self._stats_collector, daemon=True).start()

    def _load_usage(self) -> dict:
        """Load LLM usage counts from disk."""
        default_usage = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "groq": 0,
            "openrouter": 0
        }
        if not os.path.exists(self._usage_file):
            return default_usage
            
        try:
            with open(self._usage_file, "r") as f:
                data = json.load(f)
                # Reset if date has changed
                if data.get("date") != default_usage["date"]:
                    return default_usage
                return data
        except Exception as e:
            log_app(f"Failed to load usage file: {e}")
            return default_usage

    def _save_usage(self):
        """Persist LLM usage counts to disk."""
        try:
            with open(self._usage_file, "w") as f:
                json.dump(self._usage, f)
        except Exception as e:
            log_app(f"Failed to save usage file: {e}")

    def record_usage(self, provider: str):
        """Increment usage count for a provider."""
        provider = provider.lower()
        if provider not in ("groq", "openrouter"):
            return
            
        with self._lock:
            # Re-check date on every increment just in case
            today = datetime.now().strftime("%Y-%m-%d")
            if self._usage["date"] != today:
                self._usage = {"date": today, "groq": 0, "openrouter": 0}
                
            self._usage[provider] += 1
            self._save_usage()
            
            # Log periodic status
            count = self._usage[provider]
            limit = getattr(config, f"{provider.upper()}_DAILY_LIMIT", 100)
            if count % 10 == 0 or count >= limit - 5:
                log_app(f"LLM Usage ({provider}): {count}/{limit}")

    def is_exhausted(self, provider: str) -> bool:
        """Check if a provider's daily limit has been reached."""
        provider = provider.lower()
        if provider not in ("groq", "openrouter"):
            return False
            
        limit = getattr(config, f"{provider.upper()}_DAILY_LIMIT", 100)
        return self._usage.get(provider, 0) >= limit

    def is_under_stress(self) -> bool:
        """Check if the system is currently in stress mode."""
        return self._stress_mode

    def _stats_collector(self):
        """Background thread to log hardware stats to disk for the dashboard."""
        import json, os
        stats_path = os.path.join(config.DATA_DIR, 'resource_stats.json')
        while True:
            try:
                h = self.check_health()
                entry = {
                    "timestamp": datetime.now().isoformat() if 'datetime' in globals() else time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "cpu": h["cpu_percent"],
                    "mem": h["memory_percent"],
                    "disk": h["disk_percent"]
                }
                
                # Maintain a sliding window of 60 samples (last 5 mins at 5s interval)
                history = []
                if os.path.exists(stats_path):
                    with open(stats_path, 'r') as f:
                        history = json.load(f)
                
                history.append(entry)
                if len(history) > 60:
                    history = history[-60:]
                
                import tempfile
                with tempfile.NamedTemporaryFile('w', dir=os.path.dirname(stats_path), delete=False, suffix='.tmp') as tf:
                    json.dump(history, tf)
                    tf_name = tf.name
                os.replace(tf_name, stats_path)
                try:
                    os.chmod(stats_path, 0o644)
                except:
                    pass
            except Exception as e:
                log_app(f"Stats collector error: {e}")
            time.sleep(5)

    def check_health(self) -> dict:
        """Full system health check."""
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory().percent
        usage = psutil.disk_usage(config.BASE_DIR)
        disk = usage.percent
        free_gb = usage.free / (1024**3)
        
        health = {
            "cpu_percent": cpu,
            "memory_percent": mem,
            "disk_percent": disk,
            "disk_free_gb": free_gb,
            "active_llm_calls": self._active_llm_calls,
            "ollama_alive": self._check_ollama(),
            "throttled": self._throttled_requests,
            "rejected": self._rejected_requests,
            "total_requests": self._total_requests,
        }

        # Panic Check (Safety Plan Enforcement)
        if health["disk_free_gb"] < self.panic_disk_gb:
            self._trigger_panic(f"Dangerously low disk space: {health['disk_free_gb']:.2f}GB remaining")

        if health["cpu_percent"] >= 99.5:
            if not self._cpu_100_start:
                self._cpu_100_start = time.time()
            elif time.time() - self._cpu_100_start > self.panic_cpu_sustained:
                self._trigger_panic(f"Sustained 100% CPU usage for {self.panic_cpu_sustained}s")
        else:
            self._cpu_100_start = 0

        # Determine overall status
        if health["cpu_percent"] > self.cpu_threshold or health["memory_percent"] > self.memory_threshold:
            health["status"] = "critical"
            health["warning"] = f"CRITICAL: CPU {health['cpu_percent']}% | Mem {health['memory_percent']}%"
        elif health["disk_percent"] > self.disk_threshold:
            health["status"] = "critical"
            health["warning"] = f"Disk at {health['disk_percent']}%"
        elif not health["ollama_alive"]:
            health["status"] = "degraded"
            health["warning"] = "Ollama unreachable"
        elif health["cpu_percent"] > 70 or health["memory_percent"] > 70:
            health["status"] = "warning"
            health["warning"] = "Resources elevated"
        else:
            health["status"] = "healthy"
            health["warning"] = None

        return health

    def remediate_stress(self) -> str:
        """
        Autonomous remediation of system stress.
        Attempts to kill heavy processes and sets throttle flags.
        """
        now = time.time()
        if now - self._last_remediation < 300: # cooldown: 5 min
            return "Remediation on cooldown."

        self._last_remediation = now
        health = self.check_health()
        actions = []

        if health["status"] == "critical":
            self._stress_mode = True
            log_app("🚨 System stress detected! Initiating autonomous remediation...")
            
            # 1. Kill stale heavy processes (Playwright/Chrome)
            killed_count = 0
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    name = proc.info['name'].lower()
                    if any(x in name for x in ['chrome', 'chromium', 'playwright']):
                        proc.kill()
                        killed_count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if killed_count > 0:
                actions.append(f"Killed {killed_count} heavy browser processes.")

            # 2. Increase backoff system-wide
            self.apply_backoff(120) 
            actions.append("Applied 120s system-wide backoff.")

        else:
            self._stress_mode = False

        if not actions:
            return "No remediation actions needed or possible."
            
        summary = "Remediation complete: " + " ".join(actions)
        log_audit("GOVERNOR", summary)
        return summary

    def _trigger_panic(self, reason: str):
        """Hard shutdown to protect the host system (Cross-Platform)."""
        import os, signal, sys, psutil
        log_audit("PANIC", reason)
        log_app(f"🚨 PANIC SHUTDOWN INITIATED: {reason}")
        log_app("Terminating all system processes to preserve host OS stability.")
        
        try:
            # Cross-platform recursive termination
            parent = psutil.Process(os.getpid())
            for child in parent.children(recursive=True):
                try:
                    child.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            # Allow short time for children to exit before killing parent
            time.sleep(1)
            parent.terminate()
        except Exception as e:
            log_app(f"Panic termination issue: {e}")
            # Fallback to os.abort if psutil fails
            os.abort()

    def _check_ollama(self) -> bool:
# ...rest of file
        """Check if Ollama is alive and responsive."""
        try:
            resp = requests.get(
                f"{config.OLLAMA_BASE_URL}/api/tags",
                timeout=5,
            )
            return resp.status_code == 200
        except Exception:
            return False

    def can_proceed(self, operation: str = "llm") -> tuple[bool, str]:
        """
        Check if an operation can proceed given current resources.
        Returns (can_proceed, reason).
        """
        self._total_requests += 1

        # Check backoff
        if time.time() < self._backoff_until:
            self._throttled_requests += 1
            wait = self._backoff_until - time.time()
            return False, f"Backoff active — retry in {wait:.0f}s"

        health = self.check_health()

        # Critical: reject
        if health["status"] == "critical":
            self._rejected_requests += 1
            log_audit("GOVERNOR", f"REJECTED {operation}: {health['warning']}")
            return False, f"System overloaded: {health['warning']}"

        # Ollama-specific checks
        if operation == "llm":
            if not health["ollama_alive"]:
                self._rejected_requests += 1
                return False, "Ollama is unreachable"

            if self._active_llm_calls >= self._max_concurrent_llm:
                self._throttled_requests += 1
                return False, f"Too many active LLM calls ({self._active_llm_calls})"

        # Warning: allow but log
        if health["status"] == "warning":
            log_audit("GOVERNOR", f"WARNING during {operation}: {health['warning']}")

        return True, "OK"

    def acquire_llm(self, timeout: float = 60) -> bool:
        """Acquire an LLM execution slot. Blocks until available or timeout."""
        acquired = self._llm_semaphore.acquire(timeout=timeout)
        if acquired:
            with self._lock:
                self._active_llm_calls += 1
        else:
            self._throttled_requests += 1
            log_audit("GOVERNOR", "LLM slot acquisition timed out")
        return acquired

    def release_llm(self):
        """Release an LLM execution slot."""
        with self._lock:
            self._active_llm_calls = max(0, self._active_llm_calls - 1)
        self._llm_semaphore.release()

    def apply_backoff(self, seconds: float = None):
        """Apply a backoff period after errors/overload."""
        if seconds is None:
            seconds = min(30 * self._backoff_multiplier, 300)
            self._backoff_multiplier = min(self._backoff_multiplier * 2, 10)
        else:
            self._backoff_multiplier = 1

        self._backoff_until = time.time() + seconds
        log_audit("GOVERNOR", f"Backoff applied: {seconds:.0f}s")

    def reset_backoff(self):
        self._backoff_multiplier = 1
        self._backoff_until = 0

    def format_status(self) -> str:
        """Format governor status for Telegram/dashboard display."""
        h = self.check_health()
        status_emoji = {"healthy": "🟢", "warning": "🟡", "critical": "🔴", "degraded": "🟠"}
        em = status_emoji.get(h["status"], "⚪")

        lines = [
            f"{em} *Resource Governor*\n",
            f"CPU: {h['cpu_percent']:.0f}% | Memory: {h['memory_percent']:.0f}% | Disk: {h['disk_percent']:.0f}%",
            f"Ollama: {'✅ Online' if h['ollama_alive'] else '❌ Offline'}",
            f"Active LLM calls: {h['active_llm_calls']}/{self._max_concurrent_llm}",
            f"Requests: {h['total_requests']} total | {h['throttled']} throttled | {h['rejected']} rejected",
            f"LLM Usage: Groq {self._usage['groq']}/{getattr(config, 'GROQ_DAILY_LIMIT', 100)} | OR {self._usage['openrouter']}/{getattr(config, 'OPENROUTER_DAILY_LIMIT', 100)}",
        ]
        if h.get("warning"):
            lines.append(f"\n⚠️ {h['warning']}")
        return "\n".join(lines)

    def format_status_minimal(self) -> str:
        """Condensed resource stats for AI context."""
        h = self.check_health()
        return f"CPU: {h['cpu_percent']}% | MEM: {h['memory_percent']}% | DISK: {h['disk_percent']}% | Status: {h['status']}"


# ─── Singleton accessor ─────────────────────────────────────
def get_governor() -> ResourceGovernor:
    return ResourceGovernor()


def governed_llm_call(func):
    """Decorator: wrap any LLM call with governor acquire/release."""
    from functools import wraps

    @wraps(func)
    def wrapper(*args, **kwargs):
        gov = get_governor()
        can, reason = gov.can_proceed("llm")
        if not can:
            log_audit("GOVERNOR", f"LLM call blocked: {reason}")
            raise ResourceError(reason)

        if not gov.acquire_llm(timeout=60):
            raise ResourceError("Could not acquire LLM slot in time")

        try:
            result = func(*args, **kwargs)
            gov.reset_backoff()
            return result
        except Exception as e:
            gov.apply_backoff()
            raise
        finally:
            gov.release_llm()

    return wrapper


class ResourceError(Exception):
    """Raised when a resource limit is hit."""
    pass
