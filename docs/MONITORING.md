# Monitoring Setup Guide

Complete guide for setting up Prometheus and Grafana monitoring for DJ Shorts Analyzer.

## 🎯 Overview

The monitoring stack includes:
- **Prometheus**: Metrics collection and storage
- **Grafana**: Visualization and dashboards
- **Analyzer**: Metrics generation

## 🚀 Quick Start

```bash
# Start all services
docker-compose up -d

# Check services are running
docker-compose ps

# Access Grafana
open http://localhost:3000
# Login: admin / admin

# Access Prometheus
open http://localhost:9090
```

## 📦 Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Docker Compose                      │
│                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐│
│  │   Analyzer   │  │  Prometheus  │  │  Grafana  ││
│  │              │  │   :9090      │  │   :3000   ││
│  │  Generates   │─>│  Collects    │─>│ Visualizes││
│  │  Metrics     │  │  Metrics     │  │ Dashboards││
│  └──────────────┘  └──────────────┘  └───────────┘│
│                                                      │
│  Volumes:                                           │
│  • prometheus_data (metrics storage)                │
│  • grafana_data (dashboards, settings)              │
│  • ./data (video files)                             │
│  • ./clips (output clips)                           │
│  • ./metrics (metrics files)                        │
└─────────────────────────────────────────────────────┘
```

## 🛠️ Setup

### Prerequisites

- Docker and Docker Compose installed
- At least 4GB RAM available
- 10GB disk space for metrics storage

### Installation

```bash
# Clone repository
git clone https://github.com/dj-shorts/analyzer.git
cd analyzer

# Start monitoring stack
docker-compose up -d

# View logs
docker-compose logs -f
```

### Initial Configuration

1. **Access Grafana**: http://localhost:3000
   - Username: `admin`
   - Password: `admin`
   - Change password on first login

2. **Verify Prometheus datasource**:
   - Go to Configuration → Data Sources
   - Should see "Prometheus" as default datasource
   - Test connection

3. **View Dashboard**:
   - Go to Dashboards → Browse
   - Open "DJ Shorts Analyzer Overview"

## 📊 Dashboards

### Analyzer Overview Dashboard

Pre-configured dashboard showing:

#### Processing Metrics
- **Processing Time**: Total time to analyze videos
- **Clips Generated**: Number of clips created
- **Success Rate**: Percentage of successful analyses

#### Resource Metrics
- **Memory Usage**: RAM consumption during processing
- **CPU Usage**: CPU utilization percentage
- **Disk I/O**: Read/write operations

#### Stage Timings
- **Audio Extraction**: Time spent extracting audio
- **Beat Detection**: Time for beat analysis
- **Motion Analysis**: Time for motion detection
- **Video Export**: Time exporting final clips

### Creating Custom Dashboards

```json
// Example panel configuration
{
  "title": "Average Processing Time",
  "type": "graph",
  "targets": [
    {
      "expr": "rate(analyzer_processing_time_seconds[5m])",
      "legendFormat": "Avg Time"
    }
  ]
}
```

## 🔧 Configuration

### Prometheus Configuration

Edit `prometheus/prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'analyzer'
    scrape_interval: 15s  # Adjust based on needs
    static_configs:
      - targets: ['analyzer:8000']
```

### Grafana Configuration

Environment variables in `docker-compose.yml`:

```yaml
environment:
  - GF_SECURITY_ADMIN_USER=admin
  - GF_SECURITY_ADMIN_PASSWORD=admin
  - GF_USERS_ALLOW_SIGN_UP=false
  - GF_SERVER_ROOT_URL=http://localhost:3000
```

### Retention Policy

Prometheus retention (in `docker-compose.yml`):

```yaml
command:
  - '--storage.tsdb.retention.time=30d'  # Keep 30 days
  - '--storage.tsdb.retention.size=10GB' # Max 10GB
```

## 📈 Metrics Reference

### Current Metrics (from Epic G1)

| Metric | Type | Description |
|--------|------|-------------|
| `analyzer_processing_time_seconds` | Gauge | Total processing time |
| `analyzer_clips_generated_total` | Counter | Number of clips created |
| `analyzer_stage_duration_seconds` | Gauge | Per-stage timing |
| `analyzer_memory_usage_bytes` | Gauge | Memory consumption |
| `analyzer_cpu_usage_percent` | Gauge | CPU utilization |

### Labels

All metrics include these labels:
- `video_id`: Unique video identifier
- `format`: Output format (original/vertical/square)
- `stage`: Processing stage (audio/beat/motion/export)

### Example Queries

```promql
# Average processing time over 5 minutes
rate(analyzer_processing_time_seconds[5m])

