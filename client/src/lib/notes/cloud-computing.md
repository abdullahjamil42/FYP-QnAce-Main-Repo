# Cloud Computing — Senior Interview Preparation Notes

## 1. Cloud Service Models

| Model | You Manage | Provider Manages | Examples |
|-------|-----------|-----------------|----------|
| **IaaS** | OS, runtime, app, data | Hardware, networking, virtualization | EC2, Azure VMs, GCE |
| **PaaS** | App code, data | OS, runtime, middleware, infrastructure | Elastic Beanstalk, Azure App Service, Heroku |
| **SaaS** | Configuration | Everything | Gmail, Salesforce, Slack |

**Interview Q: When would you choose IaaS over PaaS?**
IaaS when you need full OS-level control (custom kernel modules, specific security hardening, legacy software). PaaS when you want to focus on application code and let the platform handle scaling, patching, and infrastructure. PaaS reduces operational burden but limits customization.

---

## 2. AWS Core Services Overview

### Compute
- **EC2**: Virtual machines with full OS control; instance types optimized for compute (C), memory (R), storage (I), GPU (P/G)
- **Lambda**: Serverless functions; pay per invocation + duration; max 15 min execution, 10GB memory
- **ECS**: Container orchestration using Docker; runs on EC2 or Fargate (serverless containers)
- **EKS**: Managed Kubernetes; for teams already invested in K8s ecosystem
- **Fargate**: Serverless compute engine for containers — no EC2 instances to manage

**Interview Q: When Lambda vs ECS/EKS?**
- **Lambda**: Event-driven, short-lived tasks (< 15 min), variable traffic, simple functions
- **ECS/EKS**: Long-running processes, complex networking, need for sidecar containers, consistent workloads, existing container workflows

### Storage
- **S3**: Object storage (unlimited, 11 nines durability); tiers: Standard, Infrequent Access, Glacier (archival)
- **EBS**: Block storage attached to EC2 (like a virtual hard drive); types: gp3 (general), io2 (high IOPS), st1 (throughput)
- **EFS**: Managed NFS file system; shared across multiple EC2 instances; auto-scales

| Storage | Type | Access | Use Case |
|---------|------|--------|----------|
| S3 | Object | HTTP API | Static assets, backups, data lakes |
| EBS | Block | Attached to 1 EC2 | Databases, boot volumes |
| EFS | File (NFS) | Shared across EC2 | Shared app data, content management |

### Networking
- **VPC** (Virtual Private Cloud): Isolated network environment
  - **Subnets**: Public (internet-facing with IGW) and Private (no direct internet access)
  - **Route Tables**: Rules for traffic routing
  - **NAT Gateway**: Allows private subnet instances to access internet (outbound only)
  - **Internet Gateway (IGW)**: Enables internet access for public subnets
- **Security Groups**: Stateful firewall at instance level (allow rules only)
- **NACLs**: Stateless firewall at subnet level (allow + deny rules)
- **VPC Peering**: Connect two VPCs privately
- **Transit Gateway**: Central hub connecting multiple VPCs and on-premises networks

### Load Balancers
- **ALB** (Application): Layer 7; HTTP/HTTPS routing, path-based routing, host-based routing
- **NLB** (Network): Layer 4; ultra-low latency, static IP, TCP/UDP
- **GLB** (Gateway): Layer 3; third-party virtual appliances (firewalls, IDS)

**Interview Q: ALB vs NLB?**
- ALB for HTTP microservices, API gateways, WebSocket support
- NLB for TCP-heavy workloads, gaming, IoT, extreme performance requirements

---

## 3. Databases in the Cloud

### Relational (RDS)
- Managed MySQL, PostgreSQL, MariaDB, Oracle, SQL Server
- Multi-AZ: Synchronous standby replica for high availability (automatic failover)
- Read Replicas: Asynchronous copies for read scaling (up to 15 for Aurora)
- **Aurora**: AWS-native, MySQL/PostgreSQL compatible, 5x throughput over standard MySQL, auto-scales storage up to 128TB

