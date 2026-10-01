# Sigma Siphon

Sigma Siphon is a Philippine point-of-interest pipeline. It acquires places from
OpenStreetMap and Overture Maps, clips them to the exact configured city or
municipality boundary, reconciles likely duplicates, classifies each canonical
place into the 2018 Philippine input-output industries, and writes a GeoParquet
dataset.

The intended normal user experience is deliberately simple:

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

The classification pipeline is hybrid:

```text
POI
 │
 ├── high-confidence deterministic rule ──> IO80
 │
 └── everything else ─────────────────────> hosted LLM ──> IO80
                                                    │
                                                    └──> deterministic IO16
```

The ordinary user does not configure an OSM server, model name, API URL, boundary
file, or output schema. Those have application defaults.

The only secret is the user's OpenAI API key. The one-time setup script stores
that key in the user's Windows environment; it is never written into this
repository.

---

## If you are completely new to this

There are two phases:

**First day only**

1. Install Git.
2. Install Miniforge.
3. Download (clone) this repository.
4. Run `setup.ps1`.
5. Choose whether to configure OpenAI now or later.
6. Close the terminal.

You can test Sigma Siphon immediately without spending anything:

```powershell
sigma-siphon run pasig --no-llm
```

That free test exercises acquisition, exact clipping, reconciliation, deterministic
IO80 classification, IO16 derivation, and output writing. It simply skips the hosted
LLM for unresolved POIs.

If an OpenAI API key is configured and the API project has usable free/granted
credits or paid credits, the normal hybrid run is:

```powershell
sigma-siphon run pasig
```

No reinstall is required when switching from the free rules-only test to OpenAI.

You do **not** need to activate Conda manually after the setup script has
completed. The setup script creates a permanent `sigma-siphon` launcher for your
Windows account.

---

# Part I — First-time installation

These instructions assume Windows 10 or Windows 11 and assume no prior knowledge
of Python, Conda, Git, or command-line tools.

You only do this section once on a computer.

## 1. Make sure you have access to the repository

Open your organization's internal GitHub page for `sigma-siphon`.

If GitHub says that the repository does not exist or that you do not have
permission, ask the repository owner or your organization's GitHub administrator
to give you access before doing anything else.

Keep the browser tab open.

## 2. Install Git for Windows

Git is the program that downloads the repository and later lets you receive
updates.

Open:

https://git-scm.com/install/windows

Download and run the normal Windows installer.

If you do not know what an installer option means, the default is normally fine.

After installation, open **PowerShell** from the Windows Start menu and type:

```powershell
git --version
```

You should see something similar to:

```text
git version 2.x.x.windows.x
```

If Windows says that `git` is not recognized, close PowerShell, open it again,
and retry. If necessary, restart Windows.

## 3. Install Miniforge

Miniforge provides the isolated Python environment used by Sigma Siphon. You do
not need to install Python separately.

Open the official Miniforge releases page:

https://github.com/conda-forge/miniforge/releases/latest

Download the Windows x86-64 installer:

```text
Miniforge3-Windows-x86_64.exe
```

Run it.

Recommended choices for a normal user:

- install for **Just Me**;
- keep the default installation folder;
- keep the Start Menu shortcut;
- otherwise accept the normal defaults.

When it finishes, open **Miniforge Prompt** from the Windows Start menu.

Type:

```powershell
conda --version
```

You should see a version number.

## 4. Download the Sigma Siphon repository

Return to the `sigma-siphon` repository in your web browser.

Click:

**Code → HTTPS → copy**

You will copy an address similar to:

```text
https://github.com/YOUR-ORGANIZATION/sigma-siphon.git
```

In **Miniforge Prompt**, make a place for GitHub repositories:

```powershell
mkdir "$HOME\Documents\GitHub" -ErrorAction SilentlyContinue
cd "$HOME\Documents\GitHub"
```

Then type `git clone`, followed by a space, and paste the repository address.
Example:

```powershell
git clone https://github.com/YOUR-ORGANIZATION/sigma-siphon.git
```

GitHub may ask you to sign in. Complete your organization's normal GitHub
authentication.

When cloning finishes:

```powershell
cd sigma-siphon
```

You are now inside the repository.

## 5. Set up OpenAI API access and create your API key

Sigma Siphon uses the OpenAI API for POIs that are not handled by the
high-confidence deterministic rules.

There are **two separate things** to understand:

1. **The API key** is simply the secret credential Sigma Siphon uses to identify
   your OpenAI API account/project.
2. **API usage** consumes credits or is billed according to your organization's
   OpenAI API billing arrangement.

Creating an API key does not itself cost money.

However, having an API key does **not** automatically mean that your account has
usable API credit.

### Free credits, if your account has them

Some OpenAI API accounts or organizations may already have free or granted API
credits.

If your account has free credits, OpenAI uses those credits before purchased
credits.

Do **not** assume that every new account receives free API usage. Availability of
free credits can vary by account, program, organization, or time.

You can check your API billing/credit status in the OpenAI API Platform.

Open:

```text
https://platform.openai.com/
```

Sign in with the account your organization expects you to use.

Then open the **Billing** or **Usage** area for the relevant organization/project
and check whether usable credit is already available.

If usable free/granted credit is present, you can create an API key and proceed
without adding a payment method until that credit is exhausted.

### Paid API access if no free credit is available

If the organization/project has no usable free credits, API billing must be
enabled before Sigma Siphon's LLM requests can succeed.

For ordinary individual/team API accounts, OpenAI currently supports prepaid
billing or automatic card billing depending on the account arrangement.

For a new prepaid API account, the normal setup is:

1. Open the OpenAI API Platform:

   ```text
   https://platform.openai.com/
   ```

2. Make sure you are in the correct **organization** and **project**.

3. Open **Billing**.

4. Add payment details if the organization has not already done so.

5. Purchase API credits.

   OpenAI currently states that the minimum initial prepaid credit purchase is
   **US$5**.

6. Review **auto-reload** carefully.

   Auto-reload can automatically buy more credits when the balance drops below a
   threshold. If your organization does not want automatic purchases, turn it off.

In a corporate deployment, the preferred arrangement is usually for the
organization's OpenAI project owner or administrator to manage billing centrally.
Individual end users should not be expected to use personal payment cards unless
that is explicitly the organization's policy.

### ChatGPT subscriptions are separate

A ChatGPT Free, Plus, Pro, Business, or other ChatGPT subscription does not by
itself provide API billing or API credits.

The ChatGPT product and the OpenAI API Platform have separate billing.

Sigma Siphon uses the **OpenAI API**, not your normal ChatGPT web subscription.

### Create the API key

Once the project has usable API credit/billing:

1. Open:

   ```text
   https://platform.openai.com/api-keys
   ```

2. Make sure you are in the correct organization/project.

3. Choose **Create new secret key**.

4. Give the key a recognizable name, for example:

   ```text
   Sigma Siphon - Your Name
   ```

5. Create the key.

6. Copy it immediately when it is shown.

OpenAI does not normally show the full secret key again after creation.

If you lose the key, create a new one and revoke the lost/old key if it is no
longer needed.

### Treat the API key like a password

Never:

- put the key in `README.md`;
- paste it into Python source code;
- put it in `.env.example`;
- commit it to GitHub;
- post it in a GitHub issue;
- send it to another employee;
- put it in email or chat;
- print it on screen for troubleshooting.

Each user should use the API key assigned to them or to the approved deployment
identity for the organization's OpenAI API project.

You will paste the key once into `setup.ps1`. The setup script stores it in the
current Windows user's environment, outside the repository.

After that, normal use does not require entering the key again.

## 6. Run the one-time setup script

Make sure Miniforge Prompt is still inside the repository. You can confirm with:

```powershell
pwd
```

The path should end in:

```text
sigma-siphon
```

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

The script does the tedious work for you. It:

1. verifies that Conda exists;
2. creates an isolated environment named `sigma-siphon`;
3. installs this repository and its dependencies;
4. asks whether you want to configure OpenAI now or later;
5. if you choose yes, securely stores the key in your Windows **User** environment;
6. creates a permanent `sigma-siphon` command;
7. adds that command to your user `PATH`;
8. runs `sigma-siphon doctor`.

You may answer **No** to the OpenAI question. Setup will still complete normally.

If you answer **Yes**, the script asks:

```text
Paste your OpenAI API key:
```

Paste the key and press Enter.

Nothing will appear while you paste or type. This is intentional.

At the end you should see:

```text
SETUP COMPLETE
```

## 7. Close the terminal

This matters.

Close Miniforge Prompt completely and open a **new PowerShell window**.

Windows loads newly installed user environment variables and PATH entries when a
new process starts.

## 8. Check the installation

In the new PowerShell window:

```powershell
sigma-siphon doctor
```

A healthy setup should report the area catalog and exact boundaries as ready.

If you configured OpenAI, the LLM line should say that the LLM is configured.

If you deliberately skipped OpenAI for the free first test, the LLM line may say
`NOT READY`. That is expected; use `--no-llm` for the free test.

## 9. Run Pasig

### Completely free first test

If you did not configure an OpenAI API key, or you simply want to test the pipeline
without using any API credits, run:

```powershell
sigma-siphon run pasig --no-llm
```

This costs nothing. It runs the complete data pipeline except for hosted LLM
classification. POIs that cannot be classified confidently by deterministic rules
remain unresolved.

### Hybrid LLM test

If you configured an OpenAI API key and the associated API project has usable
free/granted credits or paid credits, run:

```powershell
sigma-siphon run pasig
```

If free/granted API credits are available, OpenAI uses those before purchased
credits. OpenAI does **not** guarantee that every new API account receives free
credits.

You do not need to activate Conda.

You do not need to `cd` into the repository.

You do not need to supply a model.

You do not need to supply an OSM endpoint.

You do not need to supply the API key again.

The permanent launcher created by `setup.ps1` automatically runs Sigma Siphon
from the repository using its isolated Python environment.

---

# Free first, paid later

You do not have to decide about paid OpenAI usage during installation.

The recommended evaluation sequence is:

```text
1. Install Sigma Siphon
       ↓
2. Free rules-only test
   sigma-siphon run pasig --no-llm
       ↓
3. Inspect the output and verify the workflow
       ↓
4. If OpenAI free/granted credits are available:
   configure a key and test the hybrid classifier
       ↓
5. Only if the organization wants continued LLM use:
   enable or purchase API credits
```

To add OpenAI later, return to the repository and rerun:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

The script detects the existing Sigma Siphon environment and updates it. It does
**not** reinstall Miniforge or create a second Sigma Siphon environment.

Once a key is installed, the command changes from:

```powershell
sigma-siphon run pasig --no-llm
```

to:

```powershell
sigma-siphon run pasig
```

There is no code change and no reinstallation required.

---

# Part II — What happens when you run it

For:

```powershell
sigma-siphon run pasig
```

Sigma Siphon performs:

```text
resolve "pasig"
      ↓
load exact Pasig boundary
      ↓
acquire named OSM POIs
      +
acquire Overture Places
      ↓
exact boundary clipping
      ↓
reconcile likely OSM/Overture duplicates
      ↓
high-confidence deterministic IO80 rules
      ↓
LLM classification for remaining POIs
      ↓
deterministic IO80 -> IO16 roll-up
      ↓
write output\pasig\
```

The primary output is:

```text
output\pasig\pois.parquet
```

The output directory is inside the repository because the installed launcher
always runs from the repository root.

---

# Part III — How to know that the LLM was really used

A successful hybrid run prints a summary such as:

```text
Complete: 8,000 POIs, 7,950 tagged, 50 unresolved
Classification: 2,100 rules + 5,850 LLM
```

Exact numbers will differ.

Sigma Siphon also writes:

```text
output\pasig\run.json
```

Its `classification` section records:

```text
llm_enabled
llm_model
llm_base_url
tagged_by_rule
tagged_by_llm
unresolved
```

To display that section:

```powershell
python -c "import json; x=json.load(open(r'output\pasig\run.json')); print(x['classification'])"
```

If normal LLM mode was requested but the API key is missing, Sigma Siphon now
**stops before downloading data**. It no longer silently produces a rules-only
result.

A rules-only run is deliberately available:

```powershell
sigma-siphon run pasig --no-llm
```

This is the recommended zero-cost first test when no OpenAI API credits are
available yet. It is also useful for explicit comparison experiments.

---

# Part IV — Normal use

After OpenAI is configured, normal hybrid use is:

```powershell
sigma-siphon run pasig
```

Before OpenAI is configured, the zero-cost rules-only test is:

```powershell
sigma-siphon run pasig --no-llm
```

Other examples:

```powershell
sigma-siphon run quezon_city
sigma-siphon run metro_manila
sigma-siphon run 1381200000
```

`1381200000` is the PSGC code for City of Pasig and resolves to the same area.

Find an area:

```powershell
sigma-siphon areas --search pasig
```

List all configured areas:

```powershell
sigma-siphon areas
```

Force source data to be downloaded again instead of using a compatible cache:

```powershell
sigma-siphon run pasig --refresh
```

---

# Part V — Updating Sigma Siphon

The setup script intentionally creates an editable installation that points to
the repository. This means repository updates immediately update the Python code.

To update:

1. Open PowerShell.
2. Go to the repository:

```powershell
cd "$HOME\Documents\GitHub\sigma-siphon"
```

3. Pull the organization's latest version:

```powershell
git pull --ff-only
```

If dependencies or setup behavior changed, rerun:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

The script is safe to rerun. It updates the existing environment instead of
creating a duplicate and keeps an already installed API key.

---

# Part VI — Troubleshooting

## `sigma-siphon` is not recognized

First close PowerShell and open a new PowerShell window.

Try:

```powershell
sigma-siphon doctor
```

If it still fails, return to the repository and rerun:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

## `conda` is not recognized during setup

Open **Miniforge Prompt**, not ordinary PowerShell, for the initial setup.

Verify:

```powershell
conda --version
```

Then return to the repository and rerun `setup.ps1`.

## Git is not recognized

Close the terminal and open it again.

Verify:

```powershell
git --version
```

If necessary, restart Windows.

## `LLM: NOT READY`

