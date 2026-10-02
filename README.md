# Sigma Siphon

Sigma Siphon acquires Philippine points of interest from OpenStreetMap and
Overture Maps, clips them to an exact configured city or municipality boundary,
reconciles likely duplicates, classifies them to the 2018 Philippine
input-output industries, and writes the result as GeoParquet.

The default command is deliberately simple:

```powershell
sigma-siphon run pasig
```

By default, Sigma Siphon uses deterministic classification rules only. It does
**not** require an OpenAI account, API key, or API billing.

OpenAI is an optional enhancement that can be configured later:

```powershell
sigma-siphon run pasig --llm
```

---

# Fastest installation

If Git and Python 3.11 or newer already work on your computer, this is the
entire installation:

```powershell
git clone https://github.com/YOUR-ORGANIZATION/sigma-siphon.git
cd sigma-siphon
python -m pip install -e .
sigma-siphon doctor
```

Then run:

```powershell
sigma-siphon run pasig
```

That is the normal workflow.

## Important: Sigma Siphon uses your current Python environment

Sigma Siphon does **not** create a Conda environment for you.

It does **not** install or reinstall Conda.

It does **not** create a special launcher.

This command:

```powershell
python -m pip install -e .
```

installs Sigma Siphon into whichever Python environment is active when you run
it.

For example, if you already use a Conda or virtual environment, activate the
environment you want to use and then run the install command there.

If your organization provides a standard Python environment, use that.

---

# Absolute-beginner Windows walkthrough

Use this section if the short instructions above are unfamiliar.

## Step 1 — Make sure Git is installed

Open PowerShell and run:

```powershell
git --version
```

If you see a Git version number, continue to Step 2.

If Windows says that `git` is not recognized, install Git for Windows from:

```text
https://git-scm.com/install/windows
```

Accepting the normal installer defaults is usually fine.

After installation, close PowerShell, open it again, and run:

```powershell
git --version
```

## Step 2 — Make sure Python is available

Run:

```powershell
python --version
```

Sigma Siphon requires Python 3.11 or newer.

Examples that are new enough:

```text
Python 3.11.x
Python 3.12.x
Python 3.13.x
```

If your organization already provides Python, Conda, Miniforge, or another
approved Python environment, use that.

If you use Conda or a Python virtual environment, activate the environment you
want Sigma Siphon installed into **before** continuing.

Sigma Siphon will install into that environment. It will not create another one.

If Python is not installed and your organization has no standard Python setup,
ask your IT administrator which Python distribution you should use. Miniforge is
one suitable option, but Sigma Siphon itself does not require Miniforge
specifically.

## Step 3 — Clone the repository

Open your organization's internal GitHub page for `sigma-siphon`.

Click:

**Code → HTTPS → Copy**

In PowerShell, choose where you want to store the repository. For example:

```powershell
mkdir "$HOME\Documents\GitHub" -ErrorAction SilentlyContinue
cd "$HOME\Documents\GitHub"
```

Run `git clone` followed by the repository address you copied. Example:

```powershell
git clone https://github.com/YOUR-ORGANIZATION/sigma-siphon.git
```

GitHub may ask you to sign in using your organization's normal GitHub
authentication.

Enter the repository:

```powershell
cd sigma-siphon
```

## Step 4 — Install Sigma Siphon

Run:

```powershell
python -m pip install -e .
```

This installs Sigma Siphon and its Python dependencies into the Python
environment that is currently active.

It does not create a second environment.

It does not reinstall Python.

It does not reinstall Conda.

The `-e` means "editable install": the installed command points to this checkout
of the repository. If the repository code is updated later with `git pull`, the
installed command uses the updated code.

## Step 5 — Verify the installation

Run:

```powershell
sigma-siphon doctor
```

A normal installation without OpenAI should look approximately like:

```text
sigma-siphon 0.1.5
Areas: 1645 (1642 localities + 3 composites)
Exact boundaries: available
OSM endpoint: ready
LLM: optional — API key not configured (default rules-only mode is ready)
```

The LLM line saying that the API key is not configured is **not an error**.

OpenAI is optional.

## Step 6 — Test Pasig

For the first Pasig run:

```powershell
sigma-siphon run pasig --refresh
```

The `--refresh` option forces a fresh download of the source data.

After that, normal reruns can simply be:

```powershell
sigma-siphon run pasig
```

A successful run creates:

```text
output\
└── pasig\
    ├── pois.parquet
    ├── run.json
    ├── ATTRIBUTION.txt
    └── DATABASE_LICENSE.txt
```

---

# Optional convenience installer

The shortest installation command is still:

```powershell
python -m pip install -e .
```

