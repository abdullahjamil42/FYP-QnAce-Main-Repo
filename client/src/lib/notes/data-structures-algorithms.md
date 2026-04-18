# Data Structures and Algorithms — Senior Interview Prep

## 1. Big-O Notation & Complexity Analysis

**Big-O** describes the upper bound of an algorithm's growth rate as input size increases.

| Complexity | Name | Example |
|---|---|---|
| O(1) | Constant | Hash table lookup |
| O(log n) | Logarithmic | Binary search |
| O(n) | Linear | Linear search |
| O(n log n) | Linearithmic | Merge sort |
| O(n²) | Quadratic | Bubble sort |
| O(2ⁿ) | Exponential | Recursive Fibonacci |
| O(n!) | Factorial | Permutations |

**Key rules:** Drop constants, drop lower-order terms, consider worst-case unless stated otherwise. Amortized analysis (e.g., dynamic array append is O(1) amortized despite occasional O(n) resizing).

---

## 2. Arrays

- **Access:** O(1) by index. **Search:** O(n) unsorted, O(log n) sorted. **Insert/Delete:** O(n) due to shifting.
- **Dynamic arrays** (Python `list`): amortized O(1) append, O(n) insert at arbitrary position.

### Common Patterns
- **Two pointers:** sorted arrays, palindrome checks, container with most water.
- **Sliding window:** max subarray sum, longest substring without repeating characters.
- **Prefix sums:** range sum queries in O(1) after O(n) preprocessing.

```python
# Two-pointer: Two Sum on sorted array
def two_sum_sorted(nums, target):
    lo, hi = 0, len(nums) - 1
    while lo < hi:
        s = nums[lo] + nums[hi]
        if s == target:
            return [lo, hi]
        elif s < target:
            lo += 1
        else:
            hi -= 1
    return []

# Sliding window: max sum subarray of size k
def max_sum_subarray(nums, k):
    window = sum(nums[:k])
    best = window
    for i in range(k, len(nums)):
        window += nums[i] - nums[i - k]
        best = max(best, window)
    return best
```

---

## 3. Linked Lists

- **Singly linked:** each node points to next. **Doubly linked:** points to both next and prev.
- **Access:** O(n). **Insert/Delete at head:** O(1). **Search:** O(n).

