"""
=====================================================================
SQLALCHEMY ORM BASICS - Complete Notes with Executable Examples
=====================================================================

SQLAlchemy is really TWO libraries stacked on top of each other:

    CORE   - the "SQL Expression Language". You work with `Table`
             objects, `text()`, and an `Engine`, and you get back
             plain ROWS (tuples with named fields). This is a thin,
             Pythonic wrapper directly over SQL - you're still
             thinking in terms of tables and columns.

    ORM    - built ON TOP of Core. You map Python CLASSES to tables
             (`Customer`, `Order`, ...) and work with OBJECTS instead
             of rows. A `Session` tracks those objects, and generates
             the INSERT/UPDATE/DELETE statements for you.

You almost never touch the ORM without Core running underneath it -
every ORM query eventually compiles down to a Core statement, which
compiles down to a SQL string. Interviewers care about this layering
because it explains WHY you can always "drop down" to raw SQL via
`text()` when the ORM's object-mapping gets in the way of a complex
or performance-critical query - you're not fighting a black box, you're
just choosing which layer of the same tool to use.

This file uses a real, in-memory SQLite database (`sqlite:///:memory:`)
so every statement below is REAL SQL, actually executed - not a mock.
The concepts transfer directly to Postgres/MySQL by swapping the
connection string.
=====================================================================
"""

from sqlalchemy import create_engine, text, select, Table, Column, Integer, String, MetaData, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session
from typing import List, Optional
import sqlalchemy

print("--- Overview ---")
print(f"sqlalchemy version detected: {sqlalchemy.__version__}")
print("CORE = SQL Expression Language (tables, text(), rows back)")
print("ORM  = classes mapped to tables (objects back, Session tracks them)")
print("The ORM is built ON TOP of Core - both compile to the same SQL.")


"""
---------------------------------------------------------------------
1. THE ENGINE: SQLALCHEMY'S CONNECTION FACTORY  ⭐⭐
---------------------------------------------------------------------
An `Engine` is not a single open connection - it's a FACTORY that
manages a pool of connections to the database, created ONCE per
process from a connection string. `sqlite:///:memory:` gives us a
private in-memory database that lives only for this process - handy
for demos and tests, but the exact same API targets a real Postgres
server via e.g. `postgresql+psycopg2://user:pass@host/dbname`.
---------------------------------------------------------------------
"""

print("\n--- The Engine ---")

# echo=False keeps our own prints readable; set echo=True in real
# debugging to see every generated SQL statement on stdout.
engine = create_engine("sqlite:///:memory:", echo=False)
print("engine created:", engine)
print("dialect in use:", engine.dialect.name)


"""
---------------------------------------------------------------------
2. CORE vs ORM: THE SAME "SELECT ALL USERS" QUERY, TWO WAYS  ⭐⭐⭐
---------------------------------------------------------------------
To see exactly how the two layers relate, here is the SAME query -
"give me all rows from a users table" - written first with Core
(a `Table` object + engine `.execute()`, returning plain ROWS), then
with the ORM (a mapped class + `Session`, returning OBJECTS). The ORM
version is defined properly in section 3 and reused from section 6
onward; this section's Core table is a throwaway, side-by-side
comparison only.
---------------------------------------------------------------------
"""

print("\n--- Core vs ORM: Same Query, Two Ways ---")

# --- CORE: describe the table by hand, no Python class involved ---
core_metadata = MetaData()
users_table = Table(
    "users_core_demo",
    core_metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(50)),
)
core_metadata.create_all(engine)

with engine.connect() as conn:
    conn.execute(users_table.insert(), [{"name": "Ana"}, {"name": "Bo"}])
    conn.commit()
    # Core's select() returns ROWS - tuple-like objects with named fields
    core_rows = conn.execute(select(users_table)).all()

print("CORE result (rows):", core_rows)
print("  accessed like a tuple/namedtuple:", core_rows[0][0], core_rows[0].name)
print("\nThe ORM version of this exact idea appears in section 6 below,")
print("once we have a mapped class - it returns Customer OBJECTS instead")
print("of rows, but under the hood it compiles to the same kind of SQL.")


