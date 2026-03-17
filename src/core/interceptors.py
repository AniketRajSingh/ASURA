# ============================================================
# core/interceptors.py — Security & Safety Interceptor System
#
# Pre-execution validation hooks that run before any tool execution.
# Prevents dangerous commands, detects secrets, and enforces production safeguards.
# ============================================================

import re
from typing import Dict, List, Callable, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class InterceptResult:
    """Result of an interceptor check."""
    blocked: bool
    reason: str
    suggestion: Optional[str] = None
    requires_confirmation: bool = False


class InterceptorRule:
    """Represents a single security/validation rule."""

    def __init__(self, name: str, pattern: str, action: str, description: str):
        self.name = name
        self.pattern = re.compile(pattern, re.IGNORECASE)
        self.action = action  # 'block', 'warn', 'require_confirm'
        self.description = description

    def check(self, value: str) -> Optional[InterceptResult]:
        """Check if a value matches this rule."""
        match = self.pattern.search(value)
        if not match:
            return None

        if self.action == "block":
            return InterceptResult(
                blocked=True,
                reason=f"Blocked by {self.name}: {self.description}",
                suggestion=self._generate_suggestion()
            )
        elif self.action == "require_confirm":
            return InterceptResult(
                blocked=False,
                reason=f"Requires confirmation: {self.description}",
                requires_confirmation=True,
                suggestion="Add --force flag to bypass confirmation"
            )
        else:  # warn action
            return InterceptResult(
                blocked=False,
                reason=f"Warning: {self.description}",
                suggestion=self._generate_suggestion()
            )

    def _generate_suggestion(self) -> str:
        """Generate a helpful suggestion for safe alternatives."""
        suggestions = {
            "rm": "Use 'git restore' or add files to .gitignore instead",
            "chmod 777": "Set specific permissions (e.g., chmod 755)",
            "DROP": "Ensure proper transaction rollback and backups exist",
            "secrets": "Use environment variables or secure vault",
        }

        for keyword, suggestion in suggestions.items():
            if keyword.lower() in self.name.lower():
                return suggestion
        return "Review command before proceeding"


class DangerousCommandsRule:
    """Detects and blocks dangerous shell commands."""

    RULES = [
        InterceptorRule(
            name="rm-dangerous",
            pattern=r'\brm\s+(-rf|--recursive|--force)\s+([~/.]|\.\.|src|core|config)',
            action="block",
            description="Dangerous: rm -rf on critical paths (root, home, src, or parent dirs)"
        ),
        InterceptorRule(
            name="dd-destructive",
            pattern=r'\bdd\s+if=/dev/(zero|urandom|random|sd|nvme)',
            action="block",
            description="Dangerous: dd overwrite/disk commands"
        ),
        InterceptorRule(
            name="chmod-777",
            pattern=r'chmod\s+777',
            action="require_confirm",
            description="Sets world-writable permissions on files/directories"
        ),
        InterceptorRule(
            name="mkfs-destructive",
            pattern=r'\bmkfs',
            action="block",
            description="Dangerous: filesystem creation/destruction command"
        ),
        InterceptorRule(
            name="chown-root",
            pattern=r'chown\s+root:',
            action="require_confirm",
            description="Changes ownership to root user"
        ),
        InterceptorRule(
            name="asura-brain-tampering",
            pattern=r'\b(rm|mv|truncate)\b.*\.gemini/antigravity/brain',
            action="block",
            description="Unauthorized attempt to modify ASURA cognitive records"
        ),
    ]

    @classmethod
    def check_command(cls, command: str) -> Optional[InterceptResult]:
        """Check a shell command against dangerous patterns."""
        for rule in cls.RULES:
            result = rule.check(command)
            if result:
                return result
        return None


class SecretPatternRule:
    """Detects potential hardcoded secrets and credentials."""

    SECRET_PATTERNS = [
        (r'api[_-]?key\s*[=:]\s*["\']?[A-Za-z0-9]{20,}', "API key assignment"),
        (r'password\s*[=:]\s*["\']?[^\s"\']+["\']?', "Hardcoded password"),
        (r'secret[_-]?key\s*[=:]\s*["\']?[A-Za-z0-9]{16,}', "Secret key assignment"),
        (r'AWS_SECRET_ACCESS_KEY\s*[=:]', "AWS secret key"),
        (r'TELEGRAM_BOT_TOKEN\s*[=:]\s*["\']?\d+:[A-Za-z0-9_-]+', "Telegram bot token"),
        (r'Bearer\s+[A-Za-z0-9._-]+', "Bearer token in code"),
    ]

    @classmethod
    def check_content(cls, content: str) -> List[Tuple[str, str]]:
        """Scan content for potential secrets."""
        findings = []
        for pattern, description in cls.SECRET_PATTERNS:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                findings.append((description, f"{pattern} detected"))
        return findings


