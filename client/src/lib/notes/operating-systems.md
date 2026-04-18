# Operating Systems — Senior Interview Prep

## 1. Process vs Thread

| | Process | Thread |
|---|---|---|
| Memory | Own address space | Shares parent process address space |
| Creation cost | High (fork, copy-on-write) | Low (shared memory, new stack) |
| Communication | IPC (pipes, sockets, shared memory) | Direct shared memory access |
| Crash isolation | One process crash doesn't affect others | One thread crash can kill the entire process |
| Context switch | Expensive (TLB flush, page table swap) | Cheaper (same address space) |

**Key point:** Threads within a process share heap, global variables, file descriptors but have their own stack, registers, and program counter.

### User-level vs Kernel-level Threads
- **User-level:** managed by user-space library, OS unaware. Fast switching, but one blocking syscall blocks all threads.
- **Kernel-level:** managed by OS. True parallelism on multicore. Higher overhead for creation/switching.
- **Hybrid (M:N):** M user threads mapped to N kernel threads. Best of both worlds. Used by Go (goroutines → OS threads).

---

## 2. Context Switching

The process of saving the state of one process/thread and loading the state of another.

**Steps:**
1. Save current process state (PC, registers, stack pointer) to its PCB (Process Control Block).
2. Update process state (running → ready/waiting).
3. Select next process (scheduling algorithm).
4. Load new process state from its PCB.
5. Flush TLB (for process switches, not thread switches within same process).

**Cost:** typically 1–10 microseconds. Involves cache pollution (cold cache for new process), TLB misses, pipeline flush.

---

## 3. CPU Scheduling Algorithms

| Algorithm | Preemptive? | Pros | Cons |
|---|---|---|---|
| **FCFS** (First Come First Served) | No | Simple, fair | Convoy effect (short jobs behind long ones) |
| **SJF** (Shortest Job First) | No | Optimal average wait time | Requires knowing burst time; starvation of long jobs |
| **SRTF** (Shortest Remaining Time First) | Yes | Optimal preemptive variant of SJF | Same issues + overhead of preemption |
| **Round Robin** | Yes | Fair, good response time | High context switch overhead if quantum too small |
| **Priority Scheduling** | Yes/No | Important tasks first | Starvation (solved by aging) |
| **Multilevel Feedback Queue** | Yes | Adaptive, balances throughput and response | Complex to tune |

### Key Metrics
- **Turnaround time:** completion time − arrival time.
- **Waiting time:** turnaround time − burst time.
- **Response time:** first execution − arrival time (critical for interactive systems).
- **Throughput:** number of processes completed per unit time.

### Round Robin Example
```
Processes: P1(burst=10), P2(burst=4), P3(burst=6); quantum=4
Timeline:
  [0-4]  P1 runs (6 remaining)
  [4-8]  P2 runs (0 remaining, done)
  [8-12] P3 runs (2 remaining)
  [12-16] P1 runs (2 remaining)
  [16-18] P3 runs (0 remaining, done)
  [18-20] P1 runs (0 remaining, done)
Average waiting time = (10 + 4 + 12) / 3 = 8.67
```

---

## 4. Memory Management

### Address Space Layout
```
High addresses → Stack (grows downward: local variables, return addresses)
                 ↓
                 (free space)
                 ↑
                 Heap (grows upward: malloc/new allocations)
                 BSS (uninitialized global/static variables)
                 Data (initialized global/static variables)
Low addresses  → Text/Code (program instructions, read-only)
```

### Paging
- Physical memory divided into fixed-size **frames**; logical memory into same-size **pages** (typically 4 KB).
- **Page table:** maps virtual page numbers → physical frame numbers.
- **TLB (Translation Lookaside Buffer):** hardware cache for recent page table entries. TLB miss → page table walk.
- **Multi-level page tables:** reduce memory overhead. x86-64 uses 4-level page tables.

### Segmentation
- Memory divided into variable-size segments (code, stack, heap) with base + limit.
- Can be combined with paging (segmented paging).

### Virtual Memory
- Allows processes to use more memory than physically available.
- **Page fault:** accessing a page not in RAM → OS loads it from disk (swap space).
- **Demand paging:** pages loaded only when accessed, not at program start.
- **Thrashing:** excessive page faults because working set > available RAM. CPU spends all time swapping. Solution: reduce degree of multiprogramming, increase RAM.

---

## 5. Page Replacement Algorithms

When a page fault occurs and no free frames exist, the OS must evict a page.

| Algorithm | Description | Optimal? |
|---|---|---|
| **FIFO** | Evict oldest page | No. Suffers Belady's anomaly |
| **LRU** | Evict least recently used page | Near-optimal. Expensive to implement exactly |
| **Optimal (OPT)** | Evict page not used for longest future time | Yes, but requires future knowledge (benchmark only) |
| **Clock (Second Chance)** | FIFO with reference bit; skip recently used pages | Approximation of LRU |
| **LFU** | Evict least frequently used | Can retain stale popular pages |