"""
---------------------------------------------------------------------
3. DEFINING A MAPPED MODEL: THE DECLARATIVE BASE  ⭐⭐⭐
---------------------------------------------------------------------
Modern SQLAlchemy (2.0+) maps a Python class to a table using a
`DeclarativeBase` subclass shared by all your models, and typed
`Mapped[...]` annotations with `mapped_column()` to describe each
column - this gives you real type-checker support (mypy/pyright) for
free, unlike the older untyped `Column(...)` class-attribute style.
---------------------------------------------------------------------
"""

print("\n--- Defining a Mapped Model ---")

class Base(DeclarativeBase):
    """Shared declarative base - every mapped class inherits from this
    ONE base so SQLAlchemy can collect all their table definitions
    together under `Base.metadata`."""
    pass

class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(100), unique=True)

    # one-to-many: filled in properly in section 8 once Order exists.
    orders: Mapped[List["Order"]] = relationship(back_populates="customer")

    def __repr__(self):
        # Overriding __repr__ makes debugging Session output MUCH easier -
        # the default `<Customer object at 0x7f...>` tells you nothing.
        return f"Customer(id={self.id!r}, name={self.name!r}, email={self.email!r})"

print("Customer is a normal Python class - and ALSO a mapped table:")
print("  __tablename__:", Customer.__tablename__)
print("  mapped columns:", [c.name for c in Customer.__table__.columns])


"""
---------------------------------------------------------------------
4. CREATING THE SCHEMA: Base.metadata.create_all()  ⭐⭐
---------------------------------------------------------------------
Every class that inherits from `Base` registers its table in
`Base.metadata`. Calling `create_all(engine)` issues the actual
`CREATE TABLE` statements for any tables that don't already exist -
it's idempotent, so running it again is a safe no-op.
---------------------------------------------------------------------
"""

print("\n--- Creating Tables from Metadata ---")

class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    item: Mapped[str] = mapped_column(String(100))
    amount: Mapped[float]
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))

    customer: Mapped["Customer"] = relationship(back_populates="orders")

    def __repr__(self):
        return f"Order(id={self.id!r}, item={self.item!r}, amount={self.amount!r})"

# Defining Order here (rather than earlier) keeps the file readable
# top-to-bottom, but both classes are registered on the SAME Base
# before create_all() runs, so both tables get created together.
Base.metadata.create_all(engine)
print("tables now in metadata:", list(Base.metadata.tables.keys()))


"""
---------------------------------------------------------------------
5. THE SESSION: ADDING OBJECTS AND COMMITTING  ⭐⭐⭐
---------------------------------------------------------------------
A `Session` is the ORM's workspace - it wraps a database connection
and tracks every mapped object you hand it. `session.add()` doesn't
hit the database immediately; it just registers the object as
"pending". The actual `INSERT` is issued when the Session flushes
(automatically before a query, or explicitly on `commit()`).
---------------------------------------------------------------------
"""

print("\n--- Session: Adding and Committing ---")

with Session(engine) as session:
    alice = Customer(name="Alice Chen", email="alice@example.com")
    bob = Customer(name="Bob Ruiz", email="bob@example.com")
    session.add(alice)
    session.add_all([bob])          # add_all() for multiple objects at once
    print("before commit, alice.id is:", alice.id)   # None - no INSERT yet!
    session.commit()
    print("after commit, alice.id is:", alice.id)     # DB assigned the PK
    print("after commit, bob.id is:", bob.id)


"""
---------------------------------------------------------------------
6. THE ORM's "UNIT OF WORK" AND IDENTITY MAP  ⭐⭐⭐
---------------------------------------------------------------------
This is the single most interesting ORM-specific concept, and a
genuinely good interview differentiator: within ONE Session, querying
for the SAME primary key TWICE does not create two separate Python
objects - the Session's IDENTITY MAP recognizes it already has a row
with that PK loaded, and returns the EXACT SAME object both times.
This is fundamentally different from Core, where every execute()
call gives you brand-new, independent row tuples.
---------------------------------------------------------------------
"""

print("\n--- Identity Map: Same Row, Same Python Object ---")

with Session(engine) as session:
    first_lookup = session.get(Customer, 1)
    second_lookup = session.get(Customer, 1)
    print("first_lookup :", first_lookup)
    print("second_lookup:", second_lookup)
    print("first_lookup is second_lookup ->", first_lookup is second_lookup)

    # Even a full SELECT for that same row returns the identical object -
    # SQLAlchemy still runs the SELECT (unless it can skip it entirely),
    # but populates the ALREADY-TRACKED instance rather than a new one.
    via_select = session.execute(
        select(Customer).where(Customer.id == 1)
    ).scalar_one()
    print("via_select is first_lookup ->", via_select is first_lookup)
    print("\nThis 'unit of work' pattern is why mutating an object you got")
    print("from a Session and committing just works - there's only ever")
    print("ONE in-memory representation of that row per Session.")


"""
---------------------------------------------------------------------
7. QUERYING WITH select(): .where() AND .order_by()  ⭐⭐⭐
---------------------------------------------------------------------
The modern (2.0-style) way to query the ORM is the SAME `select()`
construct used by Core in section 2 - the difference is you pass it
a mapped CLASS instead of a `Table`, and execute it through a
`Session` instead of a raw `Connection`, so you get OBJECTS back.
This unification (one `select()` for both layers) is a deliberate
2.0 design choice - the old `session.query(...)` style still works
but is considered legacy.
---------------------------------------------------------------------
"""

print("\n--- Querying with select(), where(), order_by() ---")

with Session(engine) as session:
    session.add_all([
        Customer(name="Carla Diaz", email="carla@example.com"),
        Customer(name="Dev Patel", email="dev@example.com"),
    ])
    session.commit()

    stmt = (
        select(Customer)
        .where(Customer.name.like("%a%"))   # names containing "a"
        .order_by(Customer.name)
    )
    matches = session.execute(stmt).scalars().all()   # .scalars() unwraps Row -> Customer
    print("customers with 'a' in their name, alphabetical:")
    for c in matches:
        print(" ", c)


"""
---------------------------------------------------------------------
8. THE ORM's ONE-TO-MANY relationship()  ⭐⭐⭐
---------------------------------------------------------------------
`relationship()` is a purely in-Python, ORM-level construct - it adds
NO column to the table (the actual foreign key lives on `Order.customer_id`,
declared in section 4). It tells the ORM "when someone accesses
`customer.orders`, go fetch the Order rows whose customer_id matches
this customer's id". By default this is LAZY - the query only fires
the moment you actually touch `.orders`, not when the Customer itself
was loaded.
---------------------------------------------------------------------
"""

print("\n--- One-to-Many relationship(): Lazy Loading ---")

with Session(engine) as session:
    alice = session.execute(
        select(Customer).where(Customer.name == "Alice Chen")
    ).scalar_one()

    alice.orders.append(Order(item="Laptop", amount=1299.00))
    alice.orders.append(Order(item="Mouse", amount=25.50))
    session.commit()

with Session(engine) as session:
    alice = session.execute(
        select(Customer).where(Customer.name == "Alice Chen")
    ).scalar_one()
    print("Customer loaded - no Order query has run yet.")
    print("now accessing alice.orders (triggers the lazy load):")
    for order in alice.orders:          # <- SELECT against `orders` fires HERE
        print(" ", order, "-> belongs to", order.customer.name)
    print("\n`back_populates` keeps both sides in sync in memory: appending")
    print("to alice.orders set order.customer_id automatically on commit.")


"""
---------------------------------------------------------------------
9. UPDATING AND DELETING: DIRTY TRACKING  ⭐⭐⭐
---------------------------------------------------------------------
You never write an UPDATE statement by hand in the ORM. You mutate an
attribute on a loaded, Session-tracked object, and the Session marks
it "dirty". At flush/commit time, SQLAlchemy compares the object's
current state to what it loaded and generates an UPDATE containing
ONLY the changed columns. Deleting works the same way via
`session.delete(obj)`.
---------------------------------------------------------------------
"""

print("\n--- Updating and Deleting: Dirty Tracking ---")

with Session(engine) as session:
    bob = session.execute(
        select(Customer).where(Customer.name == "Bob Ruiz")
    ).scalar_one()

    bob.email = "bob.ruiz@newdomain.com"    # just a normal attribute assignment
    print("is bob in session.dirty before commit?", bob in session.dirty)
    session.commit()                          # UPDATE fires here
    print("bob's email is now:", bob.email)

    dev = session.execute(
        select(Customer).where(Customer.name == "Dev Patel")
    ).scalar_one()
    session.delete(dev)
    session.commit()                          # DELETE fires here

    remaining = session.execute(select(Customer.name).order_by(Customer.name)).scalars().all()
    print("remaining customers after delete:", remaining)


"""
---------------------------------------------------------------------
10. THE RAW SQL ESCAPE HATCH: text()  ⭐⭐⭐
---------------------------------------------------------------------
For a complex analytical query - a multi-way join with window
functions, or a database-specific optimization - fighting the ORM's
query builder often costs more than it saves. `text()` lets you drop
to raw SQL while STILL using bound parameters (never f-string
interpolation!), so you keep SQL-injection safety even outside the
ORM. This is the same escape hatch you'd reach for from Core, since
`text()` belongs to Core, not the ORM.
---------------------------------------------------------------------
"""

print("\n--- Raw SQL Escape Hatch: text() ---")

with Session(engine) as session:
    # An analytical-style query: total spend per customer, only customers
    # who have spent above a threshold - easy in raw SQL, clunkier via ORM.
    analytical_query = text("""
        SELECT c.name AS customer_name, SUM(o.amount) AS total_spent
        FROM customers c
        JOIN orders o ON o.customer_id = c.id
        GROUP BY c.name
        HAVING SUM(o.amount) > :min_spent
        ORDER BY total_spent DESC
    """)
    # :min_spent is a BOUND PARAMETER - the driver escapes it safely.
    # Never do f"... > {min_spent}" - that's exactly how SQL injection happens.
    results = session.execute(analytical_query, {"min_spent": 100}).all()
    print("big spenders (raw SQL, bound params):")
    for row in results:
        print(f"  {row.customer_name}: {row.total_spent}")

    # Proving the bound parameter is actually safe: a malicious-looking
    # string is treated purely as DATA, never as SQL syntax.
    hostile_input = "0 OR 1=1; DROP TABLE customers; --"
    try:
        safe_query = text("SELECT * FROM customers WHERE id = :cust_id")
        session.execute(safe_query, {"cust_id": hostile_input}).all()
        print("\nhostile string passed as a bound param -> matched nothing,")
        print("no SQL was altered (SQLite raised no error, just 0 rows).")
    except Exception as e:
        print("\ndriver rejected the type mismatch safely:", e)


"""
---------------------------------------------------------------------
11. CORE vs ORM: THE TRADE-OFF, DIRECTLY ANSWERING THE INTERVIEW
    QUESTION  ⭐⭐⭐
---------------------------------------------------------------------
"Difference between executing raw SQL vs using an ORM - trade-offs?"

ORM PROS:
    - Safe by default: parameters are always bound, so SQL injection
      is far harder to introduce accidentally.
    - Database-agnostic: the SAME Python code (mostly) runs against
      SQLite, Postgres, MySQL - the dialect differences are absorbed
      by SQLAlchemy.
    - Less boilerplate for standard CRUD: session.add()/commit() beats
      hand-writing INSERT/UPDATE strings for every model.
    - Object-oriented ergonomics: relationships, dirty tracking, and
      identity map give you a coherent in-memory object graph instead
      of loose rows you have to stitch together yourself.

RAW SQL / CORE PROS:
    - Full control over exactly what SQL runs - critical for complex
      joins, window functions, CTEs, or a query you need to tune for
      a specific database's query planner.
    - No ORM overhead: no object hydration, no identity-map bookkeeping,
      no relationship-loading surprises (like the classic N+1 problem).
    - Easier to reason about the EXACT generated SQL - what you write
      is very close to what actually executes, which matters when
      profiling a slow query or doing an EXPLAIN ANALYZE.

A REALISTIC DATA ENGINEERING GUIDELINE:
    Use the ORM for application-style CRUD - creating/updating/
    deleting individual records tied to business objects, where
    safety and maintainability matter more than raw throughput.
    Drop to raw SQL / Core for heavy analytical queries and bulk ETL:
    large aggregations, bulk inserts of millions of rows, or anything
    where hydrating full Python objects per row would be wasted work.
---------------------------------------------------------------------
"""

print("\n--- Core vs ORM: The Trade-off ---")
print("ORM: safety + portability + less boilerplate for CRUD.")
print("Raw SQL/Core: full control + no ORM overhead for heavy analytics.")
print("Guideline: ORM for app-style CRUD, raw SQL/Core for bulk ETL.")


"""
=====================================================================
QUICK REFERENCE
=====================================================================
Two layers:
    CORE  -> Table / text() / engine.execute()  -> returns ROWS
    ORM   -> mapped class / Session              -> returns OBJECTS

Define a model:
    class Base(DeclarativeBase): pass
    class Customer(Base):
        __tablename__ = "customers"
        id: Mapped[int] = mapped_column(primary_key=True)
        name: Mapped[str] = mapped_column(String(100))

Create tables:      Base.metadata.create_all(engine)
Add + save:          session.add(obj) -> session.commit()  (flush = INSERT)
Update:              mutate an attribute -> session.commit()  (flush = UPDATE)
Delete:              session.delete(obj) -> session.commit()
Identity map:        session.get(Model, pk) twice in ONE session -> SAME object (is)
Query:               select(Model).where(...).order_by(...) -> session.execute(...).scalars().all()
Relationship:        relationship() on both sides + back_populates, FK column separate
Lazy load:           customer.orders triggers its SELECT only when accessed
Raw SQL escape hatch: session.execute(text("... :param ..."), {"param": value})

ORM strengths   -> injection-safe by default, DB-agnostic, less CRUD
                   boilerplate, object graph ergonomics
Raw SQL strengths -> full query control, no ORM overhead, exact SQL
                     is easy to reason about / tune
Guideline        -> ORM for app CRUD, raw SQL/Core for bulk ETL/analytics
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - SQLALCHEMY ORM BASICS
=====================================================================

1. What is the difference between executing raw SQL and using an ORM
   like SQLAlchemy? What are the trade-offs of each?

2. In this file, `select(users_table)` (Core) and
   `select(Customer)` (ORM) look almost identical - what is actually
   different about what each one returns and how it's executed?

3. What does `Base.metadata.create_all(engine)` actually do, and why
   is it safe to call more than once?

4. Explain the ORM's "identity map": why does
   `session.get(Customer, 1) is session.get(Customer, 1)` return
   `True` within the same Session, and what would change if you
   opened a NEW Session for the second call?

5. What is "dirty tracking"? Walk through what happens internally
   when you do `bob.email = "new@example.com"` followed by
   `session.commit()` - what SQL gets generated, and when?

6. What does `relationship()` actually add to the database schema?
   Where does the real foreign key constraint live in this file's
   `Customer`/`Order` example?

7. What is LAZY loading in the context of `customer.orders`? At what
   exact moment does the SQL query for the related rows actually
   run?

8. Why is `text("SELECT * FROM customers WHERE id = :cust_id")` with
   a bound parameter safe from SQL injection, while building the
   same query with an f-string would not be?

9. When would you deliberately choose Core's `Table`/`select()` over
   the full ORM, even in an otherwise ORM-based codebase?

10. What's the difference between the old `session.query(Model)`
    style and the modern `session.execute(select(Model))` style in
    SQLAlchemy 2.0? Why did the library unify around `select()`?

11. If you call `session.add(alice)` but never call `session.commit()`
    (or the Session is never flushed), what state is `alice` in, and
    what happens to `alice.id`?

12. In a bulk-ETL scenario where you need to insert a million rows,
    why might using individual ORM objects and `session.add()` per
    row be a poor choice compared to Core's bulk `insert()` or raw
    SQL?

13. What is the N+1 query problem, and how could naively accessing
    `.orders` on many `Customer` objects in a loop trigger it?

14. Why does SQLAlchemy separate the CORE layer (SQL Expression
    Language) from the ORM layer architecturally, instead of just
    offering one API?

15. How would you change the connection string in this file's
    `create_engine(...)` call to target a real PostgreSQL database
    instead of the in-memory SQLite one - what stays the same about
    the rest of your ORM code?
=====================================================================
"""
