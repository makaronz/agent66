# SMC Trading Agent Stream Processor

Real-time Kafka Streams-based data processing system for market data with exactly-once processing semantics.

## Overview

The Stream Processor is a critical component of the SMC Trading Agent that handles:

- **Real-time Data Processing**: Processes market data streams from multiple exchanges
- **Data Enrichment**: Adds technical indicators, volume profiles, and SMC context
- **Pattern Detection**: Identifies Smart Money Concepts patterns in real-time
- **Exactly-Once Semantics**: Ensures data consistency and prevents duplicate processing
- **High Throughput**: Optimized for processing thousands of messages per second

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Kafka Topics  │───▶│  Stream Processor │───▶│  Output Topics  │
│                 │    │                  │    │                 │
│ • Trades        │    │ • Data Enrichment│    │ • Enriched Data │
│ • Orderbook     │    │ • SMC Detection  │    │ • SMC Signals   │
│ • Klines        │    │ • Validation     │    │ • Alerts        │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Features

### Data Processing

- **Trade Data Enrichment**: Adds technical indicators (SMA, VWAP, momentum)
- **Orderbook Analysis**: Calculates liquidity depth, spread, and imbalance
- **Kline Processing**: Derives additional metrics from candlestick data

### SMC Pattern Detection

- **Order Block Detection**: Identifies institutional order blocks
- **Liquidity Zones**: Detects support/resistance levels
- **Fair Value Gaps**: Identifies price gaps in market structure
- **Structure Breaks**: Detects trend reversals and market structure changes

### Processing Guarantees

- **Exactly-Once Processing**: Uses Kafka transactions for data consistency
- **Fault Tolerance**: Automatic recovery from failures
- **Backpressure Handling**: Manages high-volume data streams
- **Circuit Breakers**: Prevents cascade failures

## Configuration

### Environment Variables

```bash
# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=kafka-0:9092,kafka-1:9092,kafka-2:9092
PROCESSOR_ID=stream-processor-1

# Processing Configuration
BATCH_SIZE=100
COMMIT_INTERVAL_MS=5000
MAX_POLL_RECORDS=500

# Monitoring
METRICS_PORT=8080
HEALTH_CHECK_PORT=8081
LOG_LEVEL=INFO
```

### Configuration File

The processor can also be configured via YAML file at `/app/config/streams-config.yaml`:

```yaml
kafka:
  bootstrap_servers:
    - "kafka-0:9092"
    - "kafka-1:9092"
    - "kafka-2:9092"

stream_processors:
  market_data_processor:
    consumer_group: "smc-market-data-processor"
    processing_mode: "exactly_once"
    batch_size: 100
    input_topics:
      - "market_data.binance.btcusdt.trades"
      - "market_data.binance.ethusdt.trades"
    output_topics:
      enriched_trades: "enriched_trades"
      smc_signals: "smc_signals"

monitoring:
  metrics_port: 8080
  health_check_port: 8081
```

## Running the Stream Processor

### Docker

```bash
# Build the image
docker build -f stream_processor.Dockerfile -t smc-trading/stream-processor:latest .

# Run the container
docker run -d \
  --name stream-processor \
  -p 8080:8080 \
  -p 8081:8081 \
  -e KAFKA_BOOTSTRAP_SERVERS=kafka:9092 \
  -e LOG_LEVEL=INFO \
  smc-trading/stream-processor:latest
```

### Kubernetes

```bash
# Deploy to Kubernetes
kubectl apply -f deployment/kubernetes/kafka-streams-deployment.yaml

# Check status
kubectl get pods -l app=kafka-streams -n smc-trading

# View logs
kubectl logs -f deployment/kafka-streams -n smc-trading
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
export LOG_LEVEL=DEBUG

# Run the processor
python stream_processor_main.py
```

## Health Checks

The stream processor provides several health check endpoints:

### Health Check

```bash
curl http://localhost:8081/health
```

Response:

```json
{
  "healthy": true,
  "checks": {
    "processor_market_data_processor": {
      "healthy": true,
      "details": {
        "state": "running",
        "metrics": {
          "messages_processed": 12543,
          "messages_failed": 2,
          "processing_latency_ms": 15.2,
          "throughput_per_second": 850.3
        }
      }
    }
  },
  "uptime_seconds": 3600.5,
  "timestamp": 1703123456.789
}
```

### Readiness Probe

```bash
curl http://localhost:8081/ready
```

### Metrics (Prometheus Format)

```bash
curl http://localhost:8080/metrics
```

## Monitoring

### Key Metrics

- **Processing Latency**: Time to process each message
- **Throughput**: Messages processed per second
- **Error Rate**: Percentage of failed messages
- **Consumer Lag**: Delay in processing messages
- **Pattern Detection Rate**: SMC patterns detected per minute

### Grafana Dashboard

The processor exports metrics in Prometheus format for visualization in Grafana:

- Processing performance metrics
- Error rates and failure patterns
- Consumer lag and throughput
- SMC pattern detection statistics

## Troubleshooting

### Common Issues

1. **High Consumer Lag**

   - Increase number of processor replicas
   - Optimize batch size and commit interval
   - Check for slow downstream systems

2. **Processing Errors**

   - Check Kafka connectivity
   - Verify topic configurations
   - Review error logs for specific failures

3. **Memory Issues**
   - Adjust JVM heap size for Kafka clients
   - Optimize data structures in enrichment logic
   - Monitor memory usage patterns

### Debug Commands

```bash
# Check processor status
kubectl exec -it <pod-name> -- curl localhost:8081/status

# View detailed logs
kubectl logs -f <pod-name> --tail=100

# Check Kafka consumer group status
kafka-consumer-groups.sh --bootstrap-server kafka:9092 --describe --group smc-market-data-processor
```

## Development

### Adding New Processors

1. Create processor configuration in `streams-config.yaml`
2. Implement custom processing logic in `MarketDataEnricher`
3. Add health checks and metrics
4. Update Kubernetes deployment

### Testing

```bash
# Run unit tests
pytest tests/test_stream_processor.py -v

# Run integration tests
pytest tests/integration/test_kafka_integration.py -v

# Load testing
python tests/load_test_stream_processor.py
```

## Performance Tuning

### Kafka Configuration

- Adjust `batch.size` and `linger.ms` for throughput
- Configure `max.poll.records` based on processing capacity
- Tune `fetch.min.bytes` and `fetch.max.wait.ms`

### Processing Optimization

- Use batch processing for database operations
- Implement connection pooling
- Optimize data structures and algorithms
- Consider async processing for I/O operations

### Resource Allocation

- CPU: 1-2 cores per processor instance
- Memory: 2-4GB depending on data volume
- Network: High bandwidth for Kafka communication
- Storage: SSD for temporary data and logs
