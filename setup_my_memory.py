"""
Setup your personal core memory.
Run this once to configure Jarvis with your information.
"""
from memory.core_memory import get_core_memory

def setup_core_memory():
    """Interactive setup for your core memory."""
    print("🧠 Setting up your Core Memory for Jarvis")
    print("="*50)
    print("This information will be instantly available in every conversation.\n")
    
    core_mem = get_core_memory("default_user")
    
    # Identity
    print("📋 IDENTITY")
    core_mem.update("identity", "name", "Aryan Gupta")
    core_mem.update("identity", "email", "gupta368@bu.edu")
    core_mem.update("identity", "phone", "(617) 901-9378")
    core_mem.update("identity", "location", "Boston, MA")
    print("✓ Name: Aryan Gupta")
    print("✓ Email: gupta368@bu.edu")
    print("✓ Phone: (617) 901-9378")
    print("✓ Location: Boston, MA")
    
    # Education
    print("\n🎓 EDUCATION")
    core_mem.update("identity", "education", "B.S. Computer Engineering, Boston University (May 2024)")
    core_mem.update("identity", "university", "Boston University")
    core_mem.update("identity", "degree", "B.S. in Computer Engineering")
    core_mem.update("identity", "concentrations", "Machine Learning and Technology Innovation")
    core_mem.update("identity", "graduation", "May 2024")
    print("✓ Boston University - B.S. Computer Engineering (May 2024)")
    print("✓ Dual Concentration: Machine Learning and Technology Innovation")
    
    # Work
    print("\n💼 WORK")
    core_mem.update("work", "company", "Perficient")
    core_mem.update("work", "role", "Software Engineer")
    core_mem.update("work", "department", "Data and Analytics BU")
    core_mem.update("work", "location", "Boston, MA")
    core_mem.update("work", "start_date", "July 2024")
    core_mem.update("work", "focus", "AI-powered workflows, LangGraph-based Agentic AI, RAG pipelines")
    print("✓ Company: Perficient")
    print("✓ Role: Software Engineer (Data and Analytics BU)")
    print("✓ Started: July 2024")
    print("✓ Focus: AI/ML Engineering, Agentic AI Systems")
    
    # Technical Background
    print("\n💻 TECHNICAL BACKGROUND")
    core_mem.update("preferences", "primary_languages", "Python, JavaScript, Java")
    core_mem.update("preferences", "ai_frameworks", "LangChain, LangGraph, Haystack")
    core_mem.update("preferences", "cloud_platforms", "AWS, Azure, GCP")
    core_mem.update("work", "certifications", "AWS Cloud Practitioner, Azure AI Fundamentals, Azure AI Engineer Associate, Databricks Data Engineer")
    print("✓ Languages: Python, JavaScript, Java")
    print("✓ AI Frameworks: LangChain, LangGraph, Haystack")
    print("✓ Cloud: AWS, Azure, GCP")
    print("✓ Certifications: AWS, Azure AI, Databricks")
    
    # Preferences
    print("\n⚙️ PREFERENCES")
    workout_time = input("Preferred workout time (e.g., Morning 6-7 AM): ").strip()
    if workout_time:
        core_mem.update("preferences", "workout_time", workout_time)
    
    diet_type = input("Diet type/preferences (e.g., High protein, non vegetarian): ").strip()
    if diet_type:
        core_mem.update("preferences", "diet_type", diet_type)
    
    # Health
    print("\n🏥 HEALTH")
    allergies = input("Allergies (or 'None'): ").strip()
    if allergies:
        core_mem.update("health", "allergies", allergies)
    
    fitness_goal = input("Fitness goal (e.g., Build muscle, lose weight): ").strip()
    if fitness_goal:
        core_mem.update("health", "fitness_goal", fitness_goal)
    
    # Display summary
    print("\n" + "="*50)
    print("✅ Core Memory Setup Complete!")
    print("="*50)
    print(core_mem.to_context_string())
    print("\n💡 Jarvis will now have instant access to this information in every conversation!")


if __name__ == "__main__":
    setup_core_memory()