This is expected if you deliberately skipped OpenAI during the free first test.

You can still run:

```powershell
sigma-siphon run pasig --no-llm
```

When you want hosted LLM classification, rerun:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

and choose to add the OpenAI API key.

To check safely without printing the secret:

```powershell
if ($env:SIGMA_LLM_API_KEY) { "LLM key present" } else { "LLM key absent" }
```

Never run:

```text
echo $env:SIGMA_LLM_API_KEY
```

because that would print the secret on screen.

## The LLM reports authentication, permissions, billing, or quota errors

Ask the owner of your organization's OpenAI API project to verify that:

- your API key belongs to the intended project;
- the project can use the configured model;
- API billing/credits are available;
- the project has not hit a spending or usage limit.

Sigma Siphon will show a concise provider error rather than silently switching to
rules-only mode.

## An OSM request fails

The application ships with a default Overpass endpoint. Temporary provider or
internet problems can still occur.

Retry the command later:

```powershell
sigma-siphon run pasig
```

Compatible successfully downloaded source data are cached.

## I moved the repository after setup

The permanent launcher points to the repository location that existed when
`setup.ps1` ran.

Move the repository if needed, then enter its new location and rerun:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

## I want to compare LLM and rules-only classification

Hybrid production-style run:

```powershell
sigma-siphon run pasig --refresh
```

Rules-only diagnostic run:

```powershell
sigma-siphon run pasig --refresh --no-llm
```

Keep in mind that the second command deliberately leaves POIs unresolved when no
deterministic rule applies.

---

# Output files

A successful run writes:

```text
output\<area>\pois.parquet
output\<area>\run.json
output\<area>\ATTRIBUTION.txt
output\<area>\DATABASE_LICENSE.txt
```

`pois.parquet` contains canonical location and reconciliation fields, source IDs,
source-license provenance, geometry, and:

```text
io80_code
io80_label
io16_code
io16_label
tag_method
tag_confidence
tag_reason
```

`tag_method` is especially useful for evaluation:

- `rule` — classified by a deterministic high-confidence rule;
- `llm` — classified by the hosted LLM;
- `unresolved` — neither stage produced a usable classification.

IO80 is primary. IO16 is always derived deterministically from IO80.

---

# Data sources

Sigma Siphon uses only:

1. OpenStreetMap, queried through Overpass;
2. Overture Maps Places, streamed through the official `overturemaps` package.

The built-in Overpass default is:

```text
https://overpass.private.coffee/api/interpreter
```

A maintainer can override it with:

```text
SIGMA_OSM_OVERPASS_URL
```

Ordinary users should not need to do this.

---

# LLM defaults

The normal hosted classifier defaults to:

```text
model:    gpt-5.6-luna
base URL: https://api.openai.com/v1
```

Maintainers can override these without editing code:

```text
SIGMA_LLM_MODEL
SIGMA_LLM_BASE_URL
```

The only required secret is:

```text
SIGMA_LLM_API_KEY
```

`setup.ps1` stores that secret in the Windows user's environment. It is never
written into the repository.

LLM decisions are cached locally by POI evidence, endpoint, model, classification
policy, and catalog fingerprint. Compatible cached decisions are therefore reused
instead of repeatedly paying to classify identical evidence.

---

# Boundaries

`data/boundaries/areas.gpkg` contains one polygon per city or municipality and is
keyed by `psgc_code`.

`config/areas.yml` contains 1,642 canonical localities plus Metro Manila, Metro
Cebu, and Metro Davao.

A 10-digit PSGC code is accepted as an alias for its locality.

`run.json` records a fingerprint of the effective boundary used for the run.

---

# Reconciliation

OSM and Overture observations are linked only when geography and normalized names
satisfy the reconciliation thresholds.

Matches are processed strongest-first with at most one observation per source.

A two-source canonical coordinate is normally the midpoint of the two
representative points. If that midpoint would fall outside the exact configured
boundary or into a hole, Sigma Siphon deterministically falls back to an actual
in-boundary source coordinate.

---

# Licensing

Sigma Siphon software itself is proprietary.

Third-party software and acquired data retain their own licenses and terms.

OpenStreetMap data are ODbL 1.0. The project conservatively treats a reconciled
output containing OSM-derived records as an ODbL-covered database for distribution
purposes.

Every run writes:

```text
ATTRIBUTION.txt
DATABASE_LICENSE.txt
```

and retains per-record source-license provenance.

See:

```text
DATA_LICENSES.md
THIRD_PARTY_NOTICES.md
```

---

# Maintainer/developer checks

These are not required for ordinary users.

From the repository with the development dependencies installed:

```powershell
python tools\check_dependency_policy.py
python -m pytest -q
ruff check .
python -m compileall -q src tests scripts tools
git diff --check
```

The unit tests are network-free.
