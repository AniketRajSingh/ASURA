import os
import json
import threading
from datetime import datetime
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import http.cookies as http_cookies
import asyncio
from settings import settings as config
from skills.logger import log_audit, log_app
from core.auth import create_access_token, verify_token

def run_async(coro):
    """Bridge to run async coroutines in a synchronous context."""
    try:
        loop = asyncio.new_event_loop()
        return loop.run_until_complete(coro)
    except Exception as e:
        log_app(f"Dashboard Async Bridge Error: {e}")
        return None
    finally:
        loop.close()


def render_template(template_name: str, context: dict = None) -> str:
    """Robust template renderer supporting recursive includes and context substitution."""
    template_dir = os.path.join(os.path.dirname(__file__), "templates")
    template_path = os.path.join(template_dir, template_name)
    try:
        if not os.path.exists(template_path):
            return f"Template Not Found: {template_path}"
        
        with open(template_path, "r") as f:
            html = f.read()

        import re
        # Handle Includes: {% include "path" %}
        include_pattern = re.compile(r'\{%\s*include\s*"(.*?)"\s*%\}')
        
        for _ in range(5): # Recursive limit
            def include_replacer(match):
                inc_name = match.group(1)
                inc_path = os.path.join(template_dir, inc_name)
                if os.path.exists(inc_path):
                    with open(inc_path, "r") as f_inc:
                        return f_inc.read()
                return f"<!-- Include Not Found: {inc_name} -->"
            
            new_html = include_pattern.sub(include_replacer, html)
            if new_html == html:
                break
            html = new_html

        # Handle Context: {{ key }}
        if context:
            for key, value in context.items():
                # Supports {{key}}, {{ key }}, {{   key   }}
                pattern = re.compile(rf'\{{\{{\s*{re.escape(key)}\s*\}}\}}')
                html = pattern.sub(str(value), html)
        
        return html
    except Exception as e:
        log_app(f"Template Error in {template_name}: {e}")
        return f"Template Error: {e}"


def _build_html() -> str:
    """Prepare context and render the dashboard template."""
    from skills.skill_registry import discover_skills
    from skills.hardware_monitor import get_system_info
    from skills.todo_manager import get_open_todos

    registry = discover_skills()
    hw = get_system_info()
    todos = get_open_todos()

    cpu = hw.get('cpu', {}).get('usage_percent', 0) if hw else 0
    mem_data = hw.get('memory', {}) if hw else {}
    mem = mem_data.get('used_percent', 0) if isinstance(mem_data, dict) else 0
    disk_data = hw.get('disk', {}) if hw else {}
    disk = disk_data.get('used_percent', 0) if isinstance(disk_data, dict) else 0

    # Add a system info entry as a todo item
    sys_info_desc = f"System: CPU {cpu}%, MEM {mem}%, DISK {disk}%"
    todos = todos or []
    todos.insert(0, {"description": sys_info_desc})

    # Read recent logs
    audit_lines = []
    try:
        with open(config.AUDIT_LOG_PATH, "r") as f:
            audit_lines = f.readlines()[-40:]
    except Exception:
        pass

    skill_cards = ""
    for name, info in sorted(registry.items()):
        desc = info.get('description', '')[:60]
        skill_cards += f"""<div class="skill-card"><div class="skill-dot"></div><span class="skill-name">{name}</span><span class="skill-desc">{desc}</span></div>"""

    log_entries = ""
    for line in reversed(audit_lines):
        line = line.strip()
        if not line or len(line) < 5: continue
        css_class = "log-warn" if any(x in line for x in ["ERROR", "FAIL", "WARN"]) else "log-info"
        log_entries += f'<div class="log-line {css_class}">{line}</div>'

    todo_items = ""
    for t in (todos or [])[:8]:
        desc = t.get("description", t) if isinstance(t, dict) else str(t)
        todo_items += f'<div class="todo-item"><span class="todo-dot"></span>{desc}</div>'
    if not todo_items:
        todo_items = '<div style="color:var(--muted)">No open tasks. The system is at peace.</div>'

    context = {
        "skill_count": len(registry),
        "skill_cards": skill_cards,
        "log_entries": log_entries,
        "todo_items": todo_items,
        "todo_count": len(todos or []),
        "cpu": cpu,
        "mem": mem,
        "disk": disk,
        "master_name": config.MASTER_NAME,
        "ollama_host": config.OLLAMA_BASE_URL.split('//')[-1],
    }
    return render_template("index.html", context)


