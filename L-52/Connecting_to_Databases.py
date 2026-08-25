"""
=====================================================================
CONNECTING TO DATABASES FROM PYTHON - sqlite3, psycopg2, pyodbc,
AND THE DB-API 2.0 INTERFACE - Complete Notes with Executable Examples
=====================================================================

Almost every relational-database library in Python - `sqlite3`
(stdlib), `psycopg2` (PostgreSQL), `pyodbc` (SQL Server / any ODBC
source), `mysqlclient` (MySQL), etc. - implements the SAME standard
interface: PEP 249, commonly called "DB-API 2.0". This is the single
biggest interview point about Python database connectivity: once you
truly know ONE of these libraries, the others feel almost identical,
because they all expose the same shapes:

    - a CONNECTION object       (conn = library.connect(...))
    - CURSOR objects             (cur = conn.cursor())
    - cur.execute(sql, params)     - run a (parameterized) statement
    - cur.fetchone() / fetchmany(n) / fetchall()  - pull result rows
    - conn.commit() / conn.rollback()               - transaction control
    - iterating a cursor directly  - memory-efficient row-by-row reads

The libraries differ in HOW they connect (a file path for sqlite3,
host/port/credentials for psycopg2, an ODBC connection string for
pyodbc) and in small behavioral defaults (autocommit, parameter
placeholder style), but the day-to-day "write SQL, get rows back"
workflow is portable across all of them. That portability is exactly
why interviewers ask this - they want to know you understand the
STANDARD, not just one vendor's driver.

This file uses `sqlite3` (stdlib, always available, zero setup) to
run every example FOR REAL. It also shows fully correct, real
`psycopg2` connection code for PostgreSQL, wrapped so it degrades
gracefully when no Postgres server is reachable (as in this sandbox),
and closes with a brief conceptual note on `pyodbc` for SQL
Server/ODBC sources.
=====================================================================
"""

import sqlite3

print("--- Overview ---")
print("DB-API 2.0 (PEP 249) is the shared contract behind sqlite3,")
print("psycopg2, and pyodbc: connection objects, cursor objects,")
print(".execute()/.fetchall(), and .commit()/.rollback(). Learn the")
print("shape once, and every Python SQL driver reads the same way.")


"""
---------------------------------------------------------------------
1. THE DB-API 2.0 STANDARD: WHY THESE LIBRARIES ALL "FEEL THE SAME" ⭐⭐⭐
---------------------------------------------------------------------
PEP 249 defines the minimum interface every compliant driver must
expose. It does NOT standardize the connection arguments (those are
driver-specific - a file path vs a hostname vs an ODBC string), but
it DOES standardize everything after the connection is open:

    connect(...)          -> Connection object
    conn.cursor()          -> Cursor object
    cur.execute(sql, params)
    cur.executemany(sql, seq_of_params)
    cur.fetchone()          -> next row, or None
    cur.fetchmany(n)         -> up to n rows, as a list
    cur.fetchall()            -> all remaining rows, as a list
    cur.rowcount               -> rows affected by the last execute
    cur.description              -> column metadata (name, type, ...)
    conn.commit() / conn.rollback()
    conn.close() / cur.close()

Because sqlite3, psycopg2, and pyodbc all implement this same
surface, code that manipulates a `conn`/`cur` pair is largely
copy-paste portable between them - the SQL dialect may need small
tweaks (e.g. placeholder syntax, below), but the Python-level control
flow does not change.
---------------------------------------------------------------------
"""

print("\n--- The DB-API 2.0 Standard ---")

conn = sqlite3.connect(":memory:")   # ":memory:" = a throwaway in-RAM DB,
                                       # no file ever touches disk - great
                                       # for demos, tests, and this file
cur = conn.cursor()                    # every DB-API driver works through
                                        # a cursor, not the connection itself
print("connection object:", type(conn))
print("cursor object:", type(cur))
print("cur.execute, cur.fetchone, cur.fetchall, conn.commit, conn.rollback")
print("all exist on psycopg2 and pyodbc objects too, with identical names.")

cur.close()
conn.close()


