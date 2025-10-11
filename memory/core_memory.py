"""
Core Memory System - Always-available identity and context.
This is like human "instant recall" - no retrieval needed.
"""
from typing import Dict, Any, Optional
import json
from pathlib import Path


class CoreMemory:
    """
    Core memory that's always loaded and instantly accessible.
    Stores fundamental facts about the user that don't need semantic search.
    """
    
    def __init__(self, user_id: str = "default_user"):
        self.user_id = user_id
        self.memory_file = Path(f"~/.jarvis/core_memory_{user_id}.json").expanduser()
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Core memory structure
        self.core: Dict[str, Any] = {
            "identity": {},      # Name, age, location, etc.
            "work": {},          # Job, company, schedule, etc.
            "preferences": {},   # Key preferences (diet, workout style, etc.)
            "health": {},        # Allergies, conditions, goals
            "relationships": {}, # Important people
            "context": {}        # Current context (timezone, etc.)
        }
        
        self.load()
    
    def load(self):
        """Load core memory from disk."""
        if self.memory_file.exists():
            with open(self.memory_file, 'r') as f:
                self.core = json.load(f)
    
    def save(self):
        """Save core memory to disk."""
        with open(self.memory_file, 'w') as f:
            json.dump(self.core, f, indent=2)
    
    def update(self, category: str, key: str, value: Any):
        """Update a specific core memory field."""
        if category not in self.core:
            self.core[category] = {}
        self.core[category][key] = value
        self.save()
    
    def get(self, category: str, key: Optional[str] = None) -> Any:
        """Get core memory value(s)."""
        if key:
            return self.core.get(category, {}).get(key)
        return self.core.get(category, {})
    
    def get_all(self) -> Dict[str, Any]:
        """Get all core memory."""
        return self.core
    
    def delete(self, category: str, key: Optional[str] = None):
        """Delete core memory field or entire category."""
        if key:
            if category in self.core and key in self.core[category]:
                del self.core[category][key]
        else:
            if category in self.core:
                self.core[category] = {}
        self.save()
    
    def to_context_string(self) -> str:
        """
        Convert core memory to a context string for the LLM.
        This gets injected into every conversation.
        """
        lines = ["=== CORE MEMORY (Always Available) ==="]
        
        for category, data in self.core.items():
            if data:  # Only include non-empty categories
                lines.append(f"\n{category.upper()}:")
                for key, value in data.items():
                    lines.append(f"  - {key}: {value}")
        
        return "\n".join(lines) if len(lines) > 1 else ""


# Global instance
_core_memory_instances: Dict[str, CoreMemory] = {}


def get_core_memory(user_id: str = "default_user") -> CoreMemory:
    """Get or create core memory instance for a user."""
    if user_id not in _core_memory_instances:
        _core_memory_instances[user_id] = CoreMemory(user_id)
    return _core_memory_instances[user_id]
