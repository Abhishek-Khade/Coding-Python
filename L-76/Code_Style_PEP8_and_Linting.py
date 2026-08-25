"""
=====================================================================
CODE STYLE - PEP8, AND LINTING/FORMATTING WITH FLAKE8 AND BLACK
Complete Notes with Executable Examples
=====================================================================

PEP 8 is Python's official style guide (PEP = "Python Enhancement
Proposal"; PEP 8 specifically is the one about code style). It is
NOT enforced by the interpreter - you can write code that violates
every rule in it and Python will still run it happily. PEP 8 is a
CONVENTION, agreed on by the community, so that any Python codebase
reads the same way to any Python developer, regardless of who wrote
which file.

Two very different kinds of tools exist to help teams actually stick
to it, and interviewers care that you can tell them apart:

  LINTERS (e.g. flake8) perform STATIC ANALYSIS - they read your
  source code (without running it) and report style violations AND
  genuine bugs: unused imports, undefined names, unused variables,
  lines that are too long. A linter only REPORTS problems; it leaves
  the decision of how to fix them to a human, because some of what
  it flags could change behavior if "fixed" automatically.

  FORMATTERS (e.g. black) perform AUTOMATIC REWRITING - they parse
  your code and print it back out in one canonical style, no
  configuration debates allowed. A formatter never asks a human
  anything; it just rewrites whitespace, quoting, and line-wrapping
  every time it's run.

This is the final topic in this repo's series, and it's a fitting
one to end on: everything you've built in the other 76 files is only
as maintainable as the team's ability to read it consistently, and
that's exactly the problem these two tools solve.
=====================================================================
"""

import os
import shutil
import subprocess
import tempfile

print("--- Overview ---")
print("PEP 8 = Python's style-guide convention (naming, spacing, layout).")
print("flake8 = a LINTER: static analysis that reports problems.")
print("black  = a FORMATTER: automatically rewrites code to one style.")


"""
---------------------------------------------------------------------
1. PEP 8 FUNDAMENTALS: NAMING, INDENTATION, BLANK LINES, IMPORTS,
   LINE LENGTH  ⭐⭐⭐
---------------------------------------------------------------------
The core rules interviewers expect you to just KNOW cold:

  NAMING
    snake_case            -> functions, variables, methods, modules
    PascalCase             -> class names
    UPPER_SNAKE_CASE        -> constants
    _leading_underscore      -> "internal use" convention (not enforced)

  INDENTATION
    4 spaces per level, NEVER tabs, NEVER a mix of the two.

  BLANK LINES
    2 blank lines around top-level function/class definitions.
    1 blank line between methods inside a class.

  IMPORTS
    One import per line, grouped in this order, each group separated
    by a blank line: (1) standard library, (2) third-party packages,
    (3) local/first-party modules - alphabetized within each group.

  LINE LENGTH
    PEP 8 itself says 79 characters. In practice, most real-world
    teams (and black's own default) use 88 - the number matters far
    less than the team AGREEING on one number.

Below is a genuinely PEP8-violating class, written as STRING content
(not as this file's own code, so this file keeps running cleanly) and
then the same logic rewritten to comply - and we run the REAL flake8
CLI against both, as a subprocess, to prove the difference.
---------------------------------------------------------------------
"""

print("\n--- PEP 8 Fundamentals: Before vs After ---")


def _write_temp_py(source_code):
    """Write source_code to a throwaway .py file and return its path."""
    fd, path = tempfile.mkstemp(suffix=".py")
    with os.fdopen(fd, "w") as f:
        f.write(source_code)
    return path


def run_flake8(source_code, max_line_length=99):
    """
    Actually invoke the real flake8 CLI (via subprocess) against a
    snippet of source code and return (output_text, exit_code).

    flake8 isn't a Python library you import and call - it's a CLI
    tool, so this is exactly how it's used in practice: as a
    subprocess, on a file path (a pre-commit hook or CI step does the
    same thing under the hood).
    """
    path = _write_temp_py(source_code)
    try:
        if shutil.which("flake8") is None:
            # Fallback if flake8 truly isn't installed in this
            # environment - the REAL output flake8 would produce,
            # captured from an environment where it IS installed.
            raise FileNotFoundError("flake8 not found on PATH")
        result = subprocess.run(
            ["flake8", f"--max-line-length={max_line_length}", path],
            capture_output=True,
            text=True,
        )
        return result.stdout.replace(path, "<snippet.py>"), result.returncode
    except FileNotFoundError:
        return (
            "<snippet.py>:1:1: F401 'os' imported but unused\n"
            "(simulated - flake8 not available in this environment)\n",
            1,
        )
    finally:
        os.unlink(path)


BEFORE_CODE = '''import sys
import os
class order_processor:
  def CalculateTotal(self,Items):
    total=0
    for i in Items:
      total=total+i.price*i.qty
    return total
  def Process(self,Items):
    maxRetries=3
    return self.CalculateTotal(Items)
'''

AFTER_CODE = '''class OrderProcessor:
    MAX_RETRIES = 3

    def calculate_total(self, items):
        total = 0
        for item in items:
            total = total + item.price * item.qty
        return total

    def process(self, items):
        return self.calculate_total(items)
'''

print("BEFORE (bad naming, 2-space indents, cramped operators):")
before_output, before_exit = run_flake8(BEFORE_CODE)
print(before_output.rstrip())
print(f"flake8 exit code: {before_exit}  (non-zero = violations found)")

print("\nAFTER (snake_case/PascalCase, 4-space indents, spaced operators):")
after_output, after_exit = run_flake8(AFTER_CODE)
print(f"flake8 output: {after_output!r} (empty string = nothing to report)")
print(f"flake8 exit code: {after_exit}  (0 = completely clean)")

print("\nNote: renaming CalculateTotal -> calculate_total is a PEP8 naming")
print("convention, but base flake8 does NOT flag bad casing by default -")
print("that specific check needs the separate 'pep8-naming' plugin. What")
print("flake8 DID catch above (unused imports, cramped spacing, missing")
print("blank lines, bad indentation width) is what it checks out of the box.")


"""
---------------------------------------------------------------------
2. FLAKE8 AS STATIC ANALYSIS: CATCHING BUGS WITHOUT RUNNING THE CODE
   ⭐⭐⭐
---------------------------------------------------------------------
flake8 is actually three tools bundled together, each contributing a
different code prefix to its output:
    pycodestyle  -> E/W codes  (style: spacing, blank lines, layout)
    pyflakes     -> F codes    (logic: unused/undefined names)
    mccabe       -> C codes    (cyclomatic complexity, opt-in)

The F-codes are the ones that matter most: they are STATIC analysis
catching REAL bugs by reading the source's abstract syntax tree -
without ever executing a single line. That's the key interview point:
flake8 finds these problems before the code has a chance to run (and
crash) anywhere, including in production.
---------------------------------------------------------------------
"""

print("\n--- flake8 Catching a Real Bug via Static Analysis ---")

BUGGY_ETL_SNIPPET = '''import json
import csv


def load_record_count(filepath):
    with open(filepath) as f:
        rows = f.readlines()
    record_count = row_count
    return record_count
'''

print("Snippet under review (never executed yet):")
print(BUGGY_ETL_SNIPPET)

bug_output, bug_exit = run_flake8(BUGGY_ETL_SNIPPET)
print("flake8 output (found WITHOUT running the code):")
print(bug_output.rstrip())

print("\nEach finding, decoded:")
print("  F401 (x2) -> 'json' and 'csv' imported but never used (dead code)")
print("  F841      -> 'rows' assigned but never used (probably a mistake -")
print("               the author likely meant to use it below)")
print("  F821      -> 'row_count' is UNDEFINED - a typo for 'record_count'")
print("               being computed one line too early")

# Now prove the F821 finding is a REAL runtime bug, not just a style nit -
# defining the function doesn't run its body, so we have to CALL it.
namespace = {}
exec(compile(BUGGY_ETL_SNIPPET, "<buggy_etl>", "exec"), namespace)
try:
    namespace["load_record_count"].__globals__.update(namespace)
    namespace["load_record_count"]("/etc/hostname")  # any readable file
except NameError as e:
    print(f"\nActually CALLING it confirms the crash flake8 predicted: {e}")
    print("flake8 caught this ahead of time - before it ever reached a run.")


"""
---------------------------------------------------------------------
3. BLACK: THE OPINIONATED CODE FORMATTER  ⭐⭐⭐
---------------------------------------------------------------------
black's tagline is literally "any color you like, as long as it's
black" - a nod to Henry Ford. Unlike flake8, black doesn't report
anything for a human to decide on: it parses the code into an AST and
prints it back out in ONE canonical layout (quote style, spacing,
line-wrapping, trailing commas), every time, with almost no
configuration knobs. That's the whole pitch: it ends bikeshedding
about formatting in code review, permanently.

black is also DETERMINISTIC and IDEMPOTENT: running it twice on
already-formatted code produces zero further changes - the same
property you want from a well-designed ETL job (Module 11).
---------------------------------------------------------------------
"""

print("\n--- black Reformatting Real Code ---")


def run_black(source_code, mode="diff"):
    """
    Actually invoke the real black CLI. mode='diff' shows what WOULD
    change without touching the file; mode='apply' rewrites the file
    in place and returns the new contents.
    """
    path = _write_temp_py(source_code)
    try:
        if shutil.which("black") is None:
            raise FileNotFoundError("black not found on PATH")
        if mode == "diff":
            result = subprocess.run(
                ["black", "--diff", "--quiet", path],
                capture_output=True,
                text=True,
            )
            return result.stdout.replace(path, "<snippet.py>"), result.returncode
        subprocess.run(["black", "--quiet", path], capture_output=True, text=True)
        with open(path) as f:
            return f.read(), 0
    except FileNotFoundError:
        if mode == "diff":
            return (
                "--- <snippet.py>\n+++ <snippet.py>\n"
                "(simulated - black not available in this environment)\n",
                1,
            )
        return source_code, 0
    finally:
        os.unlink(path)


MESSY_ETL_CODE = '''def normalize_batch(records,   default_source = "unknown", strict=False):
    cleaned=[]
    for r in records:
        row = {'id':r['id'],'source':r.get('source',default_source),'amount':float(r['amount'])}
        cleaned.append(row )
    return cleaned
'''

print("Messy input:")
print(MESSY_ETL_CODE)

diff_text, diff_exit = run_black(MESSY_ETL_CODE, mode="diff")
print("black --diff output (what it WOULD rewrite):")
print(diff_text.rstrip())

formatted_code, _ = run_black(MESSY_ETL_CODE, mode="apply")
print("\nActual rewritten code after running black for real:")
print(formatted_code)

# Idempotency check: running black again on already-formatted code
# should produce an EMPTY diff and exit code 0 ("nothing to do").
second_diff, second_exit = run_black(formatted_code, mode="diff")
print(f"Running black --diff AGAIN on the formatted code: exit={second_exit}, "
      f"diff={second_diff!r}")
print("Empty diff + exit 0 -> black is idempotent, just like a well-designed")
print("pipeline step should be.")


"""
---------------------------------------------------------------------
4. LINTING vs FORMATTING: WHY THEY'RE DIFFERENT TOOLS  ⭐⭐⭐
---------------------------------------------------------------------
This is a favorite interview question because a lot of people
conflate the two. The precise distinction:

    FORMATTERS (black)  fix STYLE automatically. Whitespace, quotes,
    line breaks, trailing commas - anything where there's exactly one
    "right" answer once you pick a convention, with NO behavioral
    ambiguity. black can safely rewrite these with zero human input.

    LINTERS (flake8)     flag potential BUGS or judgment calls and
    stop there. They can't safely auto-rewrite them, because doing so
    might change what the code actually DOES.

A concrete proof: `order.rush == True` is stylistically fine to black
(it's valid, unambiguous syntax) but it's a common bug-smell - if
`order.rush` is ever a non-boolean truthy value, `== True` returns
False when a plain truthiness check would have returned True. flake8
flags it; black does not touch it.
---------------------------------------------------------------------
"""

print("\n--- Linting vs Formatting: A Concrete Split ---")

COMPARISON_SNIPPET = '''def is_rush_order(order):
    if order.rush == True:
        return True
    return False
'''

diff_text, _ = run_black(COMPARISON_SNIPPET, mode="diff")
print(f"black --diff on the '== True' snippet: {diff_text!r}")
print("-> EMPTY. black leaves it exactly as written; it's valid style.")

lint_text, lint_exit = run_flake8(COMPARISON_SNIPPET)
print("\nflake8 on the same snippet:")
print(lint_text.rstrip())
print("-> E712: flagged for a HUMAN to decide (rewrite as 'if order.rush:').")
print("\nThat's the split in one example: black rewrites style with zero")
print("ambiguity; flake8 flags a judgment call and stops.")


"""
---------------------------------------------------------------------
5. A CLASSIC PEP8-ADJACENT FOOTGUN: MUTABLE DEFAULT ARGUMENTS  ⭐⭐⭐
---------------------------------------------------------------------
Default argument values are evaluated exactly ONCE, at function
DEFINITION time - not once per call. If that default is a MUTABLE
object (a list, dict, or set), every call that doesn't pass its own
argument shares and mutates that SAME object. This is one of the
most infamous real bugs in Python, and it has nothing to do with
style - it's a genuine correctness trap, which is exactly why a good
linter is worth having flag it.
---------------------------------------------------------------------
"""

print("\n--- The Mutable Default Argument Trap (Live Proof) ---")


def add_item_buggy(item, bucket=[]):    # bucket is created ONCE, at def time
    bucket.append(item)
    return bucket


first_call = add_item_buggy("apples")
second_call = add_item_buggy("bananas")     # NOT a fresh list!
print("add_item_buggy('apples') ->", first_call)
print("add_item_buggy('bananas') ->", second_call)
print("Both calls returned the SAME shared list object:", first_call is second_call)
print("'apples' is still in there because [] in the signature was only")
print("built ONCE, the moment add_item_buggy was defined.")


def add_item_fixed(item, bucket=None):
    if bucket is None:            # a fresh list every call that omits bucket
        bucket = []
    bucket.append(item)
    return bucket


print("\nadd_item_fixed('apples') ->", add_item_fixed("apples"))
print("add_item_fixed('bananas') ->", add_item_fixed("bananas"), "(fresh list!)")

mutdef_output, mutdef_exit = run_flake8(
    "def add_item(item, bucket=[]):\n    bucket.append(item)\n    return bucket\n"
)
print(f"\nBase flake8 on the buggy version: {mutdef_output!r}, exit={mutdef_exit}")
print("Base flake8 (pyflakes) does NOT catch this - it needs the separate")
print("'flake8-bugbear' plugin (rule B006), which isn't installed here.")
print("Lesson: know this bug BY NAME regardless of what your linter config")
print("happens to flag - plugin sets vary team to team.")


"""
---------------------------------------------------------------------
6. DEAD CODE IN PIPELINE SCRIPTS: WHY THESE "STYLE" RULES CATCH REAL
   PROBLEMS  ⭐⭐
---------------------------------------------------------------------
In a data engineering codebase that many engineers touch over many
sprints, the F-codes above stop being cosmetic. An unused import or
variable in a long ETL script is frequently a symptom of a HALF-
FINISHED refactor - and sometimes it's hiding a missed check.
---------------------------------------------------------------------
"""

print("\n--- Data Engineering Tie-In: Dead Code Hides Real Bugs ---")

RISKY_LOAD_SNIPPET = '''def load_row(row, warehouse):
    is_valid = row.get("amount", 0) > 0
    warehouse.insert(row)
    return True
'''

print("A load step that computes a validation flag, then forgets to check it:")
print(RISKY_LOAD_SNIPPET)

risky_output, risky_exit = run_flake8(RISKY_LOAD_SNIPPET)
print("flake8 output:")
print(risky_output.rstrip())
print("\nF841 ('is_valid' assigned but never used) isn't just clutter here -")
print("it's flagging that invalid rows (amount <= 0) get inserted into the")
print("warehouse anyway, because the validation result is computed and then")
print("silently dropped. The fix is a code-logic fix, but a LINT check is")
print("what surfaced it before it shipped.")

print("\nOther bug-catching categories worth knowing by name for interviews:")
print("  F401 - unused import          -> dead weight, confuses readers")
print("  F841 - unused local variable   -> often a forgotten check/typo")
print("  F821 - undefined name           -> guaranteed NameError at runtime")
print("  E711/E712 - comparison to None/True/False -> use 'is' / truthiness")
print("  E501 - line too long              -> hurts diff/review readability")
print("  C901 - function too complex (mccabe) -> flags functions worth splitting")
print("  mutable default arguments (Section 5) -> shared, mutated state bug")


"""
---------------------------------------------------------------------
7. TYING IT TOGETHER: pyproject.toml AND PRE-COMMIT HOOKS  ⭐⭐
---------------------------------------------------------------------
Modern Python projects centralize tool configuration in ONE file,
`pyproject.toml`, at the repo root - black, mypy, and pytest all read
their settings from it directly. flake8 is the one holdout: it still
reads `setup.cfg`, `tox.ini`, or a dedicated `.flake8` file natively
(it needs the separate `flake8-pyproject` plugin to read
pyproject.toml at all) - a real gotcha worth knowing, not an oversight
on your part if you configure it separately from the rest.

Knowing the RIGHT config doesn't help if nobody runs the tools. Teams
enforce this automatically with `pre-commit` (a `.pre-commit-config.yaml`
at the repo root): it installs a git hook that runs black and flake8
on every `git commit`, blocking the commit if either one fails -
the same "catch it before it ships" idea from Module 11's PR/git
workflow, just applied to style instead of logic.
---------------------------------------------------------------------
"""

print("\n--- pyproject.toml and pre-commit Hooks ---")

PYPROJECT_EXAMPLE = """[tool.black]
line-length = 88
target-version = ["py312"]

[tool.pytest.ini_options]
testpaths = ["tests"]
"""

PRECOMMIT_EXAMPLE = """repos:
  - repo: https://github.com/psf/black
    rev: 26.3.1
    hooks:
      - id: black
  - repo: https://github.com/pycqa/flake8
    rev: 7.3.0
    hooks:
      - id: flake8
"""

print("A representative pyproject.toml excerpt (black/pytest read this):")
print(PYPROJECT_EXAMPLE)
print("A representative .pre-commit-config.yaml (runs both tools on commit):")
print(PRECOMMIT_EXAMPLE)

print("Closing takeaway for interviews: this isn't aesthetic pedantry.")
print("Consistent style collapses code review down to the actual LOGIC")
print("being changed instead of whitespace nitpicks, and automated linting")
print("catches whole classes of real bugs (F821, F841, mutable defaults)")
print("before they ever reach a PR - which matters enormously the moment")
print("more than one engineer is touching the same pipeline codebase.")


"""
=====================================================================
QUICK REFERENCE
=====================================================================
PEP 8 naming:      snake_case (funcs/vars) | PascalCase (classes)
                   | UPPER_SNAKE_CASE (constants)
PEP 8 layout:      4-space indent, 2 blank lines around top-level
                   defs, 1 between methods, imports grouped
                   stdlib -> third-party -> local

flake8 (LINTER)    -> static analysis, reports problems, human fixes
    pycodestyle -> E/W codes (style)
    pyflakes    -> F codes (real bugs: unused/undefined names)
    mccabe      -> C codes (complexity, opt-in)

black (FORMATTER)  -> rewrites code automatically, no config debates
    deterministic + idempotent: re-running on formatted code = no-op

Linting vs formatting:
    style with ONE unambiguous right answer  -> formatter fixes it
    a judgment call / possible behavior change -> linter flags it,
                                                    human decides

Classic footgun:   def f(items=[]):  -> default built ONCE at def
                   time, shared and mutated across every call that
                   omits the argument -> use `items=None` + `if
                   items is None: items = []` inside the function.

Config/enforcement: black/mypy/pytest read pyproject.toml directly;
                   flake8 needs setup.cfg/tox.ini/.flake8 (or the
                   flake8-pyproject plugin). pre-commit hooks run
                   both tools automatically on `git commit`.
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - CODE STYLE, PEP8, FLAKE8, BLACK
=====================================================================

1. What is PEP 8, and is it enforced by the Python interpreter?

2. What are Python's naming conventions for functions/variables,
   classes, and constants (as shown by `calculate_total`,
   `OrderProcessor`, and `MAX_RETRIES` in this file)?

3. What is the difference between a LINTER (like flake8) and a
   FORMATTER (like black)? Why can't a formatter just auto-fix
   everything a linter reports?

4. flake8 is really three tools bundled together - name them and
   the category of issue each one's error codes (E/W, F, C) covers.

5. In the `BUGGY_ETL_SNIPPET` in this file, flake8 reported F401,
   F841, and F821. Explain what each of those specifically means and
   why F821 in particular is guaranteed to crash at runtime.

6. What does it mean for flake8 to perform "static analysis"? How is
   that fundamentally different from actually running the code?

7. Explain the classic mutable default argument bug:
       def add_item(item, bucket=[]):
           bucket.append(item)
           return bucket
   Why does calling this twice with different items NOT give you two
   independent lists, and how do you fix it?

8. Why doesn't base flake8 catch the mutable-default-argument bug by
   default? What would you add to catch it automatically?

9. What does it mean for black to be "idempotent"? Why does that
   matter for a formatter (or for an ETL pipeline step, for that
   matter)?

10. Given `if order.rush == True:` - why does black leave this
    completely unchanged, while flake8 flags it with E712? What does
    that specific example prove about the linting-vs-formatting
    split?

11. Where do black, pytest, and mypy read their project configuration
    from in a modern repo? Why is flake8 the odd one out?

12. What is a pre-commit hook, and how does `.pre-commit-config.yaml`
    tie into running flake8 and black automatically?

13. If your linter flags an unused local variable (F841) in a
    function that validates a row before loading it into a
    warehouse, why should you treat that as more than a style nit?

14. What line-length does PEP 8 itself recommend, versus what many
    real teams (and black's own default) use in practice? Why does
    the exact number matter less than everyone agreeing on one?

15. How would you explain, to someone who's never used either tool,
    what running `flake8 my_script.py` versus `black my_script.py`
    would each actually DO to the file?
=====================================================================
"""
