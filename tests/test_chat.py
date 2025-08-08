#!/usr/bin/env python3
"""
Simple test script for ollamao API
"""

import requests
import json
import sys

API_BASE = "http://localhost:8000"
API_KEY = "my-key"

def test_health():
    """Test health endpoint"""
    print("🏥 Testing health endpoint...")
    response = requests.get(f"{API_BASE}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}\n")

def test_models():
    """Test models endpoint"""
    print("📋 Testing models endpoint...")
    response = requests.get(
        f"{API_BASE}/v1/models",
        headers={"Authorization": f"Bearer {API_KEY}"}
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}\n")

def test_chat(message: str, stream: bool = False):
    """Test chat completion"""
    print(f"💬 Testing chat {'(streaming)' if stream else '(non-streaming)'}...")
    print(f"Message: {message}")
    
    response = requests.post(
        f"{API_BASE}/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "llama3",
            "messages": [{"role": "user", "content": message}],
            "stream": stream
        },
        stream=stream
    )
    
    print(f"Status: {response.status_code}")
    
    if stream:
        print("Streaming response:")
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data = line[6:]  # Remove 'data: ' prefix
                    if data == '[DONE]':
                        print("\n✅ Stream completed")
                        break
                    try:
                        chunk = json.loads(data)
                        content = chunk.get('choices', [{}])[0].get('delta', {}).get('content', '')
                        if content:
                            print(content, end='', flush=True)
                    except json.JSONDecodeError:
                        pass
        print()
    else:
        response_data = response.json()
        content = response_data.get('choices', [{}])[0].get('message', {}).get('content', '')
        print(f"Response: {content}")
        
        usage = response_data.get('usage', {})
        print(f"Tokens - Prompt: {usage.get('prompt_tokens')}, "
              f"Completion: {usage.get('completion_tokens')}, "
              f"Total: {usage.get('total_tokens')}")
    print()

def main():
    """Run all tests"""
    print("🦙 OLLAMAO API Test Suite\n")
    
    try:
        test_health()
        test_models()
        test_chat("Hello! How are you?")
        test_chat("Count from 1 to 3", stream=True)
        test_chat("What is 2+2? Give a very short answer.")
        
        print("✅ All tests completed successfully!")
        
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to ollamao API. Is it running on localhost:8000?")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
