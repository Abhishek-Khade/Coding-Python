"""
=====================================================================
CONFIGURATION MANAGEMENT - .env, configparser, and Avoiding
Hardcoded Secrets - Complete Notes with Executable Examples
=====================================================================

Every real pipeline needs to know THINGS that differ by environment:
which database to write to, which API key to authenticate with, how
big a batch to pull, whether to run in dry-run mode. CONFIGURATION
MANAGEMENT is simply the discipline of keeping those values OUT of
your source code and feeding them in from somewhere else at runtime.

Why this matters enough to be its own interview topic: source code is
meant to be the SAME in dev, staging, and prod - only the CONFIG
should change between them. If a connection string or an API key is
hardcoded, "deploying to a new environment" means editing and
re-shipping code, which is slow, error-prone, and impossible to do
safely under time pressure (e.g. an incident at 2am). Worse, if that
hardcoded value is a SECRET, it is now sitting in your git history
forever - deleting the line in a later commit does NOT remove it from
history, anyone with clone access can recover it, and the only real
fix once a secret is committed is to treat it as compromised: rotate
the credential immediately and separately scrub history (tools like
`git filter-repo` or BFG) if the repo is or was ever shared.

This file covers, in increasing order of structure: reading plain
environment variables, failing loudly when a REQUIRED one is missing,
loading `.env` files with `python-dotenv`, structured `.ini` config
via `configparser`, and layering all of these sources together with
a clear precedence order - the pattern real ETL frameworks use.
=====================================================================
"""

import os
import sys
import configparser
import tempfile
import argparse
import contextlib

print("--- Overview ---")
print("Configuration management = keeping environment-specific values")
print("(and especially SECRETS) out of source code, so the same code")
print("runs unchanged across dev/staging/prod and secrets never end")
print("up committed to git history.")


@contextlib.contextmanager
def temporary_env_vars(**pairs):
    """Set env vars for the duration of a `with` block, then restore
    exactly what was there before - even if the block raises. This is
    how every demo below touches os.environ without leaking state into
    the real process environment beyond this script's own run."""
    originals = {name: os.environ.get(name) for name in pairs}
    os.environ.update({name: str(value) for name, value in pairs.items()})
    try:
        yield
    finally:
        for name, original in originals.items():
            if original is None:
                os.environ.pop(name, None)   # wasn't set before - remove it
            else:
                os.environ[name] = original  # restore the prior value


"""
---------------------------------------------------------------------
1. THE PROBLEM WITH HARDCODED CONFIG AND SECRETS  ⭐⭐⭐
---------------------------------------------------------------------
Two SEPARATE problems, often confused: hardcoding ANY config value
(even a non-secret like a hostname) hurts portability across
environments; hardcoding a SECRET is that same problem PLUS a genuine
security incident risk, because source code ends up in git history,
CI logs, code review threads, and every developer's laptop clone.
---------------------------------------------------------------------
"""

print("\n--- The Problem With Hardcoded Config and Secrets ---")

# !!! DO NOT DO THIS - hardcoded secret directly in source code !!!
# These are OBVIOUSLY-FAKE placeholder strings for this demo only -
# a real key/password must never appear in source, ever.
API_KEY = "sk_fake_demo_12345"       # <- anyone who ever clones this repo has it
DB_PASSWORD = "REPLACE_ME"           # <- same problem, different flavor


def bad_connect_to_warehouse():
    """The hardcoded version: works, but is frozen to ONE environment
    and leaks a real credential into version control the moment this
    file is committed."""
    return f"connecting with hardcoded key ending in ...{API_KEY[-4:]}"


print(bad_connect_to_warehouse())
print("\nWhy this is bad, concretely:")
print("  1. Can't vary per environment - dev/staging/prod need DIFFERENT")
print("     keys and hosts, so this forces editing (and redeploying) code")
print("     just to point at a different database or API.")
print("  2. Secrets committed to git history are extremely hard to fully")
print("     remove - `git rm` + a new commit does NOT erase it from")
print("     earlier commits. Every existing clone still has it. The only")
print("     safe response once this happens is to ROTATE the credential")
print("     immediately, then separately deal with scrubbing history.")
print("\nThe rest of this file replaces both of these hardcoded lines")
print("with values sourced from the environment instead.")


"""
---------------------------------------------------------------------
2. ENVIRONMENT VARIABLES: os.environ, os.getenv(), AND FAILING LOUDLY
   WHEN A REQUIRED ONE IS MISSING  ⭐⭐⭐
---------------------------------------------------------------------
`os.environ` is a dict-like mapping of the process's environment
variables. `os.environ["X"]` raises KeyError if "X" is unset;
`os.getenv("X", default)` is the safer read for OPTIONAL settings,
since it returns a default instead of raising. But for a REQUIRED
setting (a DB password, an API key), silently falling back to `None`
is worse than crashing - a pipeline that "succeeds" while quietly
writing to `None` or authenticating with no key fails LATER, in a
more confusing way. The idiomatic fix: check explicitly and raise a
clear, actionable error immediately.
---------------------------------------------------------------------
"""

print("\n--- Environment Variables and Failing Loudly ---")

# OPTIONAL setting with a sensible default - fine to use getenv() directly
log_level = os.getenv("PIPELINE_LOG_LEVEL", "INFO")
print("log_level (not set, falls back to default):", log_level)


def require_env(name: str) -> str:
    """Read a REQUIRED environment variable, or raise a clear error
    instead of silently returning None and letting the failure surface
    somewhere confusing downstream."""
    value = os.environ.get(name)
    if value is None:
        raise RuntimeError(
            f"Required environment variable '{name}' is not set. "
            f"Set it before running this pipeline - refusing to "
            f"continue with a silent None."
        )
    return value


# Case 1: the required variable IS present
with temporary_env_vars(PIPELINE_ENV="staging"):
    print("PIPELINE_ENV is set:", require_env("PIPELINE_ENV"))

# Case 2: the required variable is MISSING - fails loudly, not silently
os.environ.pop("PIPELINE_REGION", None)   # make sure it's genuinely unset
try:
    require_env("PIPELINE_REGION")
except RuntimeError as e:
    print("Error (missing required var), caught and reported:", e)

print("\nCompare this to `region = os.getenv('PIPELINE_REGION')` with no")
print("check: `region` would silently be `None`, and the bug wouldn't")
print("surface until something tries to USE it, far from the real cause.")


"""
---------------------------------------------------------------------
3. .env FILES AND python-dotenv  ⭐⭐⭐
---------------------------------------------------------------------
Setting real env vars by hand (`export X=y`) for every local dev
session is tedious. The convention is a `.env` file - plain
`KEY=VALUE` lines, one per setting - loaded into `os.environ` at
startup by the `python-dotenv` package's `load_dotenv()`. The `.env`
file itself must NEVER be committed (see section 6) - it exists only
on each developer's machine / each deployment target, holding THAT
environment's actual values.
---------------------------------------------------------------------
"""

print("\n--- .env Files and python-dotenv ---")

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

# A tiny .env file, the same format load_dotenv() expects: KEY=VALUE,
# blank lines and '#' comments ignored, quotes around values stripped.
env_file_contents = (
    "# staging database settings\n"
    "STAGING_DB_HOST=staging-db.internal.pattern.com\n"
    "STAGING_DB_PORT=5432\n"
    "STAGING_API_KEY=\"sk_fake_demo_12345\"\n"
)

env_fd, env_path = tempfile.mkstemp(suffix=".env")
try:
    with os.fdopen(env_fd, "w") as f:
        f.write(env_file_contents)

    # Make sure these three keys start unset, so we can prove the load
    # actually did the work rather than reading pre-existing state.
    for key in ("STAGING_DB_HOST", "STAGING_DB_PORT", "STAGING_API_KEY"):
        os.environ.pop(key, None)

    if DOTENV_AVAILABLE:
        # Real python-dotenv, exactly as used in production code:
        load_dotenv(dotenv_path=env_path)
        print("python-dotenv is installed - loaded the .env file for real.")
    else:
        # Fallback: python-dotenv isn't installed here, so parse the
        # same tiny format by hand and load it into os.environ
        # ourselves. This mirrors what load_dotenv() does internally
        # for the simple KEY=VALUE case.
        def parse_dotenv_manually(text: str) -> dict:
            parsed = {}
            for line in text.splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                value = value.strip().strip('"').strip("'")
                parsed[key.strip()] = value
            return parsed

        for key, value in parse_dotenv_manually(env_file_contents).items():
            os.environ[key] = value
        print("python-dotenv not installed - parsed the .env file by hand.")

    print("STAGING_DB_HOST:", os.environ.get("STAGING_DB_HOST"))
    print("STAGING_DB_PORT:", os.environ.get("STAGING_DB_PORT"))
    print("STAGING_API_KEY: sk_fake...", os.environ.get("STAGING_API_KEY", "")[-4:])