"""
---------------------------------------------------------------------
2. A FULL REAL sqlite3 WORKFLOW: CREATE, INSERT, QUERY  ⭐⭐⭐
---------------------------------------------------------------------
This is the canonical DB-API loop you will reproduce, almost
unchanged, against psycopg2 or pyodbc in real projects: connect,
get a cursor, execute DDL/DML, commit, then execute a SELECT and pull
rows back with fetchall().
---------------------------------------------------------------------
"""

print("\n--- A Full Real sqlite3 Workflow ---")

conn = sqlite3.connect(":memory:")
cur = conn.cursor()

cur.execute("""
    CREATE TABLE employees (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        department TEXT NOT NULL,
        salary REAL NOT NULL
    )
""")

# Parameterized inserts - NEVER use an f-string to build SQL with user
# data (that's how SQL injection happens). sqlite3 uses "?" as its
# placeholder style; psycopg2 uses "%s" instead (see section 6).
employees = [
    (1, "Ana",  "Engineering", 118000.0),
    (2, "Ben",  "Engineering", 95000.0),
    (3, "Cleo", "Sales",       72000.0),
    (4, "Deja", "Sales",       81000.0),
    (5, "Eli",  "Marketing",   68000.0),
]
cur.executemany(
    "INSERT INTO employees (id, name, department, salary) VALUES (?, ?, ?, ?)",
    employees,
)
conn.commit()   # DML changes are NOT durable until you commit the transaction
print(f"inserted {cur.rowcount} rows via executemany (rowcount reflects the LAST executed statement's batch)")

cur.execute("SELECT name, department, salary FROM employees WHERE department = ?", ("Engineering",))
rows = cur.fetchall()   # pulls ALL matching rows into a list of tuples at once
print("\nfetchall() result (list of tuples):")
for row in rows:
    print(" ", row)

conn.close()


"""
---------------------------------------------------------------------
3. ITERATING A CURSOR DIRECTLY: MEMORY-EFFICIENT ROW READING  ⭐⭐⭐
---------------------------------------------------------------------
`fetchall()` materializes every result row in memory at once - fine
for small result sets, dangerous for a multi-million-row table. Just
like iterating a file object line-by-line instead of calling
.read(), a DB-API cursor is itself an ITERATOR: iterating it directly
streams rows from the driver one at a time, so you're never holding
more than one row (plus the driver's internal fetch buffer) in memory
at once. This is the DB equivalent of the "don't load the whole file"
pattern from earlier file-handling notes.
---------------------------------------------------------------------
"""

print("\n--- Iterating a Cursor Directly (Memory-Efficient) ---")

conn = sqlite3.connect(":memory:")
cur = conn.cursor()
cur.execute("CREATE TABLE numbers (n INTEGER)")
cur.executemany("INSERT INTO numbers (n) VALUES (?)", [(i,) for i in range(1, 6)])
conn.commit()

cur.execute("SELECT n FROM numbers ORDER BY n")
print("iterating the cursor directly (no fetchall() call at all):")
running_total = 0
for (n,) in cur:            # the cursor yields one row at a time
    running_total += n
    print(f"  saw row n={n}, running total={running_total}")
print(f"final total: {running_total}")
print("\nfor a table with 500 million rows, this loop's memory footprint")
print("stays flat - fetchall() on the same table would try to build a")
print("500-million-element Python list and likely blow out memory.")

conn.close()


"""
---------------------------------------------------------------------
4. fetchone() AND fetchmany(n): CONTROLLING HOW MANY ROWS YOU PULL ⭐⭐
---------------------------------------------------------------------
Between "one row" (fetchone) and "everything" (fetchall) sits
fetchmany(n) - useful for manual batch/paginated processing, e.g.
processing a huge result set in fixed-size chunks without loading it
all at once and without the per-row Python-loop overhead of
iterating one row at a time.
---------------------------------------------------------------------
"""

print("\n--- fetchone() and fetchmany(n) ---")

conn = sqlite3.connect(":memory:")
cur = conn.cursor()
cur.execute("CREATE TABLE numbers (n INTEGER)")
cur.executemany("INSERT INTO numbers (n) VALUES (?)", [(i,) for i in range(1, 11)])
conn.commit()

