import React from 'react';
import { Helmet } from 'react-helmet-async';

interface SEOHeadProps {
  title?: string;
  description?: string;
  keywords?: string;
  image?: string;
  url?: string;
  type?: 'website' | 'article' | 'profile';
  noIndex?: boolean;
  structuredData?: object;
}

const SEOHead: React.FC<SEOHeadProps> = ({
  title = 'SMC Trading Agent - Smart Market Structure Trading Platform',
  description = 'Advanced trading platform using Smart Money Concepts (SMC) for market analysis, risk management, and automated trading strategies.',
  keywords = 'SMC trading, Smart Money Concepts, trading platform, market structure, forex trading, crypto trading, technical analysis',
  image = '/og-image.png',
  url = 'https://smc-trading-agent.vercel.app/',
  type = 'website',
  noIndex = false,
  structuredData
}) => {
  const fullTitle = title.includes('SMC Trading Agent') ? title : `${title} | SMC Trading Agent`;
  const fullUrl = url.startsWith('http') ? url : `https://smc-trading-agent.vercel.app${url}`;
  const fullImage = image.startsWith('http') ? image : `https://smc-trading-agent.vercel.app${image}`;

  return (
    <Helmet>
      {/* Primary Meta Tags */}
      <title>{fullTitle}</title>
      <meta name="title" content={fullTitle} />
      <meta name="description" content={description} />
      <meta name="keywords" content={keywords} />
      <meta name="robots" content={noIndex ? 'noindex, nofollow' : 'index, follow'} />
      
      {/* Canonical URL */}
      <link rel="canonical" href={fullUrl} />
      
      {/* Open Graph / Facebook */}
      <meta property="og:type" content={type} />
      <meta property="og:url" content={fullUrl} />
      <meta property="og:title" content={fullTitle} />
      <meta property="og:description" content={description} />
      <meta property="og:image" content={fullImage} />
      <meta property="og:site_name" content="SMC Trading Agent" />
      
      {/* Twitter */}
      <meta property="twitter:card" content="summary_large_image" />
      <meta property="twitter:url" content={fullUrl} />
      <meta property="twitter:title" content={fullTitle} />
      <meta property="twitter:description" content={description} />
      <meta property="twitter:image" content={fullImage} />
      
      {/* Structured Data */}
      {structuredData && (
        <script type="application/ld+json">
          {JSON.stringify(structuredData)}
        </script>
      )}
    </Helmet>
  );
};

export default SEOHead;

// Predefined SEO configurations for different pages
export const SEOConfigs = {
  dashboard: {
    title: 'Trading Dashboard',
    description: 'Real-time trading dashboard with market analysis, portfolio overview, and performance metrics using Smart Money Concepts.',
    keywords: 'trading dashboard, SMC analysis, portfolio management, real-time data',
    url: '/'
  },
  trading: {
    title: 'Trading Interface',
    description: 'Advanced trading interface with Smart Money Concepts analysis, order management, and risk controls.',
    keywords: 'trading interface, SMC trading, order management, risk management',
    url: '/trading'
  },
  analytics: {
    title: 'Market Analytics',
    description: 'Comprehensive market analytics using Smart Money Concepts, technical indicators, and performance tracking.',
    keywords: 'market analytics, SMC analysis, technical analysis, trading performance',
    url: '/analytics'
  },
  research: {
    title: 'SMC Research & Education',
    description: 'Learn Smart Money Concepts trading strategies, market structure analysis, and advanced trading techniques.',
    keywords: 'SMC education, trading strategies, market structure, trading patterns',
    url: '/research'
  },
  monitoring: {
    title: 'System Monitoring',
    description: 'Real-time system monitoring, performance metrics, and health status of the SMC trading platform.',
    keywords: 'system monitoring, performance metrics, trading system health',
    url: '/monitoring'
  },
  reports: {
    title: 'Trading Reports',
    description: 'Detailed trading reports, performance analysis, and portfolio insights with Smart Money Concepts metrics.',
    keywords: 'trading reports, performance analysis, portfolio insights, SMC metrics',
    url: '/reports'
  },
  risk: {
    title: 'Risk Management',
    description: 'Advanced risk management tools and controls for Smart Money Concepts trading strategies.',
    keywords: 'risk management, trading controls, position sizing, SMC risk',
    url: '/risk'
  },
  config: {
    title: 'Configuration',
    description: 'Configure trading parameters, SMC settings, and platform preferences for optimal performance.',
    keywords: 'trading configuration, SMC settings, platform setup',
    url: '/config'
  },
  mfa: {
    title: 'Multi-Factor Authentication',
    description: 'Secure your SMC trading account with multi-factor authentication and advanced security settings.',
    keywords: 'MFA, security, authentication, account protection',
    url: '/mfa',
    noIndex: true
  }
};

// Helper function to get structured data for different page types
export const getStructuredData = (pageType: keyof typeof SEOConfigs, additionalData?: object) => {
  const baseData = {
    '@context': 'https://schema.org',
    '@type': 'WebPage',
    'name': SEOConfigs[pageType].title,
    'description': SEOConfigs[pageType].description,
    'url': `https://smc-trading-agent.vercel.app${SEOConfigs[pageType].url}`,
    'isPartOf': {
      '@type': 'WebSite',
      'name': 'SMC Trading Agent',
      'url': 'https://smc-trading-agent.vercel.app/'
    },
    'author': {
      '@type': 'Organization',
      'name': 'SMC Trading Agent'
    }
  };

  return additionalData ? { ...baseData, ...additionalData } : baseData;
};