finally:
    os.remove(env_path)   # clean up the temp .env file
    for key in ("STAGING_DB_HOST", "STAGING_DB_PORT", "STAGING_API_KEY"):
        os.environ.pop(key, None)   # don't leak these into later sections

print("\nIn a real project: `pip install python-dotenv`, keep a `.env`")
print("file locally (never committed), and call `load_dotenv()` once at")
print("the top of your entry-point script, before reading any config.")


"""
---------------------------------------------------------------------
4. configparser FOR STRUCTURED .ini CONFIG  ⭐⭐
---------------------------------------------------------------------
`.env` files are flat - great for secrets and simple overrides, but
awkward once you have GROUPED, structured settings (one block for the
database, another for the ETL job itself). The stdlib `configparser`
module reads `.ini`-style files with `[section]` headers, and gives
you typed getters - `getint()`, `getfloat()`, `getboolean()` - instead
of hand-rolling `int(value)` / `value == "true"` everywhere.
---------------------------------------------------------------------
"""

print("\n--- configparser for Structured .ini Config ---")

ini_contents = (
    "[database]\n"
    "host = warehouse.internal.pattern.com\n"
    "port = 5432\n"
    "use_ssl = true\n"
    "\n"
    "[etl]\n"
    "batch_size = 500\n"
    "max_retries = 3\n"
    "dry_run = false\n"
)

ini_fd, ini_path = tempfile.mkstemp(suffix=".ini")
try:
    with os.fdopen(ini_fd, "w") as f:
        f.write(ini_contents)

    parser = configparser.ConfigParser()
    parser.read(ini_path)

    print("sections found:", parser.sections())
    print("[database] host:", parser.get("database", "host"))
    print("[database] port (int):", parser.getint("database", "port"))
    print("[database] use_ssl (bool):", parser.getboolean("database", "use_ssl"))
    print("[etl] batch_size (int):", parser.getint("etl", "batch_size"))
    print("[etl] dry_run (bool):", parser.getboolean("etl", "dry_run"))

    # Missing key with a fallback - avoids a KeyError for optional settings
    timeout = parser.getint("etl", "timeout_seconds", fallback=30)
    print("[etl] timeout_seconds (missing, uses fallback):", timeout)
finally:
    os.remove(ini_path)   # clean up the temp .ini file

print("\nconfigparser values are ALWAYS strings until you call a typed")
print("getter - forgetting that is a classic bug (e.g. `if dry_run:`")
print("on the raw string 'false' is truthy, since it's a non-empty str).")


"""
---------------------------------------------------------------------
5. LAYERING CONFIG SOURCES: A CLEAR PRECEDENCE ORDER  ⭐⭐⭐
---------------------------------------------------------------------
Real pipelines combine SEVERAL sources at once, and need a documented
rule for which one wins when the same setting appears in more than
one place. The near-universal convention, weakest to strongest:

    defaults < config file < environment variables < CLI arguments

Defaults are the fallback nobody had to specify; a config file sets
per-deployment norms; an environment variable is how ops/CI overrides
that for one run without touching a file; a CLI flag is the most
explicit, in-the-moment override and should always win.
---------------------------------------------------------------------
"""

print("\n--- Layering Config Sources With Clear Precedence ---")


def get_config(key: str, *, default=None, file_config: dict | None = None,
                env_var: str | None = None):
    """Resolve one setting using: default < file_config < environment.
    (CLI args are layered on top of this separately below, since
    argparse already gives each flag its own None-by-default handling.)
    """
    value = default
    if file_config is not None and key in file_config:
        value = file_config[key]                       # file beats default
    if env_var is not None and env_var in os.environ:
        value = os.environ[env_var]                     # env beats file
    return value


# Simulates what section 4's parsed .ini gave us for [etl] batch_size
file_config = {"batch_size": "500"}

os.environ.pop("ETL_BATCH_SIZE", None)   # make sure it starts unset
resolved = get_config("batch_size", default="100", file_config=file_config,
                       env_var="ETL_BATCH_SIZE")
print("no env var set  -> batch_size resolves from FILE:", resolved)

