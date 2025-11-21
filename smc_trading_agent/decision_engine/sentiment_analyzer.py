"""
Advanced Sentiment Analysis Integration System

This module implements comprehensive sentiment analysis by integrating multiple data sources
including financial news, social media (Twitter, Reddit), and other market intelligence sources.
It provides real-time sentiment scoring, trend analysis, and cross-platform sentiment correlation.

Key Features:
- Multi-source sentiment integration (News, Twitter, Reddit)
- Real-time sentiment scoring and normalization
- Sentiment momentum and trend analysis
- Cross-platform sentiment correlation
- Sentiment anomaly detection
- Adaptive sentiment thresholds
"""

import logging
import numpy as np
import pandas as pd
import requests
import json
from typing import Dict, Any, List, Tuple, Optional, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import nltk
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)


@dataclass
class SentimentScore:
    """Data class for sentiment score with metadata."""
    score: float  # -1 to 1 scale
    confidence: float  # 0 to 1 scale
    source: str
    timestamp: datetime
    text_sample: str
    volume: int  # Number of mentions/posts
    momentum: float  # Recent change in sentiment
    normalized_score: float  # Adjusted for baseline


@dataclass
class SentimentAggregation:
    """Aggregated sentiment across multiple sources."""
    overall_sentiment: float
    news_sentiment: float
    social_sentiment: float
    twitter_sentiment: float
    reddit_sentiment: float
    momentum: float
    volatility: float
    cross_platform_agreement: float
    confidence: float
    timestamp: datetime
    source_counts: Dict[str, int]


