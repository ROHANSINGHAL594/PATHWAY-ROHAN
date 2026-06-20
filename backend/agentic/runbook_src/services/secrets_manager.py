"""
Secrets Management Layer (Local SQLite Only)
This version only supports local secret storage in a SQLite database.
Compatible interface with legacy version for drop-in replacement.
"""

import asyncio
import logging
import time
from typing import Any, Dict, Optional, List
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
import datetime

logger = logging.getLogger(__name__)

Base = declarative_base()

class Secret(Base):
    __tablename__ = "secrets"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    value = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

class SecretValue:
    def __init__(self, value: str, path: str, expires_at: Optional[float] = None, metadata: Optional[Dict[str, Any]] = None):
        self.value = value
        self.source = 'local'
        self.path = path
        self.expires_at = expires_at
        self.metadata = metadata or {}
    
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

class LocalSQLiteSecretsProvider:
    def __init__(self, db_url: str = "sqlite:///secrets.db"):
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        logger.info(f"Using LocalSQLiteSecretsProvider with db {db_url}")

    async def get_secret(self, path: str, key: Optional[str] = None) -> str:
        session = self.Session()
        try:
            secret = session.query(Secret).filter_by(name=path).first()
            if not secret:
                raise ValueError(f"Secret '{path}' not found in local SQLite DB")
            if secret.expires_at and secret.expires_at < datetime.datetime.utcnow():
                raise ValueError(f"Secret '{path}' is expired")
            return secret.value
        finally:
            session.close()

    async def list_secrets(self, path: str) -> List[str]:
        session = self.Session()
        try:
            secrets = session.query(Secret).filter(Secret.name.contains(path)).all()
            return [s.name for s in secrets]
        finally:
            session.close()

    def set_secret(self, name: str, value: str, expires_at: Optional[datetime.datetime] = None) -> None:
        session = self.Session()
        try:
            secret = session.query(Secret).filter_by(name=name).first()
            if secret:
                secret.value = value
                secret.expires_at = expires_at
            else:
                secret = Secret(name=name, value=value, expires_at=expires_at)
                session.add(secret)
            session.commit()
        finally:
            session.close()

class SecretsManager:
    """
    Unified secrets management interface (local SQLite only)
    Supports: local:// URLs or just secret names
    """
    def __init__(self, db_url: str = "sqlite:///secrets.db", default_ttl: int = 3600, enable_cache: bool = True):
        self.provider = LocalSQLiteSecretsProvider(db_url=db_url)
        self.cache: Dict[str, SecretValue] = {}
        self.default_ttl = default_ttl
        self.enable_cache = enable_cache
        logger.info("SecretsManager (local SQLite) initialized")

    def _parse_secret_url(self, url: str) -> str:
        # Accepts local://secretname or just secretname
        if url.startswith("local://"):
            return url[len("local://"):]
        return url

    async def get_secret(self, url: str, ttl: Optional[int] = None) -> str:
        path = self._parse_secret_url(url)
        # Check cache
        if self.enable_cache and url in self.cache:
            cached = self.cache[url]
            if not cached.is_expired():
                logger.debug(f"Using cached secret for {url}")
                return cached.value
            else:
                del self.cache[url]
        value = await self.provider.get_secret(path)
        if self.enable_cache:
            cache_ttl = ttl or self.default_ttl
            expires_at = time.time() + cache_ttl if cache_ttl > 0 else None
            self.cache[url] = SecretValue(value=value, path=path, expires_at=expires_at)
        return value

    async def get_secrets_batch(self, urls: List[str]) -> Dict[str, str]:
        tasks = [self.get_secret(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        output = {}
        for url, result in zip(urls, results):
            if isinstance(result, Exception):
                logger.error(f"Failed to get secret {url}: {result}")
                output[url] = None
            else:
                output[url] = result
        return output

    def clear_cache(self) -> None:
        self.cache.clear()
        logger.info("Secret cache cleared")

    def clear_expired(self) -> int:
        expired_keys = [url for url, secret in self.cache.items() if secret.is_expired()]
        for key in expired_keys:
            del self.cache[key]
        logger.info(f"Cleared {len(expired_keys)} expired secrets from cache")
        return len(expired_keys)

    async def resolve_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        resolved = {}
        for key, value in parameters.items():
            if isinstance(value, str):
                try:
                    resolved[key] = await self.get_secret(value)
                    continue
                except Exception:
                    pass
            if isinstance(value, dict):
                resolved[key] = await self.resolve_parameters(value)
            elif isinstance(value, list):
                resolved[key] = [
                    await self.resolve_parameters({'item': item}) if isinstance(item, dict)
                    else await self.get_secret(item) if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                resolved[key] = value
        return resolved

    def set_secret(self, name: str, value: str, expires_at: Optional[datetime.datetime] = None) -> None:
        self.provider.set_secret(name, value, expires_at)

# Global instance
_secrets_manager: Optional[SecretsManager] = None

def get_secrets_manager() -> SecretsManager:
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager()
    return _secrets_manager

def configure_secrets_manager(db_url: str = "sqlite:///secrets.db", **kwargs) -> SecretsManager:
    global _secrets_manager
    _secrets_manager = SecretsManager(db_url=db_url, **kwargs)
    return _secrets_manager
