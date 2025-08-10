import { useState } from 'react';
import {
  BookOpen,
  Search,
  Filter,
  TrendingUp,
  Target,
  Eye,
  Play,
  Download,
  Star,
  Clock,
  Users,
  ExternalLink
} from 'lucide-react';
import { cn } from '@/lib/utils';

const smcPatterns = [
  {
    id: 1,
    name: 'Order Block',
    category: 'Support/Resistance',
    description: 'Areas where large institutional orders were placed, creating significant support or resistance levels.',
    reliability: 85,
    difficulty: 'Beginner',
    timeframes: ['1H', '4H', '1D'],
    examples: 12,
    successRate: 78,
    image: 'order-block.png'
  },
  {
    id: 2,
    name: 'Fair Value Gap (FVG)',
    category: 'Imbalance',
    description: 'Price gaps that represent imbalances in the market, often filled by institutional traders.',
    reliability: 92,
    difficulty: 'Intermediate',
    timeframes: ['15M', '1H', '4H'],
    examples: 18,
    successRate: 82,
    image: 'fvg.png'
  },
  {
    id: 3,
    name: 'Break of Structure (BOS)',
    category: 'Trend Change',
    description: 'When price breaks through a significant high or low, indicating a potential trend change.',
    reliability: 88,
    difficulty: 'Beginner',
    timeframes: ['1H', '4H', '1D'],
    examples: 15,
    successRate: 75,
    image: 'bos.png'
  },
  {
    id: 4,
    name: 'Change of Character (CHoCH)',
    category: 'Trend Change',
    description: 'A shift in market structure indicating institutional sentiment change.',
    reliability: 90,
    difficulty: 'Advanced',
    timeframes: ['4H', '1D', '1W'],
    examples: 8,
    successRate: 85,
    image: 'choch.png'
  },
  {
    id: 5,
    name: 'Liquidity Sweep',
    category: 'Liquidity',
    description: 'When price moves to collect liquidity from stop losses before reversing direction.',
    reliability: 87,
    difficulty: 'Intermediate',
    timeframes: ['15M', '1H', '4H'],
    examples: 22,
    successRate: 80,
    image: 'liquidity-sweep.png'
  },
  {
    id: 6,
    name: 'Inducement',
    category: 'Manipulation',
    description: 'False breakouts designed to trap retail traders before the real move occurs.',
    reliability: 83,
    difficulty: 'Advanced',
    timeframes: ['1H', '4H'],
    examples: 10,
    successRate: 77,
    image: 'inducement.png'
  }
];

const educationalContent = [
  {
    id: 1,
    title: 'Introduction to Smart Money Concepts',
    type: 'Course',
    duration: '2h 30m',
    level: 'Beginner',
    rating: 4.8,
    students: 1250,
    description: 'Learn the fundamentals of institutional trading and market structure.',
    topics: ['Market Structure', 'Institutional vs Retail', 'Order Flow', 'Liquidity Concepts']
  },
  {
    id: 2,
    title: 'Advanced Order Block Trading',
    type: 'Masterclass',
    duration: '1h 45m',
    level: 'Advanced',
    rating: 4.9,
    students: 890,
    description: 'Deep dive into order block identification and trading strategies.',
    topics: ['Order Block Types', 'Entry Techniques', 'Risk Management', 'Case Studies']
  },
  {
    id: 3,
    title: 'Fair Value Gap Mastery',
    type: 'Workshop',
    duration: '3h 15m',
    level: 'Intermediate',
    rating: 4.7,
    students: 675,
    description: 'Complete guide to trading Fair Value Gaps effectively.',
    topics: ['FVG Identification', 'Entry Strategies', 'Multiple Timeframe Analysis']
  },
  {
    id: 4,
    title: 'Market Structure Analysis',
    type: 'Course',
    duration: '4h 20m',
    level: 'Intermediate',
    rating: 4.6,
    students: 1100,
    description: 'Understanding how institutions move the market.',
    topics: ['Structure Breaks', 'Trend Analysis', 'Support & Resistance']
  }
];