### Example: LRU with 3 frames
```
Reference string: 7, 0, 1, 2, 0, 3, 0, 4
Frames:
  7       → [7]            fault
  0       → [7, 0]         fault
  1       → [7, 0, 1]      fault
  2       → [0, 1, 2]      fault (evict 7, LRU)
  0       → [0, 1, 2]      hit
  3       → [0, 2, 3]      fault (evict 1, LRU)
  0       → [0, 2, 3]      hit
  4       → [0, 3, 4]      fault (evict 2, LRU)
Total faults: 6
```

**Belady's anomaly:** with FIFO, increasing frames can *increase* page faults. LRU and OPT are immune (they are stack algorithms).

---

## 6. Deadlocks

### Four Necessary Conditions (Coffman Conditions)
All four must hold simultaneously for a deadlock:
1. **Mutual Exclusion:** at least one resource is non-sharable.
2. **Hold and Wait:** a process holds resources while waiting for others.
3. **No Preemption:** resources cannot be forcibly taken away.
4. **Circular Wait:** a cycle exists in the resource allocation graph.

### Handling Strategies

**Prevention** (break one of the four conditions):
- Break hold-and-wait: request all resources at once.
- Break circular wait: impose a total ordering on resources; always acquire in order.
- Break no preemption: allow OS to preempt resources.

