"""
Safe Discovery Agent - Security layer for LLM-powered discovery operations
Prevents execution of dangerous commands during client environment exploration
"""

import re
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
from enum import Enum


class CommandSafetyLevel(Enum):
    SAFE = "safe"
    SUSPICIOUS = "suspicious"
    DANGEROUS = "dangerous"
    BLOCKED = "blocked"


@dataclass
class CommandValidationResult:
    safe: bool
    level: CommandSafetyLevel
    reason: str
    sanitized_command: Optional[str] = None
    concerns: List[str] = None

    def __post_init__(self):
        if self.concerns is None:
            self.concerns = []


class SafeDiscoveryAgent:
    """
    Ensures LLM-generated discovery commands are safe to execute
    Prevents data destruction, privilege escalation, and system compromise
    """
    
    # Commands that will NEVER be allowed
    FORBIDDEN_COMMANDS = {
        'rm -rf',
        'mkfs',
        'dd if=',
        'kill -9',
        'killall',
        'shutdown',
        'reboot',
        'halt',
        'poweroff',
        'init 0',
        'init 6',
        ':(){:|:&};:',  # Fork bomb
        'chmod 777',
        'chown root',
        'sudo su',
        'su -',
        'passwd',
        'userdel',
        'groupdel',
        'crontab',
        'at',  # Job scheduler (removed trailing space for word boundary matching)
        'fdisk',
        'parted',
        'mkswap',
        'swapon',
        'swapoff',
        'mount',
        'umount',
        'systemctl stop',
        'systemctl disable',
        'service stop',
        'iptables -F',
        'ufw disable',
        'setenforce 0',
    }
    
    # Commands that are explicitly allowed for discovery
    READ_ONLY_COMMANDS = {
        'ls',
        'cat',
        'find',
        'grep',
        'awk',
        'sed',
        'head',
        'tail',
        'wc',
        'file',
        'stat',
        'which',
        'whereis',
        'type',
        'echo',
        'printf',
        'pwd',
        'whoami',
        'hostname',
        'uname',
        'date',
        'curl',
        'wget',
        'dig',
        'nslookup',
        'ping',
        'traceroute',
        'netstat',
        'ss',
        'ip addr',
        'ifconfig',
        'ps',
        'top',
        'htop',
        'df',
        'du',
        'free',
        'uptime',
        'env',
        'printenv',
        'git log',
        'git show',
        'git diff',
        'git status',
        'git branch',
        'docker ps',
        'docker images',
        'docker inspect',
        'kubectl get',
        'kubectl describe',
        'kubectl logs',
        'systemctl status',
        'systemctl list-units',
        'journalctl',
    }
    
    # Dangerous patterns in commands
    DANGEROUS_PATTERNS = [
        r';\s*rm\s+-rf',
        r'&&\s*rm\s+-rf',
        r'\|\s*bash',
        r'\|\s*sh',
        r'`[^`]*rm[^`]*`',
        r'\$\([^)]*rm[^)]*\)',
        r'>\s*/dev/sd[a-z]',
        r'>\s*/dev/null',
        r'/etc/passwd',
        r'/etc/shadow',
        r'/etc/sudoers',
        r'\.\./',
        r'\.\./\.\./',
        r'eval\s*\(',
        r'exec\s*\(',
        r'\$\([^)]*\$\(',  # Nested command substitution
        r'>\s*&',
        r'2>&1.*\|.*bash',
        r'/dev/tcp/',
        r'/dev/udp/',
        r'nc\s+-[le]',  # netcat listening
        r'ncat\s+-[le]',
        r'socat',
        r'base64.*decode',
        r'openssl.*decrypt',
        r'gpg.*decrypt',
    ]
    
    # Suspicious flags that might indicate destructive operations
    SUSPICIOUS_FLAGS = {
        '-f',  # force
        '-r',  # recursive
        '-R',  # recursive
        '--force',
        '--recursive',
        '--delete',
        '--remove',
        '--purge',
    }
    
    def __init__(self, max_command_length: int = 1000):
        self.max_command_length = max_command_length
        self.dangerous_pattern_regex = re.compile('|'.join(self.DANGEROUS_PATTERNS), re.IGNORECASE)
    
    def validate_command(self, command: str, context: str = "discovery") -> CommandValidationResult:
        """
        Validate a command for safety before execution
        
        Args:
            command: The shell command to validate
            context: Context for validation (discovery, execution, etc.)
            
        Returns:
            CommandValidationResult with safety assessment
        """
        
        concerns = []
        
        # 1. Length check
        if len(command) > self.max_command_length:
            return CommandValidationResult(
                safe=False,
                level=CommandSafetyLevel.BLOCKED,
                reason=f"Command exceeds maximum length ({len(command)} > {self.max_command_length})",
                concerns=["Abnormally long command - possible obfuscation attempt"]
            )
        
        # 2. Empty command check
        if not command or not command.strip():
            return CommandValidationResult(
                safe=False,
                level=CommandSafetyLevel.BLOCKED,
                reason="Empty command",
                concerns=["No command provided"]
            )
        
        command_lower = command.lower()
        
        # 3. Check forbidden commands (use word boundaries to avoid false positives)
        for forbidden in self.FORBIDDEN_COMMANDS:
            # Use word boundary regex for single words, exact match for multi-word commands
            if ' ' in forbidden:
                # Multi-word commands - exact substring match
                if forbidden.lower() in command_lower:
                    return CommandValidationResult(
                        safe=False,
                        level=CommandSafetyLevel.BLOCKED,
                        reason=f"Forbidden command detected: {forbidden}",
                        concerns=[f"Command contains blocked operation: {forbidden}"]
                    )
            else:
                # Single word - use word boundary to avoid false positives (e.g., 'cat' in 'concatenate')
                pattern = r'\b' + re.escape(forbidden.lower()) + r'\b'
                if re.search(pattern, command_lower):
                    return CommandValidationResult(
                        safe=False,
                        level=CommandSafetyLevel.BLOCKED,
                        reason=f"Forbidden command detected: {forbidden}",
                        concerns=[f"Command contains blocked operation: {forbidden}"]
                    )
        
        # 4. Check dangerous patterns
        if self.dangerous_pattern_regex.search(command):
            matches = self.dangerous_pattern_regex.findall(command)
            return CommandValidationResult(
                safe=False,
                level=CommandSafetyLevel.DANGEROUS,
                reason="Dangerous pattern detected",
                concerns=[f"Contains dangerous pattern: {m}" for m in matches[:3]]
            )
        
        # 5. Check for suspicious flags
        suspicious_flags_found = []
        for flag in self.SUSPICIOUS_FLAGS:
            if flag in command.split():
                suspicious_flags_found.append(flag)
        
        if suspicious_flags_found:
            concerns.append(f"Suspicious flags: {', '.join(suspicious_flags_found)}")
        
        # 6. Check for pipe chains (potentially suspicious)
        pipe_count = command.count('|')
        if pipe_count > 3:
            concerns.append(f"Complex pipe chain ({pipe_count} pipes)")
        
        # 7. Check for command substitution
        if '`' in command or '$(' in command:
            concerns.append("Contains command substitution")
        
        # 8. Check for redirection to sensitive locations
        if re.search(r'>\s*/etc/', command):
            return CommandValidationResult(
                safe=False,
                level=CommandSafetyLevel.BLOCKED,
                reason="Attempted write to /etc/ directory",
                concerns=["Cannot modify system configuration during discovery"]
            )
        
        # 9. Check if command starts with a known safe command
        command_parts = command.strip().split()
        if not command_parts:
            return CommandValidationResult(
                safe=False,
                level=CommandSafetyLevel.BLOCKED,
                reason="Invalid command format",
                concerns=["Unable to parse command"]
            )
        
        base_command = command_parts[0]
        
        # Remove sudo prefix if present (we'll check for it separately)
        if base_command == 'sudo' and len(command_parts) > 1:
            base_command = command_parts[1]
            concerns.append("Command uses sudo elevation")
        
        # Check if base command is in READ_ONLY list
        is_safe_command = False
        for safe_cmd in self.READ_ONLY_COMMANDS:
            if base_command == safe_cmd or base_command == safe_cmd.split()[0]:
                is_safe_command = True
                break
        
        if is_safe_command:
            if concerns:
                return CommandValidationResult(
                    safe=True,
                    level=CommandSafetyLevel.SUSPICIOUS,
                    reason="Safe command with suspicious elements",
                    sanitized_command=command,
                    concerns=concerns
                )
            else:
                return CommandValidationResult(
                    safe=True,
                    level=CommandSafetyLevel.SAFE,
                    reason="Command is in safe list",
                    sanitized_command=command,
                    concerns=[]
                )
        
        # 10. Unknown command - requires review
        return CommandValidationResult(
            safe=False,
            level=CommandSafetyLevel.SUSPICIOUS,
            reason=f"Unknown command: {base_command}",
            concerns=[f"Command '{base_command}' not in approved safe list"] + concerns
        )
    
    def validate_ssh_operation(
        self,
        host: str,
        command: str,
        user: Optional[str] = None
    ) -> CommandValidationResult:
        """
        Validate an SSH operation for safety
        
        Args:
            host: Target host
            command: Command to execute remotely
            user: SSH user (if specified)
            
        Returns:
            CommandValidationResult
        """
        
        # First validate the command itself
        result = self.validate_command(command, context="ssh")
        
        if not result.safe:
            return result
        
        # Additional SSH-specific checks
        concerns = list(result.concerns) if result.concerns else []
        
        # Check for suspicious host patterns
        if any(pattern in host.lower() for pattern in ['prod', 'production', 'master', 'primary']):
            concerns.append(f"Connecting to production host: {host}")
        
        # Warn about root user
        if user == 'root':
            concerns.append("Connecting as root user")
        
        if concerns:
            return CommandValidationResult(
                safe=True,
                level=CommandSafetyLevel.SUSPICIOUS,
                reason=result.reason,
                sanitized_command=result.sanitized_command,
                concerns=concerns
            )
        
        return result
    
    def validate_api_probe(self, url: str, method: str = "GET") -> CommandValidationResult:
        """
        Validate an API probe operation
        
        Args:
            url: URL to probe
            method: HTTP method
            
        Returns:
            CommandValidationResult
        """
        
        concerns = []
        
        # Check for suspicious URLs
        if any(pattern in url.lower() for pattern in ['/admin', '/root', '/system', '/delete', '/drop']):
            concerns.append(f"Probing sensitive endpoint: {url}")
        
        # Only allow safe HTTP methods during discovery
        safe_methods = {'GET', 'HEAD', 'OPTIONS'}
        if method.upper() not in safe_methods:
            return CommandValidationResult(
                safe=False,
                level=CommandSafetyLevel.BLOCKED,
                reason=f"HTTP method {method} not allowed during discovery",
                concerns=[f"Only {safe_methods} methods allowed for probing"]
            )
        
        # Check for localhost/internal IPs (SSRF risk)
        if any(pattern in url.lower() for pattern in ['localhost', '127.0.0.1', '0.0.0.0', '::1']):
            concerns.append("Probing localhost/loopback addresses")
        
        if concerns:
            return CommandValidationResult(
                safe=True,
                level=CommandSafetyLevel.SUSPICIOUS,
                reason="API probe has concerns",
                sanitized_command=f"{method} {url}",
                concerns=concerns
            )
        
        return CommandValidationResult(
            safe=True,
            level=CommandSafetyLevel.SAFE,
            reason="Safe API probe",
            sanitized_command=f"{method} {url}",
            concerns=[]
        )
    
    def sanitize_command(self, command: str) -> str:
        """
        Sanitize a command by removing dangerous elements
        
        Args:
            command: Command to sanitize
            
        Returns:
            Sanitized command (or original if no sanitization needed)
        """
        
        sanitized = command
        
        # Remove command chaining
        if '&&' in sanitized or '||' in sanitized or ';' in sanitized:
            # Only keep the first command
            sanitized = re.split(r'[;&|]', sanitized)[0].strip()
        
        # Remove command substitution
        sanitized = re.sub(r'`[^`]*`', '', sanitized)
        sanitized = re.sub(r'\$\([^)]*\)', '', sanitized)
        
        # Remove redirects
        sanitized = re.sub(r'>\s*[^\s]+', '', sanitized)
        sanitized = re.sub(r'<\s*[^\s]+', '', sanitized)
        
        return sanitized.strip()
    
    def generate_safe_alternatives(self, dangerous_command: str) -> List[str]:
        """
        Generate safe alternative commands for a dangerous operation
        
        Args:
            dangerous_command: The dangerous command
            
        Returns:
            List of safer alternatives
        """
        
        alternatives = []
        
        # Common dangerous operation -> safe alternative mappings
        if 'rm -rf' in dangerous_command:
            alternatives.append("Use 'ls -la' to list files first, then remove specific files")
            alternatives.append("Use 'mv' to move files to a backup location instead")
        
        if 'chmod 777' in dangerous_command:
            alternatives.append("Use 'chmod 755' for directories or 'chmod 644' for files")
        
        if 'sudo' in dangerous_command:
            alternatives.append("Execute without sudo first to test safety")
            alternatives.append("Request manual approval for elevated operations")
        
        if 'shutdown' in dangerous_command or 'reboot' in dangerous_command:
            alternatives.append("Use 'systemctl restart <service>' to restart specific services")
        
        if not alternatives:
            alternatives.append("Command flagged as dangerous - manual review required")
        
        return alternatives


