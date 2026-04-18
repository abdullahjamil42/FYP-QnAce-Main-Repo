# Programming (C++ / Java / Python) — Senior Interview Prep

## 1. OOP Principles

### Encapsulation
Bundling data and methods that operate on it; restricting direct access to internals.

```cpp
// C++
class BankAccount {
private:
    double balance;
public:
    BankAccount(double b) : balance(b) {}
    double getBalance() const { return balance; }
    void deposit(double amount) { if (amount > 0) balance += amount; }
};
```
```java
// Java
public class BankAccount {
    private double balance;
    public BankAccount(double balance) { this.balance = balance; }
    public double getBalance() { return balance; }
    public void deposit(double amount) { if (amount > 0) balance += amount; }
}
```
```python
# Python
class BankAccount:
    def __init__(self, balance: float):
        self._balance = balance  # convention: single underscore = protected

    @property
    def balance(self) -> float:
        return self._balance

    def deposit(self, amount: float) -> None:
        if amount > 0:
            self._balance += amount
```

### Inheritance
A class derives from another, reusing and extending behavior.

```cpp
// C++
class Shape {
public:
    virtual double area() const = 0;  // pure virtual → abstract class
    virtual ~Shape() = default;
};

class Circle : public Shape {
    double radius;
public:
    Circle(double r) : radius(r) {}
    double area() const override { return 3.14159 * radius * radius; }
};
```
```java
// Java
abstract class Shape {
    abstract double area();
}

class Circle extends Shape {
    private double radius;
    Circle(double radius) { this.radius = radius; }
    @Override
    double area() { return Math.PI * radius * radius; }
}
```
```python
# Python
from abc import ABC, abstractmethod
import math

class Shape(ABC):
    @abstractmethod
    def area(self) -> float: ...

class Circle(Shape):
    def __init__(self, radius: float):
        self.radius = radius

    def area(self) -> float:
        return math.pi * self.radius ** 2
```

### Polymorphism
Same interface, different implementations. **Compile-time** (overloading, templates/generics) and **runtime** (virtual functions / overriding).

```cpp
// C++ runtime polymorphism via virtual functions
void print_area(const Shape& s) {
    std::cout << s.area() << std::endl;  // calls correct override via vtable
}
```
```java
// Java
void printArea(Shape s) {
    System.out.println(s.area());  // dynamic dispatch
}
```
```python
# Python: duck typing — no explicit interface needed
def print_area(shape):
    print(shape.area())  # works for any object with area() method
```

### Abstraction
Exposing only essential details, hiding implementation complexity. Achieved via abstract classes and interfaces.

- **C++:** pure virtual functions (`= 0`) create abstract classes.
- **Java:** `abstract` classes and `interface` (with default methods since Java 8).
- **Python:** `ABC` + `@abstractmethod`.

---

## 2. SOLID Principles