class ProductionGuardRule:
    """Rules to protect production environments."""

    PRODUCTION_PATHS = [
        '/var/www',
        '/usr/local/www',
        '/opt/app',
        'production',
        'prod',
    ]

    @classmethod
    def check_path(cls, path: str) -> Optional[InterceptResult]:
        """Check if operation affects production paths."""
        for prod_path in cls.PRODUCTION_PATHS:
            if prod_path.lower() in path.lower():
                return InterceptResult(
                    blocked=False,
                    reason=f"Production environment detected: {path}",
                    requires_confirmation=True,
                    suggestion="Use staging environment for testing first"
                )
        return None


class ToolInterceptor:
    """Central interceptor registry and dispatcher."""

    def __init__(self):
        self.interceptors = [
            DangerousCommandsRule.check_command,
            SecretPatternRule.check_content,
            ProductionGuardRule.check_path,
        ]

        # Custom rules that can be added dynamically
        self.custom_rules: List[Tuple[Callable, str]] = []

    def add_custom_rule(self, name: str, rule_func: Callable, description: str):
        """Add a custom interceptor rule."""
        self.custom_rules.append((name, rule_func, description))

    def intercept(self, tool_name: str, tool_args: dict) -> Optional[InterceptResult]:
        """
        Run all relevant interceptors for a tool call.

        Args:
            tool_name: Name of the tool being called
            tool_args: Dictionary of tool arguments

        Returns:
            InterceptResult if any rule triggers, None otherwise
        """
        # Build content to check based on tool type
        content_to_check = " ".join(str(v) for v in tool_args.values())

        result = None
        for interceptor in self.interceptors:
            if result is None or (not result.blocked):
                try:
                    check_result = interceptor(content_to_check)
                    if check_result:
                        result = check_result
                        if result.blocked:
                            break
                except Exception:
                    continue

        # Check custom rules
        if result is None:
            for rule_name, rule_func, _ in self.custom_rules:
                try:
                    custom_result = rule_func(tool_args)
                    if custom_result:
                        result = custom_result
                        if result.blocked:
                            break
                except Exception:
                    continue

        return result

    def requires_confirmation(self, tool_name: str, tool_args: dict) -> Tuple[bool, str]:
        """Check if a tool call requires user confirmation."""
        result = self.intercept(tool_name, tool_args)
        if result and result.requires_confirmation:
            return True, f"Confirmation required: {result.reason}"
        return False, "Proceed with caution"


# Global interceptor instance
_interceptor_instance: Optional[ToolInterceptor] = None


def get_interceptor() -> ToolInterceptor:
    """Get or create the global interceptor singleton."""
    global _interceptor_instance
    if _interceptor_instance is None:
        _interceptor_instance = ToolInterceptor()
    return _interceptor_instance


def check_tool_call(tool_name: str, tool_args: dict) -> Tuple[bool, Optional[str]]:
    """
    Quick check if a tool call should be blocked or requires confirmation.

    Returns:
        Tuple of (should_block, reason_if_blocked_or_warning)
    """
    interceptor = get_interceptor()
    result = interceptor.intercept(tool_name, tool_args)

    if result:
        if result.blocked:
            return True, result.reason
        elif result.requires_confirmation:
            return False, f"Requires confirmation: {result.reason}"

    return False, None


def add_dangerous_command_rule(pattern: str, action: str = "block", description: str = ""):
    """Dynamically add a new dangerous command rule."""
    interceptor = get_interceptor()
    if not description:
        description = f"Pattern: {pattern}"

    new_rule = InterceptorRule(
        name=f"custom-{pattern[:10].replace(' ', '_')}",
        pattern=pattern,
        action=action,
        description=description
    )

    # Add to DangerousCommandsRule at runtime
    if not hasattr(DangerousCommandsRule, 'DYNAMIC_RULES'):
        DangerousCommandsRule.DYNAMIC_RULES = []
    DangerousCommandsRule.DYNAMIC_RULES.append(new_rule)
