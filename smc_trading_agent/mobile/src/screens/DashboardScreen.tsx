import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  RefreshControl,
  Dimensions,
  TouchableOpacity,
} from 'react-native';
import { LineChart } from 'react-native-chart-kit';
import { Ionicons } from '@expo/vector-icons';

import { TradingService } from '../services/TradingService';
import { WebSocketService } from '../services/WebSocketService';

const { width: screenWidth } = Dimensions.get('window');

interface DashboardData {
  totalBalance: number;
  totalPnL: number;
  totalPnLPercent: number;
  activePositions: number;
  todayTrades: number;
  winRate: number;
  equityData: any[];
  recentActivity: any[];
}

export default function DashboardScreen() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    fetchData();
    setupWebSocket();

    return () => {
      WebSocketService.unsubscribe('dashboard');
    };
  }, []);

  const setupWebSocket = () => {
    WebSocketService.subscribe('dashboard', (message) => {
      if (message.type === 'UPDATE') {
        setData(prev => prev ? { ...prev, ...message.data } : null);
      }
    });
  };

  const fetchData = async () => {
    try {
      setLoading(true);
      const dashboardData = await TradingService.getDashboardData();
      setData(dashboardData);
    } catch (error) {
      console.error('Dashboard fetch error:', error);
    } finally {
      setLoading(false);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await fetchData();
    setRefreshing(false);
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(value);
  };

  const formatPercent = (value: number) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  if (loading || !data) {
    return (
      <View style={styles.loadingContainer}>
        <Ionicons name="analytics-outline" size={48} color="#10b981" />
        <Text style={styles.loadingText}>Loading Dashboard...</Text>
      </View>
    );
  }

  const chartConfig = {
    backgroundColor: '#ffffff',
    backgroundGradientFrom: '#ffffff',
    backgroundGradientTo: '#ffffff',
    decimalPlaces: 2,
    color: (opacity = 1) => `rgba(16, 185, 129, ${opacity})`,
    labelColor: (opacity = 1) => `rgba(107, 114, 128, ${opacity})`,
    style: {
      borderRadius: 16,
    },
    propsForDots: {
      r: '4',
      strokeWidth: '2',
      stroke: '#10b981',
    },
  };

  return (
    <ScrollView
      style={styles.container}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
      }
    >
      {/* Header */}
      <View style={styles.header}>
        <View>
          <Text style={styles.headerTitle}>SMC Trading Agent</Text>
          <Text style={styles.headerSubtitle}>Real-time Trading Dashboard</Text>
        </View>
        <TouchableOpacity style={styles.notificationButton}>
          <Ionicons name="notifications-outline" size={24} color="#374151" />
        </TouchableOpacity>
      </View>

      {/* Portfolio Summary */}
      <View style={styles.summaryCard}>
        <View style={styles.summaryRow}>
          <View style={styles.summaryItem}>
            <Text style={styles.summaryLabel}>Total Balance</Text>
            <Text style={styles.summaryValue}>{formatCurrency(data.totalBalance)}</Text>
          </View>
          <View style={styles.summaryItem}>
            <Text style={styles.summaryLabel}>Today's P&L</Text>
            <Text style={[
              styles.summaryValue,
              { color: data.totalPnL >= 0 ? '#10b981' : '#ef4444' }
            ]}>
              {formatCurrency(data.totalPnL)}
            </Text>
          </View>
        </View>
        <View style={styles.summaryRow}>
          <View style={styles.summaryItem}>
            <Text style={styles.summaryLabel}>P&L %</Text>
            <Text style={[
              styles.summaryValue,
              { color: data.totalPnLPercent >= 0 ? '#10b981' : '#ef4444' }
            ]}>
              {formatPercent(data.totalPnLPercent)}
            </Text>
          </View>
          <View style={styles.summaryItem}>
            <Text style={styles.summaryLabel}>Win Rate</Text>
            <Text style={styles.summaryValue}>{formatPercent(data.winRate)}</Text>
          </View>
        </View>
      </View>

      {/* Quick Stats */}
      <View style={styles.quickStats}>
        <View style={styles.statItem}>
          <Ionicons name="trending-up-outline" size={24} color="#3b82f6" />
          <Text style={styles.statValue}>{data.activePositions}</Text>
          <Text style={styles.statLabel}>Active Positions</Text>
        </View>
        <View style={styles.statItem}>
          <Ionicons name="swap-horizontal-outline" size={24} color="#8b5cf6" />
          <Text style={styles.statValue}>{data.todayTrades}</Text>
          <Text style={styles.statLabel}>Today's Trades</Text>
        </View>
        <View style={styles.statItem}>
          <Ionicons name="checkmark-circle-outline" size={24} color="#10b981" />
          <Text style={styles.statValue}>{Math.round(data.winRate)}%</Text>
          <Text style={styles.statLabel}>Success Rate</Text>
        </View>
      </View>

      {/* Equity Chart */}
      <View style={styles.chartCard}>
        <Text style={styles.chartTitle}>Portfolio Performance</Text>
        {data.equityData && data.equityData.length > 0 ? (
          <LineChart
            data={{
              labels: data.equityData.map((_, index) => index),
              datasets: [{
                data: data.equityData.map(point => point.value),
              }]
            }}
            width={screenWidth - 32}
            height={220}
            chartConfig={chartConfig}
            bezier
            style={styles.chart}
          />
        ) : (
          <View style={styles.noDataContainer}>
            <Ionicons name="bar-chart-outline" size={48} color="#d1d5db" />
            <Text style={styles.noDataText}>No chart data available</Text>
          </View>
        )}
      </View>

      {/* Recent Activity */}
      <View style={styles.activityCard}>
        <Text style={styles.activityTitle}>Recent Activity</Text>
        {data.recentActivity && data.recentActivity.length > 0 ? (
          data.recentActivity.map((activity, index) => (
            <View key={index} style={styles.activityItem}>
              <View style={[
                styles.activityIcon,
                { backgroundColor: activity.type === 'BUY' ? '#10b981' : '#ef4444' }
              ]}>
                <Ionicons
                  name={activity.type === 'BUY' ? 'arrow-up' : 'arrow-down'}
                  size={16}
                  color="#ffffff"
                />
              </View>
              <View style={styles.activityContent}>
                <Text style={styles.activityText}>
                  {activity.type} {activity.symbol}
                </Text>
                <Text style={styles.activitySubtext}>
                  {formatCurrency(activity.price)} • {activity.quantity} units
                </Text>
              </View>
              <Text style={[
                styles.activityPnL,
                { color: activity.pnl >= 0 ? '#10b981' : '#ef4444' }
              ]}>
                {formatCurrency(activity.pnl)}
              </Text>
            </View>
          ))
        ) : (
          <View style={styles.noDataContainer}>
            <Ionicons name="time-outline" size={48} color="#d1d5db" />
            <Text style={styles.noDataText}>No recent activity</Text>
          </View>
        )}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f9fafb',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#ffffff',
  },
  loadingText: {
    marginTop: 16,
    fontSize: 16,
    color: '#6b7280',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingTop: 16,
    paddingBottom: 8,
    backgroundColor: '#ffffff',
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#1f2937',
  },
  headerSubtitle: {
    fontSize: 14,
    color: '#6b7280',
    marginTop: 4,
  },
  notificationButton: {
    padding: 8,
  },
  summaryCard: {
    backgroundColor: '#ffffff',
    margin: 16,
    padding: 20,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  summaryRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 16,
  },
  summaryRow:lastChild: {
    marginBottom: 0,
  },
  summaryItem: {
    flex: 1,
  },
  summaryLabel: {
    fontSize: 14,
    color: '#6b7280',
    marginBottom: 4,
  },
  summaryValue: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#1f2937',
  },
  quickStats: {
    flexDirection: 'row',
    marginHorizontal: 16,
    marginBottom: 16,
  },
  statItem: {
    flex: 1,
    backgroundColor: '#ffffff',
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
    marginHorizontal: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  statValue: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#1f2937',
    marginVertical: 4,
  },
  statLabel: {
    fontSize: 12,
    color: '#6b7280',
    textAlign: 'center',
  },
  chartCard: {
    backgroundColor: '#ffffff',
    margin: 16,
    padding: 20,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  chartTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#1f2937',
    marginBottom: 16,
  },
  chart: {
    marginVertical: 8,
    borderRadius: 16,
  },
  activityCard: {
    backgroundColor: '#ffffff',
    margin: 16,
    padding: 20,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  activityTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#1f2937',
    marginBottom: 16,
  },
  activityItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#f3f4f6',
  },
  activityItem:lastChild: {
    borderBottomWidth: 0,
  },
  activityIcon: {
    width: 32,
    height: 32,
    borderRadius: 16,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  activityContent: {
    flex: 1,
  },
  activityText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#1f2937',
    marginBottom: 2,
  },
  activitySubtext: {
    fontSize: 12,
    color: '#6b7280',
  },
  activityPnL: {
    fontSize: 14,
    fontWeight: '600',
  },
  noDataContainer: {
    alignItems: 'center',
    paddingVertical: 32,
  },
  noDataText: {
    marginTop: 8,
    fontSize: 14,
    color: '#9ca3af',
  },
});