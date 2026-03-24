#!/usr/bin/env python3
"""Test OpenRouter with debugging"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")

# Try different models
models = [
    "google/gemini-2.0-flash-thinking-exp:free",
    "qwen/qwen3-coder",
    "deepseek/deepseek-v3-1",
    "openai/gpt-3.5-turbo"
]

headers = {
    "Authorization": f"Bearer {OPENROUTER_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": "http://localhost",
    "X-Title": "RedCortex Test"
}

for model in models:
    print(f"\nTesting: {model}")
    print("-" * 50)
    
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": "Say 'Hello from OpenRouter' in 5 words or less."}
        ],
        "max_tokens": 50
    }
    
    try:
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=30)
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            answer = data["choices"][0]["message"]["content"]
            print(f"  Response: {answer}")
        else:
            print(f"  Error: {response.text[:200]}")
            
    except Exception as e:
        print(f"  Exception: {e}")
