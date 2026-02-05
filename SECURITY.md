# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security issue, please report it responsibly.

### How to Report

1. **Do NOT open a public GitHub issue** for security vulnerabilities
2. Email your findings to: security@YOUR_DOMAIN.com (or use GitHub's private vulnerability reporting)
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Any suggested fixes (optional)

### What to Expect

- **Acknowledgment**: Within 48 hours of your report
- **Initial Assessment**: Within 7 days
- **Resolution Timeline**: Depends on severity
  - Critical: 7 days
  - High: 14 days
  - Medium: 30 days
  - Low: 90 days

### After Reporting

1. We will investigate and validate the issue
2. We will work on a fix and coordinate disclosure
3. We will credit you in the security advisory (unless you prefer anonymity)
4. We will notify you when the fix is released

## Security Best Practices

When deploying RCA Agent:

### Environment Variables

- Never commit `.env` files to version control
- Use secrets management (Vault, AWS Secrets Manager, etc.) in production
- Rotate API keys regularly
- Use least-privilege access for service accounts

### API Security

- Deploy behind a reverse proxy (nginx, Traefik)
- Enable HTTPS/TLS in production
- Implement rate limiting
- Use authentication for production deployments

### Data Handling

- RCA Agent processes potentially sensitive incident data
- Ensure compliance with your organization's data policies
- Consider data retention policies for stored incidents
- Sanitize logs before sharing externally

### Network Security

- Restrict access to internal services (Loki, Prometheus, etc.)
- Use network policies in Kubernetes deployments
- Audit outbound connections to LLM providers

## Known Security Considerations

1. **LLM Data Exposure**: Incident data is sent to OpenAI for analysis. Review your data classification policies.

2. **Provider Credentials**: The agent requires credentials for various services (GitHub, Loki, etc.). Secure these appropriately.

3. **Webhook Endpoints**: The `/webhook/incident` endpoint accepts external requests. Implement authentication in production.

## Security Updates

Security updates will be released as patch versions and announced via:
- GitHub Security Advisories
- Release notes in CHANGELOG.md

## Acknowledgments

We thank the security researchers who have helped improve RCA Agent's security:

- (Your name could be here!)