const marketInsights = [
  {
    id: 1,
    title: 'Weekly Market Structure Analysis',
    author: 'SMC Research Team',
    date: '2 days ago',
    readTime: '5 min',
    category: 'Analysis',
    excerpt: 'Key levels and structure changes across major currency pairs this week.',
    tags: ['EURUSD', 'GBPUSD', 'Market Structure']
  },
  {
    id: 2,
    title: 'Institutional Order Flow Patterns in Gold',
    author: 'Dr. Sarah Chen',
    date: '1 week ago',
    readTime: '8 min',
    category: 'Research',
    excerpt: 'Analysis of recent institutional activity in precious metals markets.',
    tags: ['XAUUSD', 'Order Flow', 'Institutions']
  },
  {
    id: 3,
    title: 'Central Bank Policy Impact on SMC Patterns',
    author: 'Michael Rodriguez',
    date: '2 weeks ago',
    readTime: '12 min',
    category: 'Fundamental',
    excerpt: 'How monetary policy decisions affect smart money concepts.',
    tags: ['Central Banks', 'Policy', 'Market Impact']
  }
];

export default function Research() {
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [, setSelectedPattern] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState('patterns');

  const categories = ['all', 'Support/Resistance', 'Imbalance', 'Trend Change', 'Liquidity', 'Manipulation'];

  const filteredPatterns = smcPatterns.filter(pattern => {
    const matchesCategory = selectedCategory === 'all' || pattern.category === selectedCategory;
    const matchesSearch = pattern.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         pattern.description.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty) {
      case 'Beginner':
        return 'text-green-600 bg-green-100';
      case 'Intermediate':
        return 'text-yellow-600 bg-yellow-100';
      case 'Advanced':
        return 'text-red-600 bg-red-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const getReliabilityColor = (reliability: number) => {
    if (reliability >= 90) return 'text-green-600';
    if (reliability >= 80) return 'text-yellow-600';
    return 'text-red-600';
  };

  const tabs = [
    { id: 'patterns', name: 'SMC Patterns', icon: Target },
    { id: 'education', name: 'Education', icon: BookOpen },
    { id: 'insights', name: 'Market Insights', icon: TrendingUp }
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Research Center</h1>
          <p className="text-gray-600">SMC pattern library, educational resources, and market insights</p>
        </div>
        <div className="flex items-center space-x-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search patterns, courses..."
              value={searchTerm}
              onChange={(e) => { setSearchTerm(e.target.value); }}
              className="pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 w-64"
            />
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => { setActiveTab(tab.id); }}
                className={cn(
                  "flex items-center space-x-2 py-2 px-1 border-b-2 font-medium text-sm transition-colors",
                  activeTab === tab.id
                    ? "border-blue-500 text-blue-600"
                    : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                )}
              >
                <Icon className="h-4 w-4" />
                <span>{tab.name}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* SMC Patterns Tab */}
      {activeTab === 'patterns' && (
        <div className="space-y-6">
          {/* Category Filter */}
          <div className="flex items-center space-x-4">
            <Filter className="h-5 w-5 text-gray-400" />
            <div className="flex flex-wrap gap-2">
              {categories.map((category) => (
                <button
                  key={category}
                  onClick={() => { setSelectedCategory(category); }}
                  className={cn(
                    "px-3 py-1 text-sm font-medium rounded-full transition-colors",
                    selectedCategory === category
                      ? "bg-blue-600 text-white"
                      : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                  )}
                >
                  {category === 'all' ? 'All Categories' : category}
                </button>
              ))}
            </div>
          </div>

          {/* Patterns Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredPatterns.map((pattern) => (
              <div key={pattern.id} className="bg-white rounded-lg shadow hover:shadow-lg transition-shadow">
                <div className="p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900">{pattern.name}</h3>
                      <p className="text-sm text-gray-600">{pattern.category}</p>
                    </div>
                    <div className="flex items-center space-x-1">
                      <Star className="h-4 w-4 text-yellow-400 fill-current" />
                      <span className={cn("text-sm font-medium", getReliabilityColor(pattern.reliability))}>
                        {pattern.reliability}%
                      </span>
                    </div>
                  </div>

                  <p className="text-sm text-gray-700 mb-4 line-clamp-3">{pattern.description}</p>

                  <div className="flex items-center justify-between mb-4">
                    <span className={cn(
                      "px-2 py-1 text-xs font-medium rounded-full",
                      getDifficultyColor(pattern.difficulty)
                    )}>
                      {pattern.difficulty}
                    </span>
                    <div className="flex items-center space-x-1 text-sm text-gray-600">
                      <Eye className="h-4 w-4" />
                      <span>{pattern.examples} examples</span>
                    </div>
                  </div>

                  <div className="flex items-center justify-between mb-4">
                    <div className="flex space-x-1">
                      {pattern.timeframes.map((tf) => (
                        <span key={tf} className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded">
                          {tf}
                        </span>
                      ))}
                    </div>
                    <div className="flex items-center space-x-1 text-sm text-green-600">
                      <TrendingUp className="h-4 w-4" />
                      <span>{pattern.successRate}%</span>
                    </div>
                  </div>

                  <div className="flex space-x-2">
                    <button
                      onClick={() => { setSelectedPattern(pattern.id); }}
                      className="flex-1 flex items-center justify-center space-x-2 px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-md transition-colors"
                    >
                      <Play className="h-4 w-4" />
                      <span>Learn More</span>
                    </button>
                    <button className="flex items-center justify-center px-3 py-2 border border-gray-300 hover:bg-gray-50 text-gray-700 text-sm font-medium rounded-md transition-colors">
                      <Download className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Education Tab */}
      {activeTab === 'education' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {educationalContent.map((content) => (
              <div key={content.id} className="bg-white rounded-lg shadow hover:shadow-lg transition-shadow">
                <div className="p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900">{content.title}</h3>
                      <div className="flex items-center space-x-4 mt-2">
                        <span className="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded-full">
                          {content.type}
                        </span>
                        <span className={cn(
                          "px-2 py-1 text-xs rounded-full",
                          getDifficultyColor(content.level)
                        )}>
                          {content.level}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center space-x-1">
                      <Star className="h-4 w-4 text-yellow-400 fill-current" />
                      <span className="text-sm font-medium text-gray-700">{content.rating}</span>
                    </div>
                  </div>

                  <p className="text-sm text-gray-700 mb-4">{content.description}</p>

                  <div className="flex items-center space-x-4 mb-4 text-sm text-gray-600">
                    <div className="flex items-center space-x-1">
                      <Clock className="h-4 w-4" />
                      <span>{content.duration}</span>
                    </div>
                    <div className="flex items-center space-x-1">
                      <Users className="h-4 w-4" />
                      <span>{content.students.toLocaleString()} students</span>
                    </div>
                  </div>

                  <div className="mb-4">
                    <h4 className="text-sm font-medium text-gray-900 mb-2">Topics Covered:</h4>
                    <div className="flex flex-wrap gap-1">
                      {content.topics.map((topic, index) => (
                        <span key={index} className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded">
                          {topic}
                        </span>
                      ))}
                    </div>
                  </div>

                  <button className="w-full flex items-center justify-center space-x-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-md transition-colors">
                    <Play className="h-4 w-4" />
                    <span>Start Learning</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Market Insights Tab */}
      {activeTab === 'insights' && (
        <div className="space-y-6">
          <div className="space-y-4">
            {marketInsights.map((insight) => (
              <div key={insight.id} className="bg-white rounded-lg shadow hover:shadow-lg transition-shadow">
                <div className="p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3 mb-2">
                        <h3 className="text-lg font-semibold text-gray-900">{insight.title}</h3>
                        <span className="px-2 py-1 text-xs bg-purple-100 text-purple-800 rounded-full">
                          {insight.category}
                        </span>
                      </div>
                      
                      <p className="text-gray-700 mb-4">{insight.excerpt}</p>
                      
                      <div className="flex items-center space-x-4 text-sm text-gray-600 mb-4">
                        <span>By {insight.author}</span>
                        <span>•</span>
                        <span>{insight.date}</span>
                        <span>•</span>
                        <div className="flex items-center space-x-1">
                          <Clock className="h-4 w-4" />
                          <span>{insight.readTime} read</span>
                        </div>
                      </div>
                      
                      <div className="flex flex-wrap gap-2 mb-4">
                        {insight.tags.map((tag, index) => (
                          <span key={index} className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded">
                            #{tag}
                          </span>
                        ))}
                      </div>
                    </div>
                    
                    <button className="flex items-center space-x-2 px-4 py-2 text-blue-600 hover:bg-blue-50 text-sm font-medium rounded-md transition-colors">
                      <span>Read More</span>
                      <ExternalLink className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}