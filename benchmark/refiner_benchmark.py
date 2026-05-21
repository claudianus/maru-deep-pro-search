#!/usr/bin/env python3
"""Refiner Engine Benchmark for maru-deep-pro-search.

Measures token savings, inference speed, and resource usage across
different local LLM models and content scenarios.

Usage:
    python benchmark/refiner_benchmark.py
    python benchmark/refiner_benchmark.py --model Qwen3.5-0.8B-Q4_K_M
    python benchmark/refiner_benchmark.py --quick
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from maru_deep_pro_search.extraction.content import estimate_token_count
from maru_deep_pro_search.refiner.config import MODEL_REGISTRY, RefinerConfig
from maru_deep_pro_search.refiner.engine import RefinerEngine
from maru_deep_pro_search.refiner.hardware import detect_hardware

# ── Test Content ─────────────────────────────────────────────────
# Token counts are approximate (estimate_token_count uses len // 4).

TEST_CONTENTS: dict[str, str] = {
    "short_article": """\
# Python Asyncio Best Practices: A Comprehensive Guide

## Introduction

Python's asyncio module has revolutionized the way developers write
concurrent code. Introduced in Python 3.4 and significantly enhanced in
subsequent versions, asyncio provides a foundation for writing single-threaded
concurrent code using coroutines, multiplexing I/O access over sockets and
other resources, running network clients and servers, and other related
primitives. This guide covers essential best practices for writing robust,
efficient, and maintainable asyncio applications.

## Understanding the Event Loop

The event loop is the core of every asyncio application. It is responsible
for managing and distributing the execution of different tasks. Understanding
how the event loop works is crucial for writing effective asyncio code.

In Python 3.10 and later, the preferred way to run an asyncio application is
using asyncio.run(), which automatically creates and closes the event loop.
For more complex applications, you may need to manage the event loop manually.

```python
import asyncio

async def main():
    print("Hello from asyncio!")

if __name__ == "__main__":
    asyncio.run(main())
```

## Best Practice 1: Use asyncio.create_task for Fire-and-Forget

When you need to run a coroutine concurrently without waiting for its result
immediately, use asyncio.create_task(). This schedules the coroutine to run
on the event loop and returns a Task object that you can await later.

```python
async def fetch_data(url):
    await asyncio.sleep(1)
    return f"Data from {url}"

async def main():
    task1 = asyncio.create_task(fetch_data("https://api.example.com/1"))
    task2 = asyncio.create_task(fetch_data("https://api.example.com/2"))
    result1 = await task1
    result2 = await task2
    print(result1, result2)
```

## Best Practice 2: Proper Exception Handling

Always wrap await expressions in try-except blocks when dealing with
operations that may fail. Unhandled exceptions in tasks can be silently
ignored if the task is not awaited.

```python
async def risky_operation():
    raise ValueError("Something went wrong")

async def main():
    task = asyncio.create_task(risky_operation())
    try:
        await task
    except ValueError as e:
        print(f"Caught error: {e}")
```

## Best Practice 3: Use asyncio.gather for Concurrent Execution

When you need to run multiple coroutines concurrently and wait for all of
them to complete, use asyncio.gather(). It runs the awaitables concurrently
and returns a list of results.

```python
async def main():
    urls = ["url1", "url2", "url3"]
    results = await asyncio.gather(
        *[fetch_data(url) for url in urls],
        return_exceptions=True
    )
    for url, result in zip(urls, results):
        if isinstance(result, Exception):
            print(f"Failed to fetch {url}: {result}")
        else:
            print(f"{url}: {result}")
```

## Best Practice 4: Avoid Blocking the Event Loop

Never run blocking operations directly in async functions. Use
loop.run_in_executor() or asyncio.to_thread() (Python 3.9+) to offload
blocking work to a separate thread.

```python
import time

async def cpu_bound_task():
    # Bad: blocks the event loop
    # time.sleep(5)

    # Good: runs in thread pool
    await asyncio.to_thread(time.sleep, 5)
```

## Best Practice 5: Use Timeouts

Always use asyncio.wait_for() or asyncio.timeout() (Python 3.11+) to add
timeouts to operations that might hang indefinitely.

```python
async def main():
    try:
        result = await asyncio.wait_for(fetch_data("slow-url"), timeout=5.0)
    except asyncio.TimeoutError:
        print("Request timed out")
```

## Best Practice 6: Graceful Shutdown

