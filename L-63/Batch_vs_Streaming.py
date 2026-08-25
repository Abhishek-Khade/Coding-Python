"""
=====================================================================
BATCH vs STREAMING PROCESSING - Complete Notes with Executable Examples
=====================================================================

Every data pipeline eventually has to answer one design question:
"does this data arrive as a finished chunk I can process all at once,
or as a never-ending trickle I have to react to piece by piece?"
Those two answers correspond to the two fundamental data-processing
paradigms: BATCH and STREAMING.

BATCH PROCESSING operates on a BOUNDED dataset - a chunk of data that
has already been fully collected and has a known beginning AND end
(e.g. "yesterday's complete sales log file", "last month's orders
table"). A batch job reads the whole thing, computes a result, and
finishes. It typically runs on a SCHEDULE or a manual TRIGGER (nightly
at 2am, hourly, on-demand for a backfill) - not continuously.

STREAMING PROCESSING operates on an UNBOUNDED sequence of events that
arrive continuously, with no defined "end" - a Kafka topic, a live
clickstream, a feed of sensor readings. A streaming job never "finishes
reading the input" the way a batch job does; instead it processes each
event (or small group of events) as it arrives and keeps running
indefinitely, maintaining state that updates incrementally over time.

Neither paradigm is strictly "better" - they trade latency for
throughput in opposite directions, and real systems (Spark Structured
Streaming, Flink) often blur the line with MICRO-BATCHING. This file
builds a real (if small) working example of each paradigm in plain
Python, measures their trade-offs, and covers WINDOWING - the core
technique that makes streaming aggregation possible at all.
=====================================================================
"""

import itertools
import time
from collections import deque

print("--- Overview ---")
print("Batch = process a bounded, already-collected chunk of data,")
print("        on a schedule/trigger; one result, at the end.")
print("Streaming = process an unbounded sequence of events, one at a")
print("            time, continuously, with results updating live.")


"""
---------------------------------------------------------------------
1. THE CORE DISTINCTION: BOUNDED vs UNBOUNDED DATA  ⭐⭐⭐
---------------------------------------------------------------------
The single most important word in this whole topic is "bounded". A
batch dataset has a known size - you can call len() on it, you know
exactly when you've seen "all of it". A stream has no such boundary:
there is no len(), and no moment where you can say "I've now seen
everything" - there might always be one more event on the way.
---------------------------------------------------------------------
"""

print("\n--- The Core Distinction: Bounded vs Unbounded Data ---")

bounded_dataset = [1, 2, 3, 4, 5]      # BATCH: finite, already fully collected
print("bounded_dataset has a length:", len(bounded_dataset))


def unbounded_counter():
    """STREAMING: a generator with no natural stopping point - each
    call to next() just produces the next event, forever."""
    n = 0
    while True:          # no defined end - this loop never decides to stop on its own
        yield n
        n += 1


live_stream = unbounded_counter()
print("an unbounded generator has no len():")
try:
    len(live_stream)      # generators don't know (or claim to know) their own size
except TypeError as e:
    print("  TypeError calling len() on a generator:", e)
print("but it can always produce 'the next event' on demand:",
      next(live_stream), next(live_stream), next(live_stream))
print("\nThat's the whole distinction in miniature: batch code asks")
print("'how many do I have total?'; streaming code only ever asks")
print("'what's the next one?' - and keeps asking forever.")


"""
---------------------------------------------------------------------
2. BATCH PROCESSING IN ACTION: A NIGHTLY SALES BATCH JOB  ⭐⭐⭐
---------------------------------------------------------------------
A REAL batch job: a fixed, finite, in-memory list standing in for
"yesterday's complete sales log file", read all at once, with a
single aggregate produced only after every record has been consumed.
This is the classic ETL pattern: extract the whole bounded chunk,
transform/aggregate it in one pass, load one summary result.
---------------------------------------------------------------------
"""

print("\n--- Batch Processing: Nightly Sales Batch Job ---")