### NoSQL (DynamoDB)
- Key-value and document store; single-digit millisecond latency at any scale
- **Partition Key**: Determines data distribution — choose high-cardinality keys
- **Sort Key**: Enables range queries within a partition
- **GSI** (Global Secondary Index): Query on non-key attributes
- **Capacity Modes**: On-demand (pay-per-request) or Provisioned (with auto-scaling)
- **DAX**: In-memory cache for DynamoDB (microsecond reads)

**Interview Q: SQL vs NoSQL — how do you choose?**
- **SQL**: Complex queries, joins, transactions, strong consistency, relational data (orders, inventory)
- **NoSQL**: Flexible schema, massive scale, low-latency reads/writes, denormalized data (user profiles, session data, IoT telemetry)

---

## 4. Serverless Architecture

### Key Characteristics
- No server management; pay only for actual usage
- Auto-scales to zero (no cost when idle) and to thousands of concurrent executions
- Event-driven: triggered by API Gateway, S3 events, SQS messages, DynamoDB streams, CloudWatch events

### Common Serverless Patterns
```
API Gateway → Lambda → DynamoDB          (REST API)
S3 Upload → Lambda → Rekognition → S3    (Image processing)
SQS Queue → Lambda → RDS                 (Async processing)
EventBridge → Lambda → SNS               (Event-driven workflows)
CloudFront → S3                          (Static site hosting)
```

### Lambda Best Practices
- Keep functions small and focused (single responsibility)
- Minimize cold starts: smaller packages, provision concurrency for latency-sensitive paths
- Store secrets in Secrets Manager or Parameter Store, not environment variables
- Use layers for shared dependencies
- Set appropriate timeout and memory (CPU scales with memory)
- Implement idempotency (events may be delivered more than once)