cur.execute("SELECT n FROM numbers ORDER BY n")
print("fetchone():", cur.fetchone())     # pulls exactly 1 row, advances cursor
print("fetchone():", cur.fetchone())     # pulls the NEXT row (cursor has state!)
print("fetchmany(3):", cur.fetchmany(3))  # pulls the next 3 rows as a list
print("fetchall() (whatever's left):", cur.fetchall())   # drains the rest
print("fetchone() after exhausted:", cur.fetchone())       # None - nothing left

conn.close()


"""
---------------------------------------------------------------------
5. CONNECTIONS AS CONTEXT MANAGERS - THE `with conn:` GOTCHA  ⭐⭐⭐
---------------------------------------------------------------------
sqlite3.Connection supports `with conn:` - but this is a COMMON
INTERVIEW TRAP because it does NOT behave like a typical file's
`with open(...) as f:`. Using a connection as a context manager wraps
a TRANSACTION, not the connection's lifetime:

    - on successful exit  -> automatically calls conn.commit()
    - on an exception      -> automatically calls conn.rollback()
    - EITHER WAY            -> the connection itself stays OPEN

If you assume `with sqlite3.connect(...) as conn:` closes the
connection for you (the way `with open(...) as f:` closes the file),
you will leak connections. You must call conn.close() yourself,
typically in a `finally` or a separate outer context manager.
---------------------------------------------------------------------
"""

print("\n--- `with conn:` Auto-Commits/Rollbacks but Does NOT Close ---")

conn = sqlite3.connect(":memory:")
conn.execute("CREATE TABLE ledger (entry TEXT)")
conn.commit()

with conn:                              # wraps a TRANSACTION, not the connection
    conn.execute("INSERT INTO ledger (entry) VALUES ('deposit 100')")
    # no explicit commit() here - exiting the `with` block cleanly commits it

print("row committed automatically on clean exit:", conn.execute("SELECT * FROM ledger").fetchall())

try:
    with conn:
        conn.execute("INSERT INTO ledger (entry) VALUES ('this will be rolled back')")
        raise ValueError("simulated failure mid-transaction")
except ValueError as e:
    print("caught:", e)

print("row from the failed block was rolled back:", conn.execute("SELECT * FROM ledger").fetchall())

print("is the connection still usable/open after BOTH `with` blocks?", end=" ")
print(conn.execute("SELECT 1").fetchone())   # still works - conn was never closed!
print("^ proves `with conn:` never closed the connection - only close() does.")

conn.close()   # you are responsible for this - `with conn:` will not do it
try:
    conn.execute("SELECT 1")
except sqlite3.ProgrammingError as e:
    print("\nafter an explicit .close(), using the connection now fails:", e)


"""
---------------------------------------------------------------------
6. REAL psycopg2 (PostgreSQL) CODE, WITH A GRACEFUL FALLBACK  ⭐⭐⭐
---------------------------------------------------------------------
`psycopg2` is the standard PostgreSQL driver and, like sqlite3, is a
full DB-API 2.0 implementation - connect(), cursor(), execute(),
fetchall(), commit() all work exactly the same way conceptually. The
main practical differences: connection arguments (host/port/dbname/
user/password instead of a file path) and the SQL placeholder style
("%s" for psycopg2, regardless of the target column's type, vs "?"
for sqlite3).

This sandbox has psycopg2 INSTALLED but no Postgres SERVER actually
running, so the real connect() call below will fail with
psycopg2.OperationalError. The code shown IS the real, correct
production API - in a real environment with a reachable Postgres
instance, this exact code would work unmodified. We catch the
failure, explain what would have happened, and then re-run the SAME
query logic against our in-memory sqlite3 DB so the reader still sees
real, executed output.
---------------------------------------------------------------------
"""

print("\n--- Real psycopg2 Code, With a Graceful Fallback ---")

import psycopg2

try:
    # This is exactly how you'd connect to a real PostgreSQL server in
    # production - nothing here is pseudocode.
    pg_conn = psycopg2.connect(
        host="localhost",
        port=5432,
        dbname="analytics",
        user="etl_service",
        password="not-a-real-secret",   # in real code: pull from env vars/secrets manager, never hardcode
        connect_timeout=3,
    )
    pg_cur = pg_conn.cursor()
    pg_cur.execute(
        "SELECT name, department, salary FROM employees WHERE department = %s",  # note: %s, not ?
        ("Engineering",),
    )
    pg_rows = pg_cur.fetchall()
    print("connected to real Postgres, rows:", pg_rows)
    pg_cur.close()
    pg_conn.close()

