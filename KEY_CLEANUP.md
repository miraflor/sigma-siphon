# One-time cleanup for an old persisted API-key variable

An older Sigma Siphon setup script could copy an already-present process
`SIGMA_LLM_API_KEY` into the Windows User environment.

The current setup no longer does this.

If you did not intentionally configure an OpenAI key and want to remove the old
user-level variable, run:

```powershell
[Environment]::SetEnvironmentVariable("SIGMA_LLM_API_KEY", $null, "User")
```

Then close every terminal window and open a new PowerShell window.

Verify without displaying any secret:

```powershell
"Process: " + [bool][Environment]::GetEnvironmentVariable("SIGMA_LLM_API_KEY", "Process")
"User:    " + [bool][Environment]::GetEnvironmentVariable("SIGMA_LLM_API_KEY", "User")
"Machine: " + [bool][Environment]::GetEnvironmentVariable("SIGMA_LLM_API_KEY", "Machine")
```

If all three are `False`, run:

```powershell
sigma-siphon doctor
```

It should report that no API key variable is present.
