# test_key.py
# Run this FIRST to confirm your API key works.
# Command: python test_key.py

import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load .env file
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY", "").strip()

print("=" * 50)
print("GEMINI API KEY TEST")
print("=" * 50)

# Check 1 — Is key present?
if not api_key:
    print("❌ FAIL: GEMINI_API_KEY is empty or missing.")
    print("   Fix: Open backend/.env and add:")
    print("   GEMINI_API_KEY=your_key_here")
    exit(1)

print(f"✅ Key found: {api_key[:6]}...{api_key[-4:]}")
print(f"   Length   : {len(api_key)} characters")

# Check 2 — Does it start correctly?
if not (api_key.startswith("AQ") or api_key.startswith("AIza")):
    print("⚠️  WARNING: Key doesn't start with AQ or AIza.")
    print("   Double-check you copied the full key.")

# Check 3 — Call Gemini
print("\nTesting connection to Gemini 1.5 Flash...")
try:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content("Reply with exactly: KEY_WORKS")
    print(f"✅ SUCCESS! Gemini replied: {response.text.strip()}")
    print("\nYour API key is valid. You can now run the app!")

except Exception as e:
    print(f"❌ FAIL: {e}")
    print("\nFix:")
    print("1. Go to https://aistudio.google.com/app/apikey")
    print("2. Delete old keys, create a NEW one")
    print("3. Paste it in backend/.env as:")
    print("   GEMINI_API_KEY=your_new_key_here")