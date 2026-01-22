#!/usr/bin/env python3
"""
Test script for new scoring functions.
Tests each intent-specific scoring function with sample data.
"""

import sys
sys.path.insert(0, '/home/shido/RAG_project')

from src.rag_app.scraper import (
    score_text_for_news,
    score_text_for_weather,
    score_text_for_informational,
    score_text_for_spec,
    score_text_for_restaurant
)

def test_news_scoring():
    print("=" * 60)
    print("Testing News Scoring")
    print("=" * 60)
    
    # High-quality news article
    news_text = """
    2026年1月16日、NHKは最新のAI技術に関する速報を発表しました。
    記者会見では、新しいモデルの性能向上について詳しく説明されました。
    専門家によると、この技術は今後の産業に大きな影響を与えるとのことです。
    """
    score1 = score_text_for_news(news_text, title="AI技術の最新ニュース", url="https://www3.nhk.or.jp/news/article.html")
    print(f"High-quality NHK news: {score1:.2f}")
    
    # Lower quality news
    news_text2 = "AIについての記事です。"
    score2 = score_text_for_news(news_text2, title="AI", url="https://example.com/news")
    print(f"Low-quality generic news: {score2:.2f}")
    
    print()

def test_weather_scoring():
    print("=" * 60)
    print("Testing Weather Scoring")
    print("=" * 60)
    
    # High-quality weather forecast
    weather_text = """
    東京都の天気予報です。今日の最高気温は15℃、最低気温は8℃です。
    降水確率は午前30%、午後50%となっています。
    明日は晴れ、週間予報では来週まで晴天が続く見込みです。
    """
    score1 = score_text_for_weather(weather_text, title="東京の天気予報", url="https://www.jma.go.jp/bosai/forecast/")
    print(f"High-quality JMA weather: {score1:.2f}")
    
    # Lower quality weather
    weather_text2 = "今日は晴れです。"
    score2 = score_text_for_weather(weather_text2, title="天気", url="https://example.com/weather")
    print(f"Low-quality generic weather: {score2:.2f}")
    
    print()

def test_informational_scoring():
    print("=" * 60)
    print("Testing Informational Scoring")
    print("=" * 60)
    
    # High-quality informational content
    info_text = """
    富士山とは、日本最高峰の独立峰である。標高は3,776メートルで、
    山梨県と静岡県にまたがる活火山です。
    
    歴史的には、古くから信仰の対象とされ、多くの芸術作品の題材となってきました。
    例えば、葛飾北斎の「富嶽三十六景」などが有名です。
    
    具体的な特徴として、以下のような点が挙げられます：
    ・円錐形の美しい山容
    ・四季折々の景観
    ・世界文化遺産への登録（2013年）
    
    参考文献：気象庁、文化庁資料
    """
    score1 = score_text_for_informational(info_text, title="富士山について", url="https://ja.wikipedia.org/wiki/富士山")
    print(f"High-quality Wikipedia article: {score1:.2f}")
    
    # Lower quality informational
    info_text2 = "富士山は高い山です。"
    score2 = score_text_for_informational(info_text2, title="富士山", url="https://example.com/fuji")
    print(f"Low-quality generic info: {score2:.2f}")
    
    print()

def test_spec_scoring():
    print("=" * 60)
    print("Testing Spec Scoring")
    print("=" * 60)
    
    # High-quality spec document
    spec_text = """
    Gemini 2.0 API Specification
    Version: 2.0.1
    Release Date: 2025年12月
    
    This API provides access to Google's latest AI model.
    Supported features include:
    - Text generation
    - Image understanding
    - Code generation
    
    Changelog:
    - v2.0.1: Bug fixes and performance improvements
    - v2.0.0: Initial release
    """
    score1 = score_text_for_spec(spec_text, title="Gemini 2.0 API", url="https://ai.google.dev/gemini-api/docs")
    print(f"High-quality Google API docs: {score1:.2f}")
    
    # Lower quality spec
    spec_text2 = "APIの説明です。"
    score2 = score_text_for_spec(spec_text2, title="API", url="https://example.com/api")
    print(f"Low-quality generic spec: {score2:.2f}")
    
    print()

def test_restaurant_scoring():
    print("=" * 60)
    print("Testing Restaurant Scoring")
    print("=" * 60)
    
    # High-quality restaurant info
    restaurant_text = """
    渋谷の人気イタリアンレストラン
    
    営業時間：11:30-14:00（ランチ）、17:30-22:00（ディナー）
    住所：東京都渋谷区〒150-0001
    電話：03-1234-5678
    
    口コミ評価：4.5/5.0
    ランチメニューが充実しており、パスタセットは1,200円から。
    予約推奨。
    """
    score1 = score_text_for_restaurant(restaurant_text, title="渋谷イタリアン", url="https://tabelog.com/tokyo/restaurant123")
    print(f"High-quality Tabelog restaurant: {score1:.2f}")
    
    # Lower quality restaurant
    restaurant_text2 = "美味しいレストランです。"
    score2 = score_text_for_restaurant(restaurant_text2, title="レストラン", url="https://example.com/restaurant")
    print(f"Low-quality generic restaurant: {score2:.2f}")
    
    print()

def main():
    print("\n" + "=" * 60)
    print("RAG Scoring Functions Test")
    print("=" * 60 + "\n")
    
    test_news_scoring()
    test_weather_scoring()
    test_informational_scoring()
    test_spec_scoring()
    test_restaurant_scoring()
    
    print("=" * 60)
    print("All tests completed!")
    print("=" * 60)

if __name__ == "__main__":
    main()
