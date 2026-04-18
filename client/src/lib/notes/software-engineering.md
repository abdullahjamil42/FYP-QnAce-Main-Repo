# Software Engineering — Senior Interview Preparation Notes

## 1. Software Development Life Cycle (SDLC) Models

### Agile
- Iterative, incremental delivery in short cycles (sprints)
- Embrace change; respond to feedback continuously
- Core values: individuals & interactions, working software, customer collaboration, responding to change
- **Interview Q: How does Agile differ from Waterfall?** — Agile is adaptive (welcome changing requirements); Waterfall is predictive (fixed scope upfront). Agile delivers incrementally; Waterfall delivers all at once at the end.

### Scrum
- **Roles**: Product Owner (what to build), Scrum Master (process), Development Team (how to build)
- **Ceremonies**: Sprint Planning, Daily Standup, Sprint Review, Sprint Retrospective
- **Artifacts**: Product Backlog, Sprint Backlog, Increment
- **Sprint**: Fixed timebox (1-4 weeks, commonly 2 weeks)
- **Velocity**: Average story points completed per sprint — used for forecasting, not performance evaluation

### Kanban
- Continuous flow (no fixed sprints)
- **WIP limits**: Restrict work-in-progress per column to prevent bottlenecks
- Visualize workflow on a board (To Do → In Progress → Review → Done)
- Optimize lead time and cycle time

### Waterfall
- Sequential phases: Requirements → Design → Implementation → Testing → Deployment → Maintenance
- Works for: regulated industries, fixed-scope contracts, hardware projects
- Weakness: late discovery of issues; costly to change direction

---

## 2. Version Control (Git)

### Branching Strategies

**Git Flow:**
- `main` — production-ready
- `develop` — integration branch
- `feature/*` — branched from develop
- `release/*` — stabilization before production
- `hotfix/*` — emergency fixes from main
- Suited for: scheduled releases, versioned software

**Trunk-Based Development:**
- All developers commit to `main` (or short-lived feature branches merged within 1-2 days)
- Requires: feature flags, strong CI, automated testing
- Suited for: continuous deployment, web services

**GitHub Flow:**
- Simpler: `main` + feature branches → PR → merge to main → deploy
- Suited for: SaaS with continuous delivery

### Key Git Operations
```bash
# Interactive rebase — clean up commit history before merging
git rebase -i HEAD~5

# Cherry-pick — apply a specific commit to another branch
git cherry-pick abc123

# Stash — temporarily save uncommitted changes
git stash push -m "WIP: feature X"
git stash pop

# Bisect — binary search for bug-introducing commit
git bisect start
git bisect bad HEAD
git bisect good v1.0.0

# Reflog — recover lost commits
git reflog
git checkout <lost-commit-sha>
```

**Interview Q: Rebase vs Merge?**
- **Merge**: Creates a merge commit; preserves full branch history; non-destructive
- **Rebase**: Replays commits on top of target branch; creates linear history; rewrites commits
- **Rule**: Never rebase commits that have been pushed to a shared branch

---

## 3. CI/CD Pipelines

### Continuous Integration
- Every commit triggers automated build + test
- Fail fast: break the build early
- Key stages: Lint → Unit Tests → Integration Tests → Build Artifact

### Continuous Delivery vs Deployment
- **Delivery**: Every commit _can_ be deployed (manual approval gate)
- **Deployment**: Every commit _is_ deployed automatically

### Pipeline Best Practices
```yaml
# Example GitHub Actions pipeline
name: CI/CD
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci
      - run: npm run lint
      - run: npm test -- --coverage
      - run: npm run build
  deploy:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - run: ./deploy.sh
```

**Key practices:**
- Pin dependency versions (`npm ci` not `npm install`)
- Cache dependencies between runs
- Parallelize independent jobs
- Keep pipeline under 10 minutes
- Use environment-specific secrets (never hardcode)
- Run SAST/DAST security scanning in pipeline

---

## 4. Testing Strategies

### Test Pyramid
```
        /  E2E  \        ← Few, slow, expensive
       / Integration \   ← Moderate
      /    Unit Tests   \ ← Many, fast, cheap
```

