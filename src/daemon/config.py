"""
Configuration for ASURA Daemon
"""
import os
from pathlib import Path

# Project Root
PROJECT_ROOT = Path('/Users/aniketrajsingh/Desktop/ASURA')

# Daemon Configuration
DAEMON_NAME = 'asura_daemon'
LOG_DIR = PROJECT_ROOT / 'data' / 'logs'
LOG_FILE = LOG_DIR / 'daemon.log'
PID_FILE = PROJECT_ROOT / 'data' / 'daemon.pid'

# Telegram Configuration
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
ADMIN_CHAT_ID = os.getenv('TELEGRAM_ADMIN_CHAT_ID', '')

# Command Patterns
COMMANDS = {
    'restart': '/restart',
    'status': '/status',
    'stop': '/stop',
}

# Execution Paths
ASURA_STOP_SCRIPT = PROJECT_ROOT / 'asura' / 'stop'
ASURA_RUN_SCRIPT = PROJECT_ROOT / 'asura' / 'run'

# Timeout Settings
RESTART_TIMEOUT = 30
CHECK_INTERVAL = 5
