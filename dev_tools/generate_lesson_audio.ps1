param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"

if ($args -contains "--force") {
    $Force = $true
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "..")
$LessonsDir = Join-Path $RepoRoot "src\lessons"
$TtsScript = Join-Path $ScriptDir "tts_to_wav_ai.py"

if (-not (Test-Path -LiteralPath $TtsScript)) {
    throw "Could not find TTS script: $TtsScript"
}

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "Could not find 'uv' on PATH."
}

function Invoke-LessonTts {
    param(
        [Parameter(Mandatory = $true)]
        [string]$InputPath,

        [Parameter(Mandatory = $true)]
        [string]$OutputPath,

        [string]$Voice
    )

    if ((Test-Path -LiteralPath $OutputPath) -and -not $Force) {
        Write-Host "SKIP existing: $OutputPath"
        return
    }

    $outputDir = Split-Path -Parent $OutputPath
    if (-not (Test-Path -LiteralPath $outputDir)) {
        New-Item -ItemType Directory -Path $outputDir | Out-Null
    }

    Write-Host "GENERATE: $OutputPath"

    $commandArgs = @(
        "run",
        "python",
        $TtsScript,
        "-i",
        $InputPath,
        "-o",
        $OutputPath,
        "--style",
        "playful",
        "--speed",
        "1.1"
    )

    if ($Voice) {
        $commandArgs += @("--voice", $Voice)
    }

    & uv @commandArgs
    if ($LASTEXITCODE -ne 0) {
        throw "TTS generation failed for: $InputPath"
    }
}

$lessonDirs = Get-ChildItem -LiteralPath $LessonsDir -Directory |
    Where-Object { $_.Name -match "^lesson_(\d+)$" } |
    Sort-Object { [int]($_.Name -replace "^lesson_", "") }

foreach ($lessonDir in $lessonDirs) {
    $lessonNumber = [int]($lessonDir.Name -replace "^lesson_", "")
    $baseName = "lesson_$lessonNumber"

    $instructionsTxt = Join-Path $lessonDir.FullName "$baseName`_instructions.txt"
    $instructionsWav = Join-Path $lessonDir.FullName "$baseName`_instructions.wav"
    $introTxt = Join-Path $lessonDir.FullName "$baseName`_intro.txt"
    $introWav = Join-Path $lessonDir.FullName "$baseName`_intro.wav"

    if (Test-Path -LiteralPath $instructionsTxt) {
        Invoke-LessonTts `
            -InputPath $instructionsTxt `
            -OutputPath $instructionsWav `
            -Voice "am_michael"
    }
    else {
        Write-Host "MISSING instructions text: $instructionsTxt"
    }

    if (Test-Path -LiteralPath $introTxt) {
        Invoke-LessonTts `
            -InputPath $introTxt `
            -OutputPath $introWav
    }
    else {
        Write-Host "MISSING intro text: $introTxt"
    }
}

Write-Host "Done."