except psycopg2.OperationalError as e:
    print("psycopg2.OperationalError (expected - no Postgres server running here):")
    print(" ", e)
    print("in production, against a real reachable Postgres server, the code above")
    print("would connect and return rows exactly like the sqlite3 example below.")
    print("simulating the same query against sqlite3 instead, so you still see")
    print("real, executed output:")

    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE employees (name TEXT, department TEXT, salary REAL)")
    conn.executemany(
        "INSERT INTO employees VALUES (?, ?, ?)",
        [("Ana", "Engineering", 118000.0), ("Ben", "Engineering", 95000.0)],
    )
    conn.commit()
    simulated_rows = conn.execute(
        "SELECT name, department, salary FROM employees WHERE department = ?",
        ("Engineering",),
    ).fetchall()
    print("  simulated result:", simulated_rows)
    conn.close()


"""
---------------------------------------------------------------------
7. AUTOCOMMIT BEHAVIOR DIFFERS BY DRIVER - A COMMON GOTCHA  ⭐⭐⭐
---------------------------------------------------------------------
Both sqlite3 and psycopg2 comply with DB-API 2.0, but their DEFAULT
transaction behavior differs, and mixing up the two is a real-world
source of "why didn't my insert show up?" bugs:

    sqlite3   -> historically starts an IMPLICIT transaction the
                 moment you run an INSERT/UPDATE/DELETE; you must
                 call conn.commit() (or use `with conn:`, section 5)
                 for it to persist. You CAN flip conn.isolation_level
                 = None (or, on Python 3.12+, the newer conn.autocommit
                 attribute) for true autocommit mode.
    psycopg2  -> connections default to autocommit=False as well,
                 requiring an explicit conn.commit() - BUT psycopg2
                 also exposes an explicit `conn.autocommit = True`
                 flag you can set right after connecting, which many
                 engineers do for one-off scripts/DDL so they don't
                 forget the commit() call.

The interview-safe takeaway: NEVER assume a write "just happens" -
check (or explicitly set) the autocommit setting for whichever driver
you're using.
---------------------------------------------------------------------
"""

print("\n--- Autocommit Behavior Differs by Driver ---")

conn = sqlite3.connect(":memory:")
print("sqlite3 default conn.isolation_level:", repr(conn.isolation_level))   # "" -> implicit transactions are open by default
print("(Python 3.12+ also exposes conn.autocommit for explicit control - not")
print("used here directly since this sandbox runs on an earlier Python.)")
conn.execute("CREATE TABLE t (x INTEGER)")
conn.execute("INSERT INTO t VALUES (1)")
# without commit(), a second connection to the SAME on-disk file would
# not see this row yet (not observable here since :memory: DBs aren't
# shareable across connections anyway) - the discipline still applies.
conn.commit()
print("explicit conn.commit() called -> row is durable:", conn.execute("SELECT * FROM t").fetchall())
conn.close()

print("\npsycopg2.connect(...) also defaults to autocommit=False.")
print("production pattern: `pg_conn.autocommit = True` right after connecting")
print("if you want every statement to commit immediately (common for quick")
print("scripts, DDL migrations, or when you're managing transactions manually")
print("with explicit BEGIN/COMMIT SQL instead of relying on the driver).")


