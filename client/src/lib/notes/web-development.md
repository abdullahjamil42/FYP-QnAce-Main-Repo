# Web Development — Senior Interview Preparation Notes

## 1. HTTP/HTTPS Fundamentals

### HTTP Methods & Status Codes

| Method | Idempotent | Safe | Use Case |
|--------|-----------|------|----------|
| GET | Yes | Yes | Retrieve resources |
| POST | No | No | Create resources |
| PUT | Yes | No | Full update/replace |
| PATCH | No | No | Partial update |
| DELETE | Yes | No | Remove resources |

**Key Status Codes:**
- `200 OK` — Success
- `201 Created` — Resource created (POST)
- `204 No Content` — Success, no body (DELETE)
- `301/302` — Permanent/Temporary redirect
- `304 Not Modified` — Cached version is valid
- `400 Bad Request` — Client error
- `401 Unauthorized` — Authentication required
- `403 Forbidden` — Authenticated but not authorized
- `404 Not Found` — Resource doesn't exist
- `429 Too Many Requests` — Rate limited
- `500 Internal Server Error` — Server failure
- `502 Bad Gateway` — Upstream server error
- `503 Service Unavailable` — Server overloaded

### HTTPS & TLS Handshake
1. Client sends `ClientHello` (supported cipher suites, TLS version)
2. Server responds with `ServerHello` (chosen cipher, certificate)
3. Client verifies certificate against CA
4. Key exchange (asymmetric crypto) to establish shared secret
5. Both sides derive session keys; symmetric encryption begins

**Interview Q: What's the difference between HTTP/1.1, HTTP/2, and HTTP/3?**
- **HTTP/1.1**: Text-based, one request per TCP connection (or keep-alive with head-of-line blocking)
- **HTTP/2**: Binary framing, multiplexed streams over single TCP, header compression (HPACK), server push
- **HTTP/3**: Uses QUIC (over UDP), eliminates TCP head-of-line blocking, faster connection establishment (0-RTT)

---

## 2. REST vs GraphQL vs WebSockets

### REST
- Resource-oriented URLs (`/api/users/123`)
- Stateless; each request carries all context
- Standard HTTP methods map to CRUD
- Versioning via URL (`/v2/`) or headers (`Accept: application/vnd.api.v2+json`)

### GraphQL
- Single endpoint, client specifies exact data shape
- Solves over-fetching and under-fetching
- Strongly typed schema
- **Pitfall**: N+1 query problem — use DataLoader for batching
- **Pitfall**: Complex queries can be expensive — implement query depth/cost limiting

### WebSockets
- Full-duplex, persistent connection over TCP
- Starts as HTTP upgrade (`101 Switching Protocols`)
- Use cases: real-time chat, live dashboards, collaborative editing, gaming
- **Scaling concern**: Sticky sessions or pub/sub (Redis) for multi-server setups

---

## 3. JavaScript Deep Dive

### Closures
A closure is a function that retains access to its lexical scope even after the outer function has returned.

```javascript
function createCounter() {
  let count = 0;
  return {
    increment: () => ++count,
    getCount: () => count,
  };
}
const counter = createCounter();
counter.increment(); // 1
counter.increment(); // 2
// count is not directly accessible — encapsulated via closure
```

**Interview Q: What will this print?**
```javascript
for (var i = 0; i < 3; i++) {
  setTimeout(() => console.log(i), 0);
}
// Prints: 3, 3, 3 (var is function-scoped, not block-scoped)
// Fix: use `let` instead of `var`, or wrap in IIFE
```

### Event Loop
```
Call Stack → Microtask Queue (Promises, queueMicrotask)
           → Macrotask Queue (setTimeout, setInterval, I/O)
```
- Microtasks always drain before the next macrotask
- `Promise.then()` callbacks are microtasks; `setTimeout` callbacks are macrotasks

```javascript
console.log('1');
setTimeout(() => console.log('2'), 0);
Promise.resolve().then(() => console.log('3'));
console.log('4');
// Output: 1, 4, 3, 2
```

### Promises & Async/Await

```javascript
// Sequential (slow)
const a = await fetchA();
const b = await fetchB();

// Parallel (fast)
const [a, b] = await Promise.all([fetchA(), fetchB()]);

// Error handling
async function loadData() {
  try {
    const data = await fetch('/api/data');
    if (!data.ok) throw new Error(`HTTP ${data.status}`);
    return await data.json();
  } catch (err) {
    console.error('Failed:', err);
    throw err; // re-throw for caller to handle
  }
}
```

### Prototypal Inheritance
```javascript
const animal = { speak() { return `${this.name} makes a sound`; } };
const dog = Object.create(animal);
dog.name = 'Rex';
dog.speak(); // "Rex makes a sound"

// ES6 class syntax is syntactic sugar over prototypes
class Dog extends Animal {
  constructor(name) {
    super(name); // calls Animal constructor
  }
}
```

**Key concept**: Objects delegate to their prototype chain via `[[Prototype]]` (`__proto__`). `Object.create()` sets up the chain explicitly.