with temporary_env_vars(ETL_BATCH_SIZE="1000"):
    resolved = get_config("batch_size", default="100", file_config=file_config,
                           env_var="ETL_BATCH_SIZE")
    print("env var set     -> batch_size resolves from ENV: ", resolved,
          "(overrides the file's 500)")

    # Now prove CLI beats even the environment variable
    cli_parser = argparse.ArgumentParser()
    cli_parser.add_argument("--batch-size", default=None)
    simulated_argv = ["--batch-size", "2500"]   # e.g. `python job.py --batch-size 2500`
    cli_args = cli_parser.parse_args(simulated_argv)

    final_value = cli_args.batch_size if cli_args.batch_size is not None else resolved
    print("CLI flag passed -> batch_size resolves from CLI:", final_value,
          "(overrides the env var's 1000)")

    # And confirm an ABSENT CLI flag falls back to the env-resolved value
    cli_args_absent = cli_parser.parse_args([])   # no --batch-size given
    final_value_absent = (cli_args_absent.batch_size
                           if cli_args_absent.batch_size is not None else resolved)
    print("CLI flag absent -> falls through to ENV value:", final_value_absent)


"""
---------------------------------------------------------------------
6. NEVER COMMIT SECRETS: .gitignore AND REAL SECRET MANAGERS  ⭐⭐
---------------------------------------------------------------------
A `.env` file is only safe because it's kept OUT of version control -
that's a `.gitignore` entry, not an accident. For anything beyond a
solo/local project, `.env` files themselves become a liability
(they're plaintext on disk, hard to rotate or audit, and easy for
someone to `scp` off a box) - production systems reach for a real
secret manager instead.
---------------------------------------------------------------------
"""

print("\n--- Never Commit Secrets: .gitignore and Secret Managers ---")

gitignore_snippet = ".env\n.env.*\n!.env.example\n*.pem\nconfig/secrets.ini\n"
print("typical .gitignore entries for config/secrets:")
print(gitignore_snippet.rstrip())
print("(commit a checked-in '.env.example' with dummy values as the")
print(" template teammates copy from - never the real '.env')")

print("\nBeyond .env files, production-grade secret storage uses a")
print("dedicated secret manager - AWS Secrets Manager, HashiCorp Vault,")
print("or GCP Secret Manager - which add automatic ROTATION, an AUDIT")
print("log of who/what read a secret and when, and fine-grained access")
print("control per secret (vs. one .env file readable by anything with")
print("filesystem access). Real, idiomatic client code for AWS:")

try:
    import boto3
    from botocore.config import Config as BotoConfig

    # bounded timeouts + no retries, so this demo fails fast in a
    # sandbox with no AWS credentials/network instead of hanging
    client = boto3.client(
        "secretsmanager", region_name="us-east-1",
        config=BotoConfig(connect_timeout=2, read_timeout=2,
                           retries={"max_attempts": 0}),
    )
    response = client.get_secret_value(SecretId="prod/etl/api_key")
    api_key_from_vault = response["SecretString"]
except Exception as e:
    # Expected in this sandbox - no live AWS credentials/network.
    print(f"  (no live Secrets Manager reachable here: {type(e).__name__})")
    print("  in production this call returns the real, current secret,")
    print("  fetched fresh at request time - never written to disk or")
    print("  baked into a config file at all.")
    api_key_from_vault = "sk_fake_demo_12345"   # simulated fallback, this demo only

print("resolved key (simulated fallback in this sandbox): ends in",
      api_key_from_vault[-4:])


"""
---------------------------------------------------------------------
7. TYING IT TOGETHER: AN ETL PIPELINE'S DB CONNECTION + API KEY  ⭐⭐⭐
---------------------------------------------------------------------
Putting it all together the way a real pipeline entry-point would:
build the DB connection string and API key from environment variables
(themselves populated by `.env` locally, or injected directly by
CI/CD or the orchestrator in staging/prod), fail loudly if either
required value is missing, and NEVER fall back to a hardcoded value.
---------------------------------------------------------------------
"""

print("\n--- Tying It Together: ETL Pipeline Config From the Environment ---")


def build_pipeline_config() -> dict:
    """The production-shaped replacement for section 1's hardcoded
    API_KEY / DB_PASSWORD - every required value is sourced from the
    environment and validated before the pipeline is allowed to run."""
    db_host = require_env("ETL_DB_HOST")
    db_password = require_env("ETL_DB_PASSWORD")
    api_key = require_env("ETL_API_KEY")
    connection_string = f"postgresql://etl_user:{db_password}@{db_host}:5432/warehouse"
    return {"connection_string": connection_string, "api_key": api_key}


with temporary_env_vars(ETL_DB_HOST="staging-db.internal.pattern.com",
                          ETL_DB_PASSWORD="REPLACE_ME",
                          ETL_API_KEY="sk_fake_demo_12345"):
    config = build_pipeline_config()
    masked_conn = config["connection_string"].replace("REPLACE_ME", "****")
    print("pipeline started with connection string:", masked_conn)
    print("pipeline started with API key ending in:", config["api_key"][-4:])

