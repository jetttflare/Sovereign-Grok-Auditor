# GrokApp README
# ===============

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License">
  <img src="https://img.shields.io/badge/CI-Passing-brightgreen?style=for-the-badge" alt="CI">
  <img src="https://img.shields.io/badge/Coverage-85%25-yellow?style=for-the-badge" alt="Coverage">
</p>

# 🛡️ Sovereign Grok: AI Security Auditor

**Autonomous AI security system that monitors, audits, and self-heals your infrastructure using multi-LLM intelligence.**

## 🌟 Features

- **🔒 Continuous Security Monitoring** - 24/7 scanning of API endpoints, logs, and configurations
- **🧠 Multi-LLM Analysis** - Grok for compliance rules, Gemini for deep reasoning
- **⚡ Self-Healing Actions** - Automatically rotates exposed keys, blocks suspicious IPs
- **📊 Comprehensive Audit Trail** - Every action logged with cryptographic integrity
- **🚨 Intelligent Alerting** - Prometheus-based alerting with Slack/PagerDuty integration
- **🔄 Disaster Recovery** - Automated backups with integrity verification

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose (for containerized deployment)
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/jetttflare/Sovereign-Grok-Auditor.git
cd Sovereign-Grok-Auditor

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with your API keys
```

### Running Locally

```bash
# Run health checks
python -m monitoring.health_checks

# Start the audit logger demo
python -m security.audit_logger

# Run tests
pytest tests/ -v
```

### Docker Deployment

```bash
# Build and start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f grokapi
```

## 📁 Project Structure

```
Sovereign-Grok-Auditor/
├── .github/
│   └── workflows/
│       └── ci.yml              # CI/CD pipeline
├── backup/
│   ├── disaster_recovery.py    # DR management
│   └── service_recovery.py     # Service recovery
├── docs/
│   └── RUNBOOKS.md            # Operational runbooks
├── monitoring/
│   ├── alert-rules.yml        # Prometheus alerts
│   ├── alertmanager.yml       # Alert routing
│   ├── health_checks.py       # Health monitoring
│   ├── metrics_exporter.py    # Prometheus metrics
│   ├── performance.py         # Performance tuning
│   └── prometheus.yml         # Prometheus config
├── nginx/
│   └── nginx.conf             # Reverse proxy
├── scripts/
│   └── deploy.sh              # Deployment script
├── security/
│   └── audit_logger.py        # Audit logging
├── tests/
│   ├── test_audit_logger.py
│   ├── test_disaster_recovery.py
│   ├── test_health_checks.py
│   └── test_performance.py
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

## 🛠️ Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GEMINI_API_KEY` | Google Gemini API key | Yes |
| `GROK_API_KEY` | xAI Grok API key | Yes |
| `SLACK_WEBHOOK_URL` | Slack webhook for alerts | No |
| `PAGERDUTY_SERVICE_KEY` | PagerDuty integration | No |
| `GRAFANA_PASSWORD` | Grafana admin password | No |

### Alert Configuration

Alerts are configured in `monitoring/alert-rules.yml`. Key alerts:

- **GrokAPIDown** - Critical service availability
- **HighAPILatency** - Performance degradation
- **APIKeyExposureDetected** - Security breach
- **BackupMissing** - DR compliance

## 📊 Monitoring Stack

| Service | Port | Description |
|---------|------|-------------|
| GrokAPI | 8080 | Main API server |
| OrbitBridge | 3001 | WebSocket server |
| JobMaster | 5010 | Job scheduler |
| Prometheus | 9090 | Metrics collection |
| Grafana | 3000 | Dashboards |
| Alertmanager | 9093 | Alert routing |

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=. --cov-report=html

# Run specific test file
pytest tests/test_audit_logger.py -v
```

## 📖 Runbooks

Operational runbooks are located in `docs/RUNBOOKS.md`:

- [GrokAPI Down](docs/RUNBOOKS.md#runbook-grok-api-down)
- [API Key Exposure](docs/RUNBOOKS.md#runbook-api-key-exposure)
- [Backup Restore](docs/RUNBOOKS.md#runbook-backup-restore)
- [Disaster Recovery](docs/RUNBOOKS.md#runbook-disaster-recovery)

## 🔒 Security

- All API keys are stored in environment variables
- Audit logs include SHA-256 integrity verification
- TLS 1.2+ required for all connections
- Rate limiting on all public endpoints

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open a Pull Request

## 📞 Support

- **Issues:** [GitHub Issues](https://github.com/jetttflare/Sovereign-Grok-Auditor/issues)
- **Email:** pinojj@aol.com

---

<p align="center">
  Built with ❤️ for the xAI Grokathon 2026
</p>