| Principle | Meaning | Example |
|---|---|---|
| **S** — Single Responsibility | A class should have one reason to change | Separate `UserAuth` from `UserProfile` |
| **O** — Open/Closed | Open for extension, closed for modification | Add new shapes without modifying `AreaCalculator` |
| **L** — Liskov Substitution | Subtypes must be usable wherever their base type is expected | `Square` should not break `Rectangle` contract (width/height independence) |
| **I** — Interface Segregation | Many small interfaces > one fat interface | Split `Worker` into `Workable` + `Feedable` (robots don't eat) |
| **D** — Dependency Inversion | Depend on abstractions, not concretions | Inject `PaymentProcessor` interface, not `StripeProcessor` directly |

---

## 3. Design Patterns

### Singleton — Ensure only one instance exists

```python
# Python: thread-safe with module-level or using __new__
class Singleton:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```
```java
// Java: thread-safe with enum (recommended by Effective Java)
public enum DatabaseConnection {
    INSTANCE;
    public void connect() { /* ... */ }
}
```
```cpp
// C++: Meyers' Singleton (thread-safe since C++11)
class Singleton {
public:
    static Singleton& instance() {
        static Singleton s;
        return s;
    }
    Singleton(const Singleton&) = delete;
    Singleton& operator=(const Singleton&) = delete;
private:
    Singleton() = default;
};
```

### Factory Method — Defer instantiation to subclasses

```python
class Notification:
    def send(self, message: str): ...

class EmailNotification(Notification):
    def send(self, message: str):
        print(f"Email: {message}")

class SMSNotification(Notification):
    def send(self, message: str):
        print(f"SMS: {message}")

def create_notification(channel: str) -> Notification:
    factories = {"email": EmailNotification, "sms": SMSNotification}
    return factories[channel]()
```

### Observer — One-to-many dependency; when subject changes, all observers are notified

```python
class EventEmitter:
    def __init__(self):
        self._listeners: dict[str, list] = {}

    def on(self, event: str, callback):
        self._listeners.setdefault(event, []).append(callback)

    def emit(self, event: str, *args):
        for cb in self._listeners.get(event, []):
            cb(*args)

# Usage
emitter = EventEmitter()
emitter.on("user_created", lambda user: print(f"Welcome {user}"))
emitter.emit("user_created", "Alice")
```

### Strategy — Define a family of algorithms, make them interchangeable

```python
from typing import Protocol

class SortStrategy(Protocol):
    def sort(self, data: list) -> list: ...

class QuickSort:
    def sort(self, data: list) -> list:
        if len(data) <= 1: return data
        pivot = data[0]
        left = [x for x in data[1:] if x <= pivot]
        right = [x for x in data[1:] if x > pivot]
        return self.sort(left) + [pivot] + self.sort(right)

class MergeSort:
    def sort(self, data: list) -> list:
        # ... merge sort implementation
        return sorted(data)

class Sorter:
    def __init__(self, strategy: SortStrategy):
        self._strategy = strategy

    def sort(self, data: list) -> list:
        return self._strategy.sort(data)
```

### Decorator — Add behavior to objects dynamically without altering their class

```python
# Python has built-in decorator syntax
import functools
import time

def timer(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        print(f"{func.__name__} took {elapsed:.4f}s")
        return result
    return wrapper

@timer
def compute(n):
    return sum(range(n))
```

```java
// Java: Decorator pattern (structural)
interface Coffee {
    double cost();
    String description();
}

class BasicCoffee implements Coffee {
    public double cost() { return 2.0; }
    public String description() { return "Basic coffee"; }
}

class MilkDecorator implements Coffee {
    private final Coffee wrapped;
    MilkDecorator(Coffee c) { this.wrapped = c; }
    public double cost() { return wrapped.cost() + 0.5; }
    public String description() { return wrapped.description() + " + milk"; }
}
```

---

## 4. Memory Management

### Stack vs Heap

| | Stack | Heap |
|---|---|---|
| Allocation | Automatic (LIFO) | Manual (`new`/`malloc`) or GC |
| Speed | Very fast (pointer bump) | Slower (free-list search, fragmentation) |
| Size | Limited (typically 1–8 MB) | Large (limited by virtual memory) |
| Scope | Local to function | Global lifetime (until freed/GC'd) |
| Thread safety | Each thread has its own stack | Shared across threads |

### C++ Memory Model
- **RAII (Resource Acquisition Is Initialization):** tie resource lifetime to object lifetime.
- **Smart pointers (C++11+):**
  - `std::unique_ptr<T>` — exclusive ownership, no copy, zero overhead.
  - `std::shared_ptr<T>` — reference-counted shared ownership.
  - `std::weak_ptr<T>` — non-owning reference to `shared_ptr`, breaks circular references.
- **Common bugs:** dangling pointers, double free, memory leaks, use-after-free, buffer overflow.

```cpp
#include <memory>
auto ptr = std::make_unique<MyClass>(args...);  // preferred over raw new
auto shared = std::make_shared<MyClass>(args...);
```

### Java Memory Model
- **Heap:** objects and instance variables. Managed by GC.
- **Stack:** primitives, references, method frames.
- **Garbage Collectors:** Serial, Parallel, G1 (default since Java 9), ZGC (low-latency), Shenandoah.
- **GC Roots:** local variables, static fields, active threads. Reachability analysis from roots.
- **Generations:** Young (Eden + Survivor) → Old/Tenured. Minor GC (young), Major/Full GC (old).

### Python Memory Model
- **Everything is an object** on the heap. Variables are references.
- **Reference counting** + **cyclic garbage collector** (for reference cycles).
- **GIL (Global Interpreter Lock):** only one thread executes Python bytecode at a time in CPython. Limits true parallelism for CPU-bound tasks. Use `multiprocessing` or C extensions to work around.

```python
import sys
x = [1, 2, 3]
print(sys.getrefcount(x))  # reference count (includes the getrefcount arg itself)
```

---

## 5. Concurrency

### C++ Threads
```cpp
#include <thread>
#include <mutex>

std::mutex mtx;
int counter = 0;

void increment(int n) {
    for (int i = 0; i < n; ++i) {
        std::lock_guard<std::mutex> lock(mtx);  // RAII lock
        ++counter;
    }
}

int main() {
    std::thread t1(increment, 100000);
    std::thread t2(increment, 100000);
    t1.join();
    t2.join();
    // counter == 200000
}
```

### Java Threads
```java
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;

// Option 1: Runnable
Runnable task = () -> System.out.println("Running in " + Thread.currentThread().getName());
new Thread(task).start();

// Option 2: ExecutorService (preferred)
ExecutorService executor = Executors.newFixedThreadPool(4);
Future<Integer> future = executor.submit(() -> {
    Thread.sleep(1000);
    return 42;
});
System.out.println(future.get());  // blocks until complete
executor.shutdown();

// Thread-safe counter
AtomicInteger counter = new AtomicInteger(0);
counter.incrementAndGet();  // atomic, no lock needed

// synchronized keyword
class Counter {
    private int count = 0;
    public synchronized void increment() { count++; }
    public synchronized int getCount() { return count; }
}
```

### Python Concurrency
```python
# Threading (I/O-bound tasks — GIL limits CPU parallelism)
import threading

lock = threading.Lock()
counter = 0

def increment(n):
    global counter
    for _ in range(n):
        with lock:
            counter += 1

t1 = threading.Thread(target=increment, args=(100000,))
t2 = threading.Thread(target=increment, args=(100000,))
t1.start(); t2.start()
t1.join(); t2.join()

# Multiprocessing (CPU-bound tasks — bypasses GIL)
from multiprocessing import Pool

def square(x):
    return x * x

with Pool(4) as pool:
    results = pool.map(square, range(10))

# Async/Await (I/O-bound, single-threaded concurrency)
import asyncio

async def fetch_data(url: str) -> str:
    await asyncio.sleep(1)  # simulates network I/O
    return f"Data from {url}"

async def main():
    results = await asyncio.gather(
        fetch_data("url1"),
        fetch_data("url2"),
        fetch_data("url3"),
    )  # all three run concurrently
    print(results)

asyncio.run(main())
```

### Key Concepts
- **Race condition:** multiple threads access shared data with at least one write; result depends on scheduling order.
- **Deadlock:** two threads each hold a lock the other needs.
- **Livelock:** threads actively change state but make no progress.
- **Thread starvation:** a thread never gets CPU time due to other higher-priority threads.
- **volatile (Java):** ensures visibility of changes across threads (no caching in registers). Not atomic.
- **std::atomic (C++):** lock-free atomic operations for basic types.

---

## 6. Error Handling

### C++ Exceptions
```cpp
#include <stdexcept>

double divide(double a, double b) {
    if (b == 0.0) throw std::invalid_argument("division by zero");
    return a / b;
}

try {
    double result = divide(10, 0);
} catch (const std::invalid_argument& e) {
    std::cerr << "Error: " << e.what() << std::endl;
} catch (...) {
    std::cerr << "Unknown error" << std::endl;
}
// noexcept specifier: promise that function won't throw (enables optimizations)
void safe_function() noexcept { /* ... */ }
```

### Java Exceptions
```java
// Checked (must handle): IOException, SQLException
// Unchecked (runtime): NullPointerException, IllegalArgumentException

public int parseInt(String s) throws NumberFormatException {
    return Integer.parseInt(s);
}

try {
    int result = parseInt("abc");
} catch (NumberFormatException e) {
    System.err.println("Invalid number: " + e.getMessage());
} finally {
    // always executes — cleanup code
}

// Try-with-resources (AutoCloseable)
try (var reader = new BufferedReader(new FileReader("file.txt"))) {
    String line = reader.readLine();
}  // reader.close() called automatically
```

### Python Exceptions
```python
# EAFP (Easier to Ask Forgiveness than Permission) — Pythonic style
try:
    value = my_dict[key]
except KeyError:
    value = default_value

# Custom exceptions
class InsufficientFundsError(Exception):
    def __init__(self, balance, amount):
        self.balance = balance
        self.amount = amount
        super().__init__(f"Cannot withdraw {amount}: balance is {balance}")

# Context managers for cleanup
class DatabaseConnection:
    def __enter__(self):
        self.conn = connect()
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.close()
        return False  # don't suppress exceptions
```

---

## 7. Generics / Templates

### C++ Templates
```cpp
// Function template
template <typename T>
T max_val(T a, T b) {
    return (a > b) ? a : b;
}

// Class template
template <typename T>
class Stack {
    std::vector<T> data;
public:
    void push(const T& val) { data.push_back(val); }
    T pop() {
        T val = data.back();
        data.pop_back();
        return val;
    }
};
// Templates are compile-time; each instantiation generates code (code bloat possible)
```

### Java Generics
```java
// Type erasure: generics are compile-time only; at runtime, List<String> → List<Object>
public class Pair<A, B> {
    private final A first;
    private final B second;
    public Pair(A first, B second) { this.first = first; this.second = second; }
    public A getFirst() { return first; }
    public B getSecond() { return second; }
}

// Bounded type parameters
public <T extends Comparable<T>> T findMax(List<T> list) {
    return Collections.max(list);
}

// Wildcards
void printList(List<?> list) { /* read-only */ }
void addNumbers(List<? super Integer> list) { list.add(42); }
```

### Python Type Hints
```python
from typing import TypeVar, Generic

T = TypeVar("T")

class Stack(Generic[T]):
    def __init__(self):
        self._items: list[T] = []

    def push(self, item: T) -> None:
        self._items.append(item)

    def pop(self) -> T:
        return self._items.pop()

# Python generics are for static analysis only (mypy); no runtime enforcement
```

---

## 8. Lambda Expressions & Functional Features

```cpp
// C++11 lambdas
auto add = [](int a, int b) { return a + b; };
auto result = add(3, 4);

std::vector<int> nums = {3, 1, 4, 1, 5};
std::sort(nums.begin(), nums.end(), [](int a, int b) { return a > b; });

// Capture modes: [=] by value, [&] by reference, [x, &y] specific
int multiplier = 3;
auto scale = [multiplier](int x) { return x * multiplier; };
```
```java
// Java 8 lambdas (functional interfaces)
List<String> names = Arrays.asList("Charlie", "Alice", "Bob");
names.sort((a, b) -> a.compareTo(b));  // or Comparator.naturalOrder()

// Method references
names.forEach(System.out::println);

// Streams
List<String> filtered = names.stream()
    .filter(n -> n.length() > 3)
    .map(String::toUpperCase)
    .sorted()
    .collect(Collectors.toList());
```
```python
# Python lambdas (single expression only)
square = lambda x: x ** 2

# Functional tools
nums = [1, 2, 3, 4, 5]
evens = list(filter(lambda x: x % 2 == 0, nums))
doubled = list(map(lambda x: x * 2, nums))

# List comprehensions are preferred (more Pythonic)
evens = [x for x in nums if x % 2 == 0]
doubled = [x * 2 for x in nums]
```

---

## 9. Iterators & Collections

### C++ STL Containers
| Container | Access | Insert/Delete | Use Case |
|---|---|---|---|
| `vector` | O(1) | O(n) / amortized O(1) push_back | Default choice |
| `deque` | O(1) | O(1) front/back | Double-ended queue |
| `list` | O(n) | O(1) at iterator | Frequent mid-insertion |
| `map` / `set` | O(log n) | O(log n) | Ordered key-value / unique elements |
| `unordered_map/set` | O(1) avg | O(1) avg | Hash-based, fastest lookup |

### Java Collections Framework
| Interface | Implementations | Notes |
|---|---|---|
| `List` | `ArrayList`, `LinkedList` | Ordered, allows duplicates |
| `Set` | `HashSet`, `TreeSet`, `LinkedHashSet` | No duplicates |
| `Map` | `HashMap`, `TreeMap`, `LinkedHashMap`, `ConcurrentHashMap` | Key-value pairs |
| `Queue` | `LinkedList`, `PriorityQueue`, `ArrayDeque` | FIFO or priority |

```java
// Java iterator
List<String> names = new ArrayList<>(List.of("Alice", "Bob", "Charlie"));
Iterator<String> it = names.iterator();
while (it.hasNext()) {
    String name = it.next();
    if (name.startsWith("B")) it.remove();  // safe removal during iteration
}
```

### Python Collections
```python
from collections import defaultdict, Counter, deque, OrderedDict

# defaultdict — auto-initializes missing keys
word_count = defaultdict(int)
for word in words:
    word_count[word] += 1

# Counter — counting made easy
counter = Counter("abracadabra")
# Counter({'a': 5, 'b': 2, 'r': 2, 'c': 1, 'd': 1})
counter.most_common(2)  # [('a', 5), ('b', 2)]

# deque — O(1) append/pop from both ends
dq = deque([1, 2, 3])
dq.appendleft(0)  # [0, 1, 2, 3]
dq.pop()           # 3

# Python iterators and generators
def fibonacci():
    a, b = 0, 1
    while True:
        yield a
        a, b = b, a + b

fib = fibonacci()
first_10 = [next(fib) for _ in range(10)]
```

---

## 10. Language-Specific Gotchas

### C++
- **Undefined behavior:** accessing freed memory, signed integer overflow, null dereference. Compiler can do *anything*.
- **Slicing:** assigning derived class to base class value type strips derived data. Use pointers/references for polymorphism.
- **Rule of Five (C++11):** if you define any of destructor, copy constructor, copy assignment, move constructor, move assignment — define all five.
- **const correctness:** use `const` on methods that don't modify state, parameters you don't modify. Catches bugs at compile time.

### Java
- **`==` vs `.equals()`:** `==` compares references; `.equals()` compares values. Always use `.equals()` for strings and objects.
- **String immutability:** `String` is immutable; use `StringBuilder` for concatenation in loops.
- **Autoboxing overhead:** `Integer` vs `int`. Autoboxing creates objects; use primitives in performance-critical code.
- **`hashCode` contract:** if you override `equals()`, you must override `hashCode()`. Equal objects must have equal hash codes.

### Python
- **Mutable default arguments:** `def f(x=[])` shares the same list across calls. Use `def f(x=None): x = x or []`.
- **Shallow vs deep copy:** `list.copy()` / `copy.copy()` are shallow (nested objects shared). Use `copy.deepcopy()` for nested structures.
- **`is` vs `==`:** `is` checks identity (same object in memory); `==` checks equality (value). Use `is` only for `None`, `True`, `False`.
- **Integer caching:** CPython caches integers -5 to 256. `a = 256; b = 256; a is b` → True. `a = 257; b = 257; a is b` → may be False.
- **List comprehension vs generator:** `[x for x in range(10**8)]` allocates all in memory. `(x for x in range(10**8))` is lazy.

---

## 11. Common Interview Questions

1. **"Explain polymorphism with an example."** — Runtime (virtual functions/overriding: same method name, different behavior based on actual object type) vs compile-time (overloading, templates). Use the Shape/area example.

2. **"What is the diamond problem?"** — Ambiguity when a class inherits from two classes that share a common ancestor. C++: solved with virtual inheritance. Java: no multiple class inheritance; interfaces with default methods use `super` disambiguation. Python: Method Resolution Order (MRO, C3 linearization).

3. **"Explain garbage collection."** — Automatic memory reclamation. Java: generational GC (young/old), mark-and-sweep, G1 regions. Python: reference counting + cyclic GC. C++: no GC; use RAII and smart pointers.

4. **"When would you use composition over inheritance?"** — When you need "has-a" not "is-a". Avoids fragile base class problem, more flexible. Favor composition unless there's a clear type hierarchy.

5. **"What is dependency injection?"** — Providing dependencies from outside rather than creating them internally. Makes code testable (inject mocks), follows Dependency Inversion Principle. Frameworks: Spring (Java), FastAPI Depends (Python).

---

## 12. Pitfalls & Best Practices

- **Premature optimization:** profile first, optimize the bottleneck. Knuth: "premature optimization is the root of all evil."
- **Ignoring thread safety:** shared mutable state without synchronization = race conditions.
- **Not using standard library:** don't implement your own sort, hash map, etc. unless for learning.
- **Magic numbers:** use named constants instead of `if (status == 3)`.
- **Deep inheritance hierarchies:** keep to 2–3 levels max. Prefer composition.
- **Catching generic exceptions:** catch specific exception types; don't swallow errors silently.
- **Not closing resources:** use RAII (C++), try-with-resources (Java), context managers (Python).
