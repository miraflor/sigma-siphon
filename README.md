# Sigma Siphon

Sigma Siphon acquires Philippine points of interest from OpenStreetMap and
Overture Maps, clips them to an exact configured city or municipality boundary,
reconciles likely duplicates, classifies them to the 2018 Philippine
input-output industries, and writes the result as GeoParquet.

The normal user experience is intentionally simple:

```powershell
sigma-siphon run pasig
```

**That default command does not use an LLM and does not require an OpenAI API
key.**

It uses the built-in deterministic IO80 classification rules and derives IO16
from IO80.

If you later want the optional LLM-enhanced classifier, use:

```powershell
sigma-siphon run pasig --llm
```

The `--llm` option uses OpenAI only for POIs that were not resolved by the
deterministic rules.

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

# The two operating modes

## Default mode: free, deterministic, no API key

```powershell
sigma-siphon run pasig
```

Pipeline:

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

This is the normal default.

No OpenAI account, OpenAI API key, or OpenAI billing is needed.

POIs that cannot be classified confidently by the deterministic rules remain
unresolved.

## Optional mode: rules + OpenAI LLM

```powershell
sigma-siphon run pasig --llm
```

Pipeline:

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

This mode requires an OpenAI API key and usable API credits/billing.

You do not need to decide about the LLM during installation. You can install and
test Sigma Siphon first in the free default mode and add OpenAI later.

---

# First-time installation on Windows

These instructions assume Windows 10 or Windows 11 and assume that the reader
has never used Git, Conda, Python, or an API key before.

You normally do this installation only once on a computer.

## 1. Get access to the repository

Open your organization's internal GitHub page for `sigma-siphon`.

If GitHub says that the repository does not exist or you do not have permission,
ask the repository owner or your organization's GitHub administrator for access.

## 2. Install Git for Windows

Git downloads the repository and lets you receive future updates.

Open:

```text
https://git-scm.com/install/windows
```

Download and run the Windows installer.

If you are unsure about an installer option, accepting the normal default is
usually fine.

After installation, open PowerShell and run:

```powershell
git --version
```

You should see a Git version number.

If Windows says that `git` is not recognized, close PowerShell and open it again.
If needed, restart Windows.

## 3. Install Miniforge

Miniforge provides the isolated Python environment used by Sigma Siphon.

You do not need to install Python separately.

Open:

```text
https://github.com/conda-forge/miniforge/releases/latest
```

Download:

```text
Miniforge3-Windows-x86_64.exe
```

Run the installer.

Recommended choices for an ordinary user:

- choose **Just Me**;
- keep the default installation folder;
- keep the Start Menu shortcut;
- otherwise accept the normal defaults.

Open **Miniforge Prompt** from the Windows Start menu.

Run:

```powershell
conda --version
```

You should see a Conda version number.

### Important: setup does not reinstall Conda

Sigma Siphon's setup script creates a dedicated environment named
`sigma-siphon`.

It does **not** reinstall Miniforge or Conda.

Conceptually:

```text
Miniforge / Conda
        │
        └── sigma-siphon environment
```

The separate environment contains the Python packages Sigma Siphon needs and
helps prevent dependency conflicts with unrelated software.

## 4. Clone the repository

In the browser, open the `sigma-siphon` repository.

Click:

**Code → HTTPS → Copy**

In **Miniforge Prompt**, create a folder for repositories:

```powershell
mkdir "$HOME\Documents\GitHub" -ErrorAction SilentlyContinue
cd "$HOME\Documents\GitHub"
```

Clone the repository. Replace the example URL with the URL you copied:

```powershell
git clone https://github.com/YOUR-ORGANIZATION/sigma-siphon.git
```

GitHub may ask you to sign in. Complete your organization's normal GitHub
authentication.

Enter the repository:

```powershell
cd sigma-siphon
```

## 5. Run the one-time setup script

From inside the repository:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

The script:

1. checks that Conda exists;
2. creates or updates the isolated `sigma-siphon` environment;
3. installs Sigma Siphon and its dependencies;
4. optionally offers to store an OpenAI API key;
5. creates a permanent `sigma-siphon` command for your Windows user account;
6. adds that command to your user `PATH`;
7. runs `sigma-siphon doctor`.

**You may skip OpenAI setup.** Sigma Siphon works normally without it.

When setup finishes, close the terminal completely and open a **new PowerShell
window**.

## 6. Verify the installation

Run:

```powershell
sigma-siphon doctor
```

A normal installation without OpenAI should look roughly like:

```text
sigma-siphon 0.1.4
Areas: 1645 (1642 localities + 3 composites)
Exact boundaries: available
OSM endpoint: ready
LLM: optional — API key not configured (default rules-only mode is ready)
```

This is a healthy configuration.

If you previously configured OpenAI, the last line should instead say that the
LLM is configured.

## 7. Run Pasig

The normal first test is:

```powershell
sigma-siphon run pasig --refresh
```

After the first successful acquisition, ordinary reruns can simply be:

```powershell
sigma-siphon run pasig
```

You do not need to activate Conda manually.

You do not need to `cd` into the repository.

You do not need an OpenAI key.

You do not need to specify an OSM endpoint.

The setup script's launcher automatically uses the correct environment and the
repository root.

---

# Optional OpenAI setup

OpenAI is an optional enhancement, not a requirement for Sigma Siphon.

## What the LLM does

The deterministic rules run first.

Only POIs that remain unresolved are sent to the LLM when you explicitly add:

```powershell
--llm
```

Example:

```powershell
sigma-siphon run pasig --llm
```

## API key versus API usage

Two different things are involved:

1. **API key** — the secret credential used by Sigma Siphon.
2. **API usage** — may consume granted/free credits or paid credits.

Creating an API key itself does not incur a charge.

An account may or may not have free or granted API credits. Do not assume every
new OpenAI API account receives free usage.

If the account has usable free/granted credits, those can be used for an initial
LLM test.

Otherwise, the organization can decide later whether to enable paid API usage.

## ChatGPT and the API are separate

A ChatGPT subscription does not automatically provide OpenAI API credits.

Sigma Siphon's `--llm` mode uses the OpenAI API Platform.

## Create an API key

Open:

```text
https://platform.openai.com/api-keys
```

Sign in to the correct organization/project.

Create a new secret key.

Give it a recognizable name such as:

```text
Sigma Siphon - Your Name
```

Copy the secret when it is shown.

The full secret normally cannot be viewed again later. If it is lost, create a
new key and revoke the old one if appropriate.

## Keep the key secret

Never:

- commit it to GitHub;
- put it in source code;
- put it in `README.md`;
- put a real value in `.env.example`;
- paste it into an issue;
- send it in ordinary chat or email;
- print it on screen while troubleshooting.

## Add the key to Sigma Siphon

Return to the repository and rerun:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

When asked whether to configure OpenAI, answer yes and paste the key.

The typing is hidden.

The key is stored in the current Windows user's environment, outside the
repository.

Close the terminal and open a new PowerShell window.

Verify:

```powershell
sigma-siphon doctor
```

Then run the optional hybrid classifier:

```powershell
sigma-siphon run pasig --llm
```

If the key is missing and `--llm` is explicitly requested, Sigma Siphon stops
before acquisition and tells you how to configure it.

The normal command without `--llm` remains fully usable:

```powershell
sigma-siphon run pasig
```

---

# Understanding the output

A successful run writes:

```text
output\<area>\pois.parquet
output\<area>\run.json
output\<area>\ATTRIBUTION.txt
output\<area>\DATABASE_LICENSE.txt
```

## `pois.parquet`

This is the primary spatial dataset.

It includes canonical POI fields, geometry, reconciliation/provenance fields,
source-license information, and:

```text
io80_code
io80_label
io16_code
io16_label
tag_method
tag_confidence
tag_reason
```

`tag_method` indicates how a classification was obtained:

```text
rule         deterministic rule
llm          OpenAI LLM, only when --llm was requested
unresolved   no accepted classification
```

IO80 is the primary classification.

IO16 is derived deterministically from IO80.

## `run.json`

This records run metadata, source counts, output counts, boundary identity,
licensing information, and classification information.

Its classification section includes:

```text
llm_enabled
llm_model
llm_base_url
tagged_by_rule
tagged_by_llm
unresolved
```

In a default run:

```text
llm_enabled = false
tagged_by_llm = 0
```