### TDD (Test-Driven Development)
1. **Red**: Write a failing test for the desired behavior
2. **Green**: Write the minimum code to pass the test
3. **Refactor**: Clean up while keeping tests green

### BDD (Behavior-Driven Development)
- Tests written in natural language (Given/When/Then)
- Bridges gap between business and engineering
```gherkin
Feature: User Login
  Scenario: Successful login
    Given a registered user with email "user@test.com"
    When they enter valid credentials
    Then they should see the dashboard
```

### Types of Tests
| Type | Scope | Speed | Tools |
|------|-------|-------|-------|
| Unit | Single function/class | Fast | Jest, pytest, JUnit |
| Integration | Multiple modules | Medium | Supertest, TestContainers |
| System/E2E | Full application | Slow | Playwright, Cypress |
| Acceptance | Business requirements | Slow | Cucumber, manual |
| Contract | API compatibility | Fast | Pact |
| Load/Perf | System under stress | Varies | k6, JMeter, Locust |

### Test Doubles
- **Mock**: Verifies interactions (was this method called?)
- **Stub**: Returns predetermined data (no verification)
- **Spy**: Wraps real implementation; records calls
- **Fake**: Working implementation with shortcuts (in-memory DB)

---

## 5. Code Review Best Practices

### As a Reviewer
- Review within 24 hours (don't be a bottleneck)
- Focus on: correctness, edge cases, security, readability, maintainability
- Avoid bikeshedding (style debates) — let linters handle formatting
- Be specific: suggest concrete alternatives, not vague criticism
- Distinguish between blocking issues and suggestions (prefix with "nit:" for non-blocking)

### As an Author
- Keep PRs small (< 400 lines ideally)
- Write descriptive PR descriptions (what, why, how, testing)
- Self-review before requesting review
- Link to ticket/issue; include screenshots for UI changes

**Interview Q: How do you handle disagreements in code review?**
Focus on technical merit, not personal preference. Reference team conventions/style guides. If unresolved, discuss synchronously or involve a third engineer. Document decisions for future reference.

---

## 6. Design Patterns

### Creational Patterns
- **Singleton**: One instance globally (DB connection pool, logger)
- **Factory Method**: Create objects without specifying exact class
- **Builder**: Construct complex objects step-by-step
- **Abstract Factory**: Create families of related objects

```python
# Factory pattern
class NotificationFactory:
    @staticmethod
    def create(channel: str) -> Notification:
        if channel == "email":
            return EmailNotification()
        elif channel == "sms":
            return SMSNotification()
        elif channel == "push":
            return PushNotification()
        raise ValueError(f"Unknown channel: {channel}")
```

### Structural Patterns
- **Adapter**: Convert interface of one class to another (wrapping legacy APIs)
- **Decorator**: Add behavior dynamically without modifying the class
- **Facade**: Simplified interface to a complex subsystem
- **Proxy**: Control access to an object (caching proxy, auth proxy)

### Behavioral Patterns
- **Observer**: One-to-many dependency; notify subscribers on change (event emitters)
- **Strategy**: Define a family of algorithms; swap at runtime
- **Command**: Encapsulate request as an object (undo/redo, task queues)
- **State**: Object alters behavior when internal state changes (order status machine)
- **Chain of Responsibility**: Pass request through handlers (middleware pipeline)

```python
# Strategy pattern
class Sorter:
    def __init__(self, strategy):
        self._strategy = strategy

    def sort(self, data):
        return self._strategy.sort(data)

class QuickSort:
    def sort(self, data): ...

class MergeSort:
    def sort(self, data): ...

# Switch algorithm at runtime
sorter = Sorter(QuickSort())
sorter.sort(data)
```

---

## 7. SOLID Principles

| Principle | Definition | Violation Example |
|-----------|-----------|-------------------|
| **S**ingle Responsibility | A class should have one reason to change | `UserService` handles auth, email, and DB queries |
| **O**pen/Closed | Open for extension, closed for modification | Adding a new payment type requires modifying existing switch/case |
| **L**iskov Substitution | Subtypes must be substitutable for base types | `Square` extends `Rectangle` but breaks `setWidth`/`setHeight` contract |
| **I**nterface Segregation | Don't force classes to implement unused methods | `Worker` interface with `work()` and `eat()` — robots can't `eat()` |
| **D**ependency Inversion | Depend on abstractions, not concretions | `OrderService` directly instantiates `MySQLRepository` |

```python
# Dependency Inversion — depend on abstraction
class OrderService:
    def __init__(self, repository: OrderRepository):  # interface
        self.repository = repository

# Can inject any implementation
service = OrderService(PostgresOrderRepo())
service = OrderService(InMemoryOrderRepo())  # for testing
```

---

## 8. Clean Code Principles

- **Meaningful names**: `getUserById` not `getData`; `isActive` not `flag`
- **Small functions**: 5-20 lines; do one thing
- **DRY** (Don't Repeat Yourself): Extract shared logic, but avoid premature abstraction
- **YAGNI** (You Aren't Gonna Need It): Don't build features you don't need yet
- **KISS** (Keep It Simple): Prefer simple, readable solutions over clever ones
- **Boy Scout Rule**: Leave code cleaner than you found it
- **Avoid magic numbers**: Use named constants `MAX_RETRIES = 3`
- **Fail fast**: Validate inputs early; throw meaningful errors

---

## 9. Technical Debt

**Definition**: The implied cost of future rework caused by choosing an easy (limited) solution over a better approach.

**Types:**
- **Deliberate**: "We know this isn't ideal, but we ship now and fix later" (must be tracked)
- **Accidental**: Poor design decisions made unknowingly
- **Bit rot**: Code degrades as dependencies/requirements evolve without maintenance

**Managing Tech Debt:**
- Track in backlog with estimated cost-of-delay
- Allocate 10-20% of sprint capacity for debt reduction
- Boy Scout Rule: Incremental improvement during feature work
- **Interview Q**: "How do you balance feature development with tech debt?" — Prioritize debt that blocks features or causes incidents. Use data (error rates, deployment frequency, onboarding time) to justify investment.

---

## 10. Microservices vs Monolith

### Monolith
- Single deployable unit; simpler to develop, test, deploy initially
- Scaling: scale entire app even if only one module is overloaded
- Risk: becomes a "big ball of mud" as it grows

### Microservices
- Independent, deployable services around business domains
- Each service owns its data (database-per-service pattern)
- Communication: synchronous (REST, gRPC) or asynchronous (message queues)
- **Benefits**: Independent scaling, deployment, technology diversity, team autonomy
- **Costs**: Distributed system complexity, network latency, data consistency challenges, operational overhead

**Interview Q: When should you move from monolith to microservices?**
Start monolithic. Extract services when:
- Team size makes coordination painful (> 8-10 engineers on same codebase)
- Specific modules need independent scaling
- Deployment of one module shouldn't require deploying everything
- Different modules benefit from different tech stacks

### Key Microservice Patterns
- **API Gateway**: Single entry point, routing, rate limiting, auth
- **Service Discovery**: Services register/find each other (Consul, Eureka)
- **Circuit Breaker**: Prevent cascade failures (Hystrix, Resilience4j)
- **Saga Pattern**: Distributed transactions via orchestrated/choreographed compensating actions
- **CQRS**: Separate read and write models for different optimization
- **Event Sourcing**: Store state changes as immutable events

---

## 11. API Design

### RESTful Conventions
```
GET    /api/v1/users              → List users
GET    /api/v1/users/123          → Get user 123
POST   /api/v1/users              → Create user
PUT    /api/v1/users/123          → Replace user 123
PATCH  /api/v1/users/123          → Partial update user 123
DELETE /api/v1/users/123          → Delete user 123
GET    /api/v1/users/123/orders   → List orders for user 123
```

### Pagination
```json
// Offset-based (simple, but slow for large offsets)
GET /api/users?page=3&limit=20

// Cursor-based (efficient, consistent for real-time data)
GET /api/users?cursor=eyJpZCI6MTAwfQ&limit=20

// Response envelope
{
  "data": [...],
  "meta": {
    "total": 1500,
    "next_cursor": "eyJpZCI6MTIwfQ",
    "has_more": true
  }
}
```

### API Versioning
- **URL path**: `/api/v2/users` (most common, explicit)
- **Header**: `Accept: application/vnd.myapi.v2+json` (cleaner, but less discoverable)
- **Query param**: `/api/users?version=2` (least recommended)

### Error Response Format
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input",
    "details": [
      { "field": "email", "message": "Must be a valid email address" }
    ]
  }
}
```

---

## 12. Logging & Monitoring

### Structured Logging
```json
{
  "timestamp": "2025-01-15T10:30:00Z",
  "level": "ERROR",
  "service": "order-service",
  "trace_id": "abc-123-def",
  "message": "Payment processing failed",
  "user_id": "user_456",
  "error_code": "PAYMENT_DECLINED"
}
```

### Observability Pillars
1. **Logs**: What happened (structured, searchable — ELK, Datadog)
2. **Metrics**: Aggregated measurements (Prometheus, Grafana — latency, error rate, throughput)
3. **Traces**: Request journey across services (Jaeger, Zipkin — distributed tracing)

### Key Metrics (RED Method)
- **R**ate: Requests per second
- **E**rrors: Error rate (percentage of failed requests)
- **D**uration: Latency distribution (p50, p95, p99)

### Alerting Best Practices
- Alert on symptoms (high error rate), not causes (high CPU)
- Avoid alert fatigue — only alert on actionable conditions
- Use severity levels: Critical (pager), Warning (next business day), Info (dashboard)

---

## 13. Incident Response

### Incident Lifecycle
1. **Detection**: Monitoring alert or user report
2. **Triage**: Assess severity and impact
3. **Response**: Assemble team, communicate status
4. **Mitigation**: Stop the bleeding (rollback, feature flag off, scale up)
5. **Resolution**: Root cause fix deployed
6. **Post-mortem**: Blameless review — what happened, why, how to prevent recurrence

### Severity Levels
| Level | Description | Response Time |
|-------|-------------|---------------|
| SEV1 | Complete outage, data loss | Immediate, all hands |
| SEV2 | Major feature broken, many users affected | < 30 min |
| SEV3 | Minor feature impacted, workaround exists | Next business day |
| SEV4 | Cosmetic/minor issue | Backlog |

### Blameless Post-Mortem Template
1. **Summary**: What happened, duration, impact
2. **Timeline**: Minute-by-minute account
3. **Root Cause**: Technical root cause (not "human error")
4. **Contributing Factors**: What made it worse or delayed recovery
5. **Action Items**: Preventive measures with owners and deadlines
6. **Lessons Learned**: What went well, what didn't

---

## Common Interview Pitfalls

1. **Saying "it depends" without elaborating** — Always follow up with tradeoffs and recommendations
2. **Over-engineering solutions** — YAGNI; start simple, iterate
3. **Ignoring non-functional requirements** — Scalability, security, observability, maintainability
4. **Not discussing tradeoffs** — Every architecture decision has costs; mature engineers articulate them
5. **Treating patterns as gospel** — Patterns are tools, not rules; misapplied patterns create complexity

---

## Real-World Scenario Questions

**Q: You're tasked with decomposing a monolithic e-commerce app. How do you approach it?**
1. Identify bounded contexts (orders, inventory, users, payments, shipping)
2. Start with the strangler fig pattern — extract one service at a time behind an API gateway
3. Define clear API contracts between services
4. Implement async communication for non-critical paths (order confirmation email)
5. Database: migrate to database-per-service gradually; use change data capture (CDC) during transition
6. Ensure observability: distributed tracing, centralized logging
7. Feature flags for safe rollout; run old and new paths in parallel initially

**Q: A production deployment breaks things. What do you do?**
1. **Detect**: Monitoring alerts or user reports
2. **Mitigate first**: Rollback deployment immediately (don't debug in production under pressure)
3. **Communicate**: Status page update, inform stakeholders
4. **Investigate**: Check logs, diffs, recent changes in a non-production environment
5. **Fix forward**: Apply targeted fix and deploy through normal pipeline
6. **Post-mortem**: Identify gaps in testing, monitoring, or deployment process