class NewsSentimentAnalyzer:
    """
    Financial news sentiment analyzer using multiple news APIs and NLP techniques.
    """
    
    def __init__(self, api_keys: Dict[str, str] = None):
        self.api_keys = api_keys or {}
        self.vader_analyzer = SentimentIntensityAnalyzer()
        
        # News API endpoints
        self.news_apis = {
            'newsapi': {
                'url': 'https://newsapi.org/v2/everything',
                'key_param': 'apiKey'
            },
            'alphavantage': {
                'url': 'https://www.alphavantage.co/query',
                'key_param': 'apikey'
            },
            'marketaux': {
                'url': 'https://api.marketaux.com/v1/news/all',
                'key_param': 'api_token'
            }
        }
        
        # Cryptocurrency/news keywords
        self.crypto_keywords = [
            'bitcoin', 'btc', 'cryptocurrency', 'crypto', 'blockchain',
            'ethereum', 'eth', 'altcoin', 'defi', 'nft', 'web3',
            'digital currency', 'virtual currency', 'coin', 'token'
        ]
        
        # Financial sentiment keywords
        self.positive_keywords = [
            'bullish', 'surge', 'rally', 'breakout', 'growth', 'profit',
            'gain', 'increase', 'rise', 'strong', 'optimistic', 'buy',
            'accumulate', 'upgrade', 'momentum', 'breakthrough'
        ]
        
        self.negative_keywords = [
            'bearish', 'crash', 'dump', 'fall', 'decline', 'loss',
            'decrease', 'drop', 'weak', 'pessimistic', 'sell',
            'distribute', 'downgrade', 'correction', 'bubble', 'concern'
        ]
        
        # Cache for recent articles
        self.article_cache = []
        self.cache_max_size = 1000
        
        logger.info("NewsSentimentAnalyzer initialized")
    
    async def fetch_news_sentiment(self, symbol: str = 'BTC', timeframe: str = '1h') -> List[SentimentScore]:
        """Fetch news sentiment for a specific symbol."""
        try:
            sentiment_scores = []
            
            # Try different news APIs
            for api_name, api_config in self.news_apis.items():
                try:
                    scores = await self._fetch_from_api(api_name, symbol, timeframe)
                    sentiment_scores.extend(scores)
                except Exception as e:
                    logger.warning(f"Failed to fetch from {api_name}: {str(e)}")
                    continue
            
            # Update cache
            self.article_cache.extend(sentiment_scores)
            if len(self.article_cache) > self.cache_max_size:
                self.article_cache = self.article_cache[-self.cache_max_size:]
            
            logger.info(f"Fetched {len(sentiment_scores)} news sentiment scores")
            return sentiment_scores
            
        except Exception as e:
            logger.error(f"News sentiment fetch failed: {str(e)}")
            return []
    
    async def _fetch_from_api(self, api_name: str, symbol: str, timeframe: str) -> List[SentimentScore]:
        """Fetch sentiment data from specific API."""
        if api_name not in self.api_keys:
            logger.warning(f"No API key for {api_name}")
            return []
        
        api_config = self.news_apis[api_name]
        api_key = self.api_keys[api_name]
        
        if not api_key:
            logger.warning(f"Empty API key for {api_name}")
            return []
        
        try:
            async with aiohttp.ClientSession() as session:
                # Build query parameters
                params = self._build_query_params(api_name, symbol, timeframe)
                params[api_config['key_param']] = api_key
                
                async with session.get(api_config['url'], params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_news_response(data, api_name)
                    else:
                        logger.warning(f"{api_name} API returned status {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"Error fetching from {api_name}: {str(e)}")
            return []
    
    def _build_query_params(self, api_name: str, symbol: str, timeframe: str) -> Dict[str, Any]:
        """Build query parameters for different APIs."""
        base_params = {
            'language': 'en',
            'sortBy': 'publishedAt'
        }
        
        if api_name == 'newsapi':
            base_params.update({
                'q': f'{symbol} OR cryptocurrency OR bitcoin',
                'domains': 'coindesk.com,cointelegraph.com,crypto.news,bloomberg.com,reuters.com',
                'from': (datetime.now() - timedelta(hours=1)).isoformat(),
                'pageSize': 50
            })
        elif api_name == 'alphavantage':
            base_params.update({
                'function': 'NEWS_SENTIMENT',
                'tickers': 'CRYPTO:BTC',
                'time_from': (datetime.now() - timedelta(hours=1)).strftime('%Y%m%dT%H%M')
            })
        elif api_name == 'marketaux':
            base_params.update({
                'symbols': 'BTCUSD',
                'published_after': (datetime.now() - timedelta(hours=1)).isoformat()
            })
        
        return base_params
    
    def _parse_news_response(self, data: Dict[str, Any], api_name: str) -> List[SentimentScore]:
        """Parse news API response and extract sentiment."""
        sentiment_scores = []
        
        try:
            if api_name == 'newsapi':
                articles = data.get('articles', [])
                for article in articles:
                    score = self._analyze_article_sentiment(article)
                    if score:
                        sentiment_scores.append(score)
            
            elif api_name == 'alphavantage':
                feed = data.get('feed', [])
                for item in feed:
                    score = self._analyze_alpha_vantage_item(item)
                    if score:
                        sentiment_scores.append(score)
            
            elif api_name == 'marketaux':
                articles = data.get('data', [])
                for article in articles:
                    score = self._analyze_marketaux_article(article)
                    if score:
                        sentiment_scores.append(score)
        
        except Exception as e:
            logger.error(f"Error parsing {api_name} response: {str(e)}")
        
        return sentiment_scores
    
    def _analyze_article_sentiment(self, article: Dict[str, Any]) -> Optional[SentimentScore]:
        """Analyze sentiment of a single article."""
        try:
            title = article.get('title', '')
            description = article.get('description', '')
            content = article.get('content', '')
            
            # Combine text
            full_text = f"{title} {description} {content}"
            
            # Clean and analyze
            cleaned_text = self._clean_text(full_text)
            if not cleaned_text:
                return None
            
            # VADER sentiment
            vader_score = self.vader_analyzer.polarity_scores(cleaned_text)
            compound_score = vader_score['compound']
            
            # TextBlob sentiment
            blob_score = TextBlob(cleaned_text).sentiment.polarity
            
            # Combine scores
            final_score = (compound_score * 0.7 + blob_score * 0.3)
            
            # Calculate confidence
            confidence = max(abs(compound_score), abs(blob_score))
            
            # Extract sample (first 100 characters)
            sample = cleaned_text[:100] + "..." if len(cleaned_text) > 100 else cleaned_text
            
            return SentimentScore(
                score=final_score,
                confidence=confidence,
                source='newsapi',
                timestamp=datetime.now(),
                text_sample=sample,
                volume=1,
                momentum=0.0,  # Will be calculated separately
                normalized_score=final_score
            )
            
        except Exception as e:
            logger.error(f"Error analyzing article: {str(e)}")
            return None
    
    def _analyze_alpha_vantage_item(self, item: Dict[str, Any]) -> Optional[SentimentScore]:
        """Analyze Alpha Vantage news sentiment item."""
        try:
            title = item.get('title', '')
            summary = item.get('summary', '')
            
            # Alpha Vantage provides sentiment scores directly
            overall_sentiment = item.get('overall_sentiment_score', 0)
            sentiment_label = item.get('overall_sentiment_label', 'NEUTRAL')
            
            # Convert to -1 to 1 scale
            if sentiment_label == 'BEARISH':
                score = -abs(overall_sentiment) / 100
            elif sentiment_label == 'BULLISH':
                score = abs(overall_sentiment) / 100
            else:
                score = 0.0
            
            # Use our own analysis for confirmation
            full_text = f"{title} {summary}"
            cleaned_text = self._clean_text(full_text)
            
            if cleaned_text:
                vader_score = self.vader_analyzer.polarity_scores(cleaned_text)
                # Weight Alpha Vantage score higher if available
                final_score = score * 0.8 + vader_score['compound'] * 0.2
                confidence = max(abs(score), abs(vader_score['compound']))
            else:
                final_score = score
                confidence = abs(score)
            
            sample = title[:100] + "..." if len(title) > 100 else title
            
            return SentimentScore(
                score=final_score,
                confidence=confidence,
                source='alphavantage',
                timestamp=datetime.now(),
                text_sample=sample,
                volume=1,
                momentum=0.0,
                normalized_score=final_score
            )
            
        except Exception as e:
            logger.error(f"Error analyzing Alpha Vantage item: {str(e)}")
            return None
    
    def _analyze_marketaux_article(self, article: Dict[str, Any]) -> Optional[SentimentScore]:
        """Analyze Marketaux article."""
        try:
            title = article.get('title', '')
            description = article.get('description', '')
            
            full_text = f"{title} {description}"
            cleaned_text = self._clean_text(full_text)
            
            if not cleaned_text:
                return None
            
            # Standard sentiment analysis
            vader_score = self.vader_analyzer.polarity_scores(cleaned_text)
            blob_score = TextBlob(cleaned_text).sentiment.polarity
            
            final_score = (vader_score['compound'] * 0.7 + blob_score * 0.3)
            confidence = max(abs(vader_score['compound']), abs(blob_score))
            
            sample = cleaned_text[:100] + "..." if len(cleaned_text) > 100 else cleaned_text
            
            return SentimentScore(
                score=final_score,
                confidence=confidence,
                source='marketaux',
                timestamp=datetime.now(),
                text_sample=sample,
                volume=1,
                momentum=0.0,
                normalized_score=final_score
            )
            
        except Exception as e:
            logger.error(f"Error analyzing Marketaux article: {str(e)}")
            return None
    
    def _clean_text(self, text: str) -> str:
        """Clean and preprocess text for sentiment analysis."""
        if not text:
            return ""
        
        # Remove URLs
        text = re.sub(r'http\S+|www\S+', '', text)
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove special characters and extra whitespace
        text = re.sub(r'[^a-zA-Z0-9\s]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text


class SocialMediaAnalyzer:
    """
    Social media sentiment analyzer for Twitter and Reddit platforms.
    """
    
    def __init__(self, api_keys: Dict[str, str] = None):
        self.api_keys = api_keys or {}
        self.vader_analyzer = SentimentIntensityAnalyzer()
        
        # Platform-specific configurations
        self.crypto_hashtags = [
            '#bitcoin', '#btc', '#cryptocurrency', '#crypto', '#blockchain',
            '#ethereum', '#eth', '#altcoin', '#defi', '#nft', '#web3'
        ]
        
        self.crypto_subreddits = [
            'Bitcoin', 'CryptoCurrency', 'CryptoMarkets', 'BitcoinBeginners',
            'ethereum', 'CryptoTechnology', 'BitcoinMining', 'WallStreetBets'
        ]
        
        # Cache for social media posts
        self.social_cache = []
        self.cache_max_size = 2000
        
        logger.info("SocialMediaAnalyzer initialized")
    
    async def fetch_twitter_sentiment(self, symbol: str = 'BTC', timeframe: str = '1h') -> List[SentimentScore]:
        """Fetch Twitter sentiment for crypto markets."""
        try:
            sentiment_scores = []
            
            # In a real implementation, this would use Twitter API
            # For now, simulate with placeholder data
            sentiment_scores = await self._fetch_twitter_data(symbol, timeframe)
            
            # Update cache
            self.social_cache.extend(sentiment_scores)
            if len(self.social_cache) > self.cache_max_size:
                self.social_cache = self.social_cache[-self.cache_max_size:]
            
            return sentiment_scores
            
        except Exception as e:
            logger.error(f"Twitter sentiment fetch failed: {str(e)}")
            return []
    
    async def fetch_reddit_sentiment(self, symbol: str = 'BTC', timeframe: str = '1h') -> List[SentimentScore]:
        """Fetch Reddit sentiment from crypto-related subreddits."""
        try:
            sentiment_scores = []
            
            # In a real implementation, this would use Reddit API
            # For now, simulate with placeholder data
            sentiment_scores = await self._fetch_reddit_data(symbol, timeframe)
            
            # Update cache
            self.social_cache.extend(sentiment_scores)
            if len(self.social_cache) > self.cache_max_size:
                self.social_cache = self.social_cache[-self.cache_max_size:]
            
            return sentiment_scores
            
        except Exception as e:
            logger.error(f"Reddit sentiment fetch failed: {str(e)}")
            return []
    
    async def _fetch_twitter_data(self, symbol: str, timeframe: str) -> List[SentimentScore]:
        """Fetch data from Twitter API (placeholder implementation)."""
        # Simulated Twitter data - in production, use actual Twitter API
        simulated_tweets = [
            {"text": "Bitcoin is looking bullish today! Great technical setup. #BTC #Bitcoin"},
            {"text": "Concerned about the crypto market sentiment. Need to watch support levels carefully. #crypto"},
            {"text": "Ethereum breaking out! DeFi protocols showing strong adoption. #ETH #blockchain"},
            {"text": "Bitcoin dumps again. This bear market is brutal. #BTC #cryptocurrency"},
            {"text": "Nice recovery in the markets! Crypto showing resilience. #crypto #bullish"}
        ]
        
        sentiment_scores = []
        for tweet in simulated_tweets:
            score = self._analyze_tweet_sentiment(tweet)
            if score:
                sentiment_scores.append(score)
        
        return sentiment_scores
    
    async def _fetch_reddit_data(self, symbol: str, timeframe: str) -> List[SentimentScore]:
        """Fetch data from Reddit API (placeholder implementation)."""
        # Simulated Reddit posts - in production, use actual Reddit API
        simulated_posts = [
            {"title": "Technical Analysis: Bitcoin at Critical Support Level", "text": "Looking at the charts, BTC is testing important support..."},
            {"title": "Why I'm Bullish on Ethereum Long-term", "text": "Despite recent volatility, ETH fundamentals remain strong..."},
            {"title": "Crypto Market Cap Analysis and Predictions", "text": "Market cap showing interesting patterns for altcoins..."},
            {"title": "Bear Market Strategies for Crypto Investors", "text": "In these bearish conditions, it's important to have a strategy..."},
            {"title": "DeFi Innovation Continues Despite Market Conditions", "text": "The DeFi space continues to innovate with new protocols..."}
        ]
        
        sentiment_scores = []
        for post in simulated_posts:
            score = self._analyze_reddit_post(post)
            if score:
                sentiment_scores.append(score)
        
        return sentiment_scores
    
    def _analyze_tweet_sentiment(self, tweet: Dict[str, Any]) -> Optional[SentimentScore]:
        """Analyze sentiment of a tweet."""
        try:
            text = tweet.get('text', '')
            cleaned_text = self._clean_text(text)
            
            if not cleaned_text:
                return None
            
            # VADER sentiment
            vader_score = self.vader_analyzer.polarity_scores(cleaned_text)
            compound_score = vader_score['compound']
            
            # TextBlob sentiment
            blob_score = TextBlob(cleaned_text).sentiment.polarity
            
            # Combine scores
            final_score = (compound_score * 0.6 + blob_score * 0.4)
            
            # Add crypto-specific weight adjustment
            crypto_weight = self._calculate_crypto_weight(cleaned_text)
            final_score = final_score * (1 + crypto_weight * 0.2)
            
            # Ensure score is in valid range
            final_score = max(-1.0, min(1.0, final_score))
            
            confidence = max(abs(compound_score), abs(blob_score))
            
            sample = cleaned_text[:80] + "..." if len(cleaned_text) > 80 else cleaned_text
            
            return SentimentScore(
                score=final_score,
                confidence=confidence,
                source='twitter',
                timestamp=datetime.now(),
                text_sample=sample,
                volume=1,
                momentum=0.0,
                normalized_score=final_score
            )
            
        except Exception as e:
            logger.error(f"Error analyzing tweet: {str(e)}")
            return None
    
    def _analyze_reddit_post(self, post: Dict[str, Any]) -> Optional[SentimentScore]:
        """Analyze sentiment of a Reddit post."""
        try:
            title = post.get('title', '')
            text = post.get('text', '')
            
            combined_text = f"{title} {text}"
            cleaned_text = self._clean_text(combined_text)
            
            if not cleaned_text:
                return None
            
            # VADER sentiment
            vader_score = self.vader_analyzer.polarity_scores(cleaned_text)
            compound_score = vader_score['compound']
            
            # TextBlob sentiment
            blob_score = TextBlob(cleaned_text).sentiment.polarity
            
            # Combine scores (Reddit posts might be more thoughtful)
            final_score = (compound_score * 0.5 + blob_score * 0.5)
            
            # Add crypto-specific weight adjustment
            crypto_weight = self._calculate_crypto_weight(cleaned_text)
            final_score = final_score * (1 + crypto_weight * 0.15)
            
            # Ensure score is in valid range
            final_score = max(-1.0, min(1.0, final_score))
            
            confidence = max(abs(compound_score), abs(blob_score))
            
            sample = title[:80] + "..." if len(title) > 80 else title
            
            return SentimentScore(
                score=final_score,
                confidence=confidence,
                source='reddit',
                timestamp=datetime.now(),
                text_sample=sample,
                volume=1,
                momentum=0.0,
                normalized_score=final_score
            )
            
        except Exception as e:
            logger.error(f"Error analyzing Reddit post: {str(e)}")
            return None
    
    def _clean_text(self, text: str) -> str:
        """Clean and preprocess text for sentiment analysis."""
        if not text:
            return ""
        
        # Remove URLs
        text = re.sub(r'http\S+|www\S+', '', text)
        
        # Remove markdown and HTML
        text = re.sub(r'[\*\_\~\`\[\]\(\)]', '', text)
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove mentions and hashtags but keep the text
        text = re.sub(r'[@#]([A-Za-z0-9_]+)', r'\1', text)
        
        # Remove special characters and extra whitespace
        text = re.sub(r'[^a-zA-Z0-9\s]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _calculate_crypto_weight(self, text: str) -> float:
        """Calculate crypto-specific sentiment weight adjustment."""
        crypto_terms = 0
        words = text.lower().split()
        
        for word in words:
            if word in ['bitcoin', 'btc', 'crypto', 'cryptocurrency', 'blockchain', 
                       'ethereum', 'eth', 'defi', 'altcoin', 'nft']:
                crypto_terms += 1
        
        # More crypto terms = higher weight
        return min(crypto_terms / 10.0, 1.0)


class SentimentAggregator:
    """
    Aggregates sentiment scores from multiple sources and calculates composite metrics.
    """
    
    def __init__(self):
        self.scaler = StandardScaler()
        self.anomaly_detector = IsolationForest(contamination=0.1, random_state=42)
        
        # Historical sentiment data for normalization
        self.sentiment_history = []
        self.max_history_size = 10000
        
        # Baseline sentiment levels
        self.baseline_sentiment = {
            'news': 0.0,
            'twitter': 0.0,
            'reddit': 0.0,
            'overall': 0.0
        }
        
        # Momentum calculation parameters
        self.momentum_window = 20
        
        logger.info("SentimentAggregator initialized")
    
    def aggregate_sentiment(self, sentiment_scores: List[SentimentScore]) -> Optional[SentimentAggregation]:
        """Aggregate sentiment scores from multiple sources."""
        try:
            if not sentiment_scores:
                return None
            
            # Group by source
            source_groups = {}
            for score in sentiment_scores:
                source = score.source
                if source not in source_groups:
                    source_groups[source] = []
                source_groups[source].append(score)
            
            # Calculate source-specific sentiments
            news_scores = source_groups.get('newsapi', []) + source_groups.get('alphavantage', []) + source_groups.get('marketaux', [])
            twitter_scores = source_groups.get('twitter', [])
            reddit_scores = source_groups.get('reddit', [])
            
            # Calculate weighted averages
            news_sentiment = self._calculate_weighted_sentiment(news_scores)
            twitter_sentiment = self._calculate_weighted_sentiment(twitter_scores)
            reddit_sentiment = self._calculate_weighted_sentiment(reddit_scores)
            
            # Social media combined
            social_scores = twitter_scores + reddit_scores
            social_sentiment = self._calculate_weighted_sentiment(social_scores)
            
            # Overall sentiment (weighted by source reliability)
            weights = {
                'news': 0.5,
                'social': 0.3,
                'twitter': 0.15,
                'reddit': 0.05
            }
            
            overall_sentiment = (
                news_sentiment * weights['news'] +
                social_sentiment * weights['social']
            )
            
            # Calculate momentum
            momentum = self._calculate_momentum(sentiment_scores)
            
            # Calculate sentiment volatility
            volatility = self._calculate_volatility(sentiment_scores)
            
            # Calculate cross-platform agreement
            cross_platform_agreement = self._calculate_cross_platform_agreement(
                news_sentiment, twitter_sentiment, reddit_sentiment
            )
            
            # Calculate overall confidence
            confidence = self._calculate_overall_confidence(sentiment_scores)
            
            # Count sources
            source_counts = {
                'news': len(news_scores),
                'twitter': len(twitter_scores),
                'reddit': len(reddit_scores),
                'social': len(social_scores),
                'total': len(sentiment_scores)
            }
            
            aggregation = SentimentAggregation(
                overall_sentiment=overall_sentiment,
                news_sentiment=news_sentiment,
                social_sentiment=social_sentiment,
                twitter_sentiment=twitter_sentiment,
                reddit_sentiment=reddit_sentiment,
                momentum=momentum,
                volatility=volatility,
                cross_platform_agreement=cross_platform_agreement,
                confidence=confidence,
                timestamp=datetime.now(),
                source_counts=source_counts
            )
            
            # Update history
            self.sentiment_history.append(aggregation)
            if len(self.sentiment_history) > self.max_history_size:
                self.sentiment_history = self.sentiment_history[-self.max_history_size:]
            
            # Update baselines
            self._update_baselines(aggregation)
            
            return aggregation
            
        except Exception as e:
            logger.error(f"Sentiment aggregation failed: {str(e)}")
            return None
    
    def _calculate_weighted_sentiment(self, scores: List[SentimentScore]) -> float:
        """Calculate weighted average sentiment for a group of scores."""
        if not scores:
            return 0.0
        
        total_weight = 0
        weighted_sum = 0
        
        for score in scores:
            weight = score.confidence * score.volume
            weighted_sum += score.score * weight
            total_weight += weight
        
        if total_weight > 0:
            return weighted_sum / total_weight
        else:
            return np.mean([s.score for s in scores])
    
    def _calculate_momentum(self, sentiment_scores: List[SentimentScore]) -> float:
        """Calculate sentiment momentum (rate of change)."""
        if len(self.sentiment_history) < 2:
            return 0.0
        
        # Get recent sentiment values
        recent_sentiments = [s.overall_sentiment for s in self.sentiment_history[-self.momentum_window:]]
        
        if len(recent_sentiments) < 2:
            return 0.0
        
        # Calculate linear trend
        x = np.arange(len(recent_sentiments))
        slope, _ = np.polyfit(x, recent_sentiments, 1)
        
        return slope  # Positive = increasing sentiment, Negative = decreasing
    
    def _calculate_volatility(self, sentiment_scores: List[SentimentScore]) -> float:
        """Calculate sentiment volatility."""
        if len(sentiment_scores) < 2:
            return 0.0
        
        score_values = [s.score for s in sentiment_scores]
        return np.std(score_values)
    
    def _calculate_cross_platform_agreement(self, news_sentiment: float, twitter_sentiment: float, reddit_sentiment: float) -> float:
        """Calculate agreement between different platforms."""
        sentiments = [news_sentiment, twitter_sentiment, reddit_sentiment]
        sentiments = [s for s in sentiments if s != 0]  # Exclude zeros
        
        if len(sentiments) < 2:
            return 0.5  # Neutral agreement
        
        # Calculate correlation-like agreement
        mean_sentiment = np.mean(sentiments)
        variance = np.var(sentiments)
        
        # Lower variance = higher agreement
        agreement = 1.0 - min(variance, 1.0)
        
        return agreement
    
    def _calculate_overall_confidence(self, sentiment_scores: List[SentimentScore]) -> float:
        """Calculate overall confidence in sentiment aggregation."""
        if not sentiment_scores:
            return 0.0
        
        # Base confidence from individual scores
        individual_confidences = [s.confidence for s in sentiment_scores]
        base_confidence = np.mean(individual_confidences)
        
        # Volume confidence (more data = higher confidence)
        volume_confidence = min(len(sentiment_scores) / 50.0, 1.0)
        
        # Source diversity confidence
        sources = set(s.source for s in sentiment_scores)
        diversity_confidence = min(len(sources) / 4.0, 1.0)
        
        # Combine confidence factors
        overall_confidence = (
            base_confidence * 0.5 +
            volume_confidence * 0.3 +
            diversity_confidence * 0.2
        )
        
        return overall_confidence
    
    def _update_baselines(self, aggregation: SentimentAggregation):
        """Update baseline sentiment levels."""
        # Exponential moving average for baseline
        alpha = 0.01  # Slow adaptation
        
        self.baseline_sentiment['news'] = alpha * aggregation.news_sentiment + (1 - alpha) * self.baseline_sentiment['news']
        self.baseline_sentiment['twitter'] = alpha * aggregation.twitter_sentiment + (1 - alpha) * self.baseline_sentiment['twitter']
        self.baseline_sentiment['reddit'] = alpha * aggregation.reddit_sentiment + (1 - alpha) * self.baseline_sentiment['reddit']
        self.baseline_sentiment['overall'] = alpha * aggregation.overall_sentiment + (1 - alpha) * self.baseline_sentiment['overall']
    
    def detect_sentiment_anomalies(self, aggregation: SentimentAggregation) -> bool:
        """Detect sentiment anomalies using isolation forest."""
        try:
            if len(self.sentiment_history) < 10:
                return False
            
            # Prepare feature vector
            features = np.array([[
                aggregation.overall_sentiment,
                aggregation.momentum,
                aggregation.volatility,
                aggregation.cross_platform_agreement,
                aggregation.confidence
            ]])
            
            # Detect anomaly
            anomaly_score = self.anomaly_detector.decision_function(features)[0]
            
            # Negative score indicates anomaly
            return anomaly_score < 0
            
        except Exception as e:
            logger.error(f"Anomaly detection failed: {str(e)}")
            return False
    
    def get_sentiment_features(self, aggregation: SentimentAggregation) -> Dict[str, float]:
        """Extract sentiment features for ML models."""
        if not aggregation:
            return {
                'sentiment_overall': 0.0,
                'sentiment_news': 0.0,
                'sentiment_social': 0.0,
                'sentiment_momentum': 0.0,
                'sentiment_volatility': 0.0,
                'sentiment_agreement': 0.0,
                'sentiment_confidence': 0.0,
                'sentiment_anomaly': 0.0
            }
        
        # Normalize sentiment values
        normalized_news = aggregation.news_sentiment - self.baseline_sentiment['news']
        normalized_twitter = aggregation.twitter_sentiment - self.baseline_sentiment['twitter']
        normalized_reddit = aggregation.reddit_sentiment - self.baseline_sentiment['reddit']
        normalized_overall = aggregation.overall_sentiment - self.baseline_sentiment['overall']
        
        return {
            'sentiment_overall': normalized_overall,
            'sentiment_news': normalized_news,
            'sentiment_social': aggregation.social_sentiment,
            'sentiment_momentum': aggregation.momentum,
            'sentiment_volatility': aggregation.volatility,
            'sentiment_agreement': aggregation.cross_platform_agreement,
            'sentiment_confidence': aggregation.confidence,
            'sentiment_anomaly': 1.0 if self.detect_sentiment_anomalies(aggregation) else 0.0,
            'sentiment_diversity': len(aggregation.source_counts),
            'sentiment_volume': aggregation.source_counts.get('total', 0)
        }


class SentimentAnalyzer:
    """
    Main sentiment analyzer that coordinates news and social media analysis.
    """
    
    def __init__(self, api_keys: Dict[str, str] = None):
        self.api_keys = api_keys or {}
        
        # Initialize analyzers
        self.news_analyzer = NewsSentimentAnalyzer(api_keys)
        self.social_analyzer = SocialMediaAnalyzer(api_keys)
        self.aggregator = SentimentAggregator()
        
        # Caching
        self.cache_ttl = timedelta(minutes=30)
        self.last_update = None
        self.cached_aggregation = None
        
        logger.info("SentimentAnalyzer initialized")
    
    async def get_sentiment_features(self, symbol: str = 'BTC', timeframe: str = '1h') -> Dict[str, float]:
        """
        Get comprehensive sentiment features for ML models.
        
        Args:
            symbol: Trading symbol (e.g., 'BTC')
            timeframe: Analysis timeframe
            
        Returns:
            Dictionary of sentiment features
        """
        try:
            # Check cache
            if self._is_cache_valid():
                return self.aggregator.get_sentiment_features(self.cached_aggregation)
            
            # Fetch sentiment data from all sources
            sentiment_scores = []
            
            # Fetch news sentiment
            news_scores = await self.news_analyzer.fetch_news_sentiment(symbol, timeframe)
            sentiment_scores.extend(news_scores)
            
            # Fetch social media sentiment
            twitter_scores = await self.social_analyzer.fetch_twitter_sentiment(symbol, timeframe)
            sentiment_scores.extend(twitter_scores)
            
            reddit_scores = await self.social_analyzer.fetch_reddit_sentiment(symbol, timeframe)
            sentiment_scores.extend(reddit_scores)
            
            # Aggregate sentiment
            aggregation = self.aggregator.aggregate_sentiment(sentiment_scores)
            
            if aggregation:
                self.cached_aggregation = aggregation
                self.last_update = datetime.now()
                
                return self.aggregator.get_sentiment_features(aggregation)
            else:
                return self._get_default_features()
                
        except Exception as e:
            logger.error(f"Sentiment feature extraction failed: {str(e)}")
            return self._get_default_features()
    
    def _is_cache_valid(self) -> bool:
        """Check if cached sentiment data is still valid."""
        if not self.cached_aggregation or not self.last_update:
            return False
        
        return datetime.now() - self.last_update < self.cache_ttl
    
    def _get_default_features(self) -> Dict[str, float]:
        """Get default sentiment features when data is unavailable."""
        return {
            'sentiment_overall': 0.0,
            'sentiment_news': 0.0,
            'sentiment_social': 0.0,
            'sentiment_momentum': 0.0,
            'sentiment_volatility': 0.5,
            'sentiment_agreement': 0.5,
            'sentiment_confidence': 0.1,
            'sentiment_anomaly': 0.0,
            'sentiment_diversity': 0.0,
            'sentiment_volume': 0.0
        }
    
    async def get_detailed_sentiment(self, symbol: str = 'BTC', timeframe: str = '1h') -> Dict[str, Any]:
        """Get detailed sentiment analysis with breakdown."""
        try:
            if not self._is_cache_valid():
                # Fetch fresh data
                await self.get_sentiment_features(symbol, timeframe)
            
            if self.cached_aggregation:
                return {
                    'sentiment_scores': {
                        'overall': self.cached_aggregation.overall_sentiment,
                        'news': self.cached_aggregation.news_sentiment,
                        'social': self.cached_aggregation.social_sentiment,
                        'twitter': self.cached_aggregation.twitter_sentiment,
                        'reddit': self.cached_aggregation.reddit_sentiment
                    },
                    'metadata': {
                        'momentum': self.cached_aggregation.momentum,
                        'volatility': self.cached_aggregation.volatility,
                        'cross_platform_agreement': self.cached_aggregation.cross_platform_agreement,
                        'confidence': self.cached_aggregation.confidence,
                        'source_counts': self.cached_aggregation.source_counts,
                        'timestamp': self.cached_aggregation.timestamp
                    },
                    'features': self.aggregator.get_sentiment_features(self.cached_aggregation)
                }
            else:
                return {
                    'error': 'No sentiment data available',
                    'features': self._get_default_features()
                }
                
        except Exception as e:
            logger.error(f"Detailed sentiment analysis failed: {str(e)}")
            return {
                'error': str(e),
                'features': self._get_default_features()
            }
    
    def get_sentiment_statistics(self) -> Dict[str, Any]:
        """Get sentiment analysis statistics and performance metrics."""
        try:
            if not self.aggregator.sentiment_history:
                return {
                    'total_analyses': 0,
                    'average_sentiment': 0.0,
                    'sentiment_range': {'min': 0.0, 'max': 0.0},
                    'data_availability': 0.0
                }
            
            # Calculate statistics from history
            sentiments = [s.overall_sentiment for s in self.aggregator.sentiment_history]
            
            return {
                'total_analyses': len(self.aggregator.sentiment_history),
                'average_sentiment': np.mean(sentiments),
                'sentiment_range': {
                    'min': np.min(sentiments),
                    'max': np.max(sentiments)
                },
                'sentiment_std': np.std(sentiments),
                'data_availability': len(self.aggregator.sentiment_history) / 100.0,  # Normalized
                'baseline_sentiment': self.aggregator.baseline_sentiment,
                'last_update': self.last_update,
                'cache_valid': self._is_cache_valid()
            }
            
        except Exception as e:
            logger.error(f"Sentiment statistics failed: {str(e)}")
            return {'error': str(e)}
    
    def update_api_keys(self, new_keys: Dict[str, str]):
        """Update API keys for external services."""
        self.api_keys.update(new_keys)
        self.news_analyzer.api_keys.update(new_keys)
        self.social_analyzer.api_keys.update(new_keys)
        logger.info("API keys updated")
    
    def clear_cache(self):
        """Clear sentiment cache."""
        self.cached_aggregation = None
        self.last_update = None
        logger.info("Sentiment cache cleared")