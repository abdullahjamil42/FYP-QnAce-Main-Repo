# Problem Solving and Analytical Skills — Interview Prep Notes

## 1. Systematic Approach to Coding Problems

### The 4-Step Framework

#### Step 1: Understand the Problem
- Read the problem **twice**. Restate it in your own words.
- Identify **inputs** (types, ranges, constraints) and **outputs** (format, edge cases).
- Ask clarifying questions: "Can the array be empty?", "Are values always positive?", "Is the input sorted?"
- Walk through **examples** — including edge cases you invent.

#### Step 2: Plan Your Approach
- Identify the **pattern** (see Section 2 below).
- Start with brute force, then optimize.
- Think about **data structures** that help: hash map for O(1) lookup, heap for top-k, stack for matching.
- State your **time and space complexity** before coding.

#### Step 3: Implement
- Write clean, readable code with meaningful variable names.
- Handle edge cases upfront (empty input, single element, etc.).
- Don't optimize prematurely — correctness first.

#### Step 4: Verify
- Trace through your code with the given examples.
- Test edge cases: empty input, single element, all same values, very large input.
- Check off-by-one errors, especially in loops and binary search.

**Interview tip**: Always verbalize your thought process. Silence is your enemy.

---

## 2. Core Problem-Solving Patterns

### Pattern 1: Two Pointers
**When to use**: Sorted arrays, finding pairs, palindromes, partitioning.

**How it works**: Use two pointers moving toward each other or in the same direction.

```python
# Two Sum (sorted array)
def two_sum_sorted(nums, target):
    left, right = 0, len(nums) - 1
    while left < right:
        total = nums[left] + nums[right]
        if total == target:
            return [left, right]
        elif total < target:
            left += 1
        else:
            right -= 1
    return []

# Remove duplicates in-place from sorted array
def remove_duplicates(nums):
    if not nums:
        return 0
    write = 1
    for read in range(1, len(nums)):
        if nums[read] != nums[read - 1]:
            nums[write] = nums[read]
            write += 1
    return write
```

**Classic problems**: Container With Most Water, 3Sum, Trapping Rain Water, Valid Palindrome.

---

### Pattern 2: Sliding Window
**When to use**: Contiguous subarrays/substrings, maximum/minimum in window, string matching.

**How it works**: Expand window right, shrink from left when condition violated.

```python
# Longest substring without repeating characters
def length_of_longest_substring(s):
    seen = {}
    left = 0
    max_len = 0
    for right, char in enumerate(s):
        if char in seen and seen[char] >= left:
            left = seen[char] + 1
        seen[char] = right
        max_len = max(max_len, right - left + 1)
    return max_len

# Minimum window substring
def min_window(s, t):
    from collections import Counter
    need = Counter(t)
    missing = len(t)
    left = 0
    best = (0, float('inf'))
    for right, char in enumerate(s):
        if need[char] > 0:
            missing -= 1
        need[char] -= 1
        while missing == 0:
            if right - left < best[1] - best[0]:
                best = (left, right)
            need[s[left]] += 1
            if need[s[left]] > 0:
                missing += 1
            left += 1
    return "" if best[1] == float('inf') else s[best[0]:best[1] + 1]
```

**Classic problems**: Maximum Sum Subarray of Size K, Minimum Window Substring, Longest Repeating Character Replacement.

---

### Pattern 3: Binary Search
**When to use**: Sorted data, searching for a boundary, optimization problems ("minimum x such that...").

**How it works**: Eliminate half the search space each iteration.

```python
# Standard binary search
def binary_search(nums, target):
    lo, hi = 0, len(nums) - 1
    while lo <= hi:
        mid = lo + (hi - lo) // 2  # Avoids overflow
        if nums[mid] == target:
            return mid
        elif nums[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1

# Binary search on answer space (Koko eating bananas)
def min_eating_speed(piles, h):
    import math
    lo, hi = 1, max(piles)
    while lo < hi:
        mid = lo + (hi - lo) // 2
        hours = sum(math.ceil(p / mid) for p in piles)
        if hours <= h:
            hi = mid       # mid might be the answer, search left
        else:
            lo = mid + 1   # mid too slow, search right
    return lo
```

**Key insight**: Binary search works on any **monotonic function**, not just sorted arrays. If f(x) is true for all x ≥ k, binary search finds k.

**Classic problems**: Search in Rotated Sorted Array, Find First and Last Position, Median of Two Sorted Arrays.

---

### Pattern 4: BFS (Breadth-First Search)
**When to use**: Shortest path in unweighted graph, level-order traversal, minimum steps.

```python
from collections import deque

# BFS shortest path in grid
def shortest_path(grid):
    rows, cols = len(grid), len(grid[0])
    queue = deque([(0, 0, 0)])  # (row, col, distance)
    visited = {(0, 0)}
    while queue:
        r, c, dist = queue.popleft()
        if r == rows - 1 and c == cols - 1:
            return dist
        for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and (nr, nc) not in visited and grid[nr][nc] == 0:
                visited.add((nr, nc))
                queue.append((nr, nc, dist + 1))
    return -1

# Level-order tree traversal
def level_order(root):
    if not root:
        return []
    result = []
    queue = deque([root])
    while queue:
        level = []
        for _ in range(len(queue)):
            node = queue.popleft()
            level.append(node.val)
            if node.left:
                queue.append(node.left)
            if node.right:
                queue.append(node.right)
        result.append(level)
    return result
```

---

### Pattern 5: DFS (Depth-First Search)
**When to use**: Exploring all paths, connected components, tree problems, permutations/combinations.

```python
# Number of islands
def num_islands(grid):
    def dfs(r, c):
        if r < 0 or r >= len(grid) or c < 0 or c >= len(grid[0]) or grid[r][c] != '1':
            return
        grid[r][c] = '0'  # Mark visited
        for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            dfs(r + dr, c + dc)

    count = 0
    for r in range(len(grid)):
        for c in range(len(grid[0])):
            if grid[r][c] == '1':
                dfs(r, c)
                count += 1
    return count

# Path sum in binary tree (all paths)
def path_sum(root, target):
    results = []
    def dfs(node, remaining, path):
        if not node:
            return
        path.append(node.val)
        if not node.left and not node.right and remaining == node.val:
            results.append(list(path))
        dfs(node.left, remaining - node.val, path)
        dfs(node.right, remaining - node.val, path)
        path.pop()  # Backtrack
    dfs(root, target, [])
    return results
```

---

### Pattern 6: Dynamic Programming
**When to use**: Overlapping subproblems + optimal substructure. Look for "minimum/maximum", "number of ways", "is it possible".

**Approach**: Define state → recurrence relation → base cases → build bottom-up (or memoize top-down).

```python
# 0/1 Knapsack
def knapsack(weights, values, capacity):
    n = len(weights)
    dp = [[0] * (capacity + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for w in range(capacity + 1):
            dp[i][w] = dp[i - 1][w]  # Don't take item i
            if weights[i - 1] <= w:
                dp[i][w] = max(dp[i][w], dp[i - 1][w - weights[i - 1]] + values[i - 1])
    return dp[n][capacity]

# Longest Common Subsequence
def lcs(text1, text2):
    m, n = len(text1), len(text2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if text1[i - 1] == text2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    return dp[m][n]

# Climbing stairs (space-optimized)
def climb_stairs(n):
    if n <= 2:
        return n
    prev2, prev1 = 1, 2
    for _ in range(3, n + 1):
        prev2, prev1 = prev1, prev2 + prev1
    return prev1
```

**DP classification**: 1D (Fibonacci, House Robber), 2D (LCS, Edit Distance, Grid Paths), Interval (Matrix Chain), Bitmask (TSP), Tree DP.

**Classic problems**: Coin Change, Longest Increasing Subsequence, Edit Distance, Word Break, Partition Equal Subset Sum.

---

### Pattern 7: Greedy
**When to use**: Local optimal choices lead to global optimal. Prove via exchange argument or greedy stays ahead.

```python
# Activity selection / meeting rooms
def max_meetings(intervals):
    intervals.sort(key=lambda x: x[1])  # Sort by end time
    count = 0
    last_end = float('-inf')
    for start, end in intervals:
        if start >= last_end:
            count += 1
            last_end = end
    return count

# Jump Game (can you reach the end?)
def can_jump(nums):
    farthest = 0
    for i in range(len(nums)):
        if i > farthest:
            return False
        farthest = max(farthest, i + nums[i])
    return True
```

**Classic problems**: Activity Selection, Huffman Coding, Fractional Knapsack, Task Scheduler, Gas Station.

---

### Pattern 8: Backtracking
**When to use**: Generate all valid configurations, constraint satisfaction, combinatorial search.

**Template**: Choose → Explore → Unchoose.

```python
# Generate all subsets
def subsets(nums):
    result = []
    def backtrack(start, path):
        result.append(list(path))
        for i in range(start, len(nums)):
            path.append(nums[i])
            backtrack(i + 1, path)
            path.pop()
    backtrack(0, [])
    return result

# N-Queens
def solve_n_queens(n):
    results = []
    def backtrack(row, cols, diag1, diag2, board):
        if row == n:
            results.append(["".join(r) for r in board])
            return
        for col in range(n):
            if col in cols or (row - col) in diag1 or (row + col) in diag2:
                continue
            board[row][col] = 'Q'
            backtrack(row + 1, cols | {col}, diag1 | {row - col}, diag2 | {row + col}, board)
            board[row][col] = '.'
    backtrack(0, set(), set(), set(), [['.' for _ in range(n)] for _ in range(n)])
    return results
```

**Classic problems**: Permutations, Combinations, Sudoku Solver, Word Search, Palindrome Partitioning.

---

### Pattern 9: Divide and Conquer
**When to use**: Problem can be split into independent subproblems, combined in O(n) or O(n log n).

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
    result = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            result.append(left[i]); i += 1
        else:
            result.append(right[j]); j += 1
    result.extend(left[i:])
    result.extend(right[j:])
    return result

# Count inversions (modified merge sort)
def count_inversions(arr):
    if len(arr) <= 1:
        return arr, 0
    mid = len(arr) // 2
    left, left_inv = count_inversions(arr[:mid])
    right, right_inv = count_inversions(arr[mid:])
    merged, split_inv = merge_count(left, right)
    return merged, left_inv + right_inv + split_inv
```

**Classic problems**: Merge Sort, Quick Sort, Closest Pair of Points, Maximum Subarray (Kadane's is better).

---

### Pattern 10: Union-Find (Disjoint Set Union)
**When to use**: Connected components, cycle detection, grouping elements.

```python
class UnionFind:
    def __init__(self, n):
        self.parent = list(range(n))
        self.rank = [0] * n
        self.components = n

    def find(self, x):
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])  # Path compression
        return self.parent[x]

    def union(self, x, y):
        px, py = self.find(x), self.find(y)
        if px == py:
            return False
        if self.rank[px] < self.rank[py]:
            px, py = py, px
        self.parent[py] = px                              # Union by rank
        if self.rank[px] == self.rank[py]:
            self.rank[px] += 1
        self.components -= 1
        return True
```

**Classic problems**: Number of Connected Components, Redundant Connection, Accounts Merge, Kruskal's MST.

---

### Pattern 11: Topological Sort
**When to use**: Dependency ordering, course scheduling, build systems.

```python
# Kahn's Algorithm (BFS-based)
from collections import deque, defaultdict