Implement graceful shutdown handlers to clean up resources when your
application receives a termination signal.

```python
import signal

async def shutdown(signal, loop):
    print(f"Received exit signal {signal.name}...")
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()

async def main():
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(shutdown(s, loop)))
    # ... main logic
```

## Common Pitfalls

1. **Forgetting to await coroutines**: A coroutine object that is not
   awaited will not execute.
2. **Creating too many tasks**: While asyncio is lightweight, creating
   millions of tasks can still consume significant memory.
3. **Not handling cancellation**: When a task is cancelled, it raises
   CancelledError. Handle this appropriately.
4. **Mixing sync and async code improperly**: Be careful when calling
   async code from synchronous contexts.

## Performance Tips

- Use uvloop for better performance in production (can be 2-4x faster)
- Profile your event loop to identify bottlenecks
- Consider using a connection pool for HTTP requests
- Batch I/O operations when possible
- Use asyncio.Semaphore to limit concurrent connections

## Conclusion

Asyncio is a powerful tool for writing concurrent Python applications.
By following these best practices, you can write code that is not only
performant but also maintainable and robust. Remember that asyncio shines
in I/O-bound scenarios and may not be the right choice for CPU-bound work.
""",
    "medium_doc": """\
# PostgreSQL Query Optimization: Complete Documentation

## Table of Contents

1. Query Planning and Execution
2. Indexing Strategies
3. Configuration Tuning
4. Query Rewriting Techniques
5. Monitoring and Diagnostics
6. Advanced Optimization

## 1. Query Planning and Execution

PostgreSQL uses a cost-based query planner to determine the most efficient
way to execute a query. Understanding how the planner works is essential for
optimization.

### The Planner Process

When you submit a query, PostgreSQL goes through several phases:

1. **Parser**: Checks syntax and converts SQL to a query tree
2. **Rewriter**: Applies rules (views, rules) to the query tree
3. **Planner/Optimizer**: Generates execution plans and selects the cheapest
4. **Executor**: Runs the selected plan

### Reading EXPLAIN Output

The EXPLAIN command shows the execution plan:

```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT * FROM orders WHERE customer_id = 12345;
```

Key metrics to watch:
- **Cost**: Arbitrary units representing estimated effort
- **Actual Time**: Real execution time in milliseconds
- **Rows**: Estimated vs actual row counts
- **Buffers**: Shared hit/read counts

### Cost Components

The planner considers:
- Sequential page cost (seq_page_cost = 1.0)
- Random page cost (random_page_cost = 4.0)
- CPU tuple cost (cpu_tuple_cost = 0.01)
- CPU index tuple cost (cpu_index_tuple_cost = 0.005)
- CPU operator cost (cpu_operator_cost = 0.0025)

## 2. Indexing Strategies

### B-Tree Indexes

The default index type. Best for:
- Equality operators (=)
- Range operators (<, <=, >, >=)
- LIKE 'prefix%'

```sql
CREATE INDEX idx_orders_date ON orders USING btree (created_at);
```

### Hash Indexes

Best for equality comparisons only. Historically less robust but improved
significantly in PostgreSQL 10+.

```sql
CREATE INDEX idx_orders_hash ON orders USING hash (customer_id);
```

### GiST Indexes

Generalized Search Tree. Used for:
- Geometric data
- Range types
- Full-text search

### GIN Indexes

Generalized Inverted Index. Excellent for:
- JSONB operations
- Array operations
- Full-text search

```sql
CREATE INDEX idx_docs_gin ON documents USING gin (content jsonb_path_ops);
```

### BRIN Indexes

Block Range Indexes. Ideal for very large, naturally ordered tables:

```sql
CREATE INDEX idx_logs_brin ON logs USING brin (timestamp)
WITH (pages_per_range = 128);
```

### Partial Indexes

Index only a subset of rows:

```sql
CREATE INDEX idx_active_users ON users (email) WHERE active = true;
```

### Covering Indexes (Index-Only Scans)

Include additional columns to avoid table lookups:

```sql
CREATE INDEX idx_orders_covering ON orders (customer_id)
INCLUDE (total, status, created_at);
```

## 3. Configuration Tuning

### Memory Settings

```ini
shared_buffers = 25% of RAM          # Cache frequently accessed data
effective_cache_size = 50% of RAM    # Planner estimate of cache size
work_mem = 256MB                     # Per-operation sort/hash memory
maintenance_work_mem = 512MB         # VACUUM, CREATE INDEX memory
```

