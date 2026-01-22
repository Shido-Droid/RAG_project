#!/usr/bin/env python3
"""
Scoring Function Evaluation Script
Tests scoring functions against a set of graded examples to ensure rank adherence.
"""

import sys
import os
import unittest
from typing import List, Dict, NamedTuple

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import importlib.util

import importlib.util
import sys
import os

# Create a mock rag_app package
rag_app_pkg = type(sys)('rag_app')
rag_app_pkg.__path__ = []
sys.modules['rag_app'] = rag_app_pkg

# Helper to load module
def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src", "rag_app")

# Load dependencies first
config = load_module("rag_app.config", os.path.join(src_path, "config.py"))
utils = load_module("rag_app.utils", os.path.join(src_path, "utils.py"))

# Load scraper
scraper = load_module("rag_app.scraper", os.path.join(src_path, "scraper.py"))

# Expose functions
score_text_for_news = scraper.score_text_for_news
score_text_for_weather = scraper.score_text_for_weather
score_text_for_informational = scraper.score_text_for_informational
score_text_for_spec = scraper.score_text_for_spec
score_text_for_restaurant = scraper.score_text_for_restaurant

class TestCase(NamedTuple):
    name: str
    text: str
    title: str
    url: str
    expected_quality: str  # "HIGH", "MEDIUM", "LOW"
    min_score: float = 0.0

class TestScoringQuality(unittest.TestCase):
    
    def evaluate_cases(self, func, cases: List[TestCase], threshold_high=3.0, threshold_low=2.0):
        print(f"\nEvaluating {func.__name__}...")
        for case in cases:
            score = func(case.text, title=case.title, url=case.url)
            print(f"  [{case.expected_quality}] {case.name}: {score:.2f}")
            
            if case.expected_quality == "HIGH":
                self.assertGreaterEqual(score, threshold_high, f"{case.name} should be high quality (got {score:.2f})")
            elif case.expected_quality == "LOW":
                self.assertLess(score, threshold_low, f"{case.name} should be low quality (got {score:.2f})")

    def test_news_scoring(self):
        cases = [
            TestCase(
                name="NHK News (Perfect)",
                text="2026年1月16日、政府は新しい経済対策を発表した。速報によると規模は10兆円...",
                title="経済対策の発表",
                url="https://www3.nhk.or.jp/news/20260116/k1001.html",
                expected_quality="HIGH"
            ),
            TestCase(
                name="Generic Blog",
                text="今日のニュースについて思ったことを書きます。",
                title="日記",
                url="https://example.com/blog",
                expected_quality="LOW"
            )
        ]
        self.evaluate_cases(score_text_for_news, cases, threshold_high=3.0, threshold_low=2.0)

    def test_weather_scoring(self):
        cases = [
            TestCase(
                name="JMA Forecast",
                text="東京地方 16日12時 晴れ 気温15.2度 湿度40% 降水確率 0%",
                title="気象庁天気予報",
                url="https://www.jma.go.jp/bosai/forecast/",
                expected_quality="HIGH"
            ),
            TestCase(
                name="Short Comment",
                text="いい天気だね",
                title="つぶやき",
                url="https://twitter.com/user/status/123",
                expected_quality="LOW"
            )
        ]
        self.evaluate_cases(score_text_for_weather, cases, threshold_high=3.0, threshold_low=2.0)

    def test_restaurant_scoring(self):
        cases = [
            TestCase(
                name="Tabelog Detail",
                text="""
                口コミ評価 3.85
                ランチ：11:30～14:00
                ディナー：17:30～23:00
                東京都渋谷区神南1-1-1
                03-1234-5678
                人気のパスタランチは1200円から。
                シェフはイタリアで修行した本格派。
                店内は落ち着いた雰囲気で、デートや記念日にもおすすめです。
                季節の食材を使った限定メニューも充実しています。
                """,
                title="イタリアン・バル 渋谷",
                url="https://tabelog.com/tokyo/A1303/A130301/13000001/",
                expected_quality="HIGH"
            ),
            TestCase(
                name="Simple Mention",
                text="ここのパスタ美味しかった",
                title="某店",
                url="https://example.com/food",
                expected_quality="LOW"
            )
        ]
        self.evaluate_cases(score_text_for_restaurant, cases, threshold_high=2.8, threshold_low=2.0)

    def test_spec_scoring(self):
        cases = [
            TestCase(
                name="Google API Doc",
                text="""
                Gemini API v1.5 Specification
                Release Date: 2025-05-10
                Version: 1.5.0
                
                Methods:
                - generateContent
                - streamGenerateContent
                
                Usage:
                ```bash
                curl https://...
                ```
                """,
                title="Gemini API Reference",
                url="https://ai.google.dev/gemini-api/docs",
                expected_quality="HIGH"
            ),
            TestCase(
                name="Forum Question",
                text="How do I use the API?",
                title="Help me",
                url="https://stackoverflow.com/questions/1",
                expected_quality="LOW"
            )
        ]
        self.evaluate_cases(score_text_for_spec, cases, threshold_high=3.0, threshold_low=2.0)

if __name__ == "__main__":
    unittest.main()