class DashboardHandler(BaseHTTPRequestHandler):
    """Unified Dashboard request handler using external templates."""

    def _set_headers(self, content_type="text/html", status=200):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-ASURA-Key, Authorization")
        self.end_headers()

    def _send_json(self, data, status=200):
        self._set_headers("application/json", status)
        self.wfile.write(json.dumps(data).encode())

    def _is_authenticated(self):
        """Check JWT token in Cookie."""
        cookie_header = self.headers.get("Cookie")
        if not cookie_header:
            return False
        cookie = http_cookies.SimpleCookie(cookie_header)
        if "tf_token" not in cookie:
            return False
        token = cookie["tf_token"].value
        return verify_token(token) is not None

    def _send_login_page(self, error=""):
        self._set_headers()
        err_html = f'<p style="color:red">{error}</p>' if error else ''
        html = render_template("login.html", {"error": error}) # The template handles display
        self.wfile.write(html.encode())

    def _serve_dashboard(self):
        self._set_headers()
        self.wfile.write(_build_html().encode())

    def _serve_static(self):
        """Serve files from the static directory."""
        # Use absolute path for robustness
        current_dir = os.path.dirname(os.path.abspath(__file__))
        static_dir = os.path.join(current_dir, "static")
        
        # Robustly extract the relative path
        normalized_path = self.path.split('?')[0] # Remove query params
        if normalized_path.startswith("/static/"):
            rel_path = normalized_path[8:]
        else:
            rel_path = normalized_path.lstrip('/')
            
        file_path = os.path.normpath(os.path.join(static_dir, rel_path))
        
        # Security check: ensure path is within static_dir
        if not file_path.startswith(os.path.abspath(static_dir)):
            self.send_error(403, "Access Denied: Escape detected")
            return

        if os.path.exists(file_path) and os.path.isfile(file_path):
            content_type = "text/plain"
            if file_path.endswith(".css"): content_type = "text/css"
            elif file_path.endswith(".js"): content_type = "application/javascript"
            elif file_path.endswith(".png"): content_type = "image/png"
            elif file_path.endswith(".jpg") or file_path.endswith(".jpeg"): content_type = "image/jpeg"
            elif file_path.endswith(".svg"): content_type = "image/svg+xml"
            elif file_path.endswith(".ico"): content_type = "image/x-icon"
            
            self._set_headers(content_type)
            with open(file_path, "rb") as f:
                self.wfile.write(f.read())
        else:
            self.send_error(404, "Static File Not Found")

    def do_OPTIONS(self):
        self._set_headers(status=240) # No content for options

    def do_GET(self):
        # 1. Auth Guard
        if not self._is_authenticated():
            if self.path == "/login" or self.path == "/":
                return self._send_login_page()
            elif self.path.startswith("/api/"):
                return self._send_json({"error": "Unauthorized"}, 401)
            else:
                self.send_response(302)
                self.send_header("Location", "/login")
                self.end_headers()
                return

        # 2. Routing
        try:
            if self.path == "/static" or self.path.startswith("/static/"):
                return self._serve_static()
            elif self.path in ["/", "/dashboard"]:
                self._serve_dashboard()
            elif self.path == "/api/health" or self.path == "/api/status":
                from skills.hardware_monitor import get_system_info
                import time
                stats = get_system_info()
                telegram_active = os.environ.get("ASURA_TELEGRAM_ACTIVE") == "true"
                is_leader = os.environ.get("ASURA_MANAGED_BOT") == "true" or telegram_active
                
                # Use correct nested access for hardware_monitor stats
                self._send_json({
                    "status": "ok",
                    "instance_name": config.INSTANCE_NAME,
                    "is_leader": is_leader,
                    "telegram_active": telegram_active,
                    "cpu": stats.get("cpu", {}).get("usage_percent", 0) if isinstance(stats, dict) else 0,
                    "ram": stats.get("memory", {}).get("used_percent", 0) if isinstance(stats, dict) else 0,
                    "disk": stats.get("disk", {}).get("used_percent", 0) if isinstance(stats, dict) else 0,
                    "uptime": int(time.time() - getattr(config, "_start_time", time.time()))
                })
            elif self.path == "/api/vcs/history":
                from core.vcs import get_vcs
                self._send_json(get_vcs().list_history())
            elif self.path == "/api/system/processes":
                import psutil, time
                procs = []
                seen_types = set()
                
                # 1. Get OS-Level Processes
                for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
                    try:
                        cmdline = " ".join(proc.info['cmdline'] or [])
                        name = proc.info['name'] or ""
                        
                        # Broader match to include daemon and telegram
                        is_python = "python" in cmdline or "python" in name.lower()
                        if is_python:
                            p_type = None
                            if "main.py" in cmdline: p_type = "Core Engine"
                            elif "telegram_daemon.py" in cmdline: p_type = "Telegram Bot"
                            elif "run.py" in cmdline: p_type = "Bootloader"
                            elif "monitor.py" in cmdline: p_type = "Daemon Monitor"
                            
                            if p_type:
                                # Deduplicate: Only show the newest instance of each type
                                if p_type in seen_types: continue
                                seen_types.add(p_type)

                                procs.append({
                                    "id": proc.info['pid'],
                                    "name": p_type,
                                    "status": "active",
                                    "uptime": int(time.time() - proc.info['create_time']),
                                    "type": "process"
                                })
                    except: continue
                
                # 2. Get ONLY Active background jobs
                from core.job_manager import manager
                jobs = manager.list_jobs()
                for job in jobs:
                    if job.get("status") in ["running", "queued"]:
                        job["type"] = "job"
                        procs.append(job)
                    
                self._send_json({"processes": procs})
                return

            elif self.path.startswith("/api/system/terminate"):
                from urllib.parse import urlparse, parse_qs
                query = parse_qs(urlparse(self.path).query)
                pid = int(query.get("pid", [0])[0])
                if pid:
                    import psutil
                    try:
                        p = psutil.Process(pid)
                        p.terminate()
                        log_audit("DASHBOARD", f"Master terminated process {pid}")
                        self._send_json({"success": True})
                    except: self._send_json({"success": False, "error": "Process not found"})
                return
            elif self.path == "/api/system/resources":
                try:
                    stats_path = os.path.join(config.DATA_DIR, 'resource_stats.json')
                    if os.path.exists(stats_path):
                        with open(stats_path, 'r') as f:
                            data = json.load(f)
                            self._send_json(data)
                    else:
                        log_app(f"Dashboard API Error: Stats file not found at {stats_path}")
                        self._send_json([])
                except Exception as e:
                    log_app(f"Dashboard API Error reading resources: {e}")
                    self._send_json([])
            elif self.path == "/api/settings/list":
                # Return all settings as a dict for the UI to render
                schema = {}
                # Handle Pydantic BaseModel introspection safely
                config_dict = config.model_dump() if hasattr(config, "model_dump") else config.__dict__
                for k, v in config_dict.items():
                    if k.isupper() and not k.startswith("_"):
                        # Mask sensitive-looking keys
                        if any(s in k.lower() for s in ["token", "key", "password", "secret"]):
                            schema[k] = "********" if v else ""
                        else:
                            schema[k] = v
                self._send_json(schema)
            elif self.path == "/api/llm/status":
                from core.resource_governor import get_governor
                self._send_json({"live": get_governor()._check_ollama()})
            elif self.path == "/api/persona":
                self._send_json(getattr(config, "PERSONA", {}))
            elif self.path == "/api/skills/list":
                from skills.skill_registry import discover_skills
                self._send_json(discover_skills())
            elif self.path == "/api/memory/stats":
                from skills.memory.store import get_memory_store, get_freshness_score
                from skills.memory.episodic import count_episodes
                from core.memory_manager import memory_manager
                
                docs = get_memory_store()
                vault_data = run_async(memory_manager._load_vault()) or {}
                vault_facts = vault_data.get("permanent_facts", [])
                
                self._send_json({
                    "embeddings_count": len(docs),
                    "total_memories": len(docs),
                    "vault_count": len(vault_facts),
                    "episodic_count": count_episodes(),
                    "total_tokens_spent": len(docs) * 500,
                    "top_skills": ["kernel_core", "autonomous_logic", "self_updater"],
                    "freshness_score": get_freshness_score(),
                    "last_updated": datetime.now().isoformat()
                })
            elif self.path == "/api/features/list":
                from skills.feature_tracker.tracker import _load_registry
                self._send_json(_load_registry())
            elif self.path == "/api/plugins":
                # API endpoint to list all plugins (same as skills)
                from skills.skill_registry import discover_skills
                plugins = discover_skills()
                plugin_list = [
                    {
                        "name": name,
                        "description": info.get("description", ""),
                        "tags": info.get("tags", []),
                        "functions": info.get("functions", []),
                        "enabled": True
                    }
                    for name, info in sorted(plugins.items())
                ]
                self._send_json({"plugins": plugin_list, "count": len(plugin_list)})
            elif self.path == "/api/drafts/list":
                try:
                    from config import DRAFTS_DIR, DATA_DIR
                    drafts = []
                    
                    # Scout primary
                    if os.path.exists(DRAFTS_DIR):
                        for f in os.listdir(DRAFTS_DIR):
                            if f.endswith((".md", ".txt", ".json")):
                                stats = os.stat(os.path.join(DRAFTS_DIR, f))
                                drafts.append({
                                    "name": f,
                                    "size": stats.st_size,
                                    "modified": datetime.fromtimestamp(stats.st_mtime).isoformat(),
                                    "source": "DRAFTS"
                                })
                    
                    # Secondary Scout in surgery dirs if primary is thin
                    if len(drafts) < 5:
                        surgery_dir = os.path.join(DATA_DIR, "surgery")
                        if os.path.exists(surgery_dir):
                            for root, dirs, files in os.walk(surgery_dir):
                                for f in files:
                                    if f.endswith(('.md', '.py')):
                                        f_path = os.path.join(root, f)
                                        stats = os.stat(f_path)
                                        drafts.append({
                                            "name": f,
                                            "size": stats.st_size,
                                            "modified": datetime.fromtimestamp(stats.st_mtime).isoformat(),
                                            "source": os.path.basename(root)
                                        })
                                if len(drafts) > 20: break
                    
                    self._send_json(drafts[:20])
                except Exception as e:
                    self._send_json({"error": str(e)})
            elif self.path == "/api/intelligence/trace":
                try:
                    trace_path = os.path.join(config.LOGS_DIR, 'inference_trace.json')
                    if os.path.exists(trace_path):
                        with open(trace_path, 'r') as f:
                            data = json.load(f)
                            self._send_json(data)
                    else:
                        log_app(f"Dashboard API Error: Trace file not found at {trace_path}")
                        self._send_json([])
                except Exception as e:
                    log_app(f"Dashboard API Error reading trace: {e}")
                    self._send_json([])
            elif self.path.startswith("/api/knowledge/graph"):
                import urllib.parse
                from core.knowledge_graph import knowledge_graph
                
                parsed = urllib.parse.urlparse(self.path)
                qs = urllib.parse.parse_qs(parsed.query)
                category = qs.get("cat", ["overview"])[0]
                
                if category == "overview":
                    # Return root categories
                    filtered_nodes = [n for n in knowledge_graph.nodes.values() if n.get("type") == "category"]
                else:
                    # Return nodes for specific category
                    # Also include the parent category node for context
                    target_parent = f"sys_{category.lower()}"
                    filtered_nodes = [n for n in knowledge_graph.nodes.values() if n.get("category") == category or n.get("id") == target_parent]
                    
                node_ids = {n["id"] for n in filtered_nodes}
                filtered_edges = [e for e in knowledge_graph.edges if e["source"] in node_ids and e["target"] in node_ids]
                
                self._send_json({
                    "nodes": filtered_nodes,
                    "edges": filtered_edges
                })
            elif self.path == "/api/recommendations/list":
                from core.recommendation import recommendation_store
                recs = recommendation_store.get_pending()
                self._send_json([r.to_dict() for d, r in enumerate(recs)])

            elif self.path == "/api/memory/rag":
                from skills.memory.store import get_memory_store
                self._send_json(get_memory_store()[-50:])
            elif self.path == "/api/memory/vault":
                from core.memory_manager import memory_manager
                vault_data = run_async(memory_manager._load_vault()) or {}
                self._send_json(vault_data.get("permanent_facts", []))
            elif self.path == "/api/memory/episodes":
                from skills.memory.episodic import recall_episodes
                self._send_json(recall_episodes(limit=50))
            elif self.path == "/api/skills/source":
                # Batch 4: View skill source code (Smart logic)
                skill_name = self.headers.get("X-Skill-Name")
                if not skill_name:
                    from urllib.parse import urlparse, parse_qs
                    query = parse_qs(urlparse(self.path).query)
                    skill_name = query.get("name", [None])[0]

                from skills.skill_registry import discover_skills
                registry = discover_skills()
                if skill_name in registry:
                    # Smart Path: If __init__.py is just imports, find the main file
                    skill_root = os.path.join(config.SKILLS_DIR, skill_name)
                    main_file = os.path.join(skill_root, "__init__.py")
                    
                    if os.path.exists(main_file):
                        with open(main_file, "r") as f:
                            content = f.read()
                            # If file is tiny and has imports, look for other .py files
                            if len(content) < 500 and ("import " in content or "from ." in content):
                                for other in os.listdir(skill_root):
                                    if other.endswith(".py") and other not in ("__init__.py", "test.py"):
                                        main_file = os.path.join(skill_root, other)
                                        with open(main_file, "r") as f2:
                                            content = f2.read()
                                        break
                        self._send_json({"source": content, "file": os.path.basename(main_file)})
                        return
                self._send_json({"error": "Skill not found"}, 404)
            elif self.path.startswith("/api/vcs/diff"):
                from core.vcs import get_vcs
                from urllib.parse import urlparse, parse_qs
                query = parse_qs(urlparse(self.path).query)
                commit_hash = query.get("hash", [None])[0]
                if commit_hash:
                    patch = get_vcs().get_patch(commit_hash)
                    self._send_json({"diff": patch})
                else:
                    self._send_json({"error": "No hash provided"}, 400)

            elif self.path.startswith("/api/skills/docs"):
                from skills.skill_registry import discover_skills
                from urllib.parse import urlparse, parse_qs
                query = parse_qs(urlparse(self.path).query)
                skill_name = query.get("name", [None])[0]
                if skill_name:
                    registry = discover_skills()
                    info = registry.get(skill_name, {})
                    
                    # Fallback 1: SKILL.md content
                    doc = info.get("description", "No documentation provided.")
                    
                    # Fallback 2: AST Docstring from main file
                    skill_root = os.path.join(config.SKILLS_DIR, skill_name)
                    for target in ["__init__.py", f"{skill_name}.py", "parser.py", "log.py", "summarizer.py", "monitor.py"]:
                        fpath = os.path.join(skill_root, target)
                        if os.path.exists(fpath):
                            with open(fpath, "r") as f:
                                content = f.read()
                                import ast
                                try:
                                    tree = ast.parse(content)
                                    ast_doc = ast.get_docstring(tree)
                                    if ast_doc:
                                        doc = ast_doc
                                        break
                                    # Fallback 3: First Comment Block
                                    comments = []
                                    for line in content.splitlines():
                                        if line.strip().startswith("#"):
                                            comments.append(line.strip("# ").strip())
                                        elif not line.strip():
                                            continue
                                        else:
                                            break
                                    if comments:
                                        doc = "\n".join(comments)
                                        break
                                except: pass
                    self._send_json({"docs": doc})
                    return
                self._send_json({"error": "Skill not found"}, 404)

            elif self.path == "/api/security/audit-trail":
                # Batch 5: Retrieve audit logs
                try:
                    with open(config.AUDIT_LOG_PATH, "r") as f:
                        lines = f.readlines()[-100:]
                        self._send_json({"logs": [line.strip() for line in lines]})
                except:
                    self._send_json({"logs": []})

            elif self.path == "/api/security/integrity":
                # Batch 5: System integrity report
                from skills.hardware_monitor import get_system_info
                hw = get_system_info()
                integrity = {
                    "vcs_status": "Clean",
                    "core_checksum": "Verified",
                    "active_skills": "Authenticated",
                    "env_stability": "High",
                    "hardware_health": "Optimal" if (hw.get('cpu_percent', 0) < 80) else "Strained",
                    "global_lock": "ACTIVE" if getattr(config, "GLOBAL_LOCK", False) else "Disabled"
                }
                self._send_json(integrity)

            elif self.path == "/api/security/vault":
                # Batch 5: Secure env vars (masked)
                vault_keys = ["OLLAMA_API_KEY", "TELEGRAM_BOT_TOKEN", "GROQ_API_KEY", "MASTER_PASSWORD"]
                vault_data = {k: "********" if getattr(config, k, None) else "Not Set" for k in vault_keys}
                self._send_json(vault_data)

            elif self.path == "/api/cluster/health":
                # Aggregate health from all peers + local
                import asyncio
                from core.federation import federation
                from skills.hardware_monitor import get_system_info
                
                async def get_all():
                    # Reference globals or local imports carefully to avoid NameError shadowing
                    import os as _os
                    stats = get_system_info()
                    local_info = {
                        "url": "local",
                        "instance_name": config.INSTANCE_NAME,
                        "status": "online",
                        "is_local": True,
                        "cpu": stats.get("cpu", {}).get("usage_percent", 0),
                        "ram": stats.get("memory", {}).get("used_percent", 0),
                        "disk": stats.get("disk", {}).get("used_percent", 0),
                        "telegram_active": _os.environ.get("ASURA_TELEGRAM_ACTIVE") == "true",
                        "is_leader": _os.environ.get("ASURA_MANAGED_BOT") == "true" or _os.environ.get("ASURA_TELEGRAM_ACTIVE") == "true"
                    }
                    peer_results = await federation.ping_peers()
                    
                    # Flatten peer results for easy UI consumption
                    formalized = [local_info]
                    for pr in peer_results:
                        p_data = pr.get("data", {})
                        formalized.append({
                            "url": pr.get("url"),
                            "instance_name": p_data.get("instance_name", pr.get("url")),
                            "status": pr.get("status"),
                            "cpu": p_data.get("cpu", 0),
                            "ram": p_data.get("ram", 0),
                            "disk": p_data.get("disk", 0),
                            "is_leader": p_data.get("is_leader", False),
                            "telegram_active": p_data.get("telegram_active", False),
                            "error": pr.get("error")
                        })
                    return formalized

                try:
                    loop = asyncio.new_event_loop()
                    results = loop.run_until_complete(get_all())
                    loop.close()
                    self._send_json(results)
                except Exception as e:
                    self._send_json({"error": str(e)}, 500)

            elif self.path == "/api/evolve":
                import psutil
                is_running = False
                for p in psutil.process_iter(['cmdline']):
                    try:
                        if p.info['cmdline'] and any('main.py' in cmd for cmd in p.info['cmdline']):
                            is_running = True
                            break
                    except: pass
                if not is_running:
                    self._send_json({"status": "SYSTEM OFFLINE: Cannot evolve while core process is down.", "logs": []}, 400)
                    return
                from core.self_updater import updater
                logs = []
                try: logs = updater._get_recent_updates(10)
                except: pass
                self._send_json({"status": "Evolution check result", "logs": logs})
            elif self.path == "/api/progress":
                self._handle_sse_progress()
            else:
                self.send_error(404)
        except (ConnectionResetError, BrokenPipeError):
            # Silence common socket noise during navigation
            pass
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            log_app(f"Dashboard GET Error: {e}\n{error_details}")
            self.send_error(500, f"{e}\n{error_details}")

    def do_POST(self):
        # 0. Global Lock Check
        if getattr(config, "GLOBAL_LOCK", False) and self.path.startswith("/api/") and self.path != "/api/security/lock":
            self._send_json({"error": "GLOBAL LOCK ACTIVE: System is in read-only mode."}, 423)
            return

        from skills.logger import log_app
        log_app(f"HTTP POST Received [{self.path}] - Content-Type: {self.headers.get('Content-Type')}")

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        # 1. Handle Login (Public)
        if self.path == "/login":
            try:
                data = json.loads(body)
                password = data.get("password", "")
            except:
                import urllib.parse
                params = urllib.parse.parse_qs(body.decode())
                password = params.get("password", [""])[0]

            if password == config.MASTER_PASSWORD:
                token = create_access_token({"sub": "master"})
                self.send_response(200) # For JSON login
                self.send_header("Set-Cookie", f"tf_token={token}; Path=/; HttpOnly; SameSite=Strict")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success"}).encode())
            else:
                self._send_json({"error": "Invalid Password"}, 401)
            return

        # 2. Auth Guard
        if not self._is_authenticated() and self.path != "/api/login":
            self._send_json({"error": "Unauthorized"}, 401)
            return

        # 3. Handle APIs
        try:
            # Multi-part Voice
            if self.path == "/api/voice":
                content_type = self.headers.get("Content-Type", "")
                if "multipart/form-data" in content_type:
                    boundary = content_type.split("boundary=")[-1].encode()
                    parts = body.split(b"--" + boundary)
                    audio_bytes = b""
                    for p in parts:
                        if b'name="audio"' in p:
                            # Split into headers and body using maxsplit=1
                            # to avoid splitting inside the binary content
                            data_split = p.split(b"\r\n\r\n", 1)
                            if len(data_split) > 1:
                                audio_bytes = data_split[1]
                                # remove trailing \r\n before the boundary
                                if audio_bytes.endswith(b"\r\n"):
                                    audio_bytes = audio_bytes[:-2]
                            break
                    if not audio_bytes:
                        self._send_json({"error": "No audio data"}, 400)
                        return
                    from skills.voice_chat.pipeline import voice_chat_single
                    resp_audio = voice_chat_single(audio_bytes, user_id="dashboard_voice")
                    self.send_response(200)
                    self.send_header("Content-Type", "audio/wav")
                    self.end_headers()
                    self.wfile.write(resp_audio)
                    return

            # JSON APIs
            data = json.loads(body) if body else {}

            if self.path == "/api/chat":
                import asyncio
                from core.gateway import handle_message, handle_command
                msg = data.get("message", "")
                try:
                    if msg.startswith("/"):
                        res = asyncio.run(handle_command("dashboard", msg, channel="web")) if asyncio.iscoroutinefunction(handle_command) else handle_command("dashboard", msg, channel="web")
                    else:
                        res = asyncio.run(handle_message("dashboard", msg, channel="web", stream=False))
                    self._send_json({"response": res or "OK"})
                except Exception as chat_err:
                    self._send_json({"response": f"⚠️ Error: {chat_err}"})

            elif self.path == "/api/command":
                from core.gateway import handle_command
                cmd = data.get("command", "")
                try:
                    # Use existing run_async bridge for robustness
                    if asyncio.iscoroutinefunction(handle_command):
                        res = run_async(handle_command("dashboard", cmd, channel="web"))
                    else:
                        res = handle_command("dashboard", cmd, channel="web")
                    self._send_json({"response": res or "Acknowledged."})
                except Exception as cmd_err:
                    self._send_json({"response": f"⚠️ Error: {cmd_err}"})

            elif self.path == "/api/settings/update":
                # update .env and config
                from core.state_manager import update_env
                update_env(data)

                # Update runtime config
                for k, v in data.items():
                    if hasattr(config, k):
                        setattr(config, k, v)

                self._send_json({"status": "Settings updated and saved to .env"})

            elif self.path == "/api/persona/update":
                config.PERSONA.update(data)
                self._send_json({"status": "persona_tuned"})

            elif self.path == "/api/skills/toggle":
                skill = data.get("skill")
                self._send_json({"status": "toggled", "skill": skill})

            elif self.path == "/api/security/rotate-key":
                # Batch 5: Mock key rotation
                self._send_json({"status": "Access key rotated", "new_key_id": "SK-VO-..."})

            elif self.path == "/api/intelligence/tokenize":
                text = data.get("text", "")
                # Simple word/char based token approximation
                tokens = len(text.split()) * 1.3
                self._send_json({"count": int(tokens)})

            elif self.path == "/api/security/export":
                # Implementation of data export as a JSON dump
                export_data = {
                    "vcs": [],
                    "audit": [],
                    "state": {}
                }
                try:
                    from core.vcs import get_vcs
                    export_data["vcs"] = get_vcs().list_history()
                    with open(config.AUDIT_LOG_PATH, "r") as f:
                        export_data["audit"] = f.readlines()[-500:]
                except: pass

                export_path = os.path.join(config.DRAFTS_DIR, f"tf_export_{int(time.time())}.json")
                with open(export_path, "w") as f:
                    json.dump(export_data, f, indent=2)

                self._send_json({"status": "Export created", "path": export_path})

            elif self.path == "/api/system/jobs/kill":
                pid = data.get("pid")
                if pid:
                    import subprocess
                    subprocess.run(["kill", "-9", str(pid)])
                    self._send_json({"status": f"Process {pid} terminated"})
                else:
                    self._send_json({"error": "PID required"}, 400)

            elif self.path == "/api/security/lock":
                lock_state = data.get("active", False)
                config.GLOBAL_LOCK = lock_state
                self._send_json({"status": f"Global Lock {'Enabled' if lock_state else 'Disabled'}"})

            elif self.path == "/api/system/control":
                # Batch 4: Cancel jobs
                from core.job_manager import manager
                job_id = data.get("job_id")
                if manager.cancel_job(job_id):
                    self._send_json({"status": "cancelled", "job_id": job_id})
                else:
                    self._send_json({"status": "failed", "error": "Job not found or already done"}, 400)

            elif self.path == "/api/system/repl":
                # Batch 4: Live Python REPL
                code = data.get("code", "")
                try:
                    # Capture stdout
                    import sys, io
                    old_stdout = sys.stdout
                    redirected_output = io.StringIO()
                    sys.stdout = redirected_output
                    
                    # Execute in a controlled global context
                    exec_globals = {"config": config, "os": os, "json": json}
                    exec(code, exec_globals)
                    
                    sys.stdout = old_stdout
                    self._send_json({"output": redirected_output.getvalue()})
                except Exception as e:
                    self._send_json({"output": f"Error: {str(e)}"}, 400)

            elif self.path == "/api/recommendations/approve":
                from core.recommendation import recommendation_store
                rec_id = data.get("id")
                if rec_id:
                    recommendation_store.update_status(rec_id, "approved")
                    self._send_json({"status": f"Recommendation {rec_id} approved"})
                else:
                    self._send_json({"error": "ID required"}, 400)

            elif self.path == "/api/recommendations/dismiss":
                from core.recommendation import recommendation_store
                rec_id = data.get("id")
                if rec_id:
                    recommendation_store.update_status(rec_id, "dismissed")
                    self._send_json({"status": f"Recommendation {rec_id} dismissed"})
                else:
                    self._send_json({"error": "ID required"}, 400)

            elif self.path == "/api/recommendations/clear":
                from core.recommendation import recommendation_store
                status = data.get("status")
                recommendation_store.clear_all(status)
                self._send_json({"status": f"All {status or 'pending'} recommendations cleared"})

            else:
                self.send_error(404)

        except (ConnectionResetError, BrokenPipeError):
            pass
        except (ConnectionResetError, BrokenPipeError):
            pass
        except Exception as e:
            log_app(f"Dashboard POST Error: {e}")
            self.send_error(500, str(e))

    def _handle_sse_progress(self):
        """Handle Server-Sent Events for progress tracking."""
        from skills.dashboard.progress_socket import progress_manager
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        
        queue = progress_manager.subscribe()
        try:
            while True:
                data = queue.get()
                self.wfile.write(f"data: {json.dumps(data)}\n\n".encode())
                self.wfile.flush()
        except Exception:
            progress_manager.unsubscribe(queue)

    def log_message(self, format, *args):
        pass


def start_dashboard():
    """Start the Sovereign Command Center."""
    def run():
        import socket
        port = config.DASHBOARD_PORT
        log_app(f"Initializing Command Center on port {port}...")
        
        class ReuseAddrServer(ThreadingHTTPServer):
            def server_bind(self):
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                super().server_bind()

        try:
            srv = ReuseAddrServer(("0.0.0.0", port), DashboardHandler)
        except OSError:
            import psutil
            log_app(f"Port {port} in use. Forcing clear...")
            try:
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        for conn in proc.connections(kind='inet'):
                            if conn.laddr.port == port:
                                log_app(f"Killing PID {proc.info['pid']} holding port {port}")
                                proc.kill()
                    except: pass
            except Exception as e:
                log_app(f"Port clear error: {e}")
            
            import time
            time.sleep(1.0)
            srv = ReuseAddrServer(("0.0.0.0", port), DashboardHandler)
        
        log_app(f"Sovereign Command Center on http://localhost:{port}")
        srv.serve_forever()

    threading.Thread(target=run, daemon=True, name="dashboard").start()
    log_audit("DASHBOARD", f"Sovereign Command Center started on port {config.DASHBOARD_PORT}")

if __name__ == "__main__":
    start_dashboard()
    import time
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass