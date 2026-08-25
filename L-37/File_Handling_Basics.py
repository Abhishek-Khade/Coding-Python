"""
=====================================================================
FILE HANDLING BASICS - open(), Context Managers, pathlib vs os
Complete Notes with Executable Examples
=====================================================================

Every data pipeline eventually touches the filesystem: reading a raw
extract, writing a cleaned output, checking whether yesterday's batch
already ran, walking a folder of partitions to find what needs
ingesting. None of that requires a special library - it's built on
three things every Python developer must know cold:

    1. open() and its MODES - what each one does, whether it can
       create/overwrite/destroy data, and which errors it raises.
    2. READING STRATEGIES - the tradeoff between convenience
       (.read(), .readlines()) and memory (iterating the file object
       directly), which matters enormously once "the file" means
       "an 8GB extract," not a 10-line config.
    3. pathlib vs the older os/os.path module for everything path-
       and directory-related - joining paths, checking existence,
       listing/walking directories, and creating them safely.

This file is deliberately about the FUNDAMENTALS of file I/O -
opening, reading, writing, encoding, and path handling. It does NOT
cover CSV, JSON, or columnar formats (Parquet/Avro) in depth, or
large-file streaming/chunking strategies - those get their own files
later in this module. Think of this one as "everything you need
before you touch a specific file format."
=====================================================================
"""

import os
import shutil
import tempfile
from pathlib import Path

print("--- Overview ---")
print("File I/O in Python comes down to: pick the right open() mode,")
print("read it in a way that doesn't blow up memory, always close it")
print("via `with`, and use pathlib (not os.path) for the surrounding")
print("path/directory logic.")


# A scratch directory for every demo below - cleaned up at the very
# end of the script, however the script exits (see the try/finally
# wrapping every numbered section).
DEMO_DIR = tempfile.mkdtemp(prefix="file_handling_demo_")
print(f"\ndemo directory created at: {DEMO_DIR}")

try:

    """
    ---------------------------------------------------------------------
    1. open() MODES: WHAT EACH ONE DOES, AND WHEN IT RAISES  ⭐⭐⭐
    ---------------------------------------------------------------------
    The second argument to open() is the MODE - it controls whether the
    file must already exist, whether it gets wiped, and whether you're
    working in text or binary. Getting this wrong is how pipelines
    silently destroy data (opening an existing extract with 'w' truncates
    it instantly, before you write a single byte) or crash unexpectedly
    (opening a file that doesn't exist with 'r').

        'r'   read (default)     - file MUST exist -> FileNotFoundError if not
        'w'   write               - CREATES if missing, TRUNCATES if it exists
        'a'   append              - CREATES if missing, writes go to the END
        'x'   exclusive create    - CREATES only if it does NOT already
                                     exist -> FileExistsError if it does
        'r+'  read + write        - file MUST exist, does NOT truncate
                                     -> FileNotFoundError if missing
        'rb' / 'wb'                - BINARY versions of 'r' / 'w': no text
                                     decoding/encoding, you get/give bytes
    ---------------------------------------------------------------------
    """

    print("\n--- open() Modes ---")

    missing_path = os.path.join(DEMO_DIR, "does_not_exist.txt")

    # 'r' on a file that doesn't exist -> FileNotFoundError
    try:
        with open(missing_path, "r") as f:
            f.read()
    except FileNotFoundError as e:
        print("'r' on a missing file raised FileNotFoundError:", e)

    # 'w' CREATES the file (fine here) but also TRUNCATES an existing one -
    # this is the classic "oops, I just wiped my output file" gotcha
    report_path = os.path.join(DEMO_DIR, "report.txt")
    with open(report_path, "w") as f:
        f.write("run 1: 100 rows processed\n")
    print("after first 'w': ", open(report_path).read().strip())

    with open(report_path, "w") as f:      # opening with 'w' AGAIN...
        f.write("run 2: 50 rows processed\n")
    print("after second 'w':", open(report_path).read().strip())
    print("-> run 1's line is GONE. 'w' truncates unconditionally, even")
    print("   if you only meant to overwrite part of the file.")

    # 'a' appends instead of truncating - safe for logs/audit trails
    with open(report_path, "a") as f:
        f.write("run 3: 75 rows processed\n")
    print("\nafter 'a':\n ", open(report_path).read().replace("\n", "\n  ").rstrip())

    # 'x' exclusive creation - guards against accidentally overwriting
    # something that already exists; this is the SAFE choice when you
    # want "create this output file, but fail loudly if it's already there"
    exclusive_path = os.path.join(DEMO_DIR, "exclusive.txt")
    with open(exclusive_path, "x") as f:
        f.write("created exactly once\n")
    print("\n'x' created a brand-new file with no problem.")

    try:
        with open(exclusive_path, "x") as f:   # same path again
            f.write("this should never get written\n")
    except FileExistsError as e:
        print("'x' on an EXISTING file raised FileExistsError:", e)

    # 'r+' - read AND write, but the file must already exist, and it is
    # NOT truncated on open (unlike 'w'). Useful for in-place edits, but
    # it has its own gotcha: writing SHORTER content than what was there
    # only overwrites the front of the file - any leftover old bytes past
    # the new write position are NOT automatically dropped.
    inplace_path = os.path.join(DEMO_DIR, "inplace.txt")
    with open(inplace_path, "w") as f:
        f.write("ORIGINAL")              # 8 characters
    with open(inplace_path, "r+") as f:
        current = f.read()
        f.seek(0)                        # rewind before writing in-place
        f.write(current.replace("ORIGINAL", "UPDATED"))    # only 7 characters
    print("\n'r+' writing shorter text leaves a stray leftover byte:")
    print(" ", repr(open(inplace_path).read()), "<- trailing 'L' survived from ORIGINAL")

    # The fix: call f.truncate() at the current position after writing, to
    # cut off anything left over from the file's previous, longer content
    with open(inplace_path, "w") as f:
        f.write("ORIGINAL")
    with open(inplace_path, "r+") as f:
        current = f.read()
        f.seek(0)
        f.write(current.replace("ORIGINAL", "UPDATED"))
        f.truncate()                     # drop anything past this point
    print("'r+' with f.truncate() after writing:", repr(open(inplace_path).read()))

    try:
        with open(missing_path, "r+") as f:
            pass
    except FileNotFoundError as e:
        print("'r+' on a missing file ALSO raised FileNotFoundError:", e)

    # 'rb' / 'wb' - binary mode: you get/give raw bytes, no text decoding
    binary_path = os.path.join(DEMO_DIR, "data.bin")
    with open(binary_path, "wb") as f:
        f.write(bytes([0, 1, 2, 255, 254, 253]))     # arbitrary raw bytes
    with open(binary_path, "rb") as f:
        raw = f.read()
    print("\nbinary round-trip:", raw, "-> type is", type(raw).__name__)
    print("(text mode would try to DECODE these bytes as characters and")
    print(" could raise UnicodeDecodeError on binary data that isn't")
    print(" valid text at all - always use 'rb'/'wb' for non-text files)")


    """
    ---------------------------------------------------------------------
    2. READING STRATEGIES: .read() vs .readline() vs .readlines() vs
       ITERATING THE FILE OBJECT DIRECTLY  ⭐⭐⭐
    ---------------------------------------------------------------------
    All four approaches produce the same DATA but have very different
    memory profiles:

        .read()       -> ENTIRE file contents as one string, all at once
        .readline()   -> ONE line at a time, including its trailing '\\n'
        .readlines()  -> ALL lines as a LIST, all loaded into memory at once
        for line in f -> iterates lazily, ONE line in memory at a time

    `.readlines()` and direct iteration look similar in what they
    produce, but `.readlines()` must build the COMPLETE list before your
    code sees a single line - for a multi-GB file, that is the difference
    between working fine and an out-of-memory crash. Iterating the file
    object directly hands you one line at a time using the file's
    internal buffer, so memory use stays flat regardless of file size.
    This is exactly the pattern behind "read a huge CSV/log file without
    loading it fully into memory," a very common DE interview question.
    ---------------------------------------------------------------------
    """

    print("\n--- Reading Strategies ---")

    lines_path = os.path.join(DEMO_DIR, "lines.txt")
    with open(lines_path, "w") as f:
        f.write("line one\nline two\nline three\n")

    with open(lines_path) as f:
        whole = f.read()
    print("f.read() -> one big string:", repr(whole))

    with open(lines_path) as f:
        first = f.readline()
        second = f.readline()
    print("\ntwo f.readline() calls:", repr(first), repr(second))

    with open(lines_path) as f:
        all_lines = f.readlines()
    print("\nf.readlines() -> a LIST, fully materialized:", all_lines)

    print("\ndirect iteration, one line at a time (memory-efficient):")
    with open(lines_path) as f:
        for line in f:                      # no .readlines() list ever built
            print(" ", line.strip())

    # Proving the memory-shape difference isn't just style: readlines()
    # returns a list you could len() or index into immediately; the file
    # object itself is a lazy ITERATOR - it has no length and no indexing.
    with open(lines_path) as f:
        print("\nfile object has __next__ but no len():", hasattr(f, "__next__"))
        try:
            len(f)
        except TypeError as e:
            print("len(file_object) raised TypeError:", e)
    print("-> readlines() trades memory for that convenience; direct")
    print("   iteration trades convenience for a flat memory footprint.")


    """
    ---------------------------------------------------------------------
    3. WRITING AND APPENDING  ⭐⭐
    ---------------------------------------------------------------------
    `.write(str)` writes exactly what you give it - no automatic newline,
    unlike `print()`. `.writelines(iterable_of_str)` writes each string
    back-to-back with NO separators added either - you must include your
    own '\\n' characters if you want actual lines.
    ---------------------------------------------------------------------
    """

    print("\n--- Writing and Appending ---")

    manual_newlines_path = os.path.join(DEMO_DIR, "manual.txt")
    with open(manual_newlines_path, "w") as f:
        f.write("no newline added automatically")
        f.write("so this runs right into the previous line")
    print("write() with no '\\n':", repr(open(manual_newlines_path).read()))

    writelines_path = os.path.join(DEMO_DIR, "writelines.txt")
    rows = ["alpha\n", "beta\n", "gamma\n"]      # note: '\n' included by US
    with open(writelines_path, "w") as f:
        f.writelines(rows)
    print("\nwritelines() with '\\n' included:")
    print(" ", open(writelines_path).read().replace("\n", "\n  ").rstrip())

    forgot_newlines_path = os.path.join(DEMO_DIR, "forgot_newlines.txt")
    with open(forgot_newlines_path, "w") as f:
        f.writelines(["alpha", "beta", "gamma"])   # forgot the '\n's
    print("\nwritelines() WITHOUT '\\n' -> everything runs together:")
    print(" ", repr(open(forgot_newlines_path).read()))


    """
    ---------------------------------------------------------------------
    4. THE ENCODING GOTCHA: encoding='utf-8' EXPLICIT vs PLATFORM
       DEFAULT  ⭐⭐⭐
    ---------------------------------------------------------------------
    In TEXT mode, open() must translate between bytes on disk and `str`
    in memory using some ENCODING. If you don't pass `encoding=`, Python
    uses `locale.getpreferredencoding()` - the OS's default, which is
    typically UTF-8 on Linux/macOS but can be something like cp1252 on
    Windows. A script that works perfectly on your Linux laptop can crash
    on a teammate's Windows machine, or on data containing non-ASCII
    characters (accents, currency symbols, non-Latin names) - purely
    because the encoding wasn't pinned down explicitly. The fix is
    always the same: pass `encoding="utf-8"` explicitly, every time.
    ---------------------------------------------------------------------
    """

    print("\n--- The Encoding Gotcha ---")

    text_with_unicode = "Cost: 42€, name: Zoë Müller, city: Sao Tome\n"
    utf8_path = os.path.join(DEMO_DIR, "utf8_data.txt")
    with open(utf8_path, "w", encoding="utf-8") as f:
        f.write(text_with_unicode)
    print("wrote non-ASCII text with explicit encoding='utf-8'")

    # Read it back correctly, with the SAME encoding it was written in
    with open(utf8_path, "r", encoding="utf-8") as f:
        print("read back correctly:", f.read().strip())

    # Now force a MISMATCHED encoding to trigger a real UnicodeDecodeError -
    # this is exactly what happens when the platform default doesn't match
    # how the bytes were actually written
    try:
        with open(utf8_path, "r", encoding="ascii") as f:
            f.read()
    except UnicodeDecodeError as e:
        print("\nreading UTF-8 bytes as 'ascii' raised UnicodeDecodeError:")
        print(" ", e)

    try:
        with open(utf8_path, "r", encoding="cp1252") as f:
            f.read()
    except UnicodeDecodeError as e:
        print("\nreading UTF-8 bytes as 'cp1252' ALSO raised UnicodeDecodeError:")
        print(" ", e)
    print("\nthe fix in both cases: read with the SAME explicit encoding")
    print("used to write the file - encoding='utf-8' on both ends, not")
    print("whatever the current platform happens to default to.")


    """
    ---------------------------------------------------------------------
    5. ALWAYS USE with  ⭐⭐⭐
    ---------------------------------------------------------------------
    A file object is a CONTEXT MANAGER (see the previous file in this
    repo, Context_Managers.py, for the full __enter__/__exit__ protocol
    this relies on) - `with open(...) as f:` guarantees `f.close()` runs
    even if an exception happens mid-read/write, exactly the same way a
    DB connection or lock should be released. Manual open()/close() pairs
    look fine until an exception lands between them, at which point the
    close() line is simply never reached and the handle leaks.
    ---------------------------------------------------------------------
    """

    print("\n--- Always Use `with` ---")

    leak_path = os.path.join(DEMO_DIR, "leak_demo.txt")

    # BUGGY: manual open/close - the exception skips f.close() entirely
    f = open(leak_path, "w")
    try:
        f.write("partial data...\n")
        raise ValueError("simulated failure mid-write")
    except ValueError as e:
        print("caught exception from manual open/close version:", e)
    print("file handle still open after the exception? ->", not f.closed)
    f.close()   # closing by hand here so we don't actually leak an OS handle

    # FIXED: `with` closes the file no matter what happens inside the block
    try:
        with open(leak_path, "w") as f:
            f.write("partial data again...\n")
            raise ValueError("same simulated failure")
    except ValueError as e:
        print("\ncaught exception from `with` version:", e)
    print("file handle still open after the exception? ->", not f.closed)
    print("-> `with` closed it automatically despite the exception; the")
    print("   manual version left it open until we remembered to do it.")


    """
    ---------------------------------------------------------------------
    6. pathlib.Path vs os / os.path FOR THE SAME OPERATIONS  ⭐⭐⭐
    ---------------------------------------------------------------------
    `os` / `os.path` represent paths as plain STRINGS and offer a
    function for each operation (os.path.join, os.path.exists, ...).
    `pathlib.Path` represents a path as an OBJECT with methods and
    operator overloading (the `/` operator joins paths), and is the
    modern, idiomatic choice in Python 3 - more readable, cross-platform
    by construction, and it unifies operations that os.path spreads
    across os, os.path, and glob. New code should reach for pathlib;
    os.path mainly shows up now in older codebases you'll need to read.
    ---------------------------------------------------------------------
    """

    print("\n--- pathlib.Path vs os / os.path ---")

    base_str = DEMO_DIR
    base_path = Path(DEMO_DIR)

    # Joining paths
    os_joined = os.path.join(base_str, "reports", "2026", "summary.csv")
    path_joined = base_path / "reports" / "2026" / "summary.csv"
    print("os.path.join(...)     ->", os_joined)
    print("Path(...) / ... / ... ->", path_joined, "(type:", type(path_joined).__name__ + ")")

    # Creating a directory (parents=True makes intermediate dirs too;
    # exist_ok=True means "don't raise if it's already there" - the
    # combination you almost always want for pipeline output dirs)
    os.makedirs(os.path.join(base_str, "reports", "2026"), exist_ok=True)
    path_joined.parent.mkdir(parents=True, exist_ok=True)
    print("\nboth created the nested 'reports/2026' directory without error")
    print("(mkdir(parents=True, exist_ok=True) is the pathlib equivalent")
    print(" of os.makedirs(path, exist_ok=True))")

    with open(path_joined, "w") as f:
        f.write("region,total\nEU,1000\nUS,2500\n")

    # Existence checks
    print("\nos.path.exists(str)   ->", os.path.exists(str(path_joined)))
    print("Path.exists()          ->", path_joined.exists())
    print("Path.is_file()         ->", path_joined.is_file())
    print("Path.is_dir()          ->", path_joined.parent.is_dir())

    # File size and extension
    os_size = os.path.getsize(str(path_joined))
    path_size = path_joined.stat().st_size
    print("\nos.path.getsize(str)  ->", os_size, "bytes")
    print("Path.stat().st_size    ->", path_size, "bytes")
    print("os.path.splitext(str)  ->", os.path.splitext(str(path_joined)))
    print("Path.suffix            ->", path_joined.suffix)
    print("Path.stem              ->", path_joined.stem, "(name without suffix)")
    print("Path.name              ->", path_joined.name, "(final path component)")

    # Listing a directory's immediate contents
    listing_dir = path_joined.parent
    os_listing = sorted(os.listdir(str(listing_dir)))
    path_listing = sorted(p.name for p in listing_dir.iterdir())
    print("\nos.listdir(str)       ->", os_listing)
    print("[p.name for p in Path.iterdir()] ->", path_listing)
    print("\npathlib wins on readability: one object, dot-methods, and it")
    print("works identically on Windows/Linux/macOS without manual '/' vs")
    print("'\\\\' handling that raw os.path string-joining can trip on.")


    """
    ---------------------------------------------------------------------
    7. WALKING DIRECTORY TREES: Path.iterdir(), Path.glob(),
       Path.rglob() - FINDING DATA FILES TO INGEST  ⭐⭐⭐
    ---------------------------------------------------------------------
    A realistic DE scenario: an "incoming" folder has date-partitioned
    subfolders, each holding a mix of file types, and the ingestion job
    needs every .csv anywhere underneath it.

        Path.iterdir()      -> immediate children ONLY, no pattern, no
                                recursion (files AND subdirectories)
        Path.glob(pattern)  -> immediate children matching a glob
                                pattern (e.g. "*.csv"), still NOT recursive
        Path.rglob(pattern) -> RECURSIVE glob - matches the pattern at
                                ANY depth below this directory; shorthand
                                for glob("**/" + pattern)
    ---------------------------------------------------------------------
    """

    print("\n--- Walking Directory Trees for Data Ingestion ---")

    incoming = Path(DEMO_DIR) / "incoming"
    (incoming / "2026-01-01").mkdir(parents=True, exist_ok=True)
    (incoming / "2026-01-02").mkdir(parents=True, exist_ok=True)

    # Scatter a realistic mix of files across the top level and both
    # date-partitioned subfolders
    (incoming / "README.txt").write_text("ingestion drop zone\n", encoding="utf-8")
    (incoming / "2026-01-01" / "orders.csv").write_text("id,total\n1,9.99\n", encoding="utf-8")
    (incoming / "2026-01-01" / "orders.json").write_text('{"id": 1}\n', encoding="utf-8")
    (incoming / "2026-01-02" / "customers.csv").write_text("id,name\n1,Ana\n", encoding="utf-8")
    (incoming / "2026-01-02" / "_SUCCESS").write_text("", encoding="utf-8")

    print("iterdir() - immediate children only (files AND dirs):")
    for p in sorted(incoming.iterdir()):
        kind = "dir" if p.is_dir() else "file"
        print(f"  [{kind}] {p.name}")

    print("\nglob('*.csv') - top level only, misses the partitioned files:")
    print(" ", sorted(p.name for p in incoming.glob("*.csv")))

    print("\nrglob('*.csv') - recursive, finds .csv files at ANY depth:")
    csv_files = sorted(incoming.rglob("*.csv"))
    for p in csv_files:
        print("  ", p.relative_to(incoming))
    print(f"\n-> found {len(csv_files)} data file(s) to ingest, correctly")
    print("   ignoring README.txt, the .json file, and the _SUCCESS marker.")

    # The equivalent with the older os module needs manual recursion via
    # os.walk() plus filename filtering - correct, but noticeably more code
    os_found = []
    for dirpath, _dirnames, filenames in os.walk(str(incoming)):
        for name in filenames:
            if name.endswith(".csv"):
                os_found.append(os.path.relpath(os.path.join(dirpath, name), str(incoming)))
    print("\nos.walk() equivalent found the same files:", sorted(os_found))
    print("(same result, but rglob('*.csv') says it in four characters)")

finally:
    shutil.rmtree(DEMO_DIR, ignore_errors=True)
    print(f"\ncleaned up demo directory: {DEMO_DIR}")


"""
=====================================================================
QUICK REFERENCE
=====================================================================
open() modes:
    'r'   -> read, must exist          -> FileNotFoundError if missing
    'w'   -> write, creates/TRUNCATES  -> never raises for a missing file
    'a'   -> append, creates if missing, writes go to the end
    'x'   -> exclusive create          -> FileExistsError if it EXISTS
    'r+'  -> read+write, must exist, no truncation -> FileNotFoundError
              (writing SHORTER content leaves stray old bytes -
               call f.truncate() after writing to drop them)
    'rb'/'wb' -> binary versions of 'r'/'w' (bytes, not str)

Reading:
    f.read()      -> whole file as one string      (loads everything)
    f.readline()  -> one line at a time             (manual, rarely used)
    f.readlines() -> ALL lines as a list             (loads everything)
    for line in f -> lazy, one line in memory at a time (memory-efficient)

Writing:
    f.write(s)          -> no automatic newline
    f.writelines(list)  -> no separators added - include '\\n' yourself

Encoding:
    always pass encoding="utf-8" explicitly, both reading and writing -
    the platform default (locale.getpreferredencoding()) is NOT
    guaranteed to match and can raise UnicodeDecodeError

with open(...) as f:  -> ALWAYS use this; guarantees close() on
                          exception, same __enter__/__exit__ protocol
                          as any other context manager

pathlib vs os/os.path (pathlib is the modern choice):
    Path(a) / b / c                -> os.path.join(a, b, c)
    path.exists()                  -> os.path.exists(str(path))
    path.is_file() / .is_dir()     -> os.path.isfile() / os.path.isdir()
    path.stat().st_size            -> os.path.getsize(str(path))
    path.suffix / path.stem        -> os.path.splitext(str(path))
    path.mkdir(parents=True,
               exist_ok=True)      -> os.makedirs(path, exist_ok=True)
    [p.name for p in p.iterdir()]  -> os.listdir(str(p))

Directory walking:
    Path.iterdir()       -> immediate children, no pattern, no recursion
    Path.glob(pattern)   -> immediate children matching a glob pattern
    Path.rglob(pattern)  -> recursive glob, ANY depth (== glob("**/"+p))
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - FILE HANDLING BASICS
=====================================================================

1. What is the difference between opening a file with 'w' versus 'a'?
   What happens to existing content in each case?

2. Which open() modes raise FileNotFoundError if the target file does
   not exist? Which ones will happily create it instead?

3. What does mode 'x' do, and what exception does it raise if the file
   already exists? When would you deliberately choose 'x' over 'w'?

4. What is the practical difference between 'r+' and 'w' when the file
   already has content in it? What happens if you use 'r+' to write
   content SHORTER than what was already in the file, and how do you
   fix it?

5. Why would you use 'rb'/'wb' instead of 'r'/'w' for a file like an
   image or a serialized binary blob? What goes wrong if you don't?

6. Compare f.read(), f.readlines(), and iterating over the file object
   directly (`for line in f`) - which one(s) load the entire file into
   memory at once, and why does that matter for a 10GB log file?

7. Why is `.readlines()` less memory-efficient than direct iteration
   even though both eventually give you every line in the file?

8. What is the difference between f.write() and print() with respect
   to newlines? What about f.writelines() - does it add '\\n' for you?

9. Why should you always pass `encoding="utf-8"` explicitly to open()
   instead of relying on the default? What real-world bug does this
   prevent, and what exception can you get if the encodings actually
   used to write and read a file don't match?

10. Why is `with open(...) as f:` preferred over manually calling
    `f.close()`? What specifically goes wrong with the manual version
    if an exception is raised between open() and close()?

11. What protocol does the file object implement to work with `with`
    (tie this back to __enter__/__exit__ from context managers)?

12. What are the main advantages of `pathlib.Path` over the older
    `os` / `os.path` module for the same operations? Give at least
    three concrete examples of one line of pathlib code replacing an
    os.path equivalent.

13. What does `Path("a") / "b" / "c"` actually do under the hood? Why
    does this work when `/` is normally the division operator?

14. What is the difference between Path.iterdir(), Path.glob(), and
    Path.rglob()? If you needed every .csv file anywhere under a
    folder of date-partitioned subdirectories, which one would you
    use and why?

15. How would os.walk() achieve the same result as
    `Path(folder).rglob("*.csv")`? Why is the pathlib version usually
    preferred in new code?

16. What does `mkdir(parents=True, exist_ok=True)` do, and what
    happens if you omit `exist_ok=True` and the directory already
    exists?
=====================================================================
"""