class DiscoveryRateLimiter:
    """
    Rate limiter for discovery operations to prevent abuse
    """
    
    def __init__(
        self,
        max_commands_per_minute: int = 30,
        max_ssh_connections_per_host: int = 5,
        max_api_calls_per_minute: int = 60
    ):
        self.max_commands_per_minute = max_commands_per_minute
        self.max_ssh_connections_per_host = max_ssh_connections_per_host
        self.max_api_calls_per_minute = max_api_calls_per_minute
        
        self._command_history: List[float] = []
        self._ssh_connections: Dict[str, List[float]] = {}
        self._api_calls: List[float] = []
    
    def check_command_rate(self) -> bool:
        """Check if command rate limit is exceeded"""
        import time
        now = time.time()
        
        # Clean old entries (older than 1 minute)
        self._command_history = [t for t in self._command_history if now - t < 60]
        
        if len(self._command_history) >= self.max_commands_per_minute:
            return False
        
        self._command_history.append(now)
        return True
    
    def check_ssh_rate(self, host: str) -> bool:
        """Check if SSH connection rate limit is exceeded for a host"""
        import time
        now = time.time()
        
        if host not in self._ssh_connections:
            self._ssh_connections[host] = []
        
        # Clean old entries
        self._ssh_connections[host] = [t for t in self._ssh_connections[host] if now - t < 60]
        
        if len(self._ssh_connections[host]) >= self.max_ssh_connections_per_host:
            return False
        
        self._ssh_connections[host].append(now)
        return True
    
    def check_api_rate(self) -> bool:
        """Check if API call rate limit is exceeded"""
        import time
        now = time.time()
        
        # Clean old entries
        self._api_calls = [t for t in self._api_calls if now - t < 60]
        
        if len(self._api_calls) >= self.max_api_calls_per_minute:
            return False
        
        self._api_calls.append(now)
        return True


# Usage example
if __name__ == "__main__":
    agent = SafeDiscoveryAgent()
    
    # Test cases
    test_commands = [
        "ls -la /opt/scripts",
        "find /opt/scripts -type f -executable",
        "cat /etc/passwd",
        "rm -rf /",
        "curl https://api.example.com/health",
        "sudo rm -rf /tmp/cache",
        "ls -la && rm -rf /tmp",
        "cat script.sh | bash",
        "find . -name '*.sh' -exec cat {} \\;",
    ]
    
    print("Command Safety Validation Tests:\n")
    for cmd in test_commands:
        result = agent.validate_command(cmd)
        status_icon = "Yes" if result.safe else "No"
        print(f"{status_icon} [{result.level.value.upper()}] {cmd}")
        print(f"   Reason: {result.reason}")
        if result.concerns:
            print(f"   Concerns: {', '.join(result.concerns)}")
        if not result.safe and result.level == CommandSafetyLevel.BLOCKED:
            alternatives = agent.generate_safe_alternatives(cmd)
            print(f"   Alternatives: {alternatives[0]}")
        print()