**Avoidance** (Banker's Algorithm):
- Before granting a resource, check if the system remains in a **safe state** (a sequence exists where all processes can eventually finish).
- Requires knowing maximum resource needs in advance.

**Detection and Recovery:**
- Periodically run cycle detection on resource allocation graph.
- Recovery: kill a process, preempt resources, or rollback.

**Ignore (Ostrich Algorithm):** if deadlocks are rare and cost of prevention is high, simply reboot. Used by most general-purpose OSes.

### Banker's Algorithm Overview
```
Available: [3, 3, 2]
Process  Max    Allocation  Need (Max - Alloc)
P0       [7,5,3]  [0,1,0]    [7,4,3]
P1       [3,2,2]  [2,0,0]    [1,2,2]
P2       [9,0,2]  [3,0,2]    [6,0,0]
P3       [2,2,2]  [2,1,1]    [0,1,1]
P4       [4,3,3]  [0,0,2]    [4,3,1]

Safe sequence: P1 → P3 → P4 → P2 → P0
(Each process can finish with current Available + its Allocation returned)
```

---

## 7. Synchronization Primitives

### Mutex (Mutual Exclusion Lock)
- Binary lock: locked/unlocked. Only the owner can unlock.
- Used for protecting critical sections.

### Semaphore
- **Counting semaphore:** integer ≥ 0. `wait()` decrements; `signal()` increments. Blocks when 0.
- **Binary semaphore:** value 0 or 1. Similar to mutex but any thread can signal.
- Used for controlling access to a pool of resources (e.g., connection pool of size N).

### Monitor
- High-level synchronization construct (built into Java with `synchronized`).
- Encapsulates shared data + operations + condition variables.
- Only one thread can execute inside the monitor at a time.

### Condition Variable
- Allows threads to wait for a condition: `wait()` releases lock and blocks; `signal()` / `broadcast()` wakes waiting threads.
- Always paired with a mutex.

### Classic Synchronization Problems
- **Producer-Consumer (Bounded Buffer):** semaphores for empty/full slots + mutex for buffer access.
- **Readers-Writers:** multiple readers OR one writer. Variants: reader-priority, writer-priority.
- **Dining Philosophers:** 5 philosophers, 5 forks. Solutions: resource ordering, waiter (semaphore), Chandy/Misra.

---

## 8. Inter-Process Communication (IPC)

| Method | Description | Use Case |
|---|---|---|
| **Pipe** | Unidirectional byte stream between related processes | Shell pipelines (`ls | grep`) |
| **Named Pipe (FIFO)** | Like pipe but has a filesystem name; unrelated processes | Client-server on same machine |
| **Message Queue** | Kernel-managed queue of messages | Structured data exchange |
| **Shared Memory** | Both processes map same physical memory region | High-throughput data sharing |
| **Socket** | Network-capable, bidirectional | Client-server (local or remote) |
| **Signal** | Asynchronous notification to a process | SIGTERM, SIGKILL, SIGCHLD |
| **Memory-mapped file** | File mapped into address space | Large data sharing, persistence |

**Shared memory** is fastest (no kernel involvement after setup) but requires explicit synchronization (semaphores/mutexes).

---

## 9. File Systems

### Key Concepts
- **Inode:** metadata structure storing file attributes (size, permissions, timestamps, pointers to data blocks). Does NOT store the filename.
- **Directory:** maps filenames → inode numbers.
- **Hard link:** another directory entry pointing to the same inode. Deleting one link doesn't delete the file until link count = 0.
- **Soft link (symlink):** a separate file containing a path to the target. Can break if target is deleted.

### Allocation Methods
- **Contiguous:** fast sequential access, external fragmentation.
- **Linked:** each block points to next. No fragmentation, slow random access.
- **Indexed (inode-based):** inode contains block pointers. Used by ext4, NTFS. Direct + indirect + double-indirect pointers for large files.

### Common File Systems
- **ext4:** Linux default. Journaling, extents (contiguous block ranges), max file size 16 TB.
- **NTFS:** Windows. ACLs, journaling, compression, encryption.
- **ZFS/Btrfs:** Copy-on-write, checksums, snapshots, RAID built-in.

### Journaling
- Write-ahead log of metadata changes. On crash, replay journal to restore consistency.
- **Full journaling:** journal both metadata and data (slower, safer).
- **Ordered journaling (ext4 default):** journal metadata, write data before metadata commit.

---

## 10. I/O Management

### I/O Methods
- **Programmed I/O (Polling):** CPU continuously checks device status. Simple, wastes CPU.
- **Interrupt-driven I/O:** device interrupts CPU when ready. CPU free between operations.
- **DMA (Direct Memory Access):** device transfers data directly to/from memory without CPU. CPU involved only at start and end. Used for disk, network.

### Disk Scheduling (for traditional HDDs)
- **FCFS:** fair, poor seek optimization.
- **SSTF (Shortest Seek Time First):** closest request first. Low average seek but starvation possible.
- **SCAN (Elevator):** arm moves in one direction servicing requests, reverses at end. No starvation.
- **C-SCAN:** like SCAN but only services in one direction, then jumps back. More uniform wait times.

> Note: SSDs have no seek time, so disk scheduling is largely irrelevant for SSDs. I/O schedulers for SSDs focus on queue depth and parallelism (e.g., `noop`/`none` scheduler).

---

## 11. System Calls & Kernel Mode

- **User mode:** restricted access, cannot directly access hardware or kernel memory.
- **Kernel mode:** full hardware access. Entered via system calls, interrupts, or exceptions.
- **System call flow:** user program → trap instruction → kernel handler → execute → return to user mode.

Common system calls: `fork()`, `exec()`, `wait()`, `open()`, `read()`, `write()`, `close()`, `mmap()`, `ioctl()`.

### Fork and Exec
```
fork(): creates a child process (copy of parent via copy-on-write)
  - Returns 0 to child, child PID to parent
exec(): replaces current process image with new program
  - fork() + exec() = how shells launch programs
```

---

## 12. Common Interview Questions

1. **"What happens when you type a URL in the browser?"**
   - DNS resolution → TCP handshake → TLS handshake → HTTP request → Server processing → HTTP response → Browser rendering.
   - OS involvement: socket creation (syscall), process/thread for handling, network stack (TCP/IP), file system (cache), memory allocation.

2. **"Explain zombie and orphan processes."**
   - **Zombie:** child has terminated but parent hasn't called `wait()`. Entry remains in process table. Cleaned up when parent reads exit status.
   - **Orphan:** parent terminates before child. Child is adopted by `init`/`systemd` (PID 1), which calls `wait()` for cleanup.

3. **"How does virtual memory work?"**
   - Each process has its own virtual address space mapped to physical memory via page tables. Pages can be swapped to disk. MMU + TLB handle translation in hardware.

4. **"What causes thrashing and how do you fix it?"**
   - Too many processes competing for limited RAM → constant page faults. Fix: reduce multiprogramming, use working set model, increase RAM.

5. **"Compare mutex and semaphore."**
   - Mutex: binary, ownership (only locker can unlock), used for mutual exclusion.
   - Semaphore: counting, no ownership, used for signaling and resource counting.

---

## 13. Key Terminology Quick Reference

| Term | Definition |
|---|---|
| **PCB** | Process Control Block — stores process state, PC, registers, scheduling info |
| **TCB** | Thread Control Block — lighter-weight, stores thread-specific state |
| **MMU** | Memory Management Unit — hardware for virtual-to-physical translation |
| **TLB** | Translation Lookaside Buffer — cache for page table entries |
| **Working Set** | Set of pages a process is actively using in a time window |
| **Starvation** | A process waits indefinitely because others always get resources first |
| **Convoy Effect** | Short processes stuck behind a long-running process (FCFS problem) |
| **Race Condition** | Output depends on unpredictable timing of concurrent operations |
| **Critical Section** | Code region accessing shared resources that must be executed atomically |
| **Spin Lock** | Lock that busy-waits in a loop; good for very short critical sections |

---

## 14. Pitfalls

- **Confusing preemptive vs non-preemptive scheduling.** SJF is non-preemptive; SRTF is its preemptive version.
- **Thinking more frames always reduce page faults.** Belady's anomaly disproves this for FIFO.
- **Mixing up mutex and binary semaphore.** Mutex has ownership; binary semaphore does not.
- **Forgetting copy-on-write in fork().** Modern OSes don't physically copy memory on fork; they mark pages COW and copy on write.
- **Confusing internal vs external fragmentation.** Internal: wasted space within allocated blocks (fixed partitions, paging). External: free space is fragmented into small non-contiguous chunks (variable partitions, segmentation).
