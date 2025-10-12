"""
Setup script for Google Calendar integration.

This script helps you set up Google Calendar API credentials.
"""

import os
import webbrowser

CREDENTIALS_PATH = os.path.expanduser('~/.jarvis/calendar_credentials.json')


def main():
    print("=" * 60)
    print("🗓️  Google Calendar Setup for Jarvis")
    print("=" * 60)
    print()
    
    # Check if credentials already exist
    if os.path.exists(CREDENTIALS_PATH):
        print(f"✅ Credentials already exist at: {CREDENTIALS_PATH}")
        print()
        response = input("Do you want to replace them? (y/n): ")
        if response.lower() != 'y':
            print("Setup cancelled.")
            return
    
    print("📋 Follow these steps to set up Google Calendar API:")
    print()
    print("1. Go to Google Cloud Console:")
    print("   https://console.cloud.google.com/")
    print()
    print("2. Create a new project (or select existing)")
    print()
    print("3. Enable Google Calendar API:")
    print("   https://console.cloud.google.com/apis/library/calendar-json.googleapis.com")
    print()
    print("4. Create OAuth 2.0 credentials:")
    print("   - Go to: APIs & Services > Credentials")
    print("   - Click: + CREATE CREDENTIALS > OAuth client ID")
    print("   - Application type: Desktop app")
    print("   - Name: Jarvis Calendar")
    print("   - Click: CREATE")
    print()
    print("5. Download the credentials:")
    print("   - Click the download icon (⬇️) next to your OAuth client")
    print("   - Save the JSON file")
    print()
    
    response = input("Press Enter to open Google Cloud Console... ")
    webbrowser.open("https://console.cloud.google.com/apis/credentials")
    
    print()
    print("=" * 60)
    print("📁 Save your credentials file to:")
    print(f"   {CREDENTIALS_PATH}")
    print("=" * 60)
    print()
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(CREDENTIALS_PATH), exist_ok=True)
    
    print("After downloading the credentials JSON file:")
    print(f"1. Rename it to: calendar_credentials.json")
    print(f"2. Move it to: ~/.jarvis/")
    print()
    print("Or run this command:")
    print(f"   mv ~/Downloads/client_secret_*.json {CREDENTIALS_PATH}")
    print()
    
    input("Press Enter when you've saved the credentials file... ")
    
    # Verify credentials exist
    if os.path.exists(CREDENTIALS_PATH):
        print()
        print("✅ Credentials file found!")
        print()
        print("🎉 Setup complete! You can now use Google Calendar tools.")
        print()
        print("The first time you use a calendar tool, you'll be prompted to")
        print("authorize Jarvis to access your Google Calendar.")
    else:
        print()
        print("❌ Credentials file not found.")
        print(f"   Please save it to: {CREDENTIALS_PATH}")
        print()
        print("Run this script again after saving the file.")


if __name__ == "__main__":
    main()