# Total clips generated
sum(analyzer_clips_generated_total)

# Memory usage by video
analyzer_memory_usage_bytes{video_id="video_123"}

# 95th percentile processing time
histogram_quantile(0.95, analyzer_processing_time_seconds)
```

## 🔄 Running Analysis with Monitoring

### Basic Analysis

```bash
# Run analyzer with metrics
docker-compose run --rm analyzer \
  analyzer /data/video.mp4 \
    --clips 3 \
    --export-video \
    --metrics /metrics/analysis.txt
```

### Batch Processing

```bash
# Process multiple videos
for video in data/*.mp4; do
  docker-compose run --rm analyzer \
    analyzer "/data/$(basename $video)" \
      --clips 6 \
      --export-video \
      --metrics "/metrics/$(basename $video .mp4).txt"
done
```

### View Metrics in Grafana

1. Wait ~30 seconds for Prometheus to scrape
2. Open Grafana dashboard
3. Select time range
4. View metrics for your analysis

## 🐛 Troubleshooting

### Prometheus not collecting metrics

```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# View Prometheus logs
docker-compose logs prometheus

# Verify metrics file exists
ls -la metrics/
```

### Grafana dashboard not loading

```bash
# Check Grafana logs
docker-compose logs grafana

# Verify datasource connection
curl http://localhost:3000/api/datasources

# Restart Grafana
docker-compose restart grafana
```

### Services not starting

```bash
# Check all services
docker-compose ps

# View all logs
docker-compose logs

# Restart everything
docker-compose down && docker-compose up -d
```

### High memory usage

```bash
# Check resource usage
docker stats

# Limit Prometheus memory
# Edit docker-compose.yml:
services:
  prometheus:
    deploy:
      resources:
        limits:
          memory: 2G
```

## 🔒 Security

### Change Default Passwords

```bash
# Grafana password via environment
export GF_SECURITY_ADMIN_PASSWORD=your_secure_password
docker-compose up -d
```

### Enable HTTPS

```yaml
# Add to grafana service in docker-compose.yml
environment:
  - GF_SERVER_PROTOCOL=https
  - GF_SERVER_CERT_FILE=/etc/ssl/certs/grafana.crt
  - GF_SERVER_CERT_KEY=/etc/ssl/certs/grafana.key
volumes:
  - ./ssl:/etc/ssl/certs
```

### Network Isolation

```yaml
# Add to docker-compose.yml
networks:
  monitoring:
    driver: bridge
    internal: true  # No external access
```

## 📊 Performance Tips

### Optimize Scrape Interval

```yaml
# For development (fast feedback)
scrape_interval: 5s

# For production (reduce load)
scrape_interval: 30s
```

### Reduce Data Retention

```yaml
# Keep less data for better performance
command:
  - '--storage.tsdb.retention.time=7d'
  - '--storage.tsdb.retention.size=5GB'
```

### Use Recording Rules

Create `prometheus/rules.yml`:

```yaml
groups:
  - name: analyzer
    interval: 1m
    rules:
      - record: analyzer:processing_time:rate5m
        expr: rate(analyzer_processing_time_seconds[5m])
```

## 🚀 Advanced Usage

### Alert Rules

Create `prometheus/alerts.yml`:

```yaml
groups:
  - name: analyzer_alerts
    rules:
      - alert: HighProcessingTime
        expr: analyzer_processing_time_seconds > 600
        for: 5m
        annotations:
          summary: "Processing taking too long"
```

### Multiple Environments

```yaml
# docker-compose.prod.yml
services:
  prometheus:
    volumes:
      - ./prometheus/prometheus.prod.yml:/etc/prometheus/prometheus.yml
```

### External Prometheus

Point to external Prometheus instead of local:

```yaml
# grafana datasource
datasources:
  - name: Prometheus
    url: https://prometheus.example.com
```

## 🔗 Related Documentation

- [Docker Guide](./DOCKER.md) - Container usage
- [Setup Guide](./SETUP.md) - Installation
- [Metrics Documentation](../src/analyzer/metrics.py) - Metrics implementation

## 📚 References

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)

