"""
Error-Action Registry - MongoDB-backed mapping between errors and remediation actions
Maintains a local errors.json file synchronized with MongoDB
"""

import asyncio
import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from pymongo import UpdateOne

try:
    from motor.motor_asyncio import AsyncIOMotorClient
    from pymongo.errors import ConnectionFailure
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False


class ErrorActionRegistry:
    """
    Registry that maps errors to ordered remediation actions
    Stores in MongoDB and maintains synchronized errors.json file
    """
    
    def __init__(self, mongodb_uri: str, database_name: str = None, local_file_path: str = "errors.json"):
        """
        Initialize the error-action registry
        
        Args:
            mongodb_uri: MongoDB connection string (e.g., 'mongodb://localhost:27017')
            database_name: Database name to use (defaults to MONGO_DB env var or 'easyworkflow')
            local_file_path: Path to local errors.json file
        """
        if database_name is None:
            database_name = os.getenv("MONGO_DB", "easyworkflow")
        if not MONGODB_AVAILABLE:
            raise ImportError("Install MongoDB support: pip install motor pymongo")
        
        self.mongodb_uri = mongodb_uri
        self.database_name = database_name
        self.local_file_path = Path(local_file_path)
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None
        self.collection = None
    
    async def connect(self):
        """Establish MongoDB connection"""
        try:
            self.client = AsyncIOMotorClient(self.mongodb_uri)
            self.db = self.client[self.database_name]
            self.collection = self.db.error_actions
            
            # Test connection
            await self.client.admin.command('ping')
            
            # Create indexes for efficient queries
            await self.collection.create_index("error", unique=True)
            
            print(f"Connected to MongoDB: {self.database_name}.error_actions")
        except ConnectionFailure as e:
            raise ConnectionError(f"Failed to connect to MongoDB: {e}")
    
    async def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
    
    async def add_error_mapping(
        self,
        error: str,
        actions: List[str],
        description: str
    ) -> Dict[str, Any]:
        """
        Add or update error-to-actions mapping
        
        Args:
            error: Error identifier/pattern
            actions: Ordered list of action IDs to execute
            description: Human-readable description of the error
            
        Returns:
            Created/updated document
        """
        if self.collection is None:
            raise RuntimeError("Not connected to MongoDB. Call connect() first.")
        
        document = {
            "error": error,
            "actions": actions,
            "description": description,
            "updated_at": datetime.now()
        }
        
        # Upsert (insert or update)
        result = await self.collection.update_one(
            {"error": error},
            {"$set": document},
            upsert=True
        )
        
        print(f"{'Updated' if result.modified_count else 'Created'} mapping for error: {error}")
        
        # Trigger local file sync
        await self._sync_to_local_file()
        
        return document
    
    async def get_error_mapping(self, error: str) -> Optional[Dict[str, Any]]:
        """
        Get actions for a specific error
        
        Args:
            error: Error identifier
            
        Returns:
            Document with error, actions, and description, or None if not found
        """
        if self.collection is None:
            raise RuntimeError("Not connected to MongoDB. Call connect() first.")
        
        document = await self.collection.find_one(
            {"error": error},
            {"_id": 0, "error": 1, "actions": 1, "description": 1}
        )
        
        return document
    
    async def list_all_mappings(self) -> List[Dict[str, Any]]:
        """
        List all error-action mappings
        
        Returns:
            List of all error mappings
        """
        if self.collection is None:
            raise RuntimeError("Not connected to MongoDB. Call connect() first.")
        
        cursor = self.collection.find(
            {},
            {"_id": 0, "error": 1, "actions": 1, "description": 1}
        ).sort("error", 1)
        
        mappings = await cursor.to_list(length=None)
        return mappings
    
    async def delete_error_mapping(self, error: str) -> bool:
        """
        Delete an error mapping
        
        Args:
            error: Error identifier to delete
            
        Returns:
            True if deleted, False if not found
        """
        if self.collection is None:
            raise RuntimeError("Not connected to MongoDB. Call connect() first.")
        
        result = await self.collection.delete_one({"error": error})
        
        if result.deleted_count > 0:
            print(f" Deleted mapping for error: {error}")
            # Trigger local file sync
            await self._sync_to_local_file()
            return True
        
        return False
    
    async def bulk_add_mappings(self, mappings: List[Dict[str, Any]]) -> int:
        """
        Bulk add multiple error mappings
        
        Args:
            mappings: List of dicts with 'error', 'actions', 'description'
            
        Returns:
            Number of mappings added/updated
        """
        if self.collection is None:
            raise RuntimeError("Not connected to MongoDB. Call connect() first.")
        
        if not mappings:
            return 0
        
        operations = []
        for mapping in mappings:
            if not all(key in mapping for key in ['error', 'actions', 'description']):
                print(f"Skipping invalid mapping: {mapping}")
                continue
            
            operations.append(UpdateOne(
                {"error": mapping['error']},
                {"$set": {
                    "error": mapping['error'],
                    "actions": mapping['actions'],
                    "description": mapping['description'],
                    "updated_at": datetime.utcnow()
                }},
                upsert=True
            ))
        
        if operations:
            result = await self.collection.bulk_write(operations)
            count = result.upserted_count + result.modified_count
            print(f" Bulk operation: {count} mappings added/updated")
            
            # Trigger local file sync
            await self._sync_to_local_file()
            
            return count
        
        return 0
    
    async def _sync_to_local_file(self):
        """
        Synchronize MongoDB data to local errors.json file
        This is called automatically after any write operation
        """
        try:
            # Fetch all mappings from MongoDB
            mappings = await self.list_all_mappings()
            
            # Write to local JSON file
            with open(self.local_file_path, 'w', encoding='utf-8') as f:
                json.dump(mappings, f, indent=2, ensure_ascii=False)
            
            print(f" Synced {len(mappings)} mappings to {self.local_file_path}")
        
        except Exception as e:
            print(f"Failed to sync to local file: {e}")
    
    async def force_sync(self):
        """
        Force synchronization from MongoDB to local file
        Use this to manually refresh the local file
        """
        await self._sync_to_local_file()
    
    def load_from_local_file(self) -> List[Dict[str, Any]]:
        """
        Load error mappings from local errors.json file
        Useful for offline access or as fallback
        
        Returns:
            List of error mappings from local file
        """
        try:
            if not self.local_file_path.exists():
                return []
            
            with open(self.local_file_path, 'r', encoding='utf-8') as f:
                mappings = json.load(f)
            
            return mappings
        
        except Exception as e:
            print(f"Failed to load from local file: {e}")
            return []