If you prefer a script, this repository also contains:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

The script only:

1. checks the currently active Python;
2. verifies that it is Python 3.11 or newer;
3. removes the obsolete Sigma Siphon launcher used by an older setup method, if
   that launcher exists;
4. runs `python -m pip install -e .`;
5. runs diagnostics.

It does **not** create, delete, activate, update, or reinstall any Conda
environment.

It does **not** configure OpenAI.

---

# Default mode: no LLM

Normal use is:

```powershell
sigma-siphon run pasig
```

The pipeline is:

```text
OSM + Overture
      ↓
exact boundary clipping
      ↓
reconciliation
      ↓
deterministic IO80 rules
      ↓
deterministic IO16 derivation
      ↓
output
```

No OpenAI API key is required.

POIs that cannot be confidently classified by the deterministic rules remain
unresolved.

---

# Optional OpenAI LLM

You can install and use Sigma Siphon indefinitely without configuring OpenAI.

Only configure OpenAI if you decide that you want LLM classification for POIs
that remain unresolved after the deterministic rules.

The LLM is explicitly enabled with:

```powershell
sigma-siphon run pasig --llm
```

## What happens in LLM mode

```text
OSM + Overture
      ↓
exact boundary clipping
      ↓
reconciliation
      ↓
deterministic IO80 rules
      ↓
unresolved POIs only
      ↓
OpenAI LLM
      ↓
deterministic IO16 derivation
      ↓
output
```

The deterministic rules always run first.

Only unresolved POIs are passed to the LLM.

## Set up OpenAI later

When you decide to try OpenAI, you do **not** reinstall Sigma Siphon.

From the repository, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup-llm.ps1
```

The helper:

1. verifies that Sigma Siphon is already installed;
2. securely asks for your OpenAI API key;
3. stores the key in your Windows **User** environment;
4. does not write the key into the repository;
5. runs `sigma-siphon doctor`.

After the helper finishes, close PowerShell and open a new PowerShell window.

Then verify:

```powershell
sigma-siphon doctor
```

And run:

```powershell
sigma-siphon run pasig --llm
```

## Getting an OpenAI API key

Open:

```text
https://platform.openai.com/api-keys
```

Sign in to the OpenAI API organization/project your organization expects you to
use.

Create a new secret key and copy it when it is displayed.

The full secret is normally shown only when it is created. If you lose it,
create a replacement key rather than trying to recover the original secret.

Treat the key like a password.

Never:

- commit it to GitHub;
- put it in source code;
- put a real key in `.env.example`;
- put it in `README.md`;
- post it in an issue;
- share it with another employee;
- print it on screen for troubleshooting.

## Free credits and paid API usage

Creating an API key is not the same thing as paying for API usage.

If your OpenAI API organization/account has free or granted API credits, those
can be used first.

Do not assume that every new API account receives free credits.

If no usable free/granted credits are available, the organization can decide
later whether to enable paid API billing.

A ChatGPT subscription and OpenAI API billing are separate.

You do not need any of this for the default:

```powershell
sigma-siphon run pasig
```

---

# How to know whether the LLM was used

A normal default run:

```powershell
sigma-siphon run pasig
```

records:

```text
llm_enabled = false
tagged_by_llm = 0
```

An explicit LLM run:

```powershell
sigma-siphon run pasig --llm
```

records LLM usage in:

```text
output\<area>\run.json
```

The classification section includes:

```text
llm_enabled
llm_model
llm_base_url
tagged_by_rule
tagged_by_llm
unresolved
```

The terminal summary also reports rule-versus-LLM tagging counts.

---

# Common commands

Check the installation:

```powershell
sigma-siphon doctor
```

Find Pasig:

```powershell
sigma-siphon areas --search pasig
```

Normal Pasig run:

```powershell
sigma-siphon run pasig
```

Force fresh acquisition:

```powershell
sigma-siphon run pasig --refresh
```

Optional LLM-enhanced Pasig run:

```powershell
sigma-siphon run pasig --llm
```

Fresh acquisition plus LLM:

```powershell
sigma-siphon run pasig --refresh --llm
```

Other examples:

```powershell
sigma-siphon run quezon_city
sigma-siphon run metro_manila
sigma-siphon run 1381200000
```

`1381200000` is the PSGC alias for City of Pasig.

---

# Updating Sigma Siphon

Go to the repository:

```powershell
cd "$HOME\Documents\GitHub\sigma-siphon"
```

Get the latest version:

```powershell
git pull --ff-only
```

Because the package is installed in editable mode, ordinary source-code updates
take effect immediately.

If `pyproject.toml` changed, rerun:

```powershell
python -m pip install -e .
```

That updates Sigma Siphon in the **same currently active Python environment**.

---

# Troubleshooting

## `python` is not recognized

Python is not available in the current terminal.

If your organization uses Conda or another managed environment, activate that
environment first.

Otherwise ask your IT administrator which Python installation you should use.

## Python is older than 3.11

Run:

```powershell
python --version
```

Use a Python 3.11-or-newer environment.

Sigma Siphon will not create one automatically.

## `sigma-siphon` is not recognized after installation

First confirm which Python you used:

```powershell
python -c "import sys; print(sys.executable)"
```

Then reinstall into that same active environment:

```powershell
python -m pip install -e .
```

If you use Conda or a virtual environment, make sure that environment is
currently active.

You can also verify the package itself with:

```powershell
python -m sigma_siphon doctor
```

## `--llm` says the API key is missing

The default pipeline still works:

```powershell
sigma-siphon run pasig
```

If you want LLM mode, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup-llm.ps1
```