def topological_sort(num_nodes, edges):
    graph = defaultdict(list)
    in_degree = [0] * num_nodes
    for u, v in edges:
        graph[u].append(v)
        in_degree[v] += 1

    queue = deque([i for i in range(num_nodes) if in_degree[i] == 0])
    order = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for neighbor in graph[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    return order if len(order) == num_nodes else []  # Empty = cycle detected
```

**Classic problems**: Course Schedule, Alien Dictionary, Task Scheduling.

---

## 3. Communicating Your Approach

### What interviewers want to hear:
1. **Restate the problem**: "So we need to find..."
2. **Discuss constraints**: "Since n can be up to 10⁵, we need O(n log n) or better."
3. **Propose brute force first**: "The naive approach would be O(n²) by checking all pairs..."
4. **Optimize**: "We can improve this by using a hash map to get O(n)."
5. **State complexity before coding**: "This will be O(n) time and O(n) space."
6. **Narrate while coding**: "Here I'm initializing the left pointer... now I'll expand the window..."

### Red flags interviewers watch for:
- Jumping straight into code without understanding the problem
- Not considering edge cases
- Silent coding without explaining thought process
- Getting stuck and not asking for hints
- Not testing your solution at the end

---

## 4. Time Complexity Optimization Strategies

| From | To | Technique |
|------|----|-----------|
| O(n²) → O(n log n) | Sort + Two Pointers or Binary Search |
| O(n²) → O(n) | Hash Map for O(1) lookup |
| O(2ⁿ) → O(n·W) | Dynamic Programming (memoization) |
| O(n) → O(log n) | Binary Search |
| O(n log n) → O(n) | Counting Sort / Bucket Sort (limited range) |
| O(V²) → O(E log V) | Priority queue (Dijkstra's) |

### Space-Time Tradeoffs
- **Hash maps**: Trade O(n) space for O(1) lookup
- **DP table**: Trade O(n²) space for avoiding recomputation
- **Sorting**: O(n log n) time but enables O(n) solutions via two pointers
- **Precomputation**: Prefix sums, sparse tables, suffix arrays

---

## 5. Edge Case Identification Checklist

- **Empty input**: [], "", None
- **Single element**: [1], "a"
- **All same values**: [5, 5, 5, 5]
- **Already sorted / reverse sorted**
- **Negative numbers**: [-1, -2, 3]
- **Zero**: Division by zero, zero as input
- **Very large input**: Integer overflow, n = 10⁶
- **Duplicate values**: Do they affect uniqueness constraints?
- **Boundary values**: First element, last element, min/max integers
- **Disconnected graph**: Not all nodes reachable
- **Cycle in graph**: Will DFS/BFS terminate?

---

## 6. Debugging Strategies

1. **Print intermediate state**: Add print statements at key decision points.
2. **Trace with small input**: Walk through line-by-line with a 3-4 element example.
3. **Verify loop invariants**: What should be true at the start/end of each iteration?
4. **Check off-by-one**: Loop bounds, array indexing, binary search boundaries.
5. **Simplify**: If complex logic fails, break it into smaller helper functions.
6. **Test the opposite**: If your solution says "True", construct a case where it should say "False" to confirm.

---

## 7. Handling Problems You've Never Seen

1. **Don't panic.** Every problem is built from fundamental patterns.
2. **Classify the problem**: Is it a graph, tree, array, string, math problem?
3. **Identify constraints**: n ≤ 20 → backtracking/bitmask. n ≤ 10⁵ → O(n log n). n ≤ 10⁸ → O(n).
4. **Try brute force first**: Often reveals the structure needed for optimization.
5. **Work backwards**: From desired output, what information do you need?
6. **Think about what data structure would help**: Hash set for seen elements? Stack for matching? Heap for priority?
7. **Look for greedy signals**: "Minimum number of...", "Maximum profit..." — try sorting.
8. **Draw it out**: For graphs, trees, and grids, draw the example.

---

## 8. Whiteboard Coding Tips

- **Write small** — you'll need more space than you think.
- **Leave space between lines** for edits.
- **Use helper functions** — don't try to write it all in one function.
- **Use descriptive names** — not `i, j, k` for everything. `left, right, window_sum` are better.
- **Start from the top-left** corner and work down.
- **If you make a mistake**, cross out and rewrite rather than erasing everything.
- **Step through your code** with a concrete example when done.

---

## 9. Essential Data Structure Complexity Reference

| Data Structure | Access | Search | Insert | Delete |
|----------------|--------|--------|--------|--------|
| Array | O(1) | O(n) | O(n) | O(n) |
| Hash Map | — | O(1)* | O(1)* | O(1)* |
| BST (balanced) | — | O(log n) | O(log n) | O(log n) |
| Heap | O(1) top | O(n) | O(log n) | O(log n) |
| Stack/Queue | O(1) top | O(n) | O(1) | O(1) |
| Linked List | O(n) | O(n) | O(1) | O(1) |
| Trie | — | O(m) | O(m) | O(m) |

*amortized

### When to use what:
- **Need O(1) lookup?** → Hash Map / Hash Set
- **Need sorted order + fast insert?** → Balanced BST (or SortedList in Python)
- **Need min/max quickly?** → Heap (heapq)
- **Need LIFO?** → Stack (list in Python)
- **Need FIFO?** → Queue (collections.deque)
- **Need prefix matching?** → Trie
- **Need range queries?** → Segment Tree / BIT
- **Need union/membership?** → Union-Find