def run_nightly_batch_job(daily_sales_log):
    """daily_sales_log is BOUNDED and already fully collected before
    this function is ever called - exactly like a completed log file
    a nightly cron job would read in one shot after the day ends."""
    total_revenue = 0.0
    total_orders = 0
    for record in daily_sales_log:          # a normal, finite for-loop - it WILL end
        total_revenue += record["amount"]
        total_orders += 1
    # nothing is returned/emitted until EVERY record has been read -
    # that's the defining trait of batch: one result, at the very end
    return {
        "orders": total_orders,
        "revenue": round(total_revenue, 2),
        "avg_order_value": round(total_revenue / total_orders, 2),
    }


yesterdays_sales_log = [
    {"order_id": 1, "amount": 42.50},
    {"order_id": 2, "amount": 15.00},
    {"order_id": 3, "amount": 99.99},
    {"order_id": 4, "amount": 7.25},
    {"order_id": 5, "amount": 63.10},
    {"order_id": 6, "amount": 21.00},
]

print("batch job started - dataset size is known up front:",
      len(yesterdays_sales_log), "orders")
print("...processing the entire bounded file in one pass, no output yet...")
batch_result = run_nightly_batch_job(yesterdays_sales_log)
print("batch job FINISHED. Result (only available now, at the end):", batch_result)


"""
---------------------------------------------------------------------
3. STREAMING PROCESSING IN ACTION: AN UNBOUNDED GENERATOR-DRIVEN
   EVENT SOURCE  ⭐⭐⭐
---------------------------------------------------------------------
A REAL streaming-style demo: a generator driven by itertools.count()
that stands in for a genuinely unbounded event source (a Kafka topic
that never stops receiving orders). Events are processed ONE AT A
TIME, AS THEY ARRIVE, maintaining a running aggregate that updates
incrementally - contrast this directly with Section 2, which produced
NO output until the entire dataset had been consumed.
---------------------------------------------------------------------
"""

print("\n--- Streaming Processing: Unbounded Live Order Feed ---")


def unbounded_event_source():
    """Simulates a TRUE unbounded stream. itertools.count() never
    stops counting, so this generator never stops yielding - there is
    no length, no last element, nothing to 'wait for the end of'."""
    amounts = itertools.cycle([9.99, 14.50, 3.25, 27.00, 60.10, 8.75])
    for order_id, amount in zip(itertools.count(start=1), amounts):
        yield {"order_id": order_id, "amount": amount}


def process_stream_incrementally(event_stream, max_events_for_demo):
    """Processes events ONE AT A TIME as they 'arrive', updating a
    running total after EVERY single event - never waiting for 'all'
    the data, because in a real stream there is no 'all'."""
    running_total = 0.0
    running_count = 0
    for event in event_stream:
        running_total += event["amount"]
        running_count += 1
        # a real result after EVERY event - this is the key contrast
        # with the batch job, which printed nothing until it finished
        print(f"  event {event['order_id']} arrived (${event['amount']:.2f}) "
              f"-> running total: ${running_total:.2f}")
        if running_count >= max_events_for_demo:
            # stopping here is ONLY for this printed demo to terminate -
            # the generator itself would keep yielding events forever
            break
    return running_total, running_count


live_orders = unbounded_event_source()
stream_total, stream_count = process_stream_incrementally(live_orders, max_events_for_demo=6)
print(f"stream demo paused after {stream_count} events (for display only) - "
      f"running total so far: ${stream_total:.2f}")
print("Notice: a USABLE result existed after event 1 already. The batch")
print("job in Section 2 could only ever produce a result at the very end.")


"""
---------------------------------------------------------------------
4. THE BATCH MINDSET APPLIED TO A STREAM: WHY "WAIT FOR ALL THE DATA"
   BREAKS  ⭐⭐⭐
---------------------------------------------------------------------
A very common beginner mistake: treating a stream like a batch by
trying to collect "all of it" into a list first, THEN aggregating -
exactly like run_nightly_batch_job() does with its finite list. That
works fine for a bounded dataset, but a real unbounded stream has no
"all of it" to collect, so the collection loop would simply never
finish, and the aggregation step below it would never even run.
---------------------------------------------------------------------
"""

