#!/usr/bin/env python3
"""Test adding and immediately searching a memory."""

from mem0 import Memory
from dotenv import load_dotenv

load_dotenv()

memory = Memory()

print("=" * 50)
print("TEST: Add and Search Memory")
print("=" * 50)

# Add a memory
print("\n1. Adding memory...")
result = memory.add("I love sushi", user_id="test_user")
print(f"   Result: {result}")

# Immediately search
print("\n2. Searching for 'food'...")
results = memory.search("food", user_id="test_user")
print(f"   Results: {results}")

# Search with same user_id
print("\n3. Searching for 'sushi'...")
results2 = memory.search("sushi", user_id="test_user")
print(f"   Results: {results2}")

# Get all memories for user
print("\n4. Getting all memories for test_user...")
all_memories = memory.get_all(user_id="test_user")
print(f"   All memories: {all_memories}")

print("\n" + "=" * 50)
print("If you see 'I love sushi' above, it's working!")
print("=" * 50)
