# ============================================================
# core/job_manager.py — Async Background Job Execution
# Manages PAPI-style pseudo-terminal jobs and multitasking.
# ============================================================

import os
import time
import subprocess
import threading
import uuid
import json
from datetime import datetime
from typing import Dict, List, Optional
from settings import settings as config
from skills.logger import log_audit, log_app
from skills.shell_executor.executor import _analyze_command

class BackgroundJob:
    """Represents a long-running background process."""
    def __init__(self, job_id: str, name: str, command: str):
        self.job_id = job_id
        self.name = name
        self.command = command
        self.status = "running"
        self.start_time = datetime.now().isoformat()
        self.end_time = None
        self.returncode = None
        self.stdout = []
        self.stderr = []
        self._process = None
        self._thread = None

    def to_dict(self):
        return {
            "job_id": self.job_id,
            "name": self.name,
            "command": self.command,
            "status": self.status,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "returncode": self.returncode,
            "stdout_len": len(self.stdout),
            "stderr_len": len(self.stderr),
        }

class JobManager:
    """Singleton manager for background processes."""
    _instance = None
    _jobs: Dict[str, BackgroundJob] = {}
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(JobManager, cls).__new__(cls)
        return cls._instance

    def spawn_job(self, command: str, name: str = "unstated_job") -> str:
        """Starts a background process and returns its ID."""
        analysis = _analyze_command(command)
        if not analysis["safe"]:
            return f"ERROR: Command rejected by safety policy: {analysis['reason']}"

        job_id = str(uuid.uuid4())[:8]
        job = BackgroundJob(job_id, name, command)
        
        with self._lock:
            self._jobs[job_id] = job

        def _run():
            try:
                log_audit("JOB_MANAGER", f"Spawning job {job_id}: {command}")
                process = subprocess.Popen(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=config.BASE_DIR,
                    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                    bufsize=1, # Line buffered
                )
                job._process = process

                # Threads to read output streams without blocking
                def _read_stream(stream, target_list):
                    for line in iter(stream.readline, ''):
                        target_list.append(line.rstrip())
                        if len(target_list) > 1000: # Cap memory
                            target_list.pop(0)

                t1 = threading.Thread(target=_read_stream, args=(process.stdout, job.stdout), daemon=True)
                t2 = threading.Thread(target=_read_stream, args=(process.stderr, job.stderr), daemon=True)
                t1.start()
                t2.start()

                job.returncode = process.wait()
                job.status = "completed" if job.returncode == 0 else "failed"
                job.end_time = datetime.now().isoformat()
                log_audit("JOB_MANAGER", f"Job {job_id} finished with code {job.returncode}")

            except Exception as e:
                job.status = "crashed"
                job.stderr.append(str(e))
                log_audit("JOB_MANAGER_ERROR", f"Job {job_id} crashed: {e}")

        job._thread = threading.Thread(target=_run, daemon=True)
        job._thread.start()
        
        return job_id

    def list_jobs(self) -> List[dict]:
        """Returns a list of all jobs and their statuses."""
        with self._lock:
            return [j.to_dict() for j in self._jobs.values()]

    def get_job(self, job_id: str) -> Optional[BackgroundJob]:
        """Returns a specific job object."""
        with self._lock:
            return self._jobs.get(job_id)

    def kill_job(self, job_id: str) -> bool:
        """Terminates a running job."""
        job = self.get_job(job_id)
        if job and job._process:
            try:
                job._process.terminate()
                job.status = "terminated"
                return True
            except Exception:
                return False
        return False

# Export singleton
manager = JobManager()