print("\n--- Batch Mindset on a Stream: Buggy vs Fixed ---")


def naive_wait_for_all_data(event_stream, safety_limit):
    """BUGGY (conceptually): mimics batch's 'collect everything, then
    aggregate' approach against something that has no 'everything'.
    A safety_limit is added ONLY so this demo can terminate and print
    an error - a real production stream has no such limit, so this
    exact pattern would hang forever waiting for a stream to 'end'."""
    collected = []
    for i, event in enumerate(event_stream, start=1):
        collected.append(event)
        if i >= safety_limit:
            raise RuntimeError(
                f"hit demo safety_limit={safety_limit} events collected and "
                "STILL not 'done' - a real unbounded stream has no limit here, "
                "so this loop would never reach the aggregation step below it"
            )
    return sum(e["amount"] for e in collected)   # unreachable against a real stream


try:
    naive_wait_for_all_data(unbounded_event_source(), safety_limit=5)
except RuntimeError as e:
    print("Error simulating batch-style 'wait for all data' on a stream:")
    print(" ", e)

print("\nFIXED: don't wait - aggregate INCREMENTALLY as each event")
print("arrives, exactly like process_stream_incrementally() already did")
print("in Section 3 (no 'collect everything first' step at all):")
_, fixed_count = process_stream_incrementally(unbounded_event_source(), max_events_for_demo=3)
print(f"  (produced {fixed_count} incremental results with zero waiting)")


"""
---------------------------------------------------------------------
5. LATENCY vs THROUGHPUT: THE FUNDAMENTAL TRADE-OFF, MEASURED  ⭐⭐⭐
---------------------------------------------------------------------
BATCH: higher LATENCY (you wait until the whole bounded chunk is
processed before you get ANY result) but better THROUGHPUT/efficiency
- work is done in tight, bulk loops with minimal per-item overhead.
STREAMING: lower LATENCY (a result is available after every single
event) but each event pays its own per-event overhead (dispatch,
bookkeeping, framework callbacks) - so processing the SAME number of
events is typically less efficient in raw bulk throughput.
---------------------------------------------------------------------
"""

print("\n--- Latency vs Throughput, Measured on This Machine ---")


def batch_bulk_sum(events):
    """Bulk/batch style: one tight loop, no per-item bookkeeping,
    ONE result only when the whole (bounded) input is exhausted."""
    return sum(e["amount"] for e in events)


def _simulate_per_event_dispatch_overhead():
    # stand-in for real per-event streaming costs: acknowledging an
    # offset, updating a checkpoint, invoking a framework callback.
    # Even something this cheap adds up when paid on EVERY event.
    return {"checkpoint_committed": True}.get("checkpoint_committed")


def streaming_style_sum(events):
    """Streaming style: same total work, but each event pays its own
    per-event overhead - the price of getting a result immediately,
    every time, instead of only once at the very end."""
    total = 0.0
    for e in events:
        total += e["amount"]
        _simulate_per_event_dispatch_overhead()   # paid N times, not once
    return total


event_count = 200_000
sample_events = [{"amount": 1.0} for _ in range(event_count)]

start = time.perf_counter()
batch_bulk_sum(sample_events)
after_batch = time.perf_counter()
streaming_style_sum(sample_events)
after_stream = time.perf_counter()

print(f"batch bulk sum over {event_count:,} events: {after_batch - start:.4f}s "
      "(result only available at the very end)")
print(f"streaming-style sum over {event_count:,} events: {after_stream - after_batch:.4f}s "
      "(but a usable running total existed after EVERY single event)")
print("\nOn most runs the batch version is faster in raw wall-clock terms -")
print("it pays overhead once for the whole chunk. The streaming version")
print("pays a small cost per event, in exchange for never making anyone")
print("wait for a result. That's the trade-off in one measurement.")