# Now the failure path: same call, but ETL_API_KEY was never set this time
with temporary_env_vars(ETL_DB_HOST="staging-db.internal.pattern.com",
                          ETL_DB_PASSWORD="REPLACE_ME"):
    try:
        build_pipeline_config()
    except RuntimeError as e:
        print("\npipeline refused to start (fail loud, not silent):", e)

print("\nNotice build_pipeline_config() never hardcodes a real value -")
print("swap the environment (dev/staging/prod) and the SAME function")
print("call produces the right config for wherever it's actually running.")


"""
=====================================================================
QUICK REFERENCE
=====================================================================
Hardcoded config/secrets in source -> can't vary per environment, and
                                        secrets in git history are a
                                        real incident (rotate + purge)

os.getenv(name, default)     -> safe read for an OPTIONAL setting
os.environ[name]              -> raises KeyError if unset
require_env(name) pattern       -> raise a clear error if a REQUIRED
                                    var is missing; never proceed on None

.env file + python-dotenv:
    load_dotenv(dotenv_path=...)  -> loads KEY=VALUE lines into
                                       os.environ
    wrap import in try/except ImportError -> hand-parse as a fallback

configparser (.ini, sectioned):
    parser.read(path)                -> load the file
    parser.get(section, key)          -> string value
    parser.getint / getfloat /          -> typed reads (raw values are
      getboolean(section, key)            ALWAYS strings otherwise)

Precedence, weakest to strongest:
    defaults  <  config file  <  environment variables  <  CLI args

Never commit secrets:
    .gitignore the real .env / secrets.ini, commit a .env.example
    instead; for production, use a real secret manager (AWS Secrets
    Manager / HashiCorp Vault / GCP Secret Manager) for rotation,
    audit logging, and fine-grained access control.
=====================================================================
"""

print("\n--- Quick Reference (see comment block above) ---")


"""
=====================================================================
INTERVIEW QUESTIONS - CONFIGURATION MANAGEMENT
=====================================================================

1. Why is hardcoding a database connection string or API key directly
   in source code a problem, even ignoring security - i.e. what does
   it cost you operationally across dev/staging/prod?

2. A secret was accidentally committed to git and later removed in a
   follow-up commit. Is the secret actually gone? What should you do
   about it right now?

3. What's the difference between `os.environ["X"]` and
   `os.getenv("X", default)`, and when would you deliberately choose
   the one that can raise over the one that can't?

4. Walk through the `require_env()` function in this file: why is
   raising a `RuntimeError` when a required variable is missing
   better than letting the caller receive `None` and continue?

5. What does `load_dotenv()` from `python-dotenv` actually do to
   `os.environ`, and where in your program's startup should you call
   it?

6. Why should a `.env` file itself never be committed to version
   control, even though the code that reads it is committed? What do
   you commit instead so teammates know what keys are expected?

7. When would you reach for `configparser` and a `.ini` file instead
   of a flat `.env` file for configuration?

8. `configparser` values are always returned as strings by
   `parser.get()`. What bug can this cause with a setting like
   `dry_run = false`, and how do `getboolean()` / `getint()` avoid it?

9. Describe a common precedence order for layering configuration from
   defaults, a config file, environment variables, and CLI arguments.
   Why does that specific ordering (not some other order) make sense?

10. In `get_config()` in this file, walk through what happens to
    `batch_size` as each layer (default, file, env, CLI) is added -
    which value wins at each step and why?

11. Beyond `.env` files, what problem do dedicated secret managers
    (AWS Secrets Manager, HashiCorp Vault, GCP Secret Manager) solve
    that a plaintext `.env` file on disk does not?

12. How would you design an ETL script's startup so that it fails
    immediately and clearly if a required credential is missing,
    rather than failing confusingly later mid-run?

13. If you rotate an API key in your secret manager, does a
    long-running pipeline process need to be restarted to pick up the
    new value? How does that answer differ between a `.env`-loaded
    value and a value fetched live from a secret manager per request?

14. What's the security difference between an environment variable
    holding a secret and a secret manager API call fetching it at
    request time - where does each one actually live at rest?

15. How would you structure config so the exact same Python script,
    with zero code changes, correctly talks to the dev database when
    run locally and the prod database when run in the deployed job?
=====================================================================
"""
