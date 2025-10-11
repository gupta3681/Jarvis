"""
Example demonstrating the two-tier memory system.
"""
from memory.core_memory import get_core_memory

# Get core memory instance
core_mem = get_core_memory("demo_user")

# Set up core identity - instant access, no retrieval needed
print("Setting up core memory...")
core_mem.update("identity", "name", "Aryan")
core_mem.update("identity", "location", "San Francisco")

core_mem.update("work", "company", "Tech Startup")
core_mem.update("work", "role", "Software Engineer")
core_mem.update("work", "schedule", "Mon-Fri 9-5, Remote on Wed")

core_mem.update("preferences", "workout_time", "Morning, 6-7 AM")
core_mem.update("preferences", "diet_type", "High protein, low carb")

core_mem.update("health", "allergies", "None")
core_mem.update("health", "fitness_goal", "Build muscle, maintain 12% body fat")

# View all core memory
print("\n" + "="*50)
print(core_mem.to_context_string())
print("="*50)

print("\n✅ Core memory is now loaded!")
print("This will be injected into EVERY conversation automatically.")
print("No retrieval needed - instant access like human memory!")

# Example: Get specific category
print("\n📋 Work Info:")
print(core_mem.get("work"))
