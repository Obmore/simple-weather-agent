$ErrorActionPreference = "Stop"

$bashCandidates = [System.Collections.Generic.List[string]]::new()

if ($env:ProgramFiles) {
    $bashCandidates.Add((Join-Path $env:ProgramFiles "Git\bin\bash.exe"))
}

if (${env:ProgramFiles(x86)}) {
    $bashCandidates.Add((Join-Path ${env:ProgramFiles(x86)} "Git\bin\bash.exe"))
}

$gitCommand = Get-Command git.exe -ErrorAction SilentlyContinue
if ($gitCommand) {
    $gitRoot = Split-Path (Split-Path $gitCommand.Source -Parent) -Parent
    $bashCandidates.Add((Join-Path $gitRoot "bin\bash.exe"))
}

$bashPath = $bashCandidates |
    Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } |
    Select-Object -First 1

if (-not $bashPath) {
    [Console]::Error.WriteLine(
        "Git Bash was not found. Install Git for Windows or run run.sh from a Bash terminal."
    )
    exit 127
}

$exitCode = 1
$wrapperErrorActionPreference = $ErrorActionPreference
$originalInputEncoding = [Console]::InputEncoding
$originalOutputEncoding = [Console]::OutputEncoding
$utf8Encoding = [System.Text.UTF8Encoding]::new($false)
Push-Location -LiteralPath $PSScriptRoot
try {
    # Native stderr carries the application's trace path and must not become a
    # terminating PowerShell error. The Bash process exit code remains authoritative.
    $ErrorActionPreference = "Continue"
    [Console]::InputEncoding = $utf8Encoding
    [Console]::OutputEncoding = $utf8Encoding
    $OutputEncoding = $utf8Encoding
    & $bashPath "./run.sh" @args
    $exitCode = $LASTEXITCODE
}
finally {
    $ErrorActionPreference = $wrapperErrorActionPreference
    [Console]::InputEncoding = $originalInputEncoding
    [Console]::OutputEncoding = $originalOutputEncoding
    Pop-Location
}

exit $exitCode
