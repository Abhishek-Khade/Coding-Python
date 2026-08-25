"""
=====================================================================
PARAMETERIZED QUERIES & SQL INJECTION PREVENTION - Complete Notes
with Executable Examples
=====================================================================

SQL INJECTION happens when untrusted input (a username, a search box,
a config value) gets glued directly into a SQL string before that
string is sent to the database. If an attacker's input contains SQL
syntax of its own (a quote, an `OR`, a `--` comment marker), the
database can't tell "data" from "code" anymore - it just sees one big
SQL statement and executes all of it.

The fix is not "sanitize the string harder" - it's to never build the
SQL string out of untrusted data in the first place. A PARAMETERIZED
QUERY sends the SQL TEMPLATE (with placeholder markers like `?`) and
the VALUES as two SEPARATE things to the database driver. The values
are bound into the prepared statement by the driver/DB engine - they
are never re-parsed as SQL syntax, no matter what characters they
contain.

This file uses the stdlib `sqlite3` module against an in-memory
database (`:memory:`) so every example below is REAL and EXECUTABLE
with no external DB server required. Everything shown transfers
directly to `psycopg2` (Postgres), `pyodbc` (SQL Server), `MySQLdb`,
etc. - only the placeholder SYNTAX differs by driver, never the
underlying principle.

This is one of the most commonly asked Data Engineering interview
questions ("how do you prevent SQL injection from Python?") precisely
because so many real production incidents trace back to exactly the
mistake demonstrated in Section 1 below.
=====================================================================
"""

import sqlite3

print("--- Overview ---")
print("SQL injection = untrusted data gets interpreted as SQL SYNTAX")
print("because the query was built by string concatenation/formatting.")
print("Fix: send the SQL template and the values SEPARATELY using")
print("placeholders (`?` in sqlite3) - the driver never re-parses")
print("the values as code.")


"""
---------------------------------------------------------------------
1. SETUP: AN IN-MEMORY DATABASE TO EXPERIMENT ON  ⭐
---------------------------------------------------------------------
`sqlite3.connect(':memory:')` creates a throwaway database that lives
only in RAM for the life of the connection - perfect for demos, unit
tests, and this file. We seed a `users` table exactly like a login
system would have: usernames, passwords (never do this in real life
without hashing - that's a separate topic - but plaintext keeps this
demo focused purely on the injection mechanics).
---------------------------------------------------------------------
"""

print("\n--- Setup: In-Memory SQLite Database ---")

conn = sqlite3.connect(":memory:")
conn.execute(
    """
    CREATE TABLE users (
        id       INTEGER PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        is_admin INTEGER NOT NULL DEFAULT 0
    )
    """
)
conn.executemany(
    "INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)",
    [
        ("alice", "correct-horse-battery", 0),
        ("bob", "hunter2", 0),
        ("admin", "s3cr3t-root-pass", 1),
    ],
)
conn.commit()
print("seeded 'users' table with 3 rows (alice, bob, admin)")


"""
---------------------------------------------------------------------
2. THE VULNERABILITY: BUILDING SQL BY STRING FORMATTING  ⭐⭐⭐
---------------------------------------------------------------------
This is the classic mistake: an f-string (or `%`-formatting, or
`.format()`) is used to drop user input STRAIGHT into the SQL text
BEFORE the database ever sees it. The database has no way to know
that `username` and `password` were "supposed" to be plain data -
by the time it receives the string, it's just SQL, all the way
through.
---------------------------------------------------------------------
"""

print("\n--- The Vulnerability: Naive Login Check ---")


def naive_login(connection, username, password):
    """VULNERABLE: builds SQL via f-string interpolation. DO NOT USE."""
    query = (
        f"SELECT id, username, is_admin FROM users "
        f"WHERE username = '{username}' AND password = '{password}'"
    )
    print(f"  [naive] SQL actually sent to sqlite3:\n    {query}")
    cursor = connection.execute(query)
    return cursor.fetchall()

# First, prove the function "works" for legitimate use - this is why
# naive code like this ships: it passes the happy-path test.
print("legit login (bob / hunter2):", naive_login(conn, "bob", "hunter2"))
print("wrong password (bob / nope):", naive_login(conn, "bob", "nope"))


"""
---------------------------------------------------------------------
3. THE ATTACK: A REAL, WORKING SQL INJECTION  ⭐⭐⭐
---------------------------------------------------------------------
The malicious payload `' OR '1'='1` closes the quoted password
literal early, then adds `OR '1'='1'` - a condition that is ALWAYS
true. Because SQL's `AND` binds tighter than `OR`, the WHERE clause
becomes:
    (username = 'bob' AND password = '')  OR  ('1' = '1')
The right side of that OR is true for EVERY row, so the query returns
the ENTIRE users table - including the admin account - with NO
knowledge of any real password. This is a genuine authentication
bypass / data-dump, not a hypothetical.
---------------------------------------------------------------------
"""

print("\n--- The Attack: SQL Injection in Action ---")

malicious_password = "' OR '1'='1"
stolen_rows = naive_login(conn, "bob", malicious_password)
print("injected login (bob / \"' OR '1'='1\") returned:", stolen_rows)
print(f"\n{len(stolen_rows)} rows returned - the ENTIRE users table,")
print("including the admin account, with no valid password at all.")
print("A second classic variant - commenting out the rest of the")
print("query - is just as devastating:")

comment_username = "admin' --"
bypassed = naive_login(conn, comment_username, "anything-at-all")
print(f"injected username \"{comment_username}\" (password check never runs):")
print(" ", bypassed)


"""
---------------------------------------------------------------------
4. THE FIX: PARAMETERIZED QUERIES WITH `?` PLACEHOLDERS  ⭐⭐⭐
---------------------------------------------------------------------
Instead of interpolating values into the SQL text, we put `?`
placeholders in the query TEMPLATE and pass the actual values as a
SEPARATE tuple to `.execute()`. sqlite3's DB-API paramstyle is
"qmark" (confirmed below). Re-running the EXACT SAME malicious input
now returns NO rows - it is treated as a literal string to compare
against the `password` column, not as SQL syntax.
---------------------------------------------------------------------
"""

print("\n--- The Fix: Parameterized Query ---")


def safe_login(connection, username, password):
    """SAFE: SQL template and values are passed separately."""
    query = "SELECT id, username, is_admin FROM users WHERE username = ? AND password = ?"
    print(f"  [safe] SQL template sent to sqlite3 (unchanged, no matter the input):\n    {query}")
    cursor = connection.execute(query, (username, password))
    return cursor.fetchall()

print("legit login (bob / hunter2):", safe_login(conn, "bob", "hunter2"))

print("\nre-running the SAME attack payload against the SAFE function:")
safe_result = safe_login(conn, "bob", malicious_password)
print(f"injected login (bob / \"' OR '1'='1\") returned: {safe_result}")
print("Zero rows - sqlite3 compared the LITERAL text \"' OR '1'='1\"")
print("against the password column and, correctly, found no match.")

safe_comment_result = safe_login(conn, comment_username, "anything-at-all")
print(f"injected username \"{comment_username}\" returned: {safe_comment_result}")
print("Also zero rows - no username in the table is literally")
print("\"admin' --\", so the comment-based bypass fails too.")


"""
---------------------------------------------------------------------
5. WHY THIS WORKS: SEPARATION OF QUERY STRUCTURE AND DATA  ⭐⭐⭐
---------------------------------------------------------------------
With string formatting, the FULL SQL text - attacker payload
included - is assembled in Python BEFORE the database ever sees it.
The database has no way to distinguish "data the app meant literally"
from "syntax the app meant structurally" - it's all just characters
in one string by the time `execute()` runs.

With a parameterized query, the driver sends the QUERY TEMPLATE (with
placeholders) to the database first, which compiles/prepares it as a
fixed execution plan. The VALUES are bound into that already-compiled
plan afterward, purely as data slots - they are never lexed or
parsed as SQL tokens, so no combination of quotes, `OR`, or `--` in a
bound value can change the query's structure.
---------------------------------------------------------------------
"""

print("\n--- Why This Works: Structure vs. Data ---")

print("naive:  Python builds the FINAL SQL text FIRST (attacker's")
print("        characters become part of that text) -> THEN sqlite3")
print("        parses it as SQL. Too late - the damage is done in")
print("        the string-building step, before the DB is involved.")
print("safe:   sqlite3 receives the TEMPLATE (with '?' placeholders)")
print("        and prepares/compiles it as a fixed plan. The VALUES")
print("        are bound into that plan SEPARATELY and are never")
print("        re-parsed as SQL syntax - they can only ever be data.")

# Proof: the template text is IDENTICAL no matter what the value is -
# unlike the naive version, whose printed SQL text changes per input.
safe_login(conn, "anyone", "totally normal password")
safe_login(conn, "anyone", "'; DROP TABLE users; --")
print("\nNotice the '[safe] SQL template' line printed IDENTICAL SQL")
print("text both times above, even though the second password was a")
print("full DROP TABLE attempt - the template never changes shape.")


"""
---------------------------------------------------------------------
6. DIFFERENT DRIVERS, DIFFERENT PARAMSTYLES - CHECK, DON'T ASSUME  ⭐⭐
---------------------------------------------------------------------
PEP 249 (the Python DB-API spec) defines several PARAMSTYLE
conventions, and different drivers pick different ones. Every
compliant driver exposes its choice as a module-level `paramstyle`
attribute - always check it rather than assuming `?` works
everywhere.

    qmark    -> sqlite3:            "... WHERE id = ?"
    numeric  -> some ODBC drivers:  "... WHERE id = :1"
    named    -> sqlite3 (alt.):     "... WHERE id = :id"
    format   -> less common:        "... WHERE id = %s" (no % escaping)
    pyformat -> psycopg2, MySQLdb:  "... WHERE id = %(id)s" or "%s"

Mixing these up is a real, easy mistake: writing `%s` against sqlite3,
or `?` against psycopg2, raises a `sqlite3.ProgrammingError` /
`psycopg2.ProgrammingError` immediately - which is a much safer
failure mode than silently falling back to string formatting to
"make it work".
---------------------------------------------------------------------
"""

print("\n--- Driver Paramstyles: Check, Don't Assume ---")

print("sqlite3.paramstyle:", sqlite3.paramstyle)

try:
    import psycopg2
    print("psycopg2.paramstyle:", psycopg2.paramstyle)
except ImportError:
    print("psycopg2.paramstyle: 'pyformat' (not imported here, no live Postgres server)")

print("\nsqlite3 ALSO supports named placeholders (paramstyle 'named'):")
named_result = conn.execute(
    "SELECT username FROM users WHERE is_admin = :flag",
    {"flag": 1},
).fetchall()
print("named-placeholder query result:", named_result)

# What NOT to do, even though it "looks" parameterized: sqlite3 does
# not understand psycopg2's '%s' placeholder syntax at all - it just
# sees a literal '%' character in the SQL text and fails to parse it.
try:
    conn.execute("SELECT * FROM users WHERE username = %s", ("bob",))
except sqlite3.OperationalError as e:
    print("\nusing psycopg2-style '%s' against sqlite3 fails loudly:")
    print(" ", e)
print("Good - a driver mismatch errors immediately instead of quietly")
print("falling back to unsafe string formatting.")


"""
---------------------------------------------------------------------
7. executemany(): THE SAME PARAMETERIZATION FOR BULK INSERTS  ⭐⭐⭐
---------------------------------------------------------------------
Everything above applies EQUALLY to `executemany()`, which runs one
parameterized statement against a whole sequence of value-tuples in
one call - the standard way to do safe, efficient batch inserts in
an ETL load step (the natural next topic after this one). Each
tuple's values are bound the same way - never string-formatted, no
matter how large the batch is.
---------------------------------------------------------------------
"""

print("\n--- executemany(): Parameterized Bulk Inserts ---")

conn.execute(
    "CREATE TABLE login_events (username TEXT NOT NULL, note TEXT NOT NULL)"
)

incoming_events = [
    ("alice", "login success"),
    ("bob", "login failed"),
    # a value that LOOKS like an attack is still just data here:
    ("mallory", "'; DROP TABLE login_events; --"),
]
conn.executemany(
    "INSERT INTO login_events (username, note) VALUES (?, ?)",
    incoming_events,
)
conn.commit()

rows = conn.execute("SELECT * FROM login_events").fetchall()
print(f"inserted {len(rows)} rows via executemany(), table still intact:")
for row in rows:
    print(" ", row)
print("\nThe malicious-looking 'note' value for mallory was stored as")
print("an ordinary string - it never touched the SQL parser, so no")
print("DROP TABLE ever ran, and 'login_events' clearly still exists.")


"""
---------------------------------------------------------------------
8. THE ORM TRAP: SQLALCHEMY PARAMETERIZES BY DEFAULT - UNTIL YOU
   DROP INTO RAW TEXT()  ⭐⭐⭐
---------------------------------------------------------------------
A common misconception is "we use an ORM, so we're immune to SQL
injection." SQLAlchemy's query-building API (`select()`, `.where()`,
ORM queries) DOES parameterize automatically. But `sqlalchemy.text()`
accepts a raw SQL string - if that string is built with an f-string
using untrusted input, the SAME vulnerability comes right back,
"ORM" branding notwithstanding. The safe way to use `text()` is with
its OWN `:name` bind parameters, passed as a dict - never with
f-string interpolation of the values into the SQL text itself.
---------------------------------------------------------------------
"""

print("\n--- The ORM Trap: SQLAlchemy text() ---")

try:
    from sqlalchemy import create_engine, text

    engine = create_engine("sqlite://")  # separate in-memory DB for this demo
    with engine.begin() as sa_conn:
        sa_conn.execute(text("CREATE TABLE users (username TEXT, password TEXT)"))
        sa_conn.execute(
            text("INSERT INTO users (username, password) VALUES (:u, :p)"),
            {"u": "bob", "p": "hunter2"},
        )

    # SAFE: text() with its own bind parameters - still parameterized.
    with engine.connect() as sa_conn:
        safe_sa_result = sa_conn.execute(
            text("SELECT * FROM users WHERE username = :u AND password = :p"),
            {"u": "bob", "p": malicious_password},
        ).fetchall()
    print("SQLAlchemy text() WITH bind params, malicious payload:", safe_sa_result)

    # UNSAFE: someone got "clever" and f-string'd the SQL before calling text().
    with engine.connect() as sa_conn:
        unsafe_sql = f"SELECT * FROM users WHERE username = 'bob' AND password = '{malicious_password}'"
        unsafe_sa_result = sa_conn.execute(text(unsafe_sql)).fetchall()
    print("SQLAlchemy text() built via f-string, SAME payload:  ", unsafe_sa_result)
    print("\nSame ORM, same driver - the SECOND call is injectable because")
    print("the SQL TEXT itself was built from untrusted input before")
    print("text() ever saw it. The ORM protects you only as long as you")
    print("let it build/bind the query - never once you hand it a")
    print("pre-formatted string.")
except ImportError:
    print("sqlalchemy not available in this environment - in production,")
    print("the pattern above (text() + bind dict, never text(f'...')) is")
    print("the rule to enforce in code review.")


"""
---------------------------------------------------------------------
9. ETL SCENARIO: DYNAMIC WHERE CLAUSES & COLUMN ALLOWLISTS  ⭐⭐⭐
---------------------------------------------------------------------
A recurring real ETL need: build a WHERE clause (or a SELECT column
list) at runtime from config or user-supplied filters. Parameterized
placeholders ONLY work for VALUES - a `?` can stand in for
`'bob'` or `42`, but SQL does not allow a placeholder to stand in for
an IDENTIFIER like a column or table name (`SELECT ? FROM users` is
not valid SQL, and drivers will error or silently treat it as a
string literal). Interviewers like probing exactly this distinction:
"parameterized queries protect VALUES, not identifiers."

The correct fix for dynamic identifiers is an ALLOWLIST: validate the
requested column/table name against a fixed set of names YOUR code
controls, then it's safe to include it directly in the SQL text
(never take it from user input for direct interpolation without that
check). Values still go through placeholders as always.
---------------------------------------------------------------------
"""

print("\n--- ETL Scenario: Safe Dynamic Filtering with an Allowlist ---")

ALLOWED_FILTER_COLUMNS = {"username", "is_admin"}  # controlled by our code, not by input


def build_dynamic_query(filters: dict):
    """
    filters: {column_name: value, ...} - column names are validated
    against an ALLOWLIST (identifiers can't be parameterized); values
    are always bound via '?' placeholders (values CAN be parameterized).
    """
    for column in filters:
        if column not in ALLOWED_FILTER_COLUMNS:
            raise ValueError(f"column {column!r} is not in the allowlist")

    where_clause = " AND ".join(f"{column} = ?" for column in filters)
    query = f"SELECT id, username, is_admin FROM users WHERE {where_clause}"
    return query, tuple(filters.values())

