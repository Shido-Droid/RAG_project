#!/usr/bin/env python3
"""
Integration test for RAG system with new scoring functions.
Tests various intents and compares results.
"""

import requests
import json
import time

API_URL = "http://localhost:8000/api/ask"

def test_query(question: str, description: str):
    """Send a query to RAG API and display results."""
    print("\n" + "=" * 70)
    print(f"TEST: {description}")
    print("=" * 70)
    print(f"Question: {question}")
    print("-" * 70)
    
    try:
        response = requests.post(
            API_URL,
            json={"question": question},
            stream=True,
            timeout=120
        )
        
        if response.status_code != 200:
            print(f"Error: HTTP {response.status_code}")
            return
        
        answer_parts = []
        sources = []
        
        for line in response.iter_lines():
            if not line:
                continue
            
            try:
                data = json.loads(line.decode('utf-8'))
                
                if data.get("type") == "status":
                    print(f"[Status] {data.get('content')}")
                
                elif data.get("type") == "answer":
                    answer_parts.append(data.get("content", ""))
                
                elif data.get("type") == "sources":
                    sources = data.get("content", [])
            
            except json.JSONDecodeError:
                continue
        
        print("\n" + "-" * 70)
        print("ANSWER:")
        print("-" * 70)
        answer = "".join(answer_parts)
        print(answer[:500] + "..." if len(answer) > 500 else answer)
        
        if sources:
            print("\n" + "-" * 70)
            print(f"SOURCES ({len(sources)} found):")
            print("-" * 70)
            for i, source in enumerate(sources[:5], 1):
                print(f"{i}. {source.get('title', 'No title')}")
                print(f"   URL: {source.get('url', 'No URL')}")
        
        print("=" * 70)
        
    except requests.exceptions.Timeout:
        print("Error: Request timeout")
    except Exception as e:
        print(f"Error: {e}")

def main():
    print("\n" + "=" * 70)
    print("RAG SYSTEM INTEGRATION TEST")
    print("Testing new scoring functions with real queries")
    print("=" * 70)
    
    # Wait a bit to ensure server is ready
    time.sleep(2)
    
    # Test 1: News Intent
    test_query(
        "最新のAI技術のニュース",
        "News Intent - Should prioritize news sites (NHK, Nikkei, etc.)"
    )
    
    time.sleep(3)
    
    # Test 2: Weather Intent
    test_query(
        "東京の天気予報",
        "Weather Intent - Should prioritize JMA, tenki.jp"
    )
    
    time.sleep(3)
    
    # Test 3: Technical Spec Intent
    test_query(
        "Gemini 2.0のAPI仕様",
        "Spec Intent - Should prioritize Google official docs"
    )
    
    time.sleep(3)
    
    # Test 4: Informational Intent
    test_query(
        "富士山の標高",
        "Informational Intent - Should prioritize Wikipedia, official sites"
    )
    
    time.sleep(3)
    
    # Test 5: Local Search Intent
    test_query(
        "渋谷のおすすめランチ",
        "Local Search Intent - Should prioritize Tabelog, Gurunavi"
    )
    
    print("\n" + "=" * 70)
    print("ALL TESTS COMPLETED")
    print("=" * 70)
    print("\nReview the sources for each query to verify:")
    print("1. High-authority domains appear first")
    print("2. Intent-specific sites are prioritized")
    print("3. Content quality is reflected in rankings")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    main()