---

## 4. CSS Layout & Responsive Design

### Flexbox vs Grid

| Feature | Flexbox | Grid |
|---------|---------|------|
| Dimension | 1D (row or column) | 2D (rows and columns) |
| Use case | Navbars, centering, inline layouts | Page layouts, dashboards |
| Alignment | `justify-content`, `align-items` | `grid-template-areas`, `fr` units |

```css
/* Flexbox centering */
.container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
}

/* Grid responsive layout — no media queries needed */
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1rem;
}
```

### Responsive Design
- Mobile-first: start with small screens, add complexity via `min-width` media queries
- Use relative units (`rem`, `em`, `%`, `vw/vh`) over fixed `px`
- `clamp()` for fluid typography: `font-size: clamp(1rem, 2.5vw, 2rem);`

---

## 5. React — Hooks, Virtual DOM, State Management

### Core Hooks
```jsx
// useState — local state
const [count, setCount] = useState(0);

// useEffect — side effects (data fetching, subscriptions)
useEffect(() => {
  const controller = new AbortController();
  fetch('/api/data', { signal: controller.signal })
    .then(r => r.json())
    .then(setData);
  return () => controller.abort(); // cleanup
}, [dependency]); // runs when dependency changes

// useRef — mutable ref that persists across renders without triggering re-render
const inputRef = useRef(null);
inputRef.current.focus();

// useMemo — memoize expensive computation
const sorted = useMemo(() => items.sort(compare), [items]);

// useCallback — memoize function reference
const handleClick = useCallback(() => doThing(id), [id]);
```

### Virtual DOM
React maintains a lightweight in-memory representation of the DOM. On state change:
1. New virtual DOM tree is created
2. **Diffing** (reconciliation) compares old and new trees
3. Minimal set of actual DOM mutations are batched and applied

**Key**: React uses keys to identify list items — never use array index as key if list order changes.

### State Management Patterns
- **Local state**: `useState` for component-scoped state
- **Lifted state**: Share via common ancestor
- **Context**: `useContext` for cross-cutting state (theme, auth, locale)
- **External stores**: Redux, Zustand, Jotai for complex global state
- **Server state**: React Query / TanStack Query for API data (caching, refetching, deduplication)

---

## 6. Node.js

### Event-Driven Architecture
- Single-threaded event loop with non-blocking I/O via libuv
- **Worker threads** for CPU-intensive tasks (image processing, crypto)
- **Cluster module** to fork multiple processes across CPU cores

### Streams
```javascript
const fs = require('fs');
const zlib = require('zlib');

// Pipe readable → transform → writable (memory efficient)
fs.createReadStream('input.log')
  .pipe(zlib.createGzip())
  .pipe(fs.createWriteStream('input.log.gz'));
```

### Express Middleware Pattern
```javascript
// Middleware executes in order — order matters
app.use(cors());
app.use(helmet()); // security headers
app.use(express.json({ limit: '10kb' })); // body parser with size limit
app.use(rateLimiter); // custom rate limiter
app.use('/api', apiRouter);
app.use(errorHandler); // error middleware (4 params) — must be last
```

---

## 7. Authentication & Authorization

### JWT (JSON Web Token)
Structure: `header.payload.signature` (Base64URL encoded)
- **Header**: algorithm, token type
- **Payload**: claims (`sub`, `iat`, `exp`, custom claims)
- **Signature**: `HMAC-SHA256(header + payload, secret)`

**Best practices:**
- Short expiry (15 min) + refresh tokens (stored in httpOnly cookie)
- Never store JWTs in localStorage (XSS vulnerable)
- Include only necessary claims (minimize payload)

### OAuth2 Flows
- **Authorization Code + PKCE**: SPAs and mobile apps (recommended)
- **Client Credentials**: Machine-to-machine (no user involved)
- **Implicit** (deprecated): Replaced by Auth Code + PKCE

### Session-Based Auth
- Server stores session in memory/Redis; client gets session ID cookie
- Pros: easy revocation, server controls state
- Cons: sticky sessions or shared store needed for scaling

---

## 8. CORS (Cross-Origin Resource Sharing)

```
Same-origin: protocol + host + port must match
```
- Browser enforces CORS; servers declare allowed origins
- **Simple requests** (GET, POST with standard headers) include `Origin` header
- **Preflight** (`OPTIONS`) for non-simple requests — checks `Access-Control-Allow-*` headers
- **Never use `Access-Control-Allow-Origin: *` with credentials**

---

## 9. Caching Strategies

### Browser Caching
- `Cache-Control: max-age=3600, public` — cache for 1 hour
- `ETag` / `If-None-Match` — conditional validation (304 Not Modified)
- `stale-while-revalidate` — serve stale while fetching fresh in background

### CDN Caching
- Cache static assets at edge locations
- Cache invalidation via versioned filenames (`app.abc123.js`)
- Use `Vary` header to cache different versions (e.g., by Accept-Encoding)