"""
---------------------------------------------------------------------
6. WINDOWING: TUMBLING WINDOWS TURN AN UNBOUNDED STREAM INTO FINITE
   CHUNKS  ⭐⭐⭐
---------------------------------------------------------------------
You usually can't (and don't want to) aggregate "the whole stream" -
it never ends. WINDOWING solves this by chopping the unbounded stream
into small, FINITE, aggregatable pieces. A TUMBLING WINDOW is the
simplest kind: fixed-size, NON-OVERLAPPING - e.g. "every 5 events" or
"every 10 seconds". Once a window fills, it emits exactly ONE
aggregate for that window, then a brand-new, empty window starts; no
event ever belongs to two tumbling windows.
---------------------------------------------------------------------
"""

print("\n--- Tumbling Windows Over the Stream (every 5 events) ---")


def tumbling_window_aggregator(event_stream, window_size, max_events_for_demo):
    window_events = []
    window_number = 1
    for i, event in enumerate(event_stream, start=1):
        window_events.append(event)
        if len(window_events) == window_size:
            window_total = sum(e["amount"] for e in window_events)
            print(f"  [window {window_number}] {window_size} events -> "
                  f"windowed total: ${window_total:.2f}")
            window_number += 1
            window_events = []       # tumble: start a brand-new, empty window
        if i >= max_events_for_demo:
            break


tumbling_window_aggregator(unbounded_event_source(), window_size=5, max_events_for_demo=20)
print("\nEach window's aggregate was emitted as soon as it filled - the")
print("stream itself never had to 'end' for a result to come out.")


"""
---------------------------------------------------------------------
7. SLIDING WINDOWS: THE OVERLAPPING ALTERNATIVE  ⭐⭐
---------------------------------------------------------------------
A SLIDING WINDOW is also fixed-size, but OVERLAPS with the previous
one: it advances one event at a time instead of jumping by a whole
window's width, so most events belong to MULTIPLE windows. This is
the right tool for smoothed, continuously-updating metrics - e.g. "a
moving average of the last 5 orders" - as opposed to tumbling's
"a fresh, independent total every 5 orders". Implemented below with a
collections.deque(maxlen=N), which is the idiomatic Python structure
for "keep only the last N items, automatically dropping the oldest".
---------------------------------------------------------------------
"""

print("\n--- Sliding Windows: Moving Average of the Last 5 Orders ---")


def sliding_window_moving_average(event_stream, window_size, max_events_for_demo):
    window = deque(maxlen=window_size)   # auto-evicts the oldest item once full - the "slide"
    for i, event in enumerate(event_stream, start=1):
        window.append(event["amount"])
        moving_avg = sum(window) / len(window)
        print(f"  event {i}: last {len(window)} amount(s) -> moving avg: ${moving_avg:.2f}")
        if i >= max_events_for_demo:
            break


sliding_window_moving_average(unbounded_event_source(), window_size=5, max_events_for_demo=8)
print("\nCompare event 6 above to window 2 in Section 6: tumbling started a")
print("BRAND NEW total at event 6, while sliding just dropped event 1 and")
print("kept averaging - the same events, two different windowing semantics.")


"""
---------------------------------------------------------------------
8. MICRO-BATCHING: THE PRACTICAL MIDDLE GROUND  ⭐⭐
---------------------------------------------------------------------
Most production "streaming" systems don't actually process one event
at a time end-to-end - that has too much per-event overhead (Section
5). Instead they use MICRO-BATCHING: buffer events for a short,
repeating trigger interval (e.g. every 1 second, or every K events),
then run a tiny, ordinary BATCH job over just that slice - forever.
This is exactly how Spark Structured Streaming works by default: it
is literally "batch code, re-run automatically on a timer against
the newest slice of an unbounded source" - low-ish latency, most of
batch's bulk efficiency.
---------------------------------------------------------------------
"""

print("\n--- Micro-Batching: Spark Structured Streaming's Model ---")


