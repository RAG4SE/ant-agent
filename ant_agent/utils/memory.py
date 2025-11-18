from typing import Any, Optional, Tuple, List, Dict
from langgraph.store.memory import InMemoryStore
from langgraph.store.base import Item


class MemoryManager:
    """
    A memory manager class that uses LangGraph's InMemoryStore to temporarily store
    important information generated during agent execution without using embeddings.
    """

    def __init__(self):
        """Initialize the memory manager with an InMemoryStore."""
        self._store = InMemoryStore()
        self._default_namespace = ("agent", "memory")

    def store(self, key: str, value: Any, namespace: Optional[Tuple[str, ...]] = None) -> None:
        """
        Store a value in memory using LangGraph's InMemoryStore.

        Args:
            key: The key to store the value under
            value: The value to store (will be stored as-is, no embedding)
            namespace: Optional namespace tuple. If not provided, uses default namespace
        """
        ns = namespace or self._default_namespace
        self._store.put(ns, key, value)

    def retrieve(self, key: str, namespace: Optional[Tuple[str, ...]] = None, default: Any = None) -> Any:
        """
        Retrieve a value from memory.

        Args:
            key: The key to retrieve the value for
            namespace: Optional namespace tuple. If not provided, uses default namespace
            default: Default value to return if key is not found

        Returns:
            The stored value or default if not found
        """
        ns = namespace or self._default_namespace
        try:
            # get_all for all items in the namespace
            items = self._store.search(ns, limit=10000)
            # Find the item with matching key (newest first)
            for item in reversed(items):
                if item.key == key:
                    return item.value
            return default
        except Exception:
            return default

    def delete(self, key: str, namespace: Optional[Tuple[str, ...]] = None) -> bool:
        """
        Delete a value from memory.
        Note: InMemoryStore doesn't support direct deletion, so we store None as tombstone.

        Args:
            key: The key to delete
            namespace: Optional namespace tuple. If not provided, uses default namespace

        Returns:
            True if the key existed (marked as deleted), False otherwise
        """
        ns = namespace or self._default_namespace
        # Check if key exists first
        if self.has_key(key, ns):
            # Store None as a tombstone to mark deletion
            self._store.put(ns, key, None)
            return True
        return False

    def get_all(self, namespace: Optional[Tuple[str, ...]] = None, allow_date: bool = False) -> List[Dict[str, Any]]:
        """
        get all items from a namespace.

        Args:
            namespace: Optional namespace tuple. If not provided, uses default namespace

        Returns:
            List of dictionaries containing key-value pairs
        """
        ns = namespace or self._default_namespace
        try:
            items = self._store.search(ns, limit=10000)
            # Filter out None values (deleted items) and convert to dict
            result = []
            for item in items:
                if item.value is not None:  # Skip deleted items
                    if allow_date:
                        result.append({
                            'key': item.key,
                            'value': item.value,
                            'created_at': getattr(item, 'created_at', None),
                            'updated_at': getattr(item, 'updated_at', None)
                        })
                    else:
                        result.append({
                            'key': item.key,
                            'value': item.value,
                        })
            return result
        except Exception:
            return []

    def clear_namespace(self, namespace: Optional[Tuple[str, ...]] = None) -> None:
        """
        Clear all items from a specific namespace.
        Note: This creates a new namespace to effectively clear the old one.

        Args:
            namespace: Optional namespace tuple. If not provided, uses default namespace
        """
        ns = namespace or self._default_namespace
        # Create a new store instance to clear the namespace
        # This is a workaround since InMemoryStore doesn't have a clear method
        temp_items = self.get_all(ns)
        for item in temp_items:
            self.delete(item['key'], ns)

    def list_keys(self, namespace: Optional[Tuple[str, ...]] = None) -> List[str]:
        """
        List all keys in a namespace.

        Args:
            namespace: Optional namespace tuple. If not provided, uses default namespace

        Returns:
            List of all keys in the namespace
        """
        ns = namespace or self._default_namespace
        items = self.get_all(ns)
        return [item['key'] for item in items]

    def has_key(self, key: str, namespace: Optional[Tuple[str, ...]] = None) -> bool:
        """
        Check if a key exists in memory.

        Args:
            key: The key to check
            namespace: Optional namespace tuple. If not provided, uses default namespace

        Returns:
            True if the key exists and is not deleted, False otherwise
        """
        ns = namespace or self._default_namespace
        try:
            items = self._store.search(ns, limit=10000)
            for item in reversed(items):
                if item.key == key:
                    return item.value is not None  # Return False if deleted (None)
            return False
        except Exception:
            return False

    def get_stats(self, namespace: Optional[Tuple[str, ...]] = None) -> Dict[str, int]:
        """
        Get memory usage statistics for a namespace.

        Args:
            namespace: Optional namespace tuple. If not provided, uses default namespace

        Returns:
            Dictionary with memory statistics
        """
        ns = namespace or self._default_namespace
        items = self.get_all(ns)
        return {
            'total_items': len(items),
            'keys': [item['key'] for item in items]
        }

    def update(self, key: str, value: Any, namespace: Optional[Tuple[str, ...]] = None) -> bool:
        """
        Update an existing value in memory.

        Args:
            key: The key to update
            value: The new value
            namespace: Optional namespace tuple. If not provided, uses default namespace

        Returns:
            True if the key was found and updated, False otherwise
        """
        ns = namespace or self._default_namespace
        if self.has_key(key, ns):
            self._store.put(ns, key, value)
            return True
        return False

    def get_namespaces(self) -> List[Tuple[str, ...]]:
        """
        Get all namespaces currently in use.
        Note: This method attempts to discover namespaces by examining the store's internal structure.

        Returns:
            List of namespace tuples
        """
        # InMemoryStore doesn't expose namespaces directly, so we return the default
        # In a real implementation, you might track namespaces separately
        return [self._default_namespace]

shared_memory_manager = MemoryManager()