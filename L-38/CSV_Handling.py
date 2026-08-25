"""
=====================================================================
CSV HANDLING - THE csv MODULE vs PANDAS - Complete Notes with
Executable Examples
=====================================================================

CSV (Comma-Separated Values) is the single most common interchange
format a data engineer touches: every vendor export, every ad-hoc
analyst dump, and half of all "legacy system" integrations arrive as
CSV. It looks trivial ("just split on commas!") but it is actually a
loosely-specified, quoting-sensitive text format, and getting it
wrong silently corrupts data rather than raising an error.

Python gives you two very different tools for it:

    - The stdlib `csv` module: a thin, correct, ROW-AT-A-TIME parser/
      writer. It handles quoting, delimiters, and line endings
      properly, uses almost no memory beyond the current row, and has
      zero dependencies. It returns plain strings - no type inference.

    - `pandas.read_csv` / `DataFrame.to_csv`: loads the WHOLE file (or
      a chunk of it) into a DataFrame, with automatic type inference,
      column selection, date parsing, and NA handling built in - at
      the cost of memory (the whole table lives in RAM) and the
      pandas dependency.

Interviewers care about this topic because "read this CSV" is a
proxy for "do you understand where your data actually lives in
memory, and do you know the footguns (quoting, encoding, newline
translation) that make CSV break in production." This file covers
both tools, the classic `newline=''` pitfall, delimiter/quoting
edge cases, and when to reach for which tool.
=====================================================================
"""

import csv
import io
import os
import sys
import tempfile

import pandas as pd

print("--- Overview ---")
print("csv module  -> correct, row-by-row, string-only, low memory.")
print("pandas      -> whole-table, type-inferred, vectorized, more RAM.")


# All demo files live in one auto-cleaned temporary directory. Using
# TemporaryDirectory as a context manager (rather than mkdtemp + a
# manual rmtree) guarantees cleanup runs even if a demo below raised
# an exception we forgot to catch - the `with` block's __exit__ always
# fires. Everything that touches real files is indented under this
# block; the QUICK REFERENCE / INTERVIEW QUESTIONS sections at the end
# need no files, so they live outside it.
with tempfile.TemporaryDirectory(prefix="csv_demo_") as TMP_DIR:

    """
    ---------------------------------------------------------------------
    1. csv.writer / csv.reader - LIST-OF-LISTS  ⭐⭐⭐
    ---------------------------------------------------------------------
    The lowest-level API: each row is just a plain Python list (or any
    iterable) of values in positional order. `csv.writer` takes care of
    quoting/escaping and line terminators for you; `csv.reader` gives
    every field back as a str (NO type inference - "42" stays "42").
    ---------------------------------------------------------------------
    """

    print("\n--- csv.writer / csv.reader (list-of-lists) ---")

    list_csv_path = os.path.join(TMP_DIR, "employees_rows.csv")

    header = ["id", "name", "department", "salary"]
    rows = [
        [1, "Alice Chen", "Engineering", 118500],
        [2, "Bilal Khan", "Data", 104200],
        [3, "Carmen Diaz", "Engineering", 121000],
    ]

    with open(list_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)       # one row = one call
        writer.writerows(rows)        # or hand it many rows at once

    with open(list_csv_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        loaded_header = next(reader)          # first row consumed manually
        loaded_rows = list(reader)             # remaining rows

    print("header:", loaded_header)
    for row in loaded_rows:
        print(" row:", row)
    print("NOTE: every value came back as a str -", repr(loaded_rows[0][0]),
          "not the int 1 - csv.reader never guesses types for you.")


    """
    ---------------------------------------------------------------------
    2. csv.DictWriter / csv.DictReader - DICT ROWS  ⭐⭐⭐
    ---------------------------------------------------------------------
    Same underlying format, but each row is a dict keyed by column name
    instead of a positional list. This is usually preferable in real
    pipeline code: column order in the SOURCE data can't silently swap
    two fields on you, and downstream code reads like `row["salary"]`
    instead of the much more fragile `row[3]`.
    ---------------------------------------------------------------------
    """

    print("\n--- csv.DictWriter / csv.DictReader (dict rows) ---")

    dict_csv_path = os.path.join(TMP_DIR, "employees_dicts.csv")

    dict_rows = [
        {"id": 1, "name": "Alice Chen", "department": "Engineering", "salary": 118500},
        {"id": 2, "name": "Bilal Khan", "department": "Data", "salary": 104200},
        {"id": 3, "name": "Carmen Diaz", "department": "Engineering", "salary": 121000},
    ]

    with open(dict_csv_path, "w", newline="", encoding="utf-8") as f:
        # fieldnames is REQUIRED for DictWriter - it both defines the
        # header row written by writeheader() and the key order used
        # when serializing each dict.
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(dict_rows)

    with open(dict_csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)      # reads the header row itself
        for row in reader:
            print(" dict row:", row, "-> department:", row["department"])

    # A dict row missing a key entirely, or a data row with EXTRA
    # trailing fields, doesn't crash DictReader - it uses restkey/
    # restval to absorb the mismatch instead of raising. Worth knowing:
    scratch = io.StringIO("id,name\n1,Alice,extra_field\n2\n")
    for row in csv.DictReader(scratch):
        print(" ragged row:", row)
    print("extra fields land under the None key (restkey); a missing")
    print("trailing field is filled with None (restval) by default.")


    """
    ---------------------------------------------------------------------
    3. WHY open() NEEDS newline='' WHEN WRITING (OR READING) CSV  ⭐⭐⭐
    ---------------------------------------------------------------------
    `csv.writer` always terminates rows with '\\r\\n' by default
    (the format's own line terminator, regardless of platform - this
    is per the CSV spec, not a Python quirk). The problem: Python's
    text-mode file objects ALSO do their own newline translation
    unless you disable it. On WINDOWS, opening a file in text mode
    with the default newline behavior translates every '\\n' written
    to os.linesep ('\\r\\n'). Combine the two and '\\r\\n' (from csv)
    becomes '\\r\\r\\n' (also translated by the file object) - every
    row ends up with a DUPLICATED carriage return, and some CSV
    readers/Excel will show a blank line after every row, or choke
    entirely. On Linux/macOS os.linesep is already '\\n', so this
    exact bug is invisible here - which is precisely why it surprises
    people the first time they ship to Windows.

    The fix is always the same, on every platform, for every csv
    file you write OR read: pass newline='' to open() and let the csv
    module own line-ending handling completely.
    ---------------------------------------------------------------------
    """

    print("\n--- Why newline='' Is Required for CSV I/O ---")

    no_newline_path = os.path.join(TMP_DIR, "no_newline_arg.csv")
    correct_path = os.path.join(TMP_DIR, "with_newline_arg.csv")

    # WRONG on Windows (harmless-looking here on Linux): omitting
    # newline='' lets the text layer's own newline translation run
    # on top of whatever csv.writer already wrote.
    with open(no_newline_path, "w", encoding="utf-8") as f:   # no newline=''
        csv.writer(f).writerow(["a", "b"])

    # CORRECT everywhere: newline='' disables the file object's own
    # newline translation, so the '\r\n' that csv.writer produces
    # reaches disk exactly once, unmodified.
    with open(correct_path, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(["a", "b"])

    with open(no_newline_path, "rb") as f:
        print("without newline='', raw bytes written:", f.read())
    with open(correct_path, "rb") as f:
        print("with    newline='', raw bytes written:", f.read())
    print("Identical on Linux (os.linesep == '\\n' here means the text")
    print("layer has nothing extra to translate) - but on Windows the")
    print("first line would come out as b'a,b\\r\\r\\n', doubled. Always")
    print("pass newline='' for csv I/O regardless of the platform you")
    print("develop on, so the behavior doesn't depend on who runs it.")


    """
    ---------------------------------------------------------------------
    4. DELIMITERS OTHER THAN COMMA  ⭐⭐
    ---------------------------------------------------------------------
    "CSV" is used loosely - TSV (tab-separated) exports and semicolon-
    separated exports (common from European locales, where comma is
    the DECIMAL separator) are both extremely common in real data
    sources. Both `csv.writer`/`csv.reader` and `pandas.read_csv`
    accept a `delimiter=` argument - the rest of the quoting logic
    works identically regardless of which character you choose.
    ---------------------------------------------------------------------
    """

    print("\n--- Delimiters Other Than Comma ---")

    tsv_path = os.path.join(TMP_DIR, "employees.tsv")
    semi_path = os.path.join(TMP_DIR, "employees_eu.csv")

    with open(tsv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(header)
        writer.writerows(rows)

    with open(semi_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(header)
        writer.writerows(rows)

    with open(tsv_path, newline="", encoding="utf-8") as f:
        print("TSV first data row:", list(csv.reader(f, delimiter="\t"))[1])
    with open(semi_path, newline="", encoding="utf-8") as f:
        print("semicolon-CSV first data row:",
              list(csv.reader(f, delimiter=";"))[1])
    print("Same csv.reader/writer API - only `delimiter=` changes.")
    print("pandas mirrors this: pd.read_csv(path, delimiter='\\t') or")
    print("the shorthand pd.read_csv(path, sep=';') for the EU-style file.")


    """
    ---------------------------------------------------------------------
    5. QUOTING EDGE CASES: A NAIVE ','.join() BREAKS, csv DOESN'T  ⭐⭐⭐
    ---------------------------------------------------------------------
    The whole reason a dedicated csv module exists: a field can itself
    contain the delimiter, a literal double-quote, or an embedded
    newline. The CSV spec's answer is to wrap such a field in double
    quotes (and double up any literal quote characters inside it).
    Hand-rolling this with ','.join(row) looks fine until real data
    hits it - then it silently produces a MALFORMED file with the
    wrong number of columns once you parse it back.
    ---------------------------------------------------------------------
    """

    print("\n--- Quoting Edge Cases: Naive join() vs the csv Module ---")

    tricky_rows = [
        ["id", "note"],
        [1, "Smith, John"],                    # comma INSIDE a field
        [2, "Line one\nLine two"],              # newline INSIDE a field
        [3, 'He said "hello"'],                 # literal quote INSIDE a field
    ]

    # --- BUGGY: naive manual join, no quoting at all ---
    naive_path = os.path.join(TMP_DIR, "naive_join.csv")
    with open(naive_path, "w", newline="", encoding="utf-8") as f:
        for row in tricky_rows:
            f.write(",".join(str(v) for v in row) + "\n")   # no escaping!

    with open(naive_path, newline="", encoding="utf-8") as f:
        naive_line_count = sum(1 for _ in f)
    with open(naive_path, newline="", encoding="utf-8") as f:
        naive_parsed_back = list(csv.reader(f))
    print("naive file has", naive_line_count, "physical lines for",
          len(tricky_rows), "logical rows - the embedded newline SPLIT")
    print("a single record into two physical lines.")
    print("naive re-parsed row 2 (comma field):", naive_parsed_back[1],
          "<- 3 columns instead of 2! 'Smith, John' got split in half.")

    # --- FIXED: let csv.writer handle quoting ---
    correct_quote_path = os.path.join(TMP_DIR, "correct_quoting.csv")
    with open(correct_quote_path, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(tricky_rows)

    with open(correct_quote_path, newline="", encoding="utf-8") as f:
        print("raw bytes on disk:", f.read())
    with open(correct_quote_path, newline="", encoding="utf-8") as f:
        correct_parsed_back = list(csv.reader(f))
    print("csv-module re-parsed rows:")
    for row in correct_parsed_back:
        print(" ", row)
    print("Every field round-trips EXACTLY, including the embedded")
    print("comma, newline, and literal quote - csv.writer quoted the")
    print("field and doubled the internal quote character automatically.")


    """
    ---------------------------------------------------------------------
    6. READING THE SAME FILE WITH pandas.read_csv()  ⭐⭐⭐
    ---------------------------------------------------------------------
    pandas.read_csv is built ON TOP of the same underlying C parser
    concepts, but returns a whole DataFrame with per-column type
    inference instead of strings. The commonly-tested knobs:
        dtype=       force specific column types (skip/override inference)
        usecols=     load only some columns (saves memory + time)
        parse_dates= parse listed columns as datetime64 instead of str
        na_values=   extra strings to treat as missing (NaN)
    ---------------------------------------------------------------------
    """

    print("\n--- Reading the Same File with pandas.read_csv() ---")

    df_default = pd.read_csv(list_csv_path)
    print("default dtype inference:\n", df_default.dtypes)

    df_controlled = pd.read_csv(
        list_csv_path,
        usecols=["name", "department", "salary"],   # drop the id column
        dtype={"salary": "float64"},                  # force salary to float
    )
    print("\nwith usecols= and dtype=:\n", df_controlled)
    print("dtypes:\n", df_controlled.dtypes)

    # parse_dates= and na_values= demonstrated against a small file with
    # a date column and a placeholder for missing data:
    dated_path = os.path.join(TMP_DIR, "hires.csv")
    with open(dated_path, "w", newline="", encoding="utf-8") as f:
        f.write("name,hire_date,bonus\n")
        f.write("Alice Chen,2023-01-15,5000\n")
        f.write("Bilal Khan,2022-06-01,NULL\n")     # sentinel for missing
        f.write("Carmen Diaz,2024-03-10,2500\n")

    df_dates = pd.read_csv(
        dated_path,
        parse_dates=["hire_date"],       # -> datetime64[ns], not str
        na_values=["NULL"],               # treat the literal "NULL" as NaN
    )
    print("\nparse_dates + na_values:\n", df_dates)
    print("dtypes:\n", df_dates.dtypes)
    print("bonus for Bilal Khan is now:", df_dates.loc[1, "bonus"],
          "(a real NaN, ready for .fillna()/.dropna() - not the string 'NULL')")

    print("\ncsv.reader would have given us EVERY value as a str -")
    print("pandas did type inference, date parsing, and NA detection")
    print("in one call. That convenience is also pandas's cost: the")
    print("whole file was loaded and scanned twice (a type-inference")
    print("pass + a parse pass) before you got anything back.")


    """
    ---------------------------------------------------------------------
    7. csv MODULE vs PANDAS: A DECISION GUIDE  ⭐⭐⭐
    ---------------------------------------------------------------------
    This is the actual interview question underneath "how do you read
    a CSV in Python" - they want to see you reason about MEMORY and
    DEPENDENCIES, not just recite two API names.
    ---------------------------------------------------------------------
    """

    print("\n--- csv Module vs Pandas: A Decision Guide ---")

    # Streaming demo: csv.reader is a lazy ITERATOR over the underlying
    # file object - only ONE row is materialized in memory at a time,
    # no matter how large the file is. This is what makes it suitable
    # for a file that doesn't fit in RAM.
    total_salary = 0
    row_count = 0
    with open(list_csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:                  # one row in memory at a time
            total_salary += int(row["salary"])
            row_count += 1
    print(f"streamed {row_count} rows with csv.DictReader, "
          f"total_salary={total_salary}, peak memory ~ one row.")

    # The pandas equivalent is correct too, but the ENTIRE file is
    # resident in the DataFrame at once - fine at this tiny size, the
    # deciding factor once files get into the GBs.
    total_salary_pd = int(pd.read_csv(list_csv_path)["salary"].sum())
    print(f"same total via pandas vectorized .sum(): {total_salary_pd}")

    print(
        "\nUse the stdlib csv module when:\n"
        "  - the file is too large to fit in memory (stream row-by-row,\n"
        "    e.g. a nightly multi-GB export)\n"
        "  - you only need to reshape/filter/forward rows, not join or\n"
        "    aggregate across the whole dataset\n"
        "  - you can't or don't want a pandas dependency (a small\n"
        "    utility script, a Lambda with a tight package size limit)\n"
        "  - you need precise control over quoting/dialect/encoding\n"
        "\n"
        "Use pandas when:\n"
        "  - you need vectorized transforms, groupby, merge/join, or\n"
        "    pivoting after loading (i.e. real analysis, not just\n"
        "    pass-through)\n"
        "  - you want automatic/controlled type inference (dtype=,\n"
        "    parse_dates=) instead of manually casting every field\n"
        "  - the file comfortably fits in memory (or you use\n"
        "    chunksize= to process it in batches - a middle ground)\n"
    )


    """
    ---------------------------------------------------------------------
    8. REALISTIC ETL EXAMPLE: CLEANING A MESSY CSV  ⭐⭐⭐
    ---------------------------------------------------------------------
    A stand-in for a real vendor export: inconsistent whitespace,
    a missing salary, a malformed date, and a non-numeric age. This is
    exactly the kind of file interviewers hand you as a take-home.
    ---------------------------------------------------------------------
    """

    print("\n--- Realistic ETL Example: Cleaning a Messy CSV ---")

    messy_path = os.path.join(TMP_DIR, "messy_export.csv")
    with open(messy_path, "w", newline="", encoding="utf-8") as f:
        f.write("id,name,age,signup_date,salary\n")
        f.write("1,  Alice Chen ,34,2023-01-15,118500\n")     # extra whitespace
        f.write("2,Bilal Khan,not_a_number,2022-06-01,104200\n")  # bad age
        f.write("3,Carmen Diaz,29,2024-03-10,\n")               # missing salary
        f.write("4,Deepa Rao,41,31/12/2021,99500\n")            # non-ISO date
        f.write("5,Evan Wu,,2023-11-02,NA\n")                   # missing age + salary

    raw = pd.read_csv(
        messy_path,
        na_values=["", "NA", "N/A", "not_a_number"],  # normalize missing markers
    )
    print("raw load:\n", raw)

    cleaned = raw.copy()
    cleaned["name"] = cleaned["name"].str.strip()          # trim stray whitespace
    cleaned["age"] = pd.to_numeric(cleaned["age"], errors="coerce")  # -> NaN if bad
    # mixed date formats (ISO and DD/MM/YYYY): try ISO first, then fall
    # back to the day-first format for whatever ISO parsing couldn't handle
    parsed_iso = pd.to_datetime(cleaned["signup_date"], format="%Y-%m-%d", errors="coerce")
    parsed_dmy = pd.to_datetime(cleaned["signup_date"], format="%d/%m/%Y", errors="coerce")
    cleaned["signup_date"] = parsed_iso.fillna(parsed_dmy)
    cleaned["salary"] = pd.to_numeric(cleaned["salary"], errors="coerce")

    print("\ncleaned dtypes:\n", cleaned.dtypes)
    print("\ncleaned data:\n", cleaned)

    missing_salary = cleaned[cleaned["salary"].isna()]
    print(f"\n{len(missing_salary)} row(s) still missing salary after cleaning:")
    print(missing_salary[["id", "name"]])

    # A realistic pipeline decision: quarantine bad rows instead of
    # silently dropping them, so the ETL job is auditable and re-runnable.
    quarantine_path = os.path.join(TMP_DIR, "quarantine.csv")
    good_rows = cleaned.dropna(subset=["age", "salary", "signup_date"])
    bad_rows = cleaned.loc[cleaned.index.difference(good_rows.index)]
    bad_rows.to_csv(quarantine_path, index=False)
    print(f"\n{len(good_rows)} clean row(s) ready to load; "
          f"{len(bad_rows)} row(s) written to quarantine.csv for review.")

    # Cleanup note: TMP_DIR (and every file above) is removed
    # automatically the moment this `with` block exits below - that is
    # the ENTIRE cleanup mechanism, no explicit os.remove() calls needed.

print(f"\ntemp directory existed during the demo, now removed: "
      f"{not os.path.exists(TMP_DIR)}")


"""
=====================================================================
QUICK REFERENCE
=====================================================================
csv.writer(f)              -> write rows from lists/tuples
csv.reader(f)               -> read rows back as lists of str
csv.DictWriter(f, fieldnames=)   -> write rows from dicts
csv.DictReader(f)                 -> read rows back as dicts (str values)

ALWAYS: open(path, 'w', newline='')   when writing CSV
        open(path, newline='')         when reading CSV
        -> lets csv module own line-endings; skips this and Windows
           text-mode translation can DOUBLE the '\\r' csv.writer adds

delimiter='\\t' / ';'          -> any single character, same API
Naive ','.join(row)            -> BREAKS on embedded commas/newlines
csv.writer / csv.reader        -> quotes/escapes automatically, always
                                   round-trips correctly

pandas.read_csv(path,
    dtype={...})                -> force column types, skip inference
    usecols=[...]               -> load only these columns
    parse_dates=[...]            -> parse as datetime64 instead of str
    na_values=[...])              -> extra strings treated as NaN

csv module   -> huge files, streaming, minimal memory, no dependency
pandas       -> need groupby/merge/pivot/vectorized transforms after

ETL pattern: na_values= to normalize missing markers -> pd.to_numeric/
pd.to_datetime(errors='coerce') per column -> dropna() the required
columns -> route survivors vs quarantine into separate outputs.
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - CSV HANDLING (csv MODULE vs PANDAS)
=====================================================================

1. Walk through the difference between csv.writer/csv.reader and
   csv.DictWriter/csv.DictReader - when would you prefer the dict-
   based API for a pipeline over the list-based one?

2. Why must you pass `newline=''` to `open()` when writing or reading
   a CSV file with the csv module? What specific bug happens on
   Windows if you omit it, and why is it invisible on Linux/macOS?

3. What line terminator does `csv.writer` use by default, and how
   does that interact with a text-mode file object's own newline
   translation to cause the "doubled \\r\\n" bug?

4. Given `','.join(str(v) for v in row)` as a hand-rolled CSV writer,
   show a concrete row of data that breaks it, and explain exactly
   how the output gets misparsed downstream.

5. How does the csv module handle a field that itself contains the
   delimiter character, or a literal double-quote character? What
   does the resulting quoted/escaped text look like on disk?

6. How do you read or write a tab-separated (TSV) or semicolon-
   separated file with both the csv module and pandas? What single
   argument changes?

7. What does `pandas.read_csv` do differently from `csv.reader` in
   terms of the TYPES of the values you get back for each column?

8. What is `dtype=` used for in `pd.read_csv`, and why would you want
   to override pandas's automatic type inference for a column like an
   ID or ZIP code that looks numeric but shouldn't be treated as one?

9. What do `usecols=` and `parse_dates=` do in `pd.read_csv`, and why
   would you use them together on a large file with many columns?

10. How does `na_values=` in `pd.read_csv` differ from cleaning missing
    values AFTER loading with `.fillna()`/`.dropna()`?

11. You need to process a 20 GB CSV file on a machine with 8 GB of
    RAM. Would you reach for the csv module or pandas.read_csv?
    What if pandas were a hard requirement - what would you use
    instead of loading the whole file at once? (Hint: `chunksize=`.)

12. When would you choose pandas over the csv module even for a
    smallish file, despite the extra dependency and memory overhead?

13. In the messy_export.csv example, `signup_date` has two different
    date formats mixed in the same column. How did the cleaning code
    handle that, and what would `pd.to_datetime(..., errors='coerce')`
    alone (without the two-pass fallback) have done to the DD/MM/YYYY
    rows if only the ISO format string were tried?

14. Why did the ETL example write bad rows to a separate
    "quarantine" file instead of just dropping them silently? What
    does this pattern buy you operationally in a scheduled pipeline?

15. Compare read/write speed and storage between CSV, Parquet, and
    Avro at a high level - which of these is row-oriented vs
    columnar, and why does that matter for a wide table where most
    queries only touch a few columns? (Full comparison covered in a
    later file - CSV's own read/write characteristics are covered
    here.)
=====================================================================
"""