Then close PowerShell, open a new PowerShell window, and try:

```powershell
sigma-siphon run pasig --llm
```

## The OpenAI request reports billing, quota, authentication, or permission errors

This affects only explicit `--llm` runs.

The normal rules-only pipeline remains available:

```powershell
sigma-siphon run pasig
```

For LLM use, check the OpenAI API project, key, available credits/billing, and
model permissions.

## An OSM request fails

Sigma Siphon includes a default Overpass endpoint. Internet or provider outages
can still occur.

Retry:

```powershell
sigma-siphon run pasig
```

Compatible downloaded source data are cached locally.

---

# Output

A successful run writes:

```text
output\<area>\pois.parquet
output\<area>\run.json
output\<area>\ATTRIBUTION.txt
output\<area>\DATABASE_LICENSE.txt
```

`pois.parquet` includes canonical location and reconciliation fields,
source/provenance information, geometry, and:

```text
io80_code
io80_label
io16_code
io16_label
tag_method
tag_confidence
tag_reason
```

`tag_method` can be:

```text
rule
llm
unresolved
```

IO80 is the primary classification. IO16 is derived deterministically from IO80.

---

# Data sources

Sigma Siphon uses:

1. OpenStreetMap through Overpass.
2. Overture Maps Places through the official `overturemaps` Python package.

A default Overpass endpoint is built into the application. Deployment
maintainers can override it with:

```text
SIGMA_OSM_OVERPASS_URL
```

Ordinary users do not need to configure it.

---

# Boundaries

The configured Philippine city and municipality boundaries are packaged with
Sigma Siphon.

`config/areas.yml` contains the locality catalog and configured composite areas.

A locality's 10-digit PSGC is accepted as an alias.

`run.json` records a fingerprint of the effective boundary used in the run.

---

# Reconciliation

OSM and Overture observations are linked only when geography and normalized
names satisfy the reconciliation thresholds.

Candidate matches are processed strongest-first with one observation per source.

A two-source canonical coordinate is normally the midpoint of the
representative points. If that midpoint would fall outside the configured
boundary or inside a hole, Sigma Siphon falls back deterministically to an
actual in-boundary source coordinate.

---

# Licensing

Sigma Siphon software is proprietary.

Third-party software and acquired data retain their own licenses and terms.

OpenStreetMap data are ODbL 1.0. The project conservatively treats a reconciled
output containing OSM-derived records as an ODbL-covered database for
distribution purposes.

Every run writes:

```text
ATTRIBUTION.txt
DATABASE_LICENSE.txt
```

and retains source-license provenance in the output.

See:

```text
DATA_LICENSES.md
THIRD_PARTY_NOTICES.md
```

---

# Maintainer checks

Ordinary users do not need these commands.

Maintainers can run:

```powershell
python tools\check_dependency_policy.py
python -m pytest -q
ruff check .
python -m compileall -q src tests scripts tools
git diff --check
```

The unit tests are network-free.

## Built-in PSIC classification reference

Version 0.2.2 adds the self-contained reference foundation for the upcoming PSIC-first
classifier. Validate it with:

```powershell
sigma-siphon classification-check
```

The bundle contains the normalized PSIC Revision 5 hierarchy, its official reference workbook,
the Revision 5-to-PSIC-2019 bridge, the PSIC-2019-to-PSA-2018-I-O concordance, and OSM/Overture
PSIC review/crosswalk tables. Foursquare, PSCC, and PCPC rows are not included in this bundle.

This is intentionally a staging release: `sigma-siphon run` still uses the existing deterministic
IO classifier. See `CLASSIFICATION_REFERENCE.md` for the exact Stage 2 boundary.