"""
---------------------------------------------------------------------
8. pyodbc: SQL SERVER / ODBC SOURCES (CONCEPTUAL - NOT INSTALLED HERE) ⭐
---------------------------------------------------------------------
`pyodbc` is the go-to driver for Microsoft SQL Server, and more
generally for ANY data source reachable via an ODBC driver (some
legacy systems, some cloud warehouses expose an ODBC endpoint too).
It is DB-API 2.0 compliant like the others - same cursor/execute/
fetch/commit shape - so everything in sections 1-4 transfers directly
once you have a connection. The main difference is the connection
string format, which is a semicolon-delimited key=value string naming
the ODBC driver itself:

    import pyodbc   # NOT installed in this sandbox - shown conceptually only
    conn = pyodbc.connect(
        "DRIVER={ODBC Driver 18 for SQL Server};"
        "SERVER=myserver.database.windows.net,1433;"
        "DATABASE=mydb;"
        "UID=myuser;"
        "PWD=mypassword;"
        "Encrypt=yes;"
    )
    cur = conn.cursor()
    cur.execute("SELECT TOP 5 name, department FROM employees")   # note: SQL Server's own dialect (TOP, not LIMIT)
    for row in cur.fetchall():
        print(row)
    conn.commit()
    conn.close()

Two things worth knowing for interviews: (1) pyodbc uses "?" as its
placeholder style, same as sqlite3, not psycopg2's "%s"; (2) it
requires a system-level ODBC DRIVER to be installed separately from
the `pyodbc` Python package itself (e.g. "ODBC Driver 18 for SQL
Server") - a frequent source of environment-setup pain that has
nothing to do with your Python code being wrong.
---------------------------------------------------------------------
"""

print("\n--- pyodbc: SQL Server / ODBC (Conceptual Note) ---")
print("pyodbc is DB-API 2.0 compliant like sqlite3/psycopg2 - same")
print("cursor/execute/fetch/commit shape, different connection string")
print("(a 'DRIVER=...;SERVER=...;DATABASE=...' ODBC string) and it")
print("needs a separate system-level ODBC driver installed to work.")
print("not installed in this sandbox - no live demo, shown as a comment above.")


"""
---------------------------------------------------------------------
9. PRACTICAL PATTERN: ROWS AS DICTS VIA sqlite3.Row  ⭐⭐⭐
---------------------------------------------------------------------
By default, fetchall()/fetchone() return plain tuples - positional,
with no column names attached. That's inconvenient once code down-
stream (pandas, JSON serialization, a REST API response) needs to
refer to columns BY NAME. Setting conn.row_factory = sqlite3.Row
makes rows behave like dict-ish objects (indexable by column name OR
position) while still being real DB-API rows under the hood.

A small reusable helper - "run this query, hand me back a list of
plain dicts" - is one of the most genuinely useful patterns to have
memorized, since `pd.DataFrame(list_of_dicts)` and `json.dumps(...)`
both consume that shape directly.
---------------------------------------------------------------------
"""

print("\n--- Practical Pattern: Rows as Dicts via sqlite3.Row ---")

def fetch_as_dicts(conn, query, params=()):
    """Run `query` on `conn` and return results as a list of plain dicts.

    Works for ANY DB-API 2.0 connection that exposes cursor.description
    (every compliant driver does) - the row_factory trick shown here is
    sqlite3-specific, but the underlying idea (zip column names from
    cursor.description against each row) is portable to psycopg2/pyodbc
    even without a row_factory feature.
    """
    original_factory = conn.row_factory
    conn.row_factory = sqlite3.Row     # rows now support row["column_name"]
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        return [dict(row) for row in cur.fetchall()]   # dict(sqlite3.Row) -> plain dict
    finally:
        conn.row_factory = original_factory   # restore, so we don't surprise other callers

conn = sqlite3.connect(":memory:")
conn.execute("CREATE TABLE employees (name TEXT, department TEXT, salary REAL)")
conn.executemany(
    "INSERT INTO employees VALUES (?, ?, ?)",
    [("Ana", "Engineering", 118000.0), ("Cleo", "Sales", 72000.0)],
)
conn.commit()

result = fetch_as_dicts(conn, "SELECT name, department, salary FROM employees ORDER BY name")
print("list of dicts, ready for pandas or json.dumps():")
for record in result:
    print(" ", record)

import json
print("\njson.dumps() works directly on this shape:")
print(json.dumps(result, indent=2))

try:
    import pandas as pd
    df = pd.DataFrame(result)
    print("\npd.DataFrame(result) also works directly:")
    print(df)
except ImportError:
    print("\n(pandas not available - pd.DataFrame(result) would build a DataFrame directly from this list of dicts)")

conn.close()


