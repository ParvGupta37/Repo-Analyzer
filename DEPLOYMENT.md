# Deployment Guide

## Production Deployment Options

### Option 1: Docker Deployment (Recommended)

#### 1. Create Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/api/health')"

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

#### 2. Create docker-compose.yml
```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - GITHUB_TOKEN=${GITHUB_TOKEN}
      - SENTRY_DSN=${SENTRY_DSN}
    volumes:
      - ./app.db:/app/app.db
    restart: unless-stopped
    
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    restart: unless-stopped
```

#### 3. Deploy
```bash
docker-compose up -d
```

---

### Option 2: Cloud Platform Deployment

#### Heroku
```bash
# Install Heroku CLI
heroku login
heroku create repo-analyzer

# Set environment variables
heroku config:set GEMINI_API_KEY=your_key
heroku config:set GITHUB_TOKEN=your_token

# Deploy
git push heroku main
```

#### AWS EC2
```bash
# SSH into EC2 instance
ssh -i your-key.pem ubuntu@your-instance-ip

# Install dependencies
sudo apt update
sudo apt install python3-pip python3-venv nginx

# Clone repository
git clone https://github.com/your-username/Repo-Analyzer.git
cd Repo-Analyzer

# Setup virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env  # Edit with your keys

# Run with systemd
sudo nano /etc/systemd/system/repo-analyzer.service
```

**systemd service file:**
```ini
[Unit]
Description=GitHub Repository Analyzer
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/Repo-Analyzer
Environment="PATH=/home/ubuntu/Repo-Analyzer/venv/bin"
ExecStart=/home/ubuntu/Repo-Analyzer/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Start service
sudo systemctl daemon-reload
sudo systemctl enable repo-analyzer
sudo systemctl start repo-analyzer
```

#### Google Cloud Run
```bash
# Build and push container
gcloud builds submit --tag gcr.io/PROJECT_ID/repo-analyzer

# Deploy
gcloud run deploy repo-analyzer \
  --image gcr.io/PROJECT_ID/repo-analyzer \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY=your_key
```

---

### Option 3: Traditional Server Deployment

#### Using Nginx + Gunicorn

**1. Install Nginx**
```bash
sudo apt install nginx
```

**2. Configure Nginx**
```nginx
# /etc/nginx/sites-available/repo-analyzer
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

**3. Enable site**
```bash
sudo ln -s /etc/nginx/sites-available/repo-analyzer /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

**4. SSL with Let's Encrypt**
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

---

## Environment Configuration

### Production .env
```env
# API Keys
GEMINI_API_KEY=your_production_key
GITHUB_TOKEN=your_production_token
SENTRY_DSN=your_sentry_dsn

# Server
HOST=0.0.0.0
PORT=8000

# Database
DATABASE_URL=postgresql://user:pass@localhost/repo_analyzer

# Cache
REDIS_URL=redis://localhost:6379
CACHE_TTL=3600

# Rate Limiting
RATE_LIMIT_PER_MINUTE=20

# Logging
LOG_LEVEL=INFO
```

---

## Database Migration

### From SQLite to PostgreSQL

**1. Install PostgreSQL**
```bash
sudo apt install postgresql postgresql-contrib
```

**2. Create database**
```sql
CREATE DATABASE repo_analyzer;
CREATE USER analyzer WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE repo_analyzer TO analyzer;
```

**3. Update database.py**
```python
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://analyzer:password@localhost/repo_analyzer")
```

**4. Run migrations**
```bash
alembic upgrade head
```

---

## Monitoring Setup

### Sentry Integration
```python
# Already integrated in main.py
import sentry_sdk

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    traces_sample_rate=1.0
)
```

### Prometheus Metrics (Optional)
```bash
pip install prometheus-fastapi-instrumentator
```

```python
from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator().instrument(app).expose(app)
```

---

## Performance Tuning

### 1. Worker Configuration
```bash
# For CPU-bound tasks
uvicorn main:app --workers 4

# For I/O-bound tasks (recommended)
uvicorn main:app --workers 8
```

### 2. Database Connection Pool
```python
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=10
)
```

### 3. Redis Caching
```python
# Update cache_service.py to use Redis
import aioredis

redis = await aioredis.create_redis_pool('redis://localhost')
```

---

## Security Checklist

- [ ] Change default rate limits
- [ ] Configure CORS for specific origins
- [ ] Enable HTTPS only
- [ ] Set secure environment variables
- [ ] Enable Sentry error tracking
- [ ] Configure firewall rules
- [ ] Regular dependency updates
- [ ] Database backups
- [ ] API authentication (if needed)
- [ ] Input validation on all endpoints

---

## Backup Strategy

### Database Backup
```bash
# SQLite
cp app.db app.db.backup.$(date +%Y%m%d)

# PostgreSQL
pg_dump repo_analyzer > backup.sql
```

### Automated Backups
```bash
# Add to crontab
0 2 * * * /path/to/backup-script.sh
```

---

## Troubleshooting

### High Memory Usage
- Reduce worker count
- Implement cache eviction
- Check for memory leaks

### Slow Response Times
- Enable Redis caching
- Optimize database queries
- Add database indexes

### WebSocket Disconnections
- Check nginx timeout settings
- Increase keep-alive timeout
- Verify firewall rules

---

## Scaling Recommendations

### < 100 users
- Single server
- SQLite database
- In-memory cache

### 100-1000 users
- Load balancer + 2-3 servers
- PostgreSQL database
- Redis cache

### 1000+ users
- Kubernetes cluster
- Separate analysis workers
- Message queue (Celery + RabbitMQ)
- CDN for static assets

---

## Cost Estimation

### Small Scale (< 100 analyses/day)
- **Server**: $5-10/month (DigitalOcean, Linode)
- **Gemini API**: ~$5/month
- **Total**: ~$15/month

### Medium Scale (100-1000 analyses/day)
- **Servers**: $50-100/month
- **Database**: $15/month
- **Gemini API**: ~$50/month
- **Total**: ~$115/month

### Large Scale (1000+ analyses/day)
- **Infrastructure**: $500+/month
- **Gemini API**: $500+/month
- **Total**: $1000+/month