### Checkpoint Settings

```ini
checkpoint_completion_target = 0.9   # Spread checkpoint I/O over time
max_wal_size = 4GB                   # Allow more WAL before forcing checkpoint
min_wal_size = 1GB                   # Minimum WAL to keep
```

### Query Planner Settings

```ini
effective_io_concurrency = 200       # For SSDs, higher for RAID
random_page_cost = 1.1               # Lower for SSDs (default 4.0 for HDDs)
seq_page_cost = 1.0                  # Usually kept at 1.0
```

## 4. Query Rewriting Techniques

### Avoid SELECT *

Fetching unnecessary columns wastes I/O and memory.

```sql
-- Bad
SELECT * FROM users WHERE id = 1;

-- Good
SELECT id, username, email FROM users WHERE id = 1;
```

### Use Proper JOIN Types

```sql
-- Inner join when you only need matching rows
SELECT u.*, o.total
FROM users u
INNER JOIN orders o ON u.id = o.user_id;

-- Left join when you need all users regardless of orders
SELECT u.*, o.total
FROM users u
LEFT JOIN orders o ON u.id = o.user_id;
```

### Optimize Pagination

Offset-based pagination is slow for large offsets:

```sql
-- Bad for large offsets
SELECT * FROM logs ORDER BY id LIMIT 10 OFFSET 100000;

-- Good: Keyset pagination
SELECT * FROM logs
WHERE id > 100000
ORDER BY id LIMIT 10;
```

### Use CTEs Wisely

```sql
WITH recent_orders AS (
    SELECT * FROM orders
    WHERE created_at > NOW() - INTERVAL '7 days'
)
SELECT customer_id, COUNT(*)
FROM recent_orders
GROUP BY customer_id;
```

## 5. Monitoring and Diagnostics

### pg_stat_statements

Track query performance:

```sql
CREATE EXTENSION pg_stat_statements;

SELECT query, calls, mean_time, total_time
FROM pg_stat_statements
ORDER BY total_time DESC
LIMIT 10;
```

### pg_stat_user_tables

Monitor table access patterns:

```sql
SELECT schemaname, tablename,
       seq_scan, seq_tup_read,
       idx_scan, idx_tup_fetch
FROM pg_stat_user_tables
WHERE seq_scan > 100
ORDER BY seq_scan DESC;
```

### pg_stat_user_indexes

Identify unused indexes:

```sql
SELECT schemaname, tablename, indexrelname, idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan = 0
AND indexrelname NOT LIKE 'pg_toast%'
ORDER BY tablename;
```

### pg_stat_bgwriter

Check buffer writer efficiency:

```sql
SELECT * FROM pg_stat_bgwriter;
```

## 6. Advanced Optimization

### Table Partitioning

Partition large tables by range or list:

```sql
CREATE TABLE logs_2024 PARTITION OF logs
FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
```

### Parallel Query Execution

Enable parallel workers for large queries:

```ini
max_parallel_workers_per_gather = 4
parallel_tuple_cost = 0.1
parallel_setup_cost = 1000
```

### Materialized Views

Pre-compute expensive aggregations:

```sql
CREATE MATERIALIZED VIEW daily_stats AS
SELECT DATE(created_at) as day, COUNT(*) as count, AVG(total) as avg_total
FROM orders
GROUP BY DATE(created_at);

CREATE UNIQUE INDEX idx_daily_stats_day ON daily_stats (day);
REFRESH MATERIALIZED VIEW CONCURRENTLY daily_stats;
```

### Connection Pooling

Use PgBouncer to reduce connection overhead:

```ini
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 25
```

## Conclusion

Query optimization is an ongoing process. Start with proper indexing,
monitor regularly with pg_stat_statements, and adjust configuration based
on your workload characteristics. Remember that what works for one workload
may not work for another - always measure before and after changes.
""",
    "long_forum": """\
# Discussion: Major Breakthroughs in Quantum Computing (2024-2026)

## Original Post by u/QuantumResearcher

Hey everyone, I've been following quantum computing developments closely
and wanted to start a comprehensive discussion about the major breakthroughs
we've seen in the past two years. There's been so much progress that it's
hard to keep track of everything.

### Google's Willow Chip

Google's announcement of the Willow chip in late 2024 was a huge deal.
They demonstrated that increasing the number of qubits actually reduced
errors exponentially, which was the opposite of what everyone expected.
The chip has 105 qubits and achieved below-threshold error correction.