### Classic Problems
- Reverse a linked list (iterative and recursive)
- Detect cycle (Floyd's tortoise and hare)
- Merge two sorted lists
- Find the middle node

```python
class ListNode:
    def __init__(self, val=0, nxt=None):
        self.val = val
        self.next = nxt

def reverse_list(head):
    prev, curr = None, head
    while curr:
        nxt = curr.next
        curr.next = prev
        prev = curr
        curr = nxt
    return prev

def has_cycle(head):
    slow = fast = head
    while fast and fast.next:
        slow = slow.next
        fast = fast.next.next
        if slow is fast:
            return True
    return False
```

---

## 4. Stacks & Queues

| | Stack (LIFO) | Queue (FIFO) |
|---|---|---|
| Push/Enqueue | O(1) | O(1) |
| Pop/Dequeue | O(1) | O(1) |
| Use cases | Undo, DFS, parentheses matching | BFS, task scheduling, buffering |

```python
from collections import deque

# Monotonic stack: next greater element
def next_greater(nums):
    result = [-1] * len(nums)
    stack = []
    for i, num in enumerate(nums):
        while stack and nums[stack[-1]] < num:
            result[stack.pop()] = num
        stack.append(i)
    return result

# Queue using two stacks
class MyQueue:
    def __init__(self):
        self.in_stack, self.out_stack = [], []
    def push(self, x):
        self.in_stack.append(x)
    def pop(self):
        self._move()
        return self.out_stack.pop()
    def _move(self):
        if not self.out_stack:
            while self.in_stack:
                self.out_stack.append(self.in_stack.pop())
```

---

## 5. Hash Tables

- **Average:** O(1) insert, delete, lookup. **Worst:** O(n) with hash collisions.
- **Collision resolution:** chaining (linked lists at each bucket), open addressing (linear/quadratic probing).
- **Load factor:** n/capacity. Rehash when load factor exceeds threshold (~0.75).

```python
# Two Sum using hash map — O(n) time, O(n) space
def two_sum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []

# Group anagrams — O(n * k log k)
from collections import defaultdict
def group_anagrams(strs):
    groups = defaultdict(list)
    for s in strs:
        groups[tuple(sorted(s))].append(s)
    return list(groups.values())
```

---

## 6. Trees

### Binary Search Tree (BST)
- **Property:** left < root < right for all subtrees.
- **Average:** O(log n) search/insert/delete. **Worst (skewed):** O(n).

### AVL Tree
- Self-balancing BST. Height difference between left and right ≤ 1.
- Guarantees O(log n) for all operations via rotations.

### Heaps (Priority Queue)
- **Min-heap:** parent ≤ children. **Max-heap:** parent ≥ children.
- **Insert:** O(log n). **Extract-min/max:** O(log n). **Peek:** O(1).
- Implemented as array: children of `i` at `2i+1`, `2i+2`. Parent at `(i-1)//2`.

```python
import heapq

# Kth largest element — O(n log k)
def kth_largest(nums, k):
    heap = nums[:k]
    heapq.heapify(heap)  # min-heap of size k
    for num in nums[k:]:
        if num > heap[0]:
            heapq.heapreplace(heap, num)
    return heap[0]

# Validate BST
def is_valid_bst(root, lo=float('-inf'), hi=float('inf')):
    if not root:
        return True
    if not (lo < root.val < hi):
        return False
    return (is_valid_bst(root.left, lo, root.val) and
            is_valid_bst(root.right, root.val, hi))

# Tree traversals
def inorder(root):
    return inorder(root.left) + [root.val] + inorder(root.right) if root else []

def level_order(root):
    if not root:
        return []
    result, queue = [], deque([root])
    while queue:
        level = []
        for _ in range(len(queue)):
            node = queue.popleft()
            level.append(node.val)
            if node.left:  queue.append(node.left)
            if node.right: queue.append(node.right)
        result.append(level)
    return result
```

---

## 7. Tries (Prefix Trees)

- Each node represents a character. Paths from root to marked nodes form stored words.
- **Insert/Search/StartsWith:** O(m) where m = word length.

```python
class TrieNode:
    def __init__(self):
        self.children = {}
        self.is_end = False

class Trie:
    def __init__(self):
        self.root = TrieNode()

    def insert(self, word):
        node = self.root
        for ch in word:
            if ch not in node.children:
                node.children[ch] = TrieNode()
            node = node.children[ch]
        node.is_end = True

    def search(self, word):
        node = self._find(word)
        return node is not None and node.is_end

    def starts_with(self, prefix):
        return self._find(prefix) is not None

    def _find(self, prefix):
        node = self.root
        for ch in prefix:
            if ch not in node.children:
                return None
            node = node.children[ch]
        return node
```

---

## 8. Graphs

### Representations
- **Adjacency list:** space O(V + E), good for sparse graphs. Most common.
- **Adjacency matrix:** space O(V²), O(1) edge lookup, good for dense graphs.

### BFS & DFS

```python
from collections import deque

def bfs(graph, start):
    visited, queue = {start}, deque([start])
    order = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for neighbor in graph[node]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
    return order

def dfs(graph, start, visited=None):
    if visited is None:
        visited = set()
    visited.add(start)
    for neighbor in graph[start]:
        if neighbor not in visited:
            dfs(graph, neighbor, visited)
    return visited
```

### Topological Sort (DAG only) — O(V + E)
```python
def topological_sort(graph, num_nodes):
    in_degree = [0] * num_nodes
    for u in graph:
        for v in graph[u]:
            in_degree[v] += 1
    queue = deque([i for i in range(num_nodes) if in_degree[i] == 0])
    order = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for neighbor in graph.get(node, []):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
    return order if len(order) == num_nodes else []  # empty = cycle
```

### Dijkstra's Shortest Path — O((V + E) log V)
```python
import heapq

def dijkstra(graph, start):
    dist = {start: 0}
    heap = [(0, start)]
    while heap:
        d, u = heapq.heappop(heap)
        if d > dist.get(u, float('inf')):
            continue
        for v, w in graph[u]:
            nd = d + w
            if nd < dist.get(v, float('inf')):
                dist[v] = nd
                heapq.heappush(heap, (nd, v))
    return dist
```

---

## 9. Sorting Algorithms

| Algorithm | Best | Average | Worst | Space | Stable |
|---|---|---|---|---|---|
| Quick Sort | O(n log n) | O(n log n) | O(n²) | O(log n) | No |
| Merge Sort | O(n log n) | O(n log n) | O(n log n) | O(n) | Yes |
| Heap Sort | O(n log n) | O(n log n) | O(n log n) | O(1) | No |
| Counting Sort | O(n + k) | O(n + k) | O(n + k) | O(k) | Yes |

```python
# Merge Sort
def merge_sort(arr):
    if len(arr) <= 1:
        return arr
    mid = len(arr) // 2
    left = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])
    return merge(left, right)

def merge(left, right):
    result, i, j = [], 0, 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            result.append(left[i]); i += 1
        else:
            result.append(right[j]); j += 1
    return result + left[i:] + right[j:]

# Quick Sort (Lomuto partition)
def quick_sort(arr, lo=0, hi=None):
    if hi is None:
        hi = len(arr) - 1
    if lo < hi:
        p = partition(arr, lo, hi)
        quick_sort(arr, lo, p - 1)
        quick_sort(arr, p + 1, hi)

def partition(arr, lo, hi):
    pivot = arr[hi]
    i = lo
    for j in range(lo, hi):
        if arr[j] < pivot:
            arr[i], arr[j] = arr[j], arr[i]
            i += 1
    arr[i], arr[hi] = arr[hi], arr[i]
    return i
```

---

## 10. Binary Search

**Pattern:** eliminate half the search space each step. O(log n).

```python
# Standard binary search
def binary_search(arr, target):
    lo, hi = 0, len(arr) - 1
    while lo <= hi:
        mid = lo + (hi - lo) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1

# Find first occurrence (lower bound)
def lower_bound(arr, target):
    lo, hi = 0, len(arr)
    while lo < hi:
        mid = lo + (hi - lo) // 2
        if arr[mid] < target:
            lo = mid + 1
        else:
            hi = mid
    return lo
```

---

## 11. Dynamic Programming

**Core idea:** break into overlapping subproblems, store results to avoid recomputation.

### Approach
1. Define the state (what subproblem are we solving?)
2. Write the recurrence relation
3. Identify base cases
4. Decide top-down (memoization) vs bottom-up (tabulation)

### Classic Patterns

```python
# 0/1 Knapsack — O(n * W) time and space
def knapsack(weights, values, W):
    n = len(weights)
    dp = [[0] * (W + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for w in range(W + 1):
            dp[i][w] = dp[i-1][w]
            if weights[i-1] <= w:
                dp[i][w] = max(dp[i][w], dp[i-1][w - weights[i-1]] + values[i-1])
    return dp[n][W]

# Longest Common Subsequence — O(m * n)
def lcs(s1, s2):
    m, n = len(s1), len(s2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s1[i-1] == s2[j-1]:
                dp[i][j] = dp[i-1][j-1] + 1
            else:
                dp[i][j] = max(dp[i-1][j], dp[i][j-1])
    return dp[m][n]

# Coin Change — O(n * amount)
def coin_change(coins, amount):
    dp = [float('inf')] * (amount + 1)
    dp[0] = 0
    for coin in coins:
        for a in range(coin, amount + 1):
            dp[a] = min(dp[a], dp[a - coin] + 1)
    return dp[amount] if dp[amount] != float('inf') else -1

# Longest Increasing Subsequence — O(n log n) with patience sorting
import bisect
def lis(nums):
    tails = []
    for num in nums:
        pos = bisect.bisect_left(tails, num)
        if pos == len(tails):
            tails.append(num)
        else:
            tails[pos] = num
    return len(tails)
```

---

## 12. Greedy Algorithms

**Principle:** make the locally optimal choice at each step, hope for a global optimum. Works when the problem has the **greedy-choice property** and **optimal substructure**.

```python
# Activity Selection — O(n log n)
def max_activities(starts, ends):
    activities = sorted(zip(starts, ends), key=lambda x: x[1])
    count, last_end = 0, 0
    for s, e in activities:
        if s >= last_end:
            count += 1
            last_end = e
    return count

# Fractional Knapsack — O(n log n)
def fractional_knapsack(items, capacity):
    items.sort(key=lambda x: x[1] / x[0], reverse=True)  # (weight, value)
    total = 0.0
    for w, v in items:
        if capacity >= w:
            total += v
            capacity -= w
        else:
            total += v * (capacity / w)
            break
    return total
```

---

## 13. Common Pitfalls

- **Off-by-one errors** in binary search and DP boundaries.
- **Not handling edge cases:** empty input, single element, all duplicates.
- **Modifying a collection while iterating** over it.
- **Integer overflow** (less of an issue in Python, critical in C++/Java).
- **Using mutable default arguments** in Python (`def f(x=[])`).
- **Forgetting to mark visited nodes** in graph traversal → infinite loops.
- **Confusing DFS/BFS properties:** DFS finds *a* path, not necessarily shortest. BFS finds shortest in unweighted graphs.

---

## 14. Interview Tips

1. **Clarify constraints:** input size, sorted?, duplicates?, negative numbers?
2. **Start with brute force**, then optimize. Interviewers want to see your thought process.
3. **State complexity** before and after optimization.
4. **Test with examples** including edge cases before saying "done."
5. **Know when to use what:** hash map for O(1) lookup, heap for top-K, stack for nested structures, BFS for shortest path.