"""
=====================================================================
QUICK REFERENCE
=====================================================================
DB-API 2.0 (PEP 249)  -> the shared contract behind sqlite3,
                          psycopg2, pyodbc, and most other drivers

connect(...)           -> Connection object   (args are driver-specific)
conn.cursor()            -> Cursor object
cur.execute(sql, params)   -> run one (parameterized) statement
cur.executemany(sql, seq)    -> run one statement for many param sets
cur.fetchone()                 -> next row, or None
cur.fetchmany(n)                 -> up to n rows, as a list
cur.fetchall()                     -> all remaining rows, as a list
for row in cur: ...                  -> stream rows one at a time (memory-safe)
conn.commit() / conn.rollback()        -> end the current transaction

Placeholder style:
    sqlite3  -> "?"          pyodbc -> "?"          psycopg2 -> "%s"

`with conn:` (sqlite3)  -> commits/rolls back the TRANSACTION on
                            exit - does NOT close the connection;
                            call conn.close() yourself

Autocommit defaults:
    sqlite3  -> implicit transactions; commit() required unless you
                set conn.isolation_level = None (or, 3.12+: conn.autocommit)
    psycopg2 -> autocommit=False by default; set conn.autocommit=True
                to opt into per-statement autocommit

Connecting:
    sqlite3.connect(":memory:" or "path/to.db")
    psycopg2.connect(host=..., dbname=..., user=..., password=...)
    pyodbc.connect("DRIVER={...};SERVER=...;DATABASE=...;UID=...;PWD=...")

Rows as dicts -> set conn.row_factory = sqlite3.Row, then
                 dict(row) per fetched row -> list of dicts is what
                 pandas.DataFrame(...) and json.dumps(...) both want
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - CONNECTING TO DATABASES (DB-API 2.0)
=====================================================================

1. What is PEP 249 / "DB-API 2.0", and why does knowing it mean you
   can pick up psycopg2 or pyodbc quickly after learning sqlite3?

2. Walk through the standard DB-API workflow: what do you call to get
   a connection, get a cursor, run a query, and read results back?

3. What is the difference between cur.fetchone(), cur.fetchmany(n),
   and cur.fetchall()? When would you choose each?

4. Why is iterating a cursor directly (`for row in cur:`) more
   memory-efficient than calling `cur.fetchall()` on a huge result
   set? What's actually happening under the hood?

5. In this file's section 5, `with conn:` around a sqlite3
   connection auto-commits or rolls back a transaction, but does NOT
   close the connection. Why is that a commonly-missed gotcha, and
   how would you correctly ensure a connection is also closed?

6. What SQL placeholder syntax does sqlite3 use, versus psycopg2?
   Why must you always use parameterized queries (placeholders +
   a params tuple) instead of building SQL with an f-string?

7. Explain the autocommit behavior difference between sqlite3 and
   psycopg2 by default. What happens if you forget to call
   conn.commit() with each?

8. In the psycopg2 example in this file, we wrapped the connection
   attempt in `try/except psycopg2.OperationalError`. In a real
   production system, what specific problems would cause that
   exception, and how would you distinguish "server down" from "bad
   credentials" from "database doesn't exist"?

9. How would you write a function that takes ANY DB-API 2.0
   connection/query and returns rows as a list of dictionaries
   instead of raw tuples? Why is that shape more useful downstream
   (e.g., for pandas or a JSON API response)?

10. What is `sqlite3.Row`, and how does setting `conn.row_factory =
    sqlite3.Row` change what fetchall() returns?

11. What is pyodbc typically used for, and what has to be installed
    on the machine (besides `pip install pyodbc`) before it can
    actually connect to anything?

12. How would you safely insert a large batch of rows (say, 100,000)
    using a DB-API cursor, rather than calling execute() once per
    row in a loop?

13. What does cur.rowcount tell you after an INSERT/UPDATE/DELETE,
    and after a SELECT?

14. If a network blip or a bad query happens mid-transaction, what
    should your code do before letting the exception propagate -
    and which DB-API call reverses uncommitted changes?

15. Design a small reusable "get_connection()" helper for a Python
    ETL job that might target sqlite3 in tests but psycopg2 in
    production. What would you need to abstract, and what would you
    intentionally NOT try to abstract (e.g., SQL dialect
    differences)?
=====================================================================
"""