Key details:
- 105 physical qubits
- Surface code error correction
- Logical error rate decreases with more qubits
- Performed benchmark in under 5 minutes vs 10^25 years for classical

This is a major step toward fault-tolerant quantum computing. The fact that
they demonstrated below-threshold behavior means error correction is actually
working as theory predicted.

### IBM's Quantum Roadmap Advances

IBM has been making steady progress on their roadmap:

**Condor (2023)**: 1,121 qubits - proved density and yield
**Flamingo (2024)**: Error correction demonstrations
**Kookaburra**: Demonstrated modular quantum computing

They're targeting 100,000 qubits by 2033 with their Quantum System Two
architecture. The modular approach using quantum communication links
between chips is particularly interesting.

### Microsoft and Quantinuum Partnership

Microsoft's work with Quantinuum produced some of the most reliable logical
qubits yet. They demonstrated 4 logical qubits with an error rate 800x
better than physical qubits.

This matters because:
1. Logical qubits are what we actually need for useful algorithms
2. The error rate improvement is substantial
3. It validates the topological qubit approach

### Atom Computing's 1,000+ Qubit System

Atom Computing announced a 1,225 qubit system using neutral atoms. While
these are neutral atom qubits (different from superconducting), the scale
is impressive. Neutral atoms have advantages in connectivity and coherence
times.

Neutral atom pros:
- Long coherence times (seconds vs microseconds)
- All-to-all connectivity
- Easier to scale to large numbers

Cons:
- Slower gate times
- Newer technology with less mature control

### Comments and Discussion

**u/PhysicistDave** (Top Comment, 2.4k upvotes):

Great summary! I want to add some context on the Willow result that I think
gets lost in popular coverage.

The "below threshold" achievement is genuinely important, but it's worth
understanding what it means practically. They showed that a distance-3
surface code (17 physical qubits protecting 1 logical qubit) had lower
error rate than a distance-5 code with their previous chip. This proves
the scaling behavior is correct.

However, we're still very far from useful logical qubits. To run Shor's
algorithm to factor RSA-2048, estimates suggest we need:
- ~20 million physical qubits
- ~4,000 logical qubits
- Error rates around 10^-4 or better

So while Willow is a milestone, we're maybe 1% of the way there in terms
of scale. The error rates are still too high for most practical algorithms.

That said, the exponential error reduction is exactly what the field needed
to see. It validates the last 20 years of theoretical work on quantum error
correction.

**u/QCEngineer** (1.8k upvotes):

I work in quantum control systems and want to highlight the engineering
challenges that don't get enough attention.

The dilution refrigerators needed for superconducting qubits are incredibly
complex. A typical system requires:
- 3K stage (pulse tube cooler)
- 1K stage (helium-3 pot)
- 100mK stage (mixing chamber)
- 10mK stage (additional cooling)

Each stage requires careful thermal anchoring, microwave filtering, and
magnetic shielding. The cryogenic engineering alone is a massive field.

And then there's the control electronics. Each qubit needs:
- Microwave pulse generators (arbitrary waveform generators)
- Fast digitizers for readout
- Real-time feedback controllers
- Room temperature electronics

The control stack for a 1,000 qubit system can fill multiple racks and
consume 100+ kW of power. This is why modular architectures like IBM's
are so important - you can't physically fit all the control electronics
for a million qubit system in one room.

**u/CryptoAnalyst** (1.5k upvotes):

From a cryptography perspective, these developments are both exciting and
concerning. Let me break down the timeline:

Current state:
- 1,000+ physical qubits demonstrated
- ~4 logical qubits with low error rates
- No immediate threat to RSA-2048 or AES-256

Estimated timeline for cryptographically relevant quantum computers:
- 2030-2035: First demonstrations of breaking small RSA keys (512-bit)
- 2035-2040: Breaking RSA-2048 becomes feasible
- 2040+: Full "Y2Q" (Years to Quantum) scenario

This is why NIST standardized post-quantum cryptography in 2024:
- CRYSTALS-Kyber for key encapsulation
- CRYSTALS-Dilithium for digital signatures
- SPHINCS+ as a conservative backup
- FALCON for applications needing smaller signatures

Organizations should start migrating now. The "harvest now, decrypt later"
 threat is real - adversaries are storing encrypted traffic to decrypt when
quantum computers become available.

**u/StartupFounder** (987 upvotes):

I run a quantum software startup and want to share some practical insights.