# Legitimate config-driven filter: column names are safe (allowlisted),
# values are safe (parameterized) - both halves of the problem covered.
query, params = build_dynamic_query({"is_admin": 1})
print("generated query:", query, "| params:", params)
print("result:", conn.execute(query, params).fetchall())

# An attacker (or a bad upstream config value) tries to smuggle SQL
# in through what LOOKS like a column name - this is exactly the case
# a placeholder CANNOT protect against, so the allowlist check must
# catch it instead.
try:
    malicious_column = "username; DROP TABLE users; --"
    build_dynamic_query({malicious_column: 1})
except ValueError as e:
    print("\nrejected malicious 'column name' before it ever reached SQL:")
    print(" ", e)

print("\nusers table still intact after the rejected attempt:")
print(" ", conn.execute("SELECT username FROM users").fetchall())

conn.close()


"""
=====================================================================
QUICK REFERENCE
=====================================================================
The vulnerability -> f-string / % / .format() builds the FULL SQL
                      text from untrusted input BEFORE the DB sees it

The fix            -> pass a query TEMPLATE with placeholders + the
                      VALUES as a separate tuple/dict to .execute()

sqlite3 paramstyle -> "qmark": cursor.execute("... WHERE x = ?", (v,))
                      also supports "named": "... WHERE x = :x", {"x": v}
psycopg2/MySQLdb   -> "pyformat": cursor.execute("... WHERE x = %s", (v,))
Always check        -> module.paramstyle - never assume one style
                        works across every driver

Why it works        -> query structure and data are sent SEPARATELY;
                        the driver never re-parses bound values as SQL

executemany()       -> same rule, one parameterized statement applied
                        to many value-tuples - the standard safe bulk
                        insert pattern

ORMs (SQLAlchemy)   -> parameterize automatically via select()/ORM
                        queries AND via text(":name", {...}); the
                        vulnerability returns the moment text() is
                        built from an f-string/concatenated string

Values vs. identifiers -> placeholders ('?') work ONLY for VALUES.
                          Column/table names must be validated against
                          an ALLOWLIST, then interpolated directly -
                          never taken from raw user/config input
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - PARAMETERIZED QUERIES & SQL INJECTION
=====================================================================

1. How do you prevent SQL injection when running dynamic queries from
   Python?

2. In `naive_login()`, walk through exactly how the payload
   `"' OR '1'='1"` transforms the WHERE clause, and explain why it
   returns every row in the `users` table instead of zero rows.

3. Why does the identical payload against `safe_login()` correctly
   return zero rows? What is sqlite3 actually doing differently with
   the `?` placeholder versus the f-string version?

4. Explain, at a mechanical level, why parameterized queries prevent
   injection - what does it mean for "query structure" and "data" to
   be sent to the database separately?

5. What is a DB-API "paramstyle"? Name at least two different
   paramstyles and which driver(s) use each one.

6. If you passed a psycopg2-style `%s` placeholder into a `sqlite3`
   `.execute()` call, what would happen, and why is that actually a
   safer failure mode than the query silently "working"?

7. Does parameterization apply to `executemany()` the same way it
   applies to `execute()`? Describe how you'd safely bulk-insert
   10,000 rows using `executemany()`.

8. True or false: "If we use an ORM like SQLAlchemy, we can't be
   vulnerable to SQL injection." Explain your answer, referencing
   `text()` specifically.

9. In the SQLAlchemy example, both queries use `text()` - one is safe
   and one isn't. What is the actual difference between them?

10. Can a `?` (or `%s`, or `:name`) placeholder be used to
    parameterize a column name or table name in a dynamic query? Why
    or why not?

11. You need to let a config file specify which column to filter a
    report on at runtime. Since you can't parameterize an identifier,
    how do you make that safe?

12. In `build_dynamic_query()`, what happens if someone passes
    `"username; DROP TABLE users; --"` as a filter key, and at what
    point in the code is that attempt actually stopped?

13. Why is it not enough to just "escape quotes" or strip dangerous
    characters from user input as a defense against SQL injection,
    compared to using parameterized queries?

14. How would you unit test that a data-access function is NOT
    vulnerable to SQL injection?

15. Beyond login forms, name a couple of realistic places in an ETL
    pipeline where unsanitized string-built SQL could sneak in (hint:
    dynamic filters from an API, config-driven table/column names,
    user-supplied search terms feeding a report query).
=====================================================================
"""