### Application Caching (Redis)
- Cache-aside: app checks cache → miss → query DB → write to cache
- Write-through: write to cache and DB simultaneously
- TTL-based expiry to prevent stale data

---

## 10. Web Security

### XSS (Cross-Site Scripting)
- **Stored**: Malicious script saved in DB, served to other users
- **Reflected**: Script in URL params reflected in response
- **DOM-based**: Client-side JS manipulates DOM unsafely
- **Prevention**: Output encoding, Content Security Policy (CSP), sanitize inputs, use `textContent` not `innerHTML`

### CSRF (Cross-Site Request Forgery)
- Attacker tricks authenticated user into making unwanted requests
- **Prevention**: CSRF tokens (Synchronizer Token Pattern), SameSite cookies, check `Origin`/`Referer` headers

### SQL Injection
- **Prevention**: Parameterized queries (prepared statements), ORMs, input validation
```javascript
// VULNERABLE
db.query(`SELECT * FROM users WHERE id = '${userInput}'`);
// SAFE
db.query('SELECT * FROM users WHERE id = $1', [userInput]);
```

---

## 11. Performance Optimization

### Lazy Loading
```javascript
// React lazy + Suspense
const Dashboard = React.lazy(() => import('./Dashboard'));
<Suspense fallback={<Spinner />}>
  <Dashboard />
</Suspense>

// Image lazy loading (native)
<img src="photo.jpg" loading="lazy" alt="..." />
```

### Code Splitting
- Route-based splitting (each page is a separate chunk)
- Dynamic imports for heavy libraries: `const lib = await import('heavy-lib')`

### SSR vs SSG
- **SSR** (Server-Side Rendering): HTML generated per request — good for dynamic, personalized content
- **SSG** (Static Site Generation): HTML generated at build time — fastest TTFB, ideal for content sites
- **ISR** (Incremental Static Regeneration): Hybrid — static with background revalidation

### Core Web Vitals
- **LCP** (Largest Contentful Paint): < 2.5s — optimize hero images, fonts
- **INP** (Interaction to Next Paint): < 200ms — avoid long tasks on main thread
- **CLS** (Cumulative Layout Shift): < 0.1 — set explicit dimensions on images/embeds

---

## 12. Build Tools

### Webpack vs Vite
| Feature | Webpack | Vite |
|---------|---------|------|
| Dev server | Bundle-based (slow cold start) | Native ESM (instant) |
| HMR | Full module re-bundle | Granular ESM replacement |
| Config | Complex (loaders, plugins) | Minimal, convention-based |
| Production | Mature optimization | Rollup under the hood |

### Tree Shaking
- Eliminates dead code from bundles
- Requires ES modules (`import/export`), not CommonJS (`require`)
- Mark side-effect-free packages in `package.json`: `"sideEffects": false`

---

## 13. Testing Pyramid

### Unit Tests
- Test individual functions/components in isolation
- Mock external dependencies
- Tools: Jest, Vitest, React Testing Library

### Integration Tests
- Test interactions between modules (API routes, DB queries)
- Tools: Supertest (Express), MSW (mock service worker)

### E2E Tests
- Simulate real user flows in a browser
- Tools: Playwright, Cypress
- Test critical paths: signup, login, checkout, payment

```javascript
// React Testing Library — test behavior, not implementation
test('shows error on invalid email', async () => {
  render(<LoginForm />);
  await userEvent.type(screen.getByLabelText('Email'), 'invalid');
  await userEvent.click(screen.getByRole('button', { name: /submit/i }));
  expect(screen.getByText(/valid email/i)).toBeInTheDocument();
});
```

---

## Common Interview Pitfalls

1. **Confusing `==` and `===`** — Always use strict equality; `==` coerces types
2. **Not understanding `this` binding** — Arrow functions inherit `this` from lexical scope; regular functions depend on call site
3. **Memory leaks** — Forgotten event listeners, uncleared intervals, detached DOM nodes, unclosed connections in `useEffect`
4. **Over-engineering state management** — Don't reach for Redux when `useState` + prop drilling suffices for small apps
5. **Ignoring accessibility** — Semantic HTML, ARIA attributes, keyboard navigation, screen reader testing
6. **Not handling loading/error states** — Every async operation needs three states: loading, success, error

---

## Real-World Scenario Questions

**Q: How would you optimize a slow-loading e-commerce product page?**
1. Audit with Lighthouse / WebPageTest
2. Optimize images (WebP/AVIF, responsive srcset, lazy load below-fold)
3. Code-split route bundles; lazy load non-critical JS
4. Implement CDN caching with immutable asset hashing
5. Use SSG/ISR for product pages; hydrate client-side for dynamic elements
6. Preconnect to critical origins; preload critical fonts/CSS
7. Implement service worker for offline-first capability

**Q: How do you handle real-time updates in a distributed system?**
- WebSockets for bidirectional real-time (chat)
- Server-Sent Events (SSE) for one-way streaming (notifications, feeds)
- Long polling as fallback
- Scale with Redis Pub/Sub or message queues (Kafka) behind WebSocket servers