The current NISQ (Noisy Intermediate-Scale Quantum) era is actually quite
frustrating for application development. We have ~100-1000 qubits but with
error rates too high for most algorithms. This has led to several
approaches:

1. **Variational Quantum Eigensolver (VQE)**: Used for chemistry simulations
2. **Quantum Approximate Optimization Algorithm (QAOA)**: For optimization
3. **Quantum Machine Learning**: Still very experimental
4. **Quantum Annealing**: D-Wave's approach, different from gate-based

The most commercially viable applications right now are:
- Optimization problems (logistics, finance)
- Quantum chemistry (drug discovery)
- Materials science
- Some ML kernel methods

But honestly, most "quantum advantage" claims are still debatable. Classical
algorithms keep improving and narrowing the gap. I think true quantum
advantage for practical problems is still 5-10 years away.

**u/AcademicResearcher** (754 upvotes):

I want to address some misconceptions about quantum computing that I see
frequently.

Misconception 1: "Quantum computers are faster at everything"
Reality: They're only faster for specific problems with structure that
exploits quantum parallelism. For most everyday computing, classical
computers are and will remain superior.

Misconception 2: "More qubits = better computer"
Reality: Qubit quality matters more than quantity. 50 high-quality qubits
can be more useful than 1,000 noisy ones. Metrics like coherence time,
gate fidelity, and connectivity are crucial.

Misconception 3: "Quantum computers will replace classical computers"
Reality: They'll be co-processors, similar to how GPUs work today. You'll
use quantum processors for specific subroutines within classical algorithms.

Misconception 4: "Error correction solves everything"
Reality: Error correction requires massive overhead. A single logical qubit
might need 1,000+ physical qubits. The resource requirements are enormous.

**u/IndustryVeteran** (623 upvotes):

Having worked in this field for 15 years, here's my perspective on the
investment and hype cycles.

We're currently in the third major wave of quantum computing investment:

Wave 1 (1994-2000): Post-Shor's algorithm excitement
- Lots of theoretical work
- Limited experimental progress
- First quantum algorithms developed

Wave 2 (2010-2015): Early commercialization attempts
- D-Wave Systems founded
- First venture capital investments
- Initial skepticism about quantum annealing

Wave 3 (2018-present): Scale-up and error correction
- Google, IBM, Microsoft, Amazon investing billions
- National quantum initiatives (US, EU, China)
- First demonstrations of error correction

Investment levels:
- 2020: ~$1B total global investment
- 2022: ~$2.5B
- 2024: ~$4B
- Projected 2026: $6-8B

But I worry about a "quantum winter" if we don't show practical advantage
soon. The field needs a "killer app" - a problem where quantum computers
are definitively better than classical approaches.

**u/GradStudent** (445 upvotes):

As a PhD student in quantum information, here's what I'm working on and
what I see as open problems.

My research focuses on quantum error correction codes beyond surface codes.
Some promising directions:

1. **Color codes**: Better transversal gates but harder to decode
2. **LDPC codes**: Higher encoding rates, potentially more efficient
3. **Quantum turbo codes**: Borrowing from classical coding theory
4. **Dynamic decoupling**: Protecting qubits during idle times

Open problems that need solving:
- Better decoding algorithms (ML-based decoders show promise)
- Improved qubit connectivity in hardware
- Scalable control electronics
- Room-temperature qubits (diamond NV centers, etc.)
- Quantum networking and distributed quantum computing

The job market is actually quite good right now. There's high demand for
quantum software engineers, error correction theorists, and cryogenic
engineers. Salaries are competitive with FAANG companies.

**u/CuriousLurker** (312 upvotes):

This thread is amazing! Can someone explain quantum supremacy vs quantum
advantage in simple terms?

**u/QuantumResearcher** (Reply, 289 upvotes):

Sure! Here's the distinction:

**Quantum Supremacy** (now often called "Quantum Computational Supremacy"):
A quantum computer performs a task that is practically impossible for any
classical computer, regardless of whether the task is useful. Google's 2019
experiment was an example - they performed a random circuit sampling task
in 200 seconds that would take Summit supercomputer 10,000 years.

**Quantum Advantage**:
A quantum computer solves a practically useful problem faster or better
than classical methods. This is the holy grail. Examples might include:
- Simulating a complex molecule for drug discovery
- Optimizing a global supply chain
- Breaking current encryption (though this is more of a threat)

