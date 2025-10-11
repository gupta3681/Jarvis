#!/usr/bin/env python3
"""Test if Mem0 memories persist across restarts."""

from mem0 import Memory
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize memory (same as in tools.py)
memory = Memory()

# Test search
print("Searching for cafe memories...")
results = memory.search("cafe", user_id="default_user")

print(f"\n📊 Results type: {type(results)}")
print(f"📊 Raw results: {results}\n")

# Extract actual results
if isinstance(results, dict) and 'results' in results:
    results_list = results['results']
    print(f"✅ Found {len(results_list)} memories:\n")
    
    for idx, result in enumerate(results_list, 1):
        if isinstance(result, dict):
            mem = result.get('memory', 'N/A')
            score = result.get('score', 'N/A')
            print(f"{idx}. {mem}")
            print(f"   Score: {score}\n")
else:
    print("❌ No results found or unexpected format")

print("\n" + "="*50)
print("If you see memories above, persistence is working! ✅")
print("="*50)
