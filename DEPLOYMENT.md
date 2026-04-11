# 📋 Deployment Notes

## Step-by-Step Production Deployment

### Prerequisites
1. Ubuntu 20.04+ server
2. Docker & Docker Compose installed
3. Domain name configured (DNS A record pointing to server)
4. SSH access to server

### Initial Server Setup

```bash
# 1. Update system
sudo apt update && sudo apt upgrade -y

# 2. Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 3. Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 4. Install Nginx
sudo apt install nginx -y

# 5. Install Certbot (for SSL)
sudo apt install certbot python3-certbot-nginx -y
```

### Deploy Application

```bash
# 1. Clone repository
git clone https://github.com/yourusername/FIN.git
cd FIN

# 2. Create .env file
cp .env.example .env
nano .env  # Edit with production values

# 3. Run deployment script
./deploy.sh
```

### Configure Nginx

```bash
# 1. Copy nginx config
sudo cp nginx.conf /etc/nginx/sites-available/fin

# 2. Update domain name in config
sudo nano /etc/nginx/sites-available/fin
# Replace 'yourdomain.com' with your actual domain

# 3. Enable site
sudo ln -s /etc/nginx/sites-available/fin /etc/nginx/sites-enabled/

# 4. Test configuration
sudo nginx -t

# 5. Reload Nginx
sudo systemctl reload nginx
```

### Setup SSL Certificate

```bash
# 1. Get Let's Encrypt certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# 2. Test auto-renewal
sudo certbot renew --dry-run

# Certificate will auto-renew every 90 days
```

### Configure GitHub Actions CD

```bash
# 1. Generate SSH key on your local machine
ssh-keygen -t ed25519 -C "github-actions"

# 2. Copy public key to server
ssh-copy-id -i ~/.ssh/id_ed25519.pub user@yourserver.com

# 3. Add secrets to GitHub repository:
# Go to: Settings → Secrets and variables → Actions → New repository secret

# Add these secrets:
# - SSH_PRIVATE_KEY: (content of ~/.ssh/id_ed25519)
# - SERVER_HOST: yourserver.com
# - SERVER_USER: your-username
# - DEPLOY_PATH: /home/user/FIN
```

### Verify Deployment

```bash
# 1. Check services are running
docker-compose ps

# 2. Check health endpoints
curl https://yourdomain.com/health

# 3. Check logs
docker-compose logs -f

# 4. Test API
curl https://yourdomain.com/api/dashboard/1
```

---

## 🚨 Risk Notes - What Can Break in Production

### CRITICAL RISKS

#### 1. Database Migration Failures
**Risk**: Migration fails mid-deployment, leaving database in inconsistent state
**Impact**: Service downtime, data corruption
**Mitigation**:
- Always backup database before deployment
- Test migrations in staging first
- Keep rollback script ready
- Monitor migration logs

#### 2. Race Conditions Under High Load
**Risk**: Despite locks, extreme concurrency might cause deadlocks
**Impact**: Transaction failures, user complaints
**Mitigation**:
- Concurrency tests in CI (already implemented)
- Monitor PostgreSQL for deadlocks
- Set appropriate connection pool size
- Implement retry logic with exponential backoff

#### 3. Redis Failure
**Risk**: Redis crashes, rate limiting and caching fail
**Impact**: Increased database load, potential DDoS
**Mitigation**:
- Redis persistence enabled (RDB + AOF)
- Graceful degradation (fail open for rate limiting)
- Monitor Redis memory usage
- Set up Redis replication for HA

#### 4. SSL Certificate Expiration
**Risk**: Let's Encrypt certificate expires (90 days)
**Impact**: HTTPS stops working, users can't access site
**Mitigation**:
- Certbot auto-renewal configured
- Monitor certificate expiration (30 days warning)
- Test renewal: `sudo certbot renew --dry-run`

#### 5. Disk Space Exhaustion
**Risk**: Logs, backups, or database fill disk
**Impact**: Service crashes, data loss
**Mitigation**:
- Monitor disk usage (alert at 80%)
- Rotate logs (logrotate configured)
- Clean old backups (keep last 7 days)
- Set up automated cleanup

#### 6. Memory Leaks
**Risk**: Python services leak memory over time
**Impact**: OOM kills, service restarts
**Mitigation**:
- Monitor container memory usage
- Set memory limits in docker-compose
- Restart services weekly (maintenance window)
- Profile memory usage in staging

