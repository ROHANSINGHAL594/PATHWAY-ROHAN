"""
Simplified Runbook Registry - PostgreSQL-backed action store
Clean, simple, production-ready implementation using SQLAlchemy
"""

from datetime import datetime
from typing import Dict, List, Any, Optional,Union
import json

from pydantic import BaseModel, Field, field_validator

try:
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
    from sqlalchemy import String, Boolean, Text, DateTime, select, func, or_, JSON
    from sqlalchemy.dialects.postgresql import JSONB
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False


class RemediationAction(BaseModel):
    """Essential action schema - Pydantic model for LLM structured outputs"""
    
    # Core identity
    action_id: str = Field(description="Unique action identifier")
    method: str = Field(description="Action method: rpc, script, api, k8s, command")
    service: str = Field(description="Service this action targets")
    definition: str = Field(description="Human-readable description of what this action does")
    
    # Safety
    requires_approval: bool = Field(default=False, description="Whether human approval is required")
    risk_level: str = Field(default="medium", description="Risk level: low, medium, or high")
    validated: bool = Field(default=False, description="Whether this action has been validated")
    
    # Execution details
    execution: Dict[str, Any] = Field(default_factory=dict, description="Execution configuration (endpoint, script_path, command, etc.)")
    parameters: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Action parameters with validation rules")
    secrets: Any = Field(default_factory=list, description="List of secret parameter names or dict with secret_references for execution")
    action_metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    @field_validator('risk_level')
    @classmethod
    def validate_risk_level(cls, v: str) -> str:
        valid_levels = ['low', 'medium', 'high']
        if v not in valid_levels:
            return 'medium'
        return v
    
    @field_validator('method')
    @classmethod
    def validate_method(cls, v: str) -> str:
        valid_methods = ['rpc', 'script', 'api', 'k8s', 'command']
        if v not in valid_methods:
            raise ValueError(f"Invalid method '{v}'. Must be one of: {valid_methods}")
        return v
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict"""
        return self.model_dump()


# =============================================================================
# SQLAlchemy Model
# =============================================================================

if SQLALCHEMY_AVAILABLE:
    class Base(DeclarativeBase):
        pass
    
    class ActionModel(Base):
        """Database table for actions - works with both PostgreSQL and SQLite"""
        __tablename__ = 'remediation_actions'
        
        action_id: Mapped[str] = mapped_column(String(255), primary_key=True)
        method: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
        service: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
        definition: Mapped[str] = mapped_column(Text, nullable=False)
        requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
        risk_level: Mapped[str] = mapped_column(String(20), default='medium', index=True)
        validated: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
        execution: Mapped[dict] = mapped_column(JSON, nullable=False)
        parameters: Mapped[dict] = mapped_column(JSON, nullable=False)
        secrets: Mapped[Dict] = mapped_column(JSON, nullable=False)  # Can be list (legacy) or dict with secret_references
        action_metadata: Mapped[dict] = mapped_column(JSON, nullable=False)
        created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
        updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class RunbookRegistry:
    """Database registry supporting both PostgreSQL and SQLite"""
    
    def __init__(self, database_url: str):
        """
        Args:
            database_url: 
                PostgreSQL: 'postgresql+asyncpg://user:pass@localhost/db'
                SQLite: 'sqlite+aiosqlite:///./runbook.db'
        """
        if not SQLALCHEMY_AVAILABLE:
            raise ImportError("Install: pip install sqlalchemy[asyncio] asyncpg")
        
        self.engine = create_async_engine(database_url, echo=False, pool_pre_ping=True)
        self.session_maker = async_sessionmaker(self.engine, expire_on_commit=False)
    
    async def initialize(self):
        """Create tables - call once at startup"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def save(self, action: RemediationAction) -> bool:
        """Save or update an action"""
        async with self.session_maker() as session:
            stmt = select(ActionModel).where(ActionModel.action_id == action.action_id)
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if existing:
                existing.method = action.method
                existing.service = action.service
                existing.definition = action.definition
                existing.requires_approval = action.requires_approval
                existing.risk_level = action.risk_level
                existing.validated = action.validated
                existing.execution = action.execution
                existing.parameters = action.parameters
                existing.secrets = action.secrets
                existing.action_metadata = action.action_metadata
                existing.updated_at = datetime.now()
            else:
                model = ActionModel(
                    action_id=action.action_id,
                    method=action.method,
                    service=action.service,
                    definition=action.definition,
                    requires_approval=action.requires_approval,
                    risk_level=action.risk_level,
                    validated=action.validated,
                    execution=action.execution,
                    parameters=action.parameters,
                    secrets=action.secrets,
                    action_metadata=action.action_metadata,
                )
                session.add(model)
            
            await session.commit()
            return True
    
    async def get(self, action_id: str) -> Optional[RemediationAction]:
        """Get action by ID"""
        async with self.session_maker() as session:
            stmt = select(ActionModel).where(ActionModel.action_id == action_id)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            
            if not model:
                return None
            
            return self._to_action(model)
    
    async def get_by_service(self, service: str, validated_only: bool = False) -> List[RemediationAction]:
        """Get all actions for a service"""
        async with self.session_maker() as session:
            stmt = select(ActionModel).where(ActionModel.service == service)
            if validated_only:
                stmt = stmt.where(ActionModel.validated == True)
            stmt = stmt.order_by(ActionModel.validated.desc(), ActionModel.action_id)
            
            result = await session.execute(stmt)
            models = result.scalars().all()
            
            return [self._to_action(m) for m in models]
    
    async def get_by_method(self, method: str) -> List[RemediationAction]:
        """Get actions by method type"""
        async with self.session_maker() as session:
            stmt = select(ActionModel).where(ActionModel.method == method)
            result = await session.execute(stmt)
            models = result.scalars().all()
            return [self._to_action(m) for m in models]
    
    async def get_validated(self) -> List[RemediationAction]:
        """Get all validated actions"""
        async with self.session_maker() as session:
            stmt = select(ActionModel).where(ActionModel.validated == True)
            result = await session.execute(stmt)
            models = result.scalars().all()
            return [self._to_action(m) for m in models]
    
    async def list_all(self) -> List[RemediationAction]:
        """Get all actions from the registry"""
        async with self.session_maker() as session:
            stmt = select(ActionModel).order_by(ActionModel.service, ActionModel.action_id)
            result = await session.execute(stmt)
            models = result.scalars().all()
            return [self._to_action(m) for m in models]
    
    async def search(self, term: str) -> List[RemediationAction]:
        """Search actions by ID or definition"""
        async with self.session_maker() as session:
            pattern = f"%{term}%"
            stmt = select(ActionModel).where(
                or_(ActionModel.action_id.ilike(pattern), ActionModel.definition.ilike(pattern))
            )
            result = await session.execute(stmt)
            models = result.scalars().all()
            return [self._to_action(m) for m in models]
    
    async def mark_validated(self, action_id: str, validated_by: str) -> bool:
        """Mark action as validated"""
        async with self.session_maker() as session:
            stmt = select(ActionModel).where(ActionModel.action_id == action_id)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            
            if not model:
                return False
            
            model.validated = True
            model.action_metadata = {
                **model.action_metadata,
                'validated_by': validated_by,
                'validated_at': datetime.now().isoformat()
            }
            await session.commit()
            return True
    
    async def stats(self) -> Dict[str, int]:
        """Get registry statistics"""
        async with self.session_maker() as session:
            total = await session.execute(select(func.count(ActionModel.action_id)))
            validated = await session.execute(
                select(func.count(ActionModel.action_id)).where(ActionModel.validated == True)
            )
            services = await session.execute(select(func.count(func.distinct(ActionModel.service))))
            
            return {
                'total': total.scalar(),
                'validated': validated.scalar(),
                'services': services.scalar()
            }
    
    async def bulk_save(self, actions: List[RemediationAction]) -> int:
        """Save multiple actions in one transaction"""
        async with self.session_maker() as session:
            for action in actions:
                stmt = select(ActionModel).where(ActionModel.action_id == action.action_id)
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()
                
                if existing:
                    existing.method = action.method
                    existing.service = action.service
                    existing.definition = action.definition
                    existing.requires_approval = action.requires_approval
                    existing.risk_level = action.risk_level
                    existing.validated = action.validated
                    existing.execution = action.execution
                    existing.parameters = action.parameters
                    existing.secrets = action.secrets
                    existing.action_metadata = action.action_metadata
                else:
                    session.add(ActionModel(
                        action_id=action.action_id,
                        method=action.method,
                        service=action.service,
                        definition=action.definition,
                        requires_approval=action.requires_approval,
                        risk_level=action.risk_level,
                        validated=action.validated,
                        execution=action.execution,
                        parameters=action.parameters,
                        secrets=action.secrets,
                        action_metadata=action.action_metadata,
                    ))
            
            await session.commit()
            return len(actions)
    
    async def delete(self, action_id: str) -> bool:
        """Delete an action"""
        async with self.session_maker() as session:
            stmt = select(ActionModel).where(ActionModel.action_id == action_id)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            
            if model:
                await session.delete(model)
                await session.commit()
                return True
            return False
    
    def _to_action(self, model: 'ActionModel') -> RemediationAction:
        """Convert DB model to action"""
        return RemediationAction(
            action_id=model.action_id,
            method=model.method,
            service=model.service,
            definition=model.definition,
            requires_approval=model.requires_approval,
            risk_level=model.risk_level,
            validated=model.validated,
            execution=model.execution,
            parameters=model.parameters,
            secrets=model.secrets,
            action_metadata=model.action_metadata,
        )

