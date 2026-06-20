"""
SSH client implementation with mock support for testing
Implements the ScriptHostClient protocol for script discovery
Uses asyncssh for production, falls back to mock for testing
"""

import asyncio
import logging
import os
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

try:
    import asyncssh
    ASYNCSSH_AVAILABLE = True
except ImportError:
    ASYNCSSH_AVAILABLE = False
    asyncssh = None

# Check if we should use mock SSH (for testing)
USE_MOCK_SSH = os.getenv('USE_MOCK_SSH', 'false').lower() == 'true'

logger = logging.getLogger(__name__)


@dataclass
class SSHCredentials:
    """SSH authentication credentials"""
    username: str
    password: Optional[str] = None
    private_key_path: Optional[str] = None
    private_key_passphrase: Optional[str] = None


class AsyncSSHClient:
    """
    SSH client with mock support for testing
    Uses asyncssh for production, mock implementation for testing
    """
    
    def __init__(
        self,
        host: str,
        port: int,
        credentials,
        timeout: int = 30,
        connection_pool_size: int = 5
    ):
        self.host = host
        self.port = port
        self.credentials = credentials
        self.timeout = timeout
        self.connection_pool_size = connection_pool_size
        self._connection: Optional[Any] = None
        self._connection_lock = asyncio.Lock()
        self._connected = False
        
        # Determine if we should use mock (only if explicitly enabled via env var)
        self.use_mock = USE_MOCK_SSH
        
        if not self.use_mock and not ASYNCSSH_AVAILABLE:
            raise ImportError(
                "asyncssh is required for SSH functionality. "
                "Install it with: pip install asyncssh"
            )
    
    async def connect(self) -> None:
        """Establish SSH connection"""
        async with self._connection_lock:
            if self._connected and self._connection:
                return
            
            if self.use_mock:
                # Mock connection for testing
                logger.info(f"Using mock SSH connection to {self.host}:{self.port}")
                self._connected = True
                return
            
            try:
                # Prepare connection options
                connect_kwargs = {
                    'host': self.host,
                    'port': self.port,
                    'username': self.credentials.username,
                    'known_hosts': None,  # Disable host key checking (use with caution)
                    'connect_timeout': self.timeout
                }
                
                # Add authentication method
                if self.credentials.private_key_path:
                    connect_kwargs['client_keys'] = [self.credentials.private_key_path]
                    if self.credentials.private_key_passphrase:
                        connect_kwargs['passphrase'] = self.credentials.private_key_passphrase
                elif self.credentials.password:
                    connect_kwargs['password'] = self.credentials.password
                else:
                    # Try default keys
                    connect_kwargs['client_keys'] = None
                
                logger.info(f"Connecting to {self.host}:{self.port} as {self.credentials.username}")
                self._connection = await asyncssh.connect(**connect_kwargs)
                self._connected = True
                logger.info(f"Successfully connected to {self.host}")
                
            except asyncssh.Error as e:
                logger.error(f"SSH connection failed: {e}")
                raise ConnectionError(f"Failed to connect to {self.host}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error during SSH connection: {e}")
                raise
    
    async def disconnect(self) -> None:
        """Close SSH connection"""
        async with self._connection_lock:
            if self._connection:
                self._connection.close()
                await self._connection.wait_closed()
                self._connection = None
                self._connected = False
                logger.info(f"Disconnected from {self.host}")
    
    async def _ensure_connected(self) -> None:
        """Ensure connection is established"""
        if not self._connected or not self._connection:
            await self.connect()
    
    async def execute_command(
        self,
        command: str,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute a command over SSH
        
        Returns:
            Dict with 'stdout', 'stderr', 'exit_status'
        """
        await self._ensure_connected()
        
        if self.use_mock:
            # Use mock SSH server
            try:
                from tests.ssh.mock_ssh_server import get_mock_ssh_server
                
                server = get_mock_ssh_server()
                if not server.is_running:
                    raise ConnectionError("Mock SSH server not running")
                
                # Authenticate
                username = self.credentials.username
                password = getattr(self.credentials, 'password', None)
                
                if not server.authenticate(username, password=password):
                    raise PermissionError(f"Authentication failed for user {username}")
                
                # Execute command
                result = server.execute_command(command, username)
                
                return {
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'exit_status': result.exit_code
                }
                
            except ImportError:
                raise RuntimeError("Mock SSH server not available")
        
        try:
            timeout_val = timeout or self.timeout
            logger.debug(f"Executing command on {self.host}: {command}")
            
            result = await asyncio.wait_for(
                self._connection.run(command, check=False),
                timeout=timeout_val
            )
            
            return {
                'stdout': result.stdout.strip(),
                'stderr': result.stderr.strip(),
                'exit_status': result.exit_status
            }
            
        except asyncio.TimeoutError:
            logger.error(f"Command timed out after {timeout_val}s: {command}")
            raise TimeoutError(f"Command execution timed out after {timeout_val}s")
        except asyncssh.Error as e:
            logger.error(f"SSH command execution failed: {e}")
            raise RuntimeError(f"SSH command failed: {e}")
    
    async def list_scripts(self, directory: str) -> List[str]:
        """
        List executable scripts in a directory
        Implements ScriptHostClient protocol
        """
        # Escape directory path to prevent injection
        directory = directory.replace("'", "'\\''")
        
        # Find executable files (scripts)
        command = f"find '{directory}' -type f -executable 2>/dev/null"
        
        try:
            result = await self.execute_command(command)
            
            if result['exit_status'] != 0:
                logger.warning(
                    f"Script listing failed with exit status {result['exit_status']}: "
                    f"{result['stderr']}"
                )
                return []
            
            # Parse output - one file per line
            stdout = result['stdout']
            if not stdout:
                return []
            
            scripts = [line.strip() for line in stdout.split('\n') if line.strip()]
            logger.info(f"Found {len(scripts)} executable scripts in {directory}")
            return scripts
            
        except Exception as e:
            logger.error(f"Failed to list scripts in {directory}: {e}")
            return []
    
    async def read_file(self, path: str) -> str:
        """
        Read file contents
        Implements ScriptHostClient protocol
        """
        # Escape file path to prevent injection
        path = path.replace("'", "'\\''")
        
        # Use cat to read file
        command = f"cat '{path}' 2>/dev/null"
        
        try:
            result = await self.execute_command(command)
            
            if result['exit_status'] != 0:
                logger.error(
                    f"Failed to read file {path}: {result['stderr']}"
                )
                return ""
            
            logger.debug(f"Successfully read file {path} ({len(result['stdout'])} bytes)")
            return result['stdout']
            
        except Exception as e:
            logger.error(f"Failed to read file {path}: {e}")
            return ""
    
    async def file_exists(self, path: str) -> bool:
        """Check if a file exists"""
        path = path.replace("'", "'\\''")
        command = f"test -f '{path}' && echo 'exists' || echo 'not_found'"
        
        try:
            result = await self.execute_command(command)
            return result['stdout'] == 'exists'
        except Exception:
            return False
    
    async def is_executable(self, path: str) -> bool:
        """Check if a file is executable"""
        path = path.replace("'", "'\\''")
        command = f"test -x '{path}' && echo 'executable' || echo 'not_executable'"
        
        try:
            result = await self.execute_command(command)
            return result['stdout'] == 'executable'
        except Exception:
            return False
    
    async def get_file_info(self, path: str) -> Optional[Dict[str, Any]]:
        """Get file metadata"""
        path = path.replace("'", "'\\''")
        # Use stat with custom format
        command = (
            f"stat -c 'size:%s mode:%a modified:%Y' '{path}' 2>/dev/null || "
            f"stat -f 'size:%z mode:%p modified:%m' '{path}' 2>/dev/null"  # BSD/macOS
        )
        
        try:
            result = await self.execute_command(command)
            
            if result['exit_status'] != 0:
                return None
            
            # Parse stat output
            info = {}
            for pair in result['stdout'].split():
                if ':' in pair:
                    key, value = pair.split(':', 1)
                    info[key] = value
            
            return {
                'size': int(info.get('size', 0)),
                'mode': info.get('mode', ''),
                'modified': int(info.get('modified', 0))
            }
            
        except Exception as e:
            logger.error(f"Failed to get file info for {path}: {e}")
            return None
    
    async def __aenter__(self):
        """Context manager entry"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.disconnect()


class SSHClientFactory:
    """Factory for creating SSH clients with connection pooling"""
    
    def __init__(self, max_connections_per_host: int = 5):
        self.max_connections_per_host = max_connections_per_host
        self._pools: Dict[str, List[AsyncSSHClient]] = {}
        self._pool_locks: Dict[str, asyncio.Lock] = {}
    
    def create_client(
        self,
        host: str,
        credentials: Any,
        port: int = 22,
        timeout: int = 30
    ) -> AsyncSSHClient:
        """
        Create an SSH client
        
        Args:
            host: SSH host
            credentials: SSHCredentials or dict with username, password, etc.
            port: SSH port (default: 22)
            timeout: Connection timeout (default: 30)
        """
        # Convert dict credentials to SSHCredentials
        if isinstance(credentials, dict):
            creds = SSHCredentials(
                username=credentials.get('username', 'root'),
                password=credentials.get('password'),
                private_key_path=credentials.get('private_key_path'),
                private_key_passphrase=credentials.get('private_key_passphrase')
            )
        else:
            creds = credentials
        
        return AsyncSSHClient(
            host=host,
            credentials=creds,
            port=port,
            timeout=timeout,
            connection_pool_size=self.max_connections_per_host
        )
    
    async def get_client(
        self,
        host: str,
        credentials: Any,
        port: int = 22
    ) -> AsyncSSHClient:
        """Get a client from pool or create new one"""
        pool_key = f"{host}:{port}"
        
        # Initialize pool and lock if needed
        if pool_key not in self._pools:
            self._pools[pool_key] = []
            self._pool_locks[pool_key] = asyncio.Lock()
        
        async with self._pool_locks[pool_key]:
            # Try to reuse existing connection
            pool = self._pools[pool_key]
            for client in pool:
                if client._connected:
                    return client
            
            # Create new client if pool not full
            if len(pool) < self.max_connections_per_host:
                client = self.create_client(host, credentials, port)
                pool.append(client)
                return client
            
            # Pool full, return first client (will reconnect if needed)
            return pool[0]
    
    async def close_all(self) -> None:
        """Close all connections in all pools"""
        for pool in self._pools.values():
            for client in pool:
                await client.disconnect()
        self._pools.clear()
        self._pool_locks.clear()


# Global factory instance
_ssh_factory = SSHClientFactory()


def get_ssh_factory() -> SSHClientFactory:
    """Get the global SSH factory instance"""
    return _ssh_factory


def ssh_client_factory(host: str, credentials: Any) -> AsyncSSHClient:
    """
    Convenience function to create SSH clients
    Compatible with llm_client_integrator.py expectations
    """
    return _ssh_factory.create_client(host, credentials)
