# find_models.py
# Run this to see ALL Gemini models available for your API key.
# Command: python find_models.py

import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY", "").strip()

genai.configure(api_key=api_key)

print("=" * 50)
print("AVAILABLE GEMINI MODELS FOR YOUR KEY")
print("=" * 50)

models_that_support_generate = []

for m in genai.list_models():
    if "generateContent" in m.supported_generation_methods:
        models_that_support_generate.append(m.name)
        print(f"✅ {m.name}")

print("=" * 50)
print(f"\nTotal usable models: {len(models_that_support_generate)}")

# Test the first available model
if models_that_support_generate:
    best = models_that_support_generate[0]
    print(f"\nTesting: {best} ...")
    try:
        model = genai.GenerativeModel(best)
        response = model.generate_content("Reply with exactly: KEY_WORKS")
        print(f"✅ SUCCESS with {best}")
        print(f"   Reply: {response.text.strip()}")
        print(f"\n👉 Use this in your config.py:")
        print(f'   LLM_MODEL: str = "{best.replace("models/", "")}"')
    except Exception as e:
        print(f"❌ {e}")