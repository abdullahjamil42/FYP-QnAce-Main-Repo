# Databases — Senior Interview Prep

## 1. SQL vs NoSQL

| Feature | SQL (Relational) | NoSQL |
|---|---|---|
| Schema | Fixed, predefined | Flexible, schema-less |
| Scaling | Vertical (scale up) | Horizontal (scale out) |
| Transactions | Full ACID | Varies (eventual consistency common) |
| Query language | SQL | Database-specific APIs |
| Examples | PostgreSQL, MySQL, Oracle | MongoDB, Cassandra, Redis, DynamoDB |

**When to choose SQL:** Complex queries, joins, transactions, data integrity critical (banking, ERP).
**When to choose NoSQL:** High write throughput, flexible schema, horizontal scaling, hierarchical/document data (social feeds, IoT, caching).

### Types of NoSQL
- **Document:** MongoDB, CouchDB — JSON-like documents, nested structures.
- **Key-Value:** Redis, DynamoDB — fast lookups, caching, session stores.
- **Column-Family:** Cassandra, HBase — wide rows, time-series data.
- **Graph:** Neo4j, Amazon Neptune — relationships are first-class (social networks, recommendations).

---

## 2. ACID Properties

| Property | Meaning |
|---|---|
| **Atomicity** | All operations in a transaction succeed or all fail (rollback). |
| **Consistency** | Database moves from one valid state to another. Constraints are always satisfied. |
| **Isolation** | Concurrent transactions don't interfere with each other. |
| **Durability** | Once committed, data persists even after crash (write-ahead log, fsync). |

### Interview question: *"What happens if a bank transfer fails mid-way?"*
Atomicity ensures both the debit and credit happen together or neither does. The entire transaction rolls back on failure.

---

## 3. Normalization

Purpose: eliminate redundancy, prevent update/insert/delete anomalies.