The key difference: supremacy is about proving quantum computers can do
something classical computers can't, even if it's useless. Advantage is
about solving real problems better.

We have achieved supremacy (debatably). We have not yet achieved clear,
uncontested advantage for practical problems.

**u/InvestorWatch** (198 upvotes):

From an investment perspective, the quantum computing landscape is
fascinating but risky.

Public companies with quantum exposure:
- IBM (IBM): Leading quantum roadmap, diversified business
- Google (GOOGL): Willow chip, but quantum is tiny part of business
- Microsoft (MSFT): Azure Quantum, topological qubits
- IonQ (IONQ): Pure-play quantum computing stock
- Rigetti (RGTI): Quantum cloud services

Private companies to watch:
- PsiQuantum: Building a million-qubit photonic quantum computer
- Xanadu: Photonic quantum computing, PennyLane software
- Quantum Brilliance: Room-temperature diamond qubits
- Alice & Bob: Cat qubit approach

My take: Don't invest in pure-play quantum companies unless you can afford
to lose the money. The technology is 10-20 years from mass commercialization.
Better to invest in companies where quantum is a bonus (IBM, Microsoft) rather
than the entire thesis.

---

**Discussion Summary**: This thread covers major quantum computing
breakthroughs from 2024-2026, including Google's Willow chip, IBM's modular
architecture, Microsoft's logical qubit advances, and neutral atom systems.
Experts agree that while progress is rapid, practical quantum advantage for
real-world problems remains 5-10 years away. Error correction is improving
but requires massive overhead. Post-quantum cryptography migration should
begin now.
""",
}

TEST_QUERIES: dict[str, str] = {
    "short_article": "Python asyncio best practices",
    "medium_doc": "How to optimize PostgreSQL queries",
    "long_forum": "Latest quantum computing breakthroughs",
}

BENCHMARK_MODELS: list[str] = [
    "Qwen3.5-0.8B-Q4_K_M",
    "Qwen3.5-2B-Q4_K_M",
    "Qwen3.5-4B-Q4_K_M",
]


# ── Data Classes ─────────────────────────────────────────────────


@dataclass
class BenchmarkResult:
    """Single benchmark run result."""

    model: str
    scenario: str
    query: str
    input_tokens: int
    output_tokens: int
    savings_percent: float
    ttft_seconds: float
    total_time_seconds: float
    tokens_per_second: float
    peak_ram_mb: int
    peak_vram_mb: int | None


@dataclass
class BenchmarkReport:
    """Complete benchmark report."""

    benchmark_date: str
    hardware_profile: dict[str, Any]
    results: list[dict[str, Any]]
    summary: dict[str, Any]


# ── Resource Monitor ─────────────────────────────────────────────


class ResourceMonitor:
    """Monitor RAM and VRAM usage during inference."""

    def __init__(self, interval: float = 0.05) -> None:
        self.interval = interval
        self.peak_ram_mb = 0
        self.peak_vram_mb: int | None = None
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._nvml_initialized = False
        self._nvml_handle: Any = None

    def start(self) -> None:
        """Start monitoring in a background thread."""
        try:
            import pynvml

            pynvml.nvmlInit()
            self._nvml_initialized = True
            self._nvml_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        except Exception:
            pass

        self._stop_event.clear()
        self.peak_ram_mb = 0
        self.peak_vram_mb = None
        self._thread = threading.Thread(target=self._poll, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop monitoring and clean up."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        if self._nvml_initialized:
            try:
                import pynvml

                pynvml.nvmlShutdown()
            except Exception:
                pass
            self._nvml_initialized = False

    def _poll(self) -> None:
        """Poll resource usage until stopped."""
        try:
            import psutil

            process = psutil.Process()
        except Exception:
            return

        while not self._stop_event.is_set():
            try:
                ram_mb = process.memory_info().rss // (1024 * 1024)
                self.peak_ram_mb = max(self.peak_ram_mb, ram_mb)
            except Exception:
                pass

            if self._nvml_handle is not None:
                try:
                    import pynvml

                    info = pynvml.nvmlDeviceGetMemoryInfo(self._nvml_handle)
                    vram_mb = info.used // (1024 * 1024)
                    if self.peak_vram_mb is None:
                        self.peak_vram_mb = vram_mb
                    else:
                        self.peak_vram_mb = max(self.peak_vram_mb, vram_mb)
                except Exception:
                    pass

            time.sleep(self.interval)


# ── Benchmark Logic ──────────────────────────────────────────────


class BenchmarkRunner:
    """Orchestrates refiner benchmark runs."""

    def __init__(self, models: list[str], scenarios: list[str]) -> None:
        self.models = models
        self.scenarios = scenarios
        self.hardware = detect_hardware()

    def _can_run_model(self, model_name: str) -> bool:
        """Check if the system can run the specified model."""
        config = MODEL_REGISTRY.get(model_name)
        if config is None:
            return False

        min_ram = config.get("min_ram_mb", 0)
        min_vram = config.get("min_vram_mb", 0)

        if self.hardware.total_ram_mb < min_ram:
            return False

        return not (
            min_vram > 0
            and self.hardware.gpu_vram_mb is not None
            and self.hardware.gpu_vram_mb < min_vram
        )

    async def _measure_ttft(
        self,
        engine: RefinerEngine,
        text: str,
        query: str,
        max_tokens: int,
    ) -> float:
        """Measure time to first token using streaming inference."""
        if engine._llama is None:
            return 0.0

        prompt = engine._build_prompt(
            text=text,
            query=query,
            task="content",
            max_tokens=max_tokens,
        )

        def _stream_first() -> Any:
            try:
                stream = engine._llama.create_completion(
                    prompt,
                    max_tokens=max_tokens,
                    temperature=engine._config.temperature,
                    top_p=engine._config.top_p,
                    stop=["<|im_end|>", "<|endoftext|>"],
                    stream=True,
                )
                for chunk in stream:
                    return chunk
            except Exception:
                return None

        start = time.monotonic()
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _stream_first)
        return time.monotonic() - start

    async def _run_single_benchmark(
        self,
        model_name: str,
        scenario: str,
        text: str,
        query: str,
    ) -> BenchmarkResult | None:
        """Run a single benchmark iteration."""
        config = RefinerConfig(
            model_name=model_name,
            max_tokens=1500,
            timeout_seconds=120.0,
        )
        engine = RefinerEngine(config=config)

        input_tokens = estimate_token_count(text)

        # Warm-up: load model and run once to warm caches
        print(f"    Warming up {model_name}...", end=" ", flush=True)
        try:
            _ = await engine.refine_content(text=text, query=query, max_tokens=1500)
        except Exception as exc:
            print(f"warm-up failed: {exc}")
            return None
        print("done")

        # Measure TTFT via streaming
        print("    Measuring TTFT...", end=" ", flush=True)
        ttft = await self._measure_ttft(engine, text, query, max_tokens=1500)
        print(f"{ttft:.2f}s")

        # Run monitored benchmark
        print("    Running benchmark...", end=" ", flush=True)
        monitor = ResourceMonitor()
        monitor.start()

        start_time = time.monotonic()
        try:
            refined = await engine.refine_content(text=text, query=query, max_tokens=1500)
        except Exception as exc:
            monitor.stop()
            print(f"failed: {exc}")
            return None

        total_time = time.monotonic() - start_time
        monitor.stop()

        output_tokens = estimate_token_count(refined)
        savings = ((input_tokens - output_tokens) / input_tokens) * 100 if input_tokens > 0 else 0.0
        tps = output_tokens / total_time if total_time > 0 else 0.0

        print(f"{total_time:.1f}s, {input_tokens}→{output_tokens} tokens, {savings:.1f}% savings")

        return BenchmarkResult(
            model=model_name,
            scenario=scenario,
            query=query,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            savings_percent=round(savings, 1),
            ttft_seconds=round(ttft, 2),
            total_time_seconds=round(total_time, 2),
            tokens_per_second=round(tps, 1),
            peak_ram_mb=monitor.peak_ram_mb,
            peak_vram_mb=monitor.peak_vram_mb,
        )

    async def run(self) -> BenchmarkReport:
        """Run the full benchmark suite."""
        results: list[BenchmarkResult] = []

        print("=" * 70)
        print("REFINER ENGINE BENCHMARK")
        print("=" * 70)
        print(f"Hardware: {self.hardware.platform}")
        print(f"CPU: {self.hardware.cpu_count} cores")
        print(f"RAM: {self.hardware.total_ram_mb} MB")
        if self.hardware.has_gpu:
            print(f"GPU: {self.hardware.gpu_name} ({self.hardware.gpu_backend})")
            if self.hardware.gpu_vram_mb:
                print(f"VRAM: {self.hardware.gpu_vram_mb} MB")
        print("=" * 70)

        for model_name in self.models:
            print(f"\n{'─' * 70}")
            print(f"Model: {model_name}")
            print(f"{'─' * 70}")

            if not self._can_run_model(model_name):
                print("  SKIPPED: Insufficient hardware resources")
                continue

            for scenario in self.scenarios:
                text = TEST_CONTENTS[scenario]
                query = TEST_QUERIES[scenario]
                print(f"\n  Scenario: {scenario} ({estimate_token_count(text)} tokens)")
                print(f"  Query: {query}")

                result = await self._run_single_benchmark(
                    model_name=model_name,
                    scenario=scenario,
                    text=text,
                    query=query,
                )
                if result is not None:
                    results.append(result)

        # Compute summary
        summary = self._compute_summary(results)

        return BenchmarkReport(
            benchmark_date=datetime.now(timezone.utc).isoformat(),
            hardware_profile={
                "platform": self.hardware.platform,
                "cpu_count": self.hardware.cpu_count,
                "cpu_features": self.hardware.cpu_features,
                "total_ram_mb": self.hardware.total_ram_mb,
                "has_gpu": self.hardware.has_gpu,
                "gpu_name": self.hardware.gpu_name,
                "gpu_vram_mb": self.hardware.gpu_vram_mb,
                "gpu_backend": self.hardware.gpu_backend,
                "is_apple_silicon": self.hardware.is_apple_silicon,
            },
            results=[asdict(r) for r in results],
            summary=summary,
        )

    def _compute_summary(self, results: list[BenchmarkResult]) -> dict[str, Any]:
        """Compute aggregate statistics from results."""
        if not results:
            return {
                "best_model": None,
                "average_savings": 0.0,
                "recommendation": "No successful benchmark runs.",
            }

        # Find best model by average savings
        model_savings: dict[str, list[float]] = {}
        model_speed: dict[str, list[float]] = {}
        for r in results:
            model_savings.setdefault(r.model, []).append(r.savings_percent)
            model_speed.setdefault(r.model, []).append(r.tokens_per_second)

        avg_savings = {m: sum(v) / len(v) for m, v in model_savings.items()}
        avg_speed = {m: sum(v) / len(v) for m, v in model_speed.items()}

        best_model = max(avg_savings, key=lambda m: avg_savings[m])
        overall_avg_savings = sum(r.savings_percent for r in results) / len(results)

        # Generate recommendation
        if best_model == "Qwen3.5-0.8B-Q4_K_M":
            rec = (
                "Use 0.8B for fastest inference on limited hardware. "
                "Quality may be lower than larger models."
            )
        elif best_model == "Qwen3.5-2B-Q4_K_M":
            rec = (
                "2B model offers the best balance of speed, quality, and "
                "resource usage for most deployments."
            )
        else:
            rec = (
                "4B model provides best quality if VRAM permits. "
                "Consider for high-quality refinement pipelines."
            )

        return {
            "best_model": best_model,
            "average_savings": round(overall_avg_savings, 1),
            "model_avg_savings": {k: round(v, 1) for k, v in avg_savings.items()},
            "model_avg_tps": {k: round(v, 1) for k, v in avg_speed.items()},
            "total_runs": len(results),
            "successful_models": list(model_savings.keys()),
            "recommendation": rec,
        }


# ── CLI ──────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark refiner engine across models and scenarios",
    )
    parser.add_argument(
        "--model",
        type=str,
        choices=BENCHMARK_MODELS,
        help="Run benchmark for a specific model only",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick test with only the short_article scenario",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="benchmark/results",
        help="Directory to save benchmark results",
    )
    args = parser.parse_args()

    # Select models
    models = [args.model] if args.model else BENCHMARK_MODELS

    # Select scenarios
    scenarios = ["short_article"] if args.quick else ["short_article", "medium_doc", "long_forum"]

    runner = BenchmarkRunner(models=models, scenarios=scenarios)
    report = asyncio.run(runner.run())

    # Save results
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"refiner_benchmark_{timestamp}.json"
    output_path.write_text(
        json.dumps(asdict(report), indent=2),
        encoding="utf-8",
    )

    print(f"\n{'=' * 70}")
    print("BENCHMARK COMPLETE")
    print(f"{'=' * 70}")
    print(f"Results saved: {output_path}")
    print(f"Best model: {report.summary['best_model']}")
    print(f"Average savings: {report.summary['average_savings']:.1f}%")
    print(f"Recommendation: {report.summary['recommendation']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