def micro_batch_consumer(event_stream, micro_batch_size, num_micro_batches):
    """Every 'trigger', pull a small finite SLICE off the unbounded
    source with itertools.islice and run ordinary batch code (sum())
    over just that bounded slice - then repeat."""
    for batch_num in range(1, num_micro_batches + 1):
        micro_batch = list(itertools.islice(event_stream, micro_batch_size))  # one bounded slice
        batch_total = batch_bulk_sum(micro_batch)          # reuse the SAME batch-style function!
        print(f"  micro-batch {batch_num} (trigger fired): "
              f"{len(micro_batch)} events -> ${batch_total:.2f}")


micro_batch_consumer(unbounded_event_source(), micro_batch_size=4, num_micro_batches=5)
print("\n# In production against a real cluster, this would instead look like:")
print("#   spark.readStream.format('kafka')...load() \\")
print("#       .groupBy(window('event_time', '10 seconds')).sum('amount') \\")
print("#       .writeStream.trigger(processingTime='10 seconds').start()")
print("# - same idea: batch-style aggregation code, re-triggered on a timer.")


"""
---------------------------------------------------------------------
9. CHOOSING BATCH vs STREAMING: A DATA ENGINEER'S DECISION GUIDE  ⭐⭐⭐
---------------------------------------------------------------------
This is the question interviewers actually care about: not "define
streaming" but "given THIS requirement, which would you build, and
why?" The deciding factors are usually (a) how fresh does the result
need to be, and (b) does the source data even have a natural "end".
---------------------------------------------------------------------
"""

print("\n--- Decision Guide: Batch vs Streaming ---")

USE_CASE_RECOMMENDATIONS = {
    "nightly revenue report": ("BATCH", "runs once/day over a bounded day's data; latency is fine"),
    "historical backfill of 2 years of orders": ("BATCH", "the data is entirely bounded and already exists"),
    "hourly warehouse load from an OLTP replica": ("BATCH", "hourly freshness is enough; bulk loads are efficient"),
    "credit card fraud detection": ("STREAMING", "a fraudulent charge must be caught in seconds, not hours"),
    "real-time operations dashboard": ("STREAMING", "viewers expect the number on screen to be 'live'"),
    "server error-rate alerting": ("STREAMING", "an outage needs paging within seconds of it starting"),
}


def recommend_paradigm(use_case):
    paradigm, reason = USE_CASE_RECOMMENDATIONS.get(
        use_case, ("BATCH", "default to batch unless low latency is a hard requirement")
    )
    return f"{use_case!r} -> {paradigm} ({reason})"


for use_case in USE_CASE_RECOMMENDATIONS:
    print(" ", recommend_paradigm(use_case))

print("\nRule of thumb: if a human or an automated system needs to REACT")
print("within seconds, lean streaming. If a daily/hourly report or a")
print("historical reprocessing job is fine, lean batch - it's simpler")
print("to build, test, and reason about, and it's more resource-efficient.")


"""
---------------------------------------------------------------------
10. REAL-WORLD TOOLING LANDSCAPE  ⭐⭐
---------------------------------------------------------------------
This file's generators stand in for real infrastructure that isn't
available in this sandbox. Knowing the real names matters for
interviews even without writing code against them here.
---------------------------------------------------------------------
"""

print("\n--- Real-World Tooling Landscape ---")

TOOLING_LANDSCAPE = {
    "Kafka / Kinesis": "durable, unbounded event ingestion - the 'stream' itself",
    "Spark Structured Streaming / Flink": "micro-batch or true event-at-a-time stream PROCESSING engines",
    "Airflow / dbt": "scheduling and orchestrating BATCH jobs and their dependencies",
}
for tool, role in TOOLING_LANDSCAPE.items():
    print(f"  {tool:<38} -> {role}")

print("\nA typical real pipeline: Kafka ingests events -> Spark Structured")
print("Streaming (micro-batches) aggregates them into windows -> results")
print("land in a warehouse, where Airflow/dbt orchestrate the downstream")
print("BATCH transforms that run on top of that already-streamed data.")