| Normal Form | Rule |
|---|---|
| **1NF** | Atomic values only (no repeating groups, no arrays in cells). Each row unique. |
| **2NF** | 1NF + no partial dependencies (every non-key attribute depends on the *whole* primary key). |
| **3NF** | 2NF + no transitive dependencies (non-key attributes don't depend on other non-key attributes). |
| **BCNF** | Every determinant is a candidate key. Stricter than 3NF. |

### Example: Violation → Fix
```
-- Violates 2NF: student_name depends only on student_id, not on the composite PK
StudentCourses(student_id, course_id, student_name, grade)

-- Fix: separate into two tables
Students(student_id PK, student_name)
Enrollments(student_id FK, course_id, grade)  -- composite PK
```

**Denormalization:** intentionally adding redundancy for read performance (common in analytics, data warehouses). Trade-off: faster reads, slower writes, risk of inconsistency.

---

## 4. Indexing

An index is a data structure that speeds up data retrieval at the cost of extra storage and slower writes.

### Types
- **B-Tree index:** default in most RDBMS. Balanced tree, O(log n) lookups. Good for range queries (`BETWEEN`, `<`, `>`), equality, and `ORDER BY`.
- **Hash index:** O(1) equality lookups only. No range support.
- **Composite index:** multiple columns. Order matters — follows **leftmost prefix rule**.
- **Covering index:** includes all columns needed by a query, avoiding table lookup.
- **Partial index:** indexes a subset of rows (PostgreSQL: `CREATE INDEX ... WHERE condition`).

```sql
-- Composite index: supports WHERE a = ? AND b = ? and WHERE a = ?
-- Does NOT support WHERE b = ? alone
CREATE INDEX idx_a_b ON orders(customer_id, order_date);

-- Covering index
CREATE INDEX idx_covering ON orders(customer_id, order_date) INCLUDE (total);
```

### When NOT to index
- Small tables (full scan is faster than index lookup + random I/O).
- Columns with low cardinality (e.g., boolean, gender).
- Write-heavy tables where index maintenance overhead is too high.

---

## 5. Query Optimization

### Tools
- `EXPLAIN` / `EXPLAIN ANALYZE` — shows query execution plan and actual timings.
- Look for: sequential scans on large tables, nested loop joins on big datasets, sort spill to disk.

### Optimization Techniques
1. **Use indexes** on WHERE, JOIN, ORDER BY, GROUP BY columns.
2. **Avoid SELECT ***  — fetch only needed columns.
3. **Use EXISTS instead of IN** for correlated subqueries.
4. **Avoid functions on indexed columns** in WHERE (`WHERE YEAR(date) = 2024` → can't use index. Use `WHERE date >= '2024-01-01' AND date < '2025-01-01'`).
5. **Batch operations** — insert in batches, not row by row.
6. **Pagination:** use keyset pagination (`WHERE id > last_seen_id LIMIT 20`) over `OFFSET` for large datasets.

```sql
-- Slow: function on indexed column prevents index usage
SELECT * FROM orders WHERE YEAR(created_at) = 2024;

-- Fast: sargable predicate
SELECT * FROM orders
WHERE created_at >= '2024-01-01' AND created_at < '2025-01-01';
```

---

## 6. Joins

```sql
-- INNER JOIN: only matching rows from both tables
SELECT e.name, d.dept_name
FROM employees e INNER JOIN departments d ON e.dept_id = d.id;

-- LEFT OUTER JOIN: all rows from left + matched from right (NULL if no match)
SELECT e.name, d.dept_name
FROM employees e LEFT JOIN departments d ON e.dept_id = d.id;

-- RIGHT OUTER JOIN: all rows from right + matched from left
-- FULL OUTER JOIN: all rows from both (NULL-filled where no match)

-- CROSS JOIN: Cartesian product — every row from A paired with every row from B
SELECT * FROM sizes CROSS JOIN colors;

-- SELF JOIN: table joined with itself
-- Find employees earning more than their manager
SELECT e.name AS employee, m.name AS manager
FROM employees e
JOIN employees m ON e.manager_id = m.id
WHERE e.salary > m.salary;
```

### Anti-join Pattern (find rows with no match)
```sql
-- Employees with no orders
SELECT e.id, e.name
FROM employees e
LEFT JOIN orders o ON e.id = o.employee_id
WHERE o.id IS NULL;
```

---

## 7. Transactions & Isolation Levels

### Concurrency Problems
- **Dirty read:** reading uncommitted data from another transaction.
- **Non-repeatable read:** re-reading a row returns different data (another txn committed an update).
- **Phantom read:** re-running a query returns new rows (another txn committed an insert).

| Isolation Level | Dirty Read | Non-Repeatable | Phantom |
|---|---|---|---|
| **READ UNCOMMITTED** | Yes | Yes | Yes |
| **READ COMMITTED** | No | Yes | Yes |
| **REPEATABLE READ** | No | No | Yes |
| **SERIALIZABLE** | No | No | No |

```sql
SET TRANSACTION ISOLATION LEVEL REPEATABLE READ;
BEGIN;
SELECT balance FROM accounts WHERE id = 1;
-- Another transaction cannot modify this row until we commit
UPDATE accounts SET balance = balance - 100 WHERE id = 1;
COMMIT;
```

**PostgreSQL default:** READ COMMITTED. **MySQL InnoDB default:** REPEATABLE READ.

---

## 8. CAP Theorem

In a distributed system, you can guarantee at most **two of three**:

- **Consistency:** every read returns the most recent write.
- **Availability:** every request receives a response (success/failure).
- **Partition Tolerance:** system continues despite network partitions.

Since network partitions are inevitable, the real choice is **CP vs AP**:
- **CP (Consistency + Partition tolerance):** MongoDB (with majority write concern), HBase, Zookeeper.
- **AP (Availability + Partition tolerance):** Cassandra, DynamoDB, CouchDB.

### PACELC Extension
If there is a **P**artition, choose **A** or **C**; **E**lse (normal operation), choose **L**atency or **C**onsistency. DynamoDB under normal conditions: low latency with eventual consistency.

---

## 9. Sharding & Partitioning

### Partitioning (single database)
- **Horizontal:** split rows across partitions (e.g., by date range, region).
- **Vertical:** split columns across tables (e.g., separate rarely-used BLOB columns).

### Sharding (across multiple database servers)
Strategies:
- **Range-based:** shard by date range, ID range. Simple but can cause hotspots.
- **Hash-based:** `shard = hash(key) % num_shards`. Even distribution but range queries span all shards.
- **Directory-based:** lookup table maps keys to shards. Flexible but the directory is a SPOF.

**Challenges:** cross-shard joins, distributed transactions, resharding (adding shards), data skew.

---

## 10. Replication

- **Leader-Follower (Master-Slave):** writes → leader, reads → followers. Simple. Read scaling. Risk of stale reads.
- **Leader-Leader (Multi-Master):** writes to any node. Conflict resolution needed. Used in multi-region deployments.
- **Synchronous:** leader waits for follower acknowledgment. Strong consistency, higher latency.
- **Asynchronous:** leader doesn't wait. Lower latency, risk of data loss on leader failure.

**Replication lag:** the delay before a follower catches up. Can cause read-your-writes inconsistency. Solutions: read from leader after writes, or causal consistency.

---

## 11. Stored Procedures & Views

```sql
-- Stored Procedure: precompiled SQL on the server side
CREATE PROCEDURE get_top_customers(IN min_orders INT)
BEGIN
    SELECT customer_id, COUNT(*) AS order_count
    FROM orders
    GROUP BY customer_id
    HAVING COUNT(*) >= min_orders
    ORDER BY order_count DESC;
END;

-- View: virtual table based on a query
CREATE VIEW active_customers AS
SELECT c.id, c.name, COUNT(o.id) AS total_orders
FROM customers c
JOIN orders o ON c.id = o.customer_id
WHERE o.created_at >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY c.id, c.name;

-- Materialized View (PostgreSQL): cached result, refresh needed
CREATE MATERIALIZED VIEW monthly_sales AS
SELECT DATE_TRUNC('month', order_date) AS month, SUM(total) AS revenue
FROM orders GROUP BY 1;

REFRESH MATERIALIZED VIEW monthly_sales;
```

---

## 12. Database Design Patterns

### Soft Deletes
```sql
ALTER TABLE users ADD COLUMN deleted_at TIMESTAMP NULL;
-- "Delete": UPDATE users SET deleted_at = NOW() WHERE id = ?;
-- Query: SELECT * FROM users WHERE deleted_at IS NULL;
```

### Audit Trail
```sql
CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    table_name VARCHAR(50),
    record_id BIGINT,
    action VARCHAR(10),  -- INSERT, UPDATE, DELETE
    old_values JSONB,
    new_values JSONB,
    changed_by INT REFERENCES users(id),
    changed_at TIMESTAMP DEFAULT NOW()
);
```

### Polymorphic Associations
```sql
-- Option 1: Single table (STI)
CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    type VARCHAR(20),  -- 'email', 'sms', 'push'
    recipient VARCHAR(255),
    message TEXT
);

-- Option 2: Separate tables with shared interface
CREATE TABLE email_notifications (...);
CREATE TABLE sms_notifications (...);
```

### Hierarchical Data
```sql
-- Adjacency List (simple, recursive queries needed)
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    parent_id INT REFERENCES categories(id)
);

-- Recursive CTE to get full tree
WITH RECURSIVE tree AS (
    SELECT id, name, parent_id, 0 AS depth
    FROM categories WHERE parent_id IS NULL
    UNION ALL
    SELECT c.id, c.name, c.parent_id, t.depth + 1
    FROM categories c JOIN tree t ON c.parent_id = t.id
)
SELECT * FROM tree ORDER BY depth, name;
```

---

## 13. Window Functions

```sql
-- Rank employees by salary within each department
SELECT name, department, salary,
    RANK() OVER (PARTITION BY department ORDER BY salary DESC) AS rank,
    ROW_NUMBER() OVER (PARTITION BY department ORDER BY salary DESC) AS row_num,
    DENSE_RANK() OVER (PARTITION BY department ORDER BY salary DESC) AS dense_rank
FROM employees;

-- Running total
SELECT order_date, amount,
    SUM(amount) OVER (ORDER BY order_date) AS running_total
FROM orders;

-- Moving average (last 7 days)
SELECT order_date, amount,
    AVG(amount) OVER (ORDER BY order_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS moving_avg
FROM daily_sales;
```

---

## 14. Common Interview Questions

1. **"Design a schema for an e-commerce platform."** — Users, Products, Orders, OrderItems, Categories, Reviews. Discuss normalization vs denormalization trade-offs.
2. **"How would you handle a slow query?"** — EXPLAIN ANALYZE, check missing indexes, simplify joins, avoid SELECT *, consider materialized views.
3. **"Explain the difference between clustered and non-clustered indexes."** — Clustered: rows stored in index order (one per table). Non-clustered: separate structure with pointers to data rows.
4. **"How do you handle concurrent writes to the same row?"** — Optimistic locking (version column), pessimistic locking (SELECT ... FOR UPDATE), isolation levels.
5. **"What is a deadlock and how do you prevent it?"** — Two transactions waiting for each other's locks. Prevention: consistent lock ordering, timeouts, keep transactions short.

---

## 15. Pitfalls

- **N+1 query problem:** fetching a list then querying each item's details separately. Use JOINs or batch fetching.
- **Over-indexing:** every index slows writes and uses storage.
- **Not using parameterized queries:** opens the door to SQL injection.
- **Ignoring query plans:** always use EXPLAIN before deploying queries on large tables.
- **Using OFFSET for deep pagination:** scans and discards rows. Use keyset pagination instead.
- **Storing passwords in plain text:** always use bcrypt/argon2 hashing.