### Cold Starts
- First invocation after idle period requires container initialization
- Factors: runtime (Java/C# worst, Python/Node.js better), package size, VPC configuration
- Mitigation: Provisioned Concurrency, SnapStart (Java), keep packages lean

---

## 5. Containers — Docker & Kubernetes

### Docker Fundamentals
```dockerfile
# Multi-stage build — minimize image size
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --production
COPY . .
RUN npm run build

FROM node:20-alpine
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
EXPOSE 3000
USER node
CMD ["node", "dist/server.js"]
```

**Best Practices:**
- Use specific base image tags (not `:latest`)
- Multi-stage builds to reduce image size
- Run as non-root user
- Use `.dockerignore` to exclude unnecessary files
- Order layers from least to most frequently changed (leverage cache)
- Scan images for vulnerabilities (Trivy, Snyk)

### Kubernetes Core Concepts

**Pods**: Smallest deployable unit; one or more containers sharing network/storage
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: web-server
spec:
  containers:
  - name: app
    image: myapp:v1.2.3
    ports:
    - containerPort: 3000
    resources:
      requests:
        cpu: "250m"
        memory: "256Mi"
      limits:
        cpu: "500m"
        memory: "512Mi"
    livenessProbe:
      httpGet:
        path: /healthz
        port: 3000
      initialDelaySeconds: 10
      periodSeconds: 15
    readinessProbe:
      httpGet:
        path: /ready
        port: 3000
      initialDelaySeconds: 5
      periodSeconds: 10
```

**Deployments**: Manage ReplicaSets; handle rolling updates and rollbacks
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      containers:
      - name: app
        image: myapp:v1.2.3
```

**Services**: Stable networking endpoint for pods
- **ClusterIP**: Internal only (default)
- **NodePort**: Exposes on each node's IP at a static port
- **LoadBalancer**: Provisions cloud load balancer
- **Headless** (clusterIP: None): Direct pod DNS (for StatefulSets)

**ConfigMaps & Secrets:**
```yaml
# ConfigMap — non-sensitive configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  DATABASE_HOST: "db.internal"
  LOG_LEVEL: "info"

# Secret — sensitive data (base64 encoded, encrypted at rest)
apiVersion: v1
kind: Secret
metadata:
  name: db-credentials
type: Opaque
data:
  DB_PASSWORD: cGFzc3dvcmQxMjM=  # base64 encoded
```

**Interview Q: How does a rolling update work?**
1. New ReplicaSet created with updated pod template
2. New pods are gradually created (maxSurge)
3. Old pods are terminated after new ones pass readiness checks (maxUnavailable)
4. If new pods fail health checks, rollout is halted
5. `kubectl rollout undo` reverts to previous ReplicaSet

---

## 6. Infrastructure as Code (IaC)

### Terraform
```hcl
# Declarative — define desired state
resource "aws_instance" "web" {
  ami           = "ami-0c02fb55956c7d316"
  instance_type = "t3.micro"
  subnet_id     = aws_subnet.public.id

  tags = {
    Name        = "web-server"
    Environment = "production"
  }
}

resource "aws_security_group" "web_sg" {
  vpc_id = aws_vpc.main.id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
```

**Key Concepts:**
- **State file**: Tracks real-world resources; store remotely (S3 + DynamoDB lock)
- **Modules**: Reusable, composable infrastructure components
- **Plan → Apply**: Preview changes before applying
- **Workspaces**: Manage multiple environments (dev, staging, prod)

### Terraform vs CloudFormation
| Feature | Terraform | CloudFormation |
|---------|-----------|---------------|
| Provider | Multi-cloud | AWS only |
| Language | HCL | JSON/YAML |
| State | Self-managed (remote backend) | AWS-managed |
| Ecosystem | Rich module registry | AWS-native integration |
| Drift detection | `terraform plan` | Stack drift detection |

---

## 7. Auto-Scaling

### Horizontal vs Vertical Scaling
- **Vertical** (scale up): Bigger instance — limited by hardware; requires downtime
- **Horizontal** (scale out): More instances — preferred for cloud-native apps

### AWS Auto Scaling
- **Target Tracking**: Maintain metric at target (e.g., CPU at 60%)
- **Step Scaling**: Add/remove capacity based on alarm thresholds
- **Scheduled Scaling**: Scale based on known traffic patterns (e.g., business hours)
- **Predictive Scaling**: ML-based forecasting of traffic patterns

**Configuration:**
- Min/Max/Desired capacity
- Cooldown period (prevent thrashing)
- Health checks (EC2 or ELB-based)
- Launch templates (instance configuration)

---

## 8. Caching

### ElastiCache
- **Redis**: Rich data structures, persistence, pub/sub, Lua scripting, replication
- **Memcached**: Simple key-value, multi-threaded, no persistence

### CloudFront (CDN)
- Edge locations cache static and dynamic content
- Reduces latency by serving from nearest POP (Point of Presence)
- Origin: S3, ALB, custom HTTP server
- Cache invalidation via versioned URLs or explicit invalidation API

### Caching Patterns
- **Cache-aside (Lazy Loading)**: App checks cache first; on miss, queries DB and populates cache
- **Write-through**: Every write goes to cache and DB simultaneously
- **Write-behind**: Write to cache; async write to DB (higher throughput, eventual consistency)
- **Read-through**: Cache transparently loads from DB on miss

**Interview Q: How do you handle cache invalidation?**
- TTL-based expiry (simple, eventual consistency)
- Event-driven invalidation (DB change triggers cache update)
- Versioned keys (`user:123:v5`)
- "There are only two hard things in CS: cache invalidation and naming things."

---

## 9. Message Queues & Event Streaming

### SQS (Simple Queue Service)
- Fully managed message queue; decouples producers and consumers
- **Standard**: At-least-once delivery, best-effort ordering (nearly unlimited throughput)
- **FIFO**: Exactly-once processing, strict ordering (300 msg/s without batching)
- Dead Letter Queue (DLQ): Capture messages that fail processing after max retries
- Visibility timeout: Message hidden from other consumers while being processed

### SNS (Simple Notification Service)
- Pub/sub model; one message → many subscribers (fan-out)
- Subscribers: SQS, Lambda, HTTP, email, SMS
- **Pattern**: SNS → multiple SQS queues (fan-out for parallel processing)

### Kafka
- Distributed event streaming platform; high throughput, durable, ordered
- **Topics** → **Partitions** → **Consumer Groups**
- Consumers track offset; can replay messages
- Use cases: Event sourcing, log aggregation, real-time analytics, CDC

**Interview Q: SQS vs Kafka?**
- SQS: Simple queuing, auto-managed, per-message deletion, great for decoupling microservices
- Kafka: Event streaming, message replay, ordered partitions, high throughput, complex setup

---

## 10. Monitoring & Observability

### CloudWatch
- **Metrics**: CPU, network, custom metrics; 1-min or 5-min granularity
- **Alarms**: Threshold-based alerts → SNS, Auto Scaling, Lambda
- **Logs**: Centralized log collection from EC2, Lambda, ECS
- **Dashboards**: Visualization of metrics and logs

### Prometheus + Grafana
- **Prometheus**: Pull-based metrics collection; time-series database; PromQL for queries
- **Grafana**: Visualization and dashboarding; supports multiple data sources
- Common for Kubernetes monitoring

### Key Metrics to Monitor
- **Infrastructure**: CPU, memory, disk I/O, network throughput
- **Application**: Request rate, error rate, latency (p50/p95/p99), active connections
- **Business**: Signups, orders, revenue, API usage
- **Satellite**: DNS, CDN hit rate, third-party API health

---

## 11. Cost Optimization

### Compute Cost Strategies
- **Right-sizing**: Match instance type to actual workload requirements
- **Reserved Instances / Savings Plans**: 1-3 year commitments for 30-72% discount
- **Spot Instances**: Up to 90% discount for interruptible workloads (batch processing, CI runners)
- **Auto-scaling**: Scale down during low-traffic periods
- **Graviton (ARM) instances**: 20-40% better price-performance

### Storage Cost Strategies
- **S3 Lifecycle Policies**: Transition objects between tiers automatically
  - Standard → Infrequent Access (30 days) → Glacier (90 days) → Deep Archive (365 days)
- **EBS**: Delete unattached volumes; use gp3 over gp2 (20% cheaper, better performance)
- **Data transfer**: Minimize cross-region/cross-AZ transfers; use VPC endpoints for AWS services

### General Practices
- **Tagging**: Tag all resources for cost allocation and accountability
- **Budgets & Alerts**: Set up AWS Budgets with alerts at 50%, 80%, 100%
- **Trusted Advisor / Cost Explorer**: Identify idle resources, underutilized instances
- **FinOps**: Cross-functional team (engineering + finance) for continuous cost optimization

---

## 12. Well-Architected Framework (AWS)

### Six Pillars
1. **Operational Excellence**: Automate operations, make frequent small changes, learn from failures
2. **Security**: Least privilege, encrypt everywhere, automate security controls
3. **Reliability**: Auto-recover, scale horizontally, test recovery procedures
4. **Performance Efficiency**: Right technology for workload, experiment, go global in minutes
5. **Cost Optimization**: Pay only for what you use, measure efficiency
6. **Sustainability**: Minimize environmental impact of workloads

---

## Common Interview Pitfalls

1. **Over-provisioning**: Not right-sizing resources; wasting money on idle capacity
2. **Ignoring multi-AZ/region**: Single AZ is a single point of failure
3. **Hardcoded configuration**: Use Parameter Store, Secrets Manager, ConfigMaps
4. **Not planning for failure**: Assume everything will fail; design for resilience
5. **Lift-and-shift without optimization**: Moving on-prem workloads to cloud without re-architecting misses cloud-native benefits

---

## Real-World Scenario Questions

**Q: Design a highly available web application on AWS.**
```
Route53 (DNS) → CloudFront (CDN) → ALB (multi-AZ)
  → ECS/EKS (auto-scaling, multi-AZ)
    → RDS Aurora (multi-AZ, read replicas)
    → ElastiCache (Redis, multi-AZ)
    → S3 (static assets, backups)
  → SQS + Lambda (async processing)
  → CloudWatch (monitoring + alerting)
  → WAF (web application firewall)
```
Key decisions: Multi-AZ for all stateful services, auto-scaling based on request rate, CDN for static content, read replicas for read-heavy workloads, async processing for non-critical paths.

**Q: How would you migrate a legacy on-premises application to the cloud?**
1. **Assess**: Inventory applications, dependencies, data volumes
2. **Strategy per workload** (6 R's): Rehost (lift-and-shift), Replatform (minor optimizations), Refactor (cloud-native), Repurchase (SaaS), Retire, Retain
3. **Migrate incrementally**: Start with low-risk workloads; build team confidence
4. **Data migration**: AWS DMS for databases; S3 Transfer Acceleration for files
5. **Cutover plan**: DNS-based failover, run parallel for validation
6. **Optimize**: Right-size, implement auto-scaling, leverage managed services