"""
=====================================================================
QUICK REFERENCE
=====================================================================
BATCH               -> bounded data, known size, runs on schedule/
                        trigger, ONE result at the end, high latency,
                        high throughput/efficiency (bulk work)
STREAMING            -> unbounded data, no known size, runs
                        continuously, incremental results per event,
                        low latency, lower per-event throughput

Core loop shapes:
    batch:     for record in FINITE_LIST: aggregate  -> return once
    streaming: for event in INFINITE_GENERATOR: aggregate  -> yield/
               print/update EVERY time, loop never "finishes" itself

Windowing (turns unbounded -> finite, aggregatable chunks):
    tumbling window -> fixed size, NON-overlapping, each event in ONE window
    sliding window  -> fixed size, OVERLAPPING, most events in MANY windows

Micro-batching -> buffer a short trigger interval, run ordinary BATCH
                  code on that one small slice, repeat forever.
                  (Spark Structured Streaming's default model.)

Choose BATCH when:  daily/hourly reports, historical backfills,
                     some latency is acceptable, bulk efficiency matters.
Choose STREAMING when: fraud detection, live dashboards, alerting -
                        anything that must react within seconds.

Tools: Kafka/Kinesis (stream ingestion) -> Spark Streaming/Flink
       (stream processing) -> Airflow/dbt (batch orchestration)
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - BATCH vs STREAMING PROCESSING
=====================================================================

1. What is the fundamental difference between batch and streaming
   processing, in terms of "bounded" vs "unbounded" data?

2. In this file, why does run_nightly_batch_job() only ever return a
   result once, at the end, while process_stream_incrementally()
   prints a result after every single event?

3. Why does calling len() on the unbounded_counter() generator raise
   a TypeError? What does that tell you about streaming data sources
   in general?

4. Explain what naive_wait_for_all_data() gets wrong when it's given
   a real unbounded stream. What would actually happen in production
   if the safety_limit check were removed?

5. Describe the latency vs throughput trade-off between batch and
   streaming. Which one generally has lower latency, and which one
   generally has higher raw throughput/efficiency, and why?

6. In Section 5, streaming_style_sum() pays a small per-event
   overhead (_simulate_per_event_dispatch_overhead()) that
   batch_bulk_sum() never pays. What real-world costs is that
   simulating in an actual streaming system?

7. What is a TUMBLING WINDOW? Using tumbling_window_aggregator() as
   an example, explain why no single event can ever belong to two
   different tumbling windows.

8. What is a SLIDING WINDOW, and how does it differ from a tumbling
   window? Why does sliding_window_moving_average() use a
   collections.deque(maxlen=N) instead of a plain list?

9. Walk through what would happen if you ran
   sliding_window_moving_average() and tumbling_window_aggregator()
   over the exact same 10 events with window_size=5 - would they
   produce the same aggregates? Why or why not?

10. What is micro-batching, and why is it described as "the practical
    middle ground" between batch and streaming? How does Spark
    Structured Streaming use this model by default?

11. Look at micro_batch_consumer() - why is it valid to reuse
    batch_bulk_sum() (an ordinary batch function) inside a function
    that's meant to process a stream?

12. Give a concrete example of a use case where you'd choose BATCH
    over streaming, and one where you'd choose STREAMING over batch,
    and justify each choice the way you would in a system design
    interview.

13. Name the real-world tools you'd reach for at each stage of a
    streaming pipeline: event ingestion, stream processing, and batch
    orchestration. (Hint: Kafka/Kinesis, Spark Streaming/Flink,
    Airflow/dbt.)

14. A stakeholder says "just make everything streaming, it's always
    better." How would you push back, using the latency/throughput
    trade-off and the added system complexity of streaming as your
    argument?

15. How does windowing relate to the idea of "idempotent pipelines"
    (Module 11)? If a tumbling window's aggregate needs to be
    recomputed after a late-arriving event, what property would you
    want that recomputation to have?
=====================================================================
"""