In an explicit LLM run:

```powershell
sigma-siphon run pasig --llm
```

`llm_enabled` is true and `tagged_by_llm` shows how many POIs were classified by
the LLM.

---

# Common commands

Normal/default Pasig run:

```powershell
sigma-siphon run pasig
```

Force fresh acquisition:

```powershell
sigma-siphon run pasig --refresh
```

Optional LLM-enhanced run:

```powershell
sigma-siphon run pasig --llm
```

Optional LLM-enhanced run with fresh acquisition:

```powershell
sigma-siphon run pasig --llm --refresh
```

Find an area:

```powershell
sigma-siphon areas --search pasig
```

List all areas:

```powershell
sigma-siphon areas
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

Open PowerShell and go to the repository:

```powershell
cd "$HOME\Documents\GitHub\sigma-siphon"
```

Pull the latest code:

```powershell
git pull --ff-only
```

If setup or dependencies changed, rerun:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

The script updates the existing `sigma-siphon` environment. It does not reinstall
Miniforge.

---

# Troubleshooting

## `sigma-siphon` is not recognized

Close PowerShell and open a new PowerShell window.

Try:

```powershell
sigma-siphon doctor
```

If it still fails, return to the repository and rerun:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

## `conda` is not recognized during setup

Use **Miniforge Prompt** for the first setup.

Check:

```powershell
conda --version
```

## The default Pasig run asks for an OpenAI key

It should not.

The default is rules-only:

```powershell
sigma-siphon run pasig
```

OpenAI should be required only when you explicitly run:

```powershell
sigma-siphon run pasig --llm
```

Check the installed version:

```powershell
sigma-siphon doctor
```

## `--llm` says the API key is missing

Either continue without the LLM:

```powershell
sigma-siphon run pasig
```

or rerun setup and add an OpenAI key:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

## The LLM reports authentication, permissions, billing, or quota errors

The deterministic/default mode remains usable:

```powershell
sigma-siphon run pasig
```

For LLM use, ask the OpenAI API project owner to verify the API key, project
access, model access, and available credits/billing.

## An OSM request fails

Sigma Siphon includes a default Overpass endpoint, but internet or provider
outages can still occur.

Retry:

```powershell
sigma-siphon run pasig
```

Successfully downloaded compatible source data are cached.

## I moved the repository

The permanent launcher points to the repository location that existed when
`setup.ps1` last ran.

Enter the repository at its new location and rerun:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

---

# Data sources

Sigma Siphon uses two acquisition sources:

1. OpenStreetMap through Overpass.
2. Overture Maps Places through the official `overturemaps` package.

The application contains a normal Overpass endpoint default. A deployment
maintainer can override it with:

```text
SIGMA_OSM_OVERPASS_URL
```

Ordinary users should not need to set that variable.

---

# LLM configuration defaults

OpenAI support is optional.

The application contains defaults for:

```text
SIGMA_LLM_MODEL
SIGMA_LLM_BASE_URL
```

Ordinary users normally do not need to set either one.

The only secret used by optional LLM mode is:

```text
SIGMA_LLM_API_KEY
```

LLM decisions are cached locally by POI evidence, model endpoint, model,
classification-policy identity, and catalog fingerprint.

---

# Boundaries

`data/boundaries/areas.gpkg` contains the configured city/municipality boundary
geometries keyed by PSGC.

`config/areas.yml` contains the locality catalog and the configured composite
areas.

A locality's 10-digit PSGC is accepted as an alias.

`run.json` records a fingerprint of the effective boundary used for the run.

---

# Reconciliation

OSM and Overture observations are linked only when geography and normalized
names satisfy the reconciliation thresholds.

Candidate matches are processed strongest-first with one observation per source.

A two-source canonical coordinate is normally the midpoint of the representative
points. If that midpoint would fall outside the configured boundary or inside a
hole, Sigma Siphon falls back deterministically to an actual in-boundary source
coordinate.

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

# Maintainer/developer checks

Ordinary users do not need these commands.

Maintainers can run:

```powershell
python tools\check_dependency_policy.py
python -m pytest -q
ruff check .
python -m compileall -q src tests scripts tools
git diff --check
```

Unit tests are network-free.
