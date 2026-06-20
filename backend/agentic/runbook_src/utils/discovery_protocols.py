"""
Protocol definitions for discovery agents

These protocols define interfaces for external systems that discovery agents
may interact with (SSH clients, documentation fetchers, etc.)
"""

from typing import Dict, List, Any, Protocol
import aiohttp


class ScriptHostClient(Protocol):
    """Interface for SSH/remote clients that can list and read scripts"""

    async def list_scripts(self, directory: str) -> List[str]:
        """List executable scripts in a directory"""
        ...

    async def read_file(self, path: str) -> str:
        """Read contents of a file"""
        ...


class DocumentationFetcherProtocol(Protocol):
    """Interface for fetching documentation from various sources"""

    async def fetch(self, source: Dict[str, Any]) -> List[str]:
        """
        Fetch documentation from a source
        
        Args:
            source: Dict with 'type' (raw/url/wiki/github) and relevant keys
            
        Returns:
            List of documentation strings
        """
        ...


class DefaultDocumentationFetcher:
    """Default implementation that fetches from URLs and raw content"""

    async def fetch(self, source: Dict[str, Any]) -> List[str]:
        """
        Fetch documentation from supported sources
        
        Supported types:
        - 'raw': Direct content in source['content']
        - 'url' or 'wiki': HTTP URL in source['url']
        - 'github': Placeholder - provide content directly
        """
        src_type = source.get('type', 'raw')
        
        if src_type == 'raw':
            return [source.get('content', '')]
        
        if src_type in ('wiki', 'url'):
            url = source.get('url')
            if not url:
                return []
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                    resp.raise_for_status()
                    return [await resp.text()]
        
        if src_type == 'github':
            # Placeholder: caller should provide raw content
            return [source.get('content', '')]
        
        return []