# =============================================================================
# Example Usage
# =============================================================================

async def example_usage():
    """Demonstrate error-action registry usage"""
    
    # Initialize registry (database_name will use MONGO_DB env var)
    registry = ErrorActionRegistry(
        mongodb_uri=os.getenv("MONGO_URI", "mongodb://localhost:27017"),
        database_name=None,  # Uses MONGO_DB env var or 'easyworkflow'
        local_file_path="errors.json"
    )
    
    await registry.connect()
    
    try:
        # Add single error mapping
        await registry.add_error_mapping(
            error="DatabaseConnectionTimeout",
            actions=["check-db-health", "restart-db-connection-pool", "restart-db-service"],
            description="Database connection pool exhausted or database is unresponsive"
        )
        
        await registry.add_error_mapping(
            error="HighMemoryUsage",
            actions=["clear-cache", "restart-service", "scale-up-instances"],
            description="Service memory usage exceeded 90% threshold"
        )
        
        await registry.add_error_mapping(
            error="APIRateLimitExceeded",
            actions=["enable-circuit-breaker", "scale-up-instances"],
            description="External API rate limit exceeded, requests being throttled"
        )
        
        # Bulk add multiple mappings
        bulk_mappings = [
            {
                "error": "DiskSpaceFull",
                "actions": ["clear-temp-files", "archive-old-logs", "expand-disk-volume"],
                "description": "Disk usage at 95%, no space left on device"
            },
            {
                "error": "SSLCertificateExpired",
                "actions": ["renew-ssl-certificate", "reload-nginx-config"],
                "description": "SSL certificate has expired or will expire within 7 days"
            }
        ]
        
        await registry.bulk_add_mappings(bulk_mappings)
        
        # Retrieve specific error mapping
        print("\nRetrieving mapping for 'DatabaseConnectionTimeout':")
        mapping = await registry.get_error_mapping("DatabaseConnectionTimeout")
        print(f"  Error: {mapping['error']}")
        print(f"  Actions: {mapping['actions']}")
        print(f"  Description: {mapping['description']}")
        
        # List all mappings
        print("\nAll error mappings:")
        all_mappings = await registry.list_all_mappings()
        for m in all_mappings:
            print(f"  • {m['error']}: {len(m['actions'])} actions")
        
        # Force sync to local file
        await registry.force_sync()
        
        # Load from local file (offline access)
        print("\nLoading from local errors.json:")
        local_mappings = registry.load_from_local_file()
        print(f"  Loaded {len(local_mappings)} mappings from local file")
        
    finally:
        await registry.close()


if __name__ == "__main__":
    # Run example
    asyncio.run(example_usage())