#### 7. Database Connection Pool Exhaustion
**Risk**: All connections used, new requests fail
**Impact**: 500 errors, service degradation
**Mitigation**:
- Connection pool size: 20 (configured)
- Max overflow: 10 (configured)
- Monitor active connections
- Set connection timeout: 30s

#### 8. Nginx Misconfiguration
**Risk**: Wrong proxy settings, headers not forwarded
**Impact**: Authentication fails, IP logging broken
**Mitigation**:
- Test nginx config: `sudo nginx -t`
- Verify headers in logs
- Test with curl -v
- Keep backup of working config

### MEDIUM RISKS

#### 9. Docker Build Failures
**Risk**: Build fails due to network issues, missing dependencies
**Impact**: Deployment blocked, rollback needed
**Mitigation**:
- CD pipeline checks build before restart
- Keep previous images as backup
- Use Docker layer caching
- Pin dependency versions

#### 10. GitHub Actions Quota
**Risk**: CI/CD minutes exhausted
**Impact**: Can't deploy, can't run tests
**Mitigation**:
- Monitor GitHub Actions usage
- Optimize CI pipeline (cache dependencies)
- Consider self-hosted runners for large projects

#### 11. SSH Key Compromise
**Risk**: GitHub Actions SSH key leaked
**Impact**: Unauthorized access to production server
**Mitigation**:
- Rotate SSH keys quarterly
- Use dedicated key for CI/CD (not personal)
- Monitor SSH login attempts
- Enable 2FA on GitHub

#### 12. Environment Variable Leaks
**Risk**: .env file committed to git, secrets exposed
**Impact**: Database compromise, JWT forgery
**Mitigation**:
- .env in .gitignore (already configured)
- Use GitHub Secrets for sensitive data
- Rotate secrets if leaked
- Scan commits for secrets (git-secrets)

### LOW RISKS

#### 13. Time Drift
**Risk**: Server time out of sync
**Impact**: JWT expiration issues, log timestamps wrong
**Mitigation**:
- NTP configured on server
- Monitor time drift
- Use UTC everywhere

#### 14. DNS Propagation Delays
**Risk**: DNS changes take time to propagate
**Impact**: Some users can't access site during migration
**Mitigation**:
- Lower TTL before DNS changes (1 hour)
- Wait 24-48 hours for full propagation
- Keep old server running during transition

#### 15. Docker Hub Rate Limits
**Risk**: Too many image pulls, rate limited
**Impact**: Can't pull base images, build fails
**Mitigation**:
- Use Docker Hub authentication
- Cache images locally
- Consider private registry

---

## 🔍 Monitoring Checklist

### Daily Checks
- [ ] Service health endpoints responding
- [ ] No errors in logs
- [ ] Database connections < 80% of pool
- [ ] Disk usage < 80%
- [ ] Memory usage < 80%

### Weekly Checks
- [ ] Review error logs
- [ ] Check backup integrity
- [ ] Review slow queries
- [ ] Check SSL certificate expiration
- [ ] Review security logs

### Monthly Checks
- [ ] Update dependencies
- [ ] Review and rotate logs
- [ ] Performance testing
- [ ] Disaster recovery drill
- [ ] Security audit

---

## 🆘 Emergency Procedures

### Service Down
```bash
# 1. Check status
docker-compose ps

# 2. Check logs
docker-compose logs --tail=100

# 3. Restart services
docker-compose restart

# 4. If still down, full restart
docker-compose down
docker-compose up -d
```

### Database Corruption
```bash
# 1. Stop services
docker-compose stop gateway transactions ai

# 2. Restore from backup
docker-compose exec -T postgres psql -U finuser financedb < backups/latest.sql

# 3. Restart services
docker-compose start gateway transactions ai
```

### Rollback Deployment
```bash
# 1. Stop services
docker-compose down

# 2. Checkout previous version
git log --oneline  # Find previous commit
git checkout <previous-commit>

# 3. Rebuild and restart
docker-compose build
docker-compose up -d
```

### SSL Certificate Issues
```bash
# 1. Check certificate
sudo certbot certificates

# 2. Force renewal
sudo certbot renew --force-renewal

# 3. Reload Nginx
sudo systemctl reload nginx
```

---

## 📞 Support Contacts

- **DevOps Lead**: [Your contact]
- **Database Admin**: [Your contact]
- **Security Team**: [Your contact]
- **On-Call**: [Your contact]

---

**Remember**: Always test in staging before production. Always have a rollback plan. Always monitor after deployment.
