param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Remaining
)

$ErrorActionPreference = "Stop"

$Force = $false
$Select = ""
$Speed = "1.2"

$allArgs = @()
if ($Remaining) {
    $allArgs += $Remaining
}

$remainingArgs = @()
for ($index = 0; $index -lt $allArgs.Count; $index++) {
    $arg = [string]$allArgs[$index]
    if ($arg -in @("--force", "-Force", "-force")) {
        $Force = $true
        continue
    }
    if ($arg -in @("--select", "-Select", "-select")) {
        if ($index + 1 -ge $allArgs.Count) {
            throw "--select requires a lesson number or range."
        }
        $Select = [string]$allArgs[$index + 1]
        $index++
        continue
    }
    if ($arg -like "--select=*") {
        $Select = $arg.Substring("--select=".Length)
        continue
    }
    if ($arg -like "-Select=*") {
        $Select = $arg.Substring("-Select=".Length)
        continue
    }
    if ($arg -in @("--speed", "-Speed", "-speed")) {
        if ($index + 1 -ge $allArgs.Count) {
            throw "--speed requires a numeric value."
        }
        $Speed = [string]$allArgs[$index + 1]
        $index++
        continue
    }
    if ($arg -like "--speed=*") {
        $Speed = $arg.Substring("--speed=".Length)
        continue
    }
    if ($arg -like "-Speed=*") {
        $Speed = $arg.Substring("-Speed=".Length)
        continue
    }
    if ($arg -match "^--\d+(\+|-\d+)?$") {
        $Select = $arg.Substring(2)
        continue
    }
    if ($arg -match "^\d+(\+|-\d+)?$") {
        $Select = $arg
        continue
    }
    $remainingArgs += $arg
}

if ($remainingArgs.Count -gt 0) {
    throw "Unknown argument(s): $($remainingArgs -join ', ')"
}

$parsedSpeed = 0.0
if (-not [double]::TryParse($Speed, [System.Globalization.NumberStyles]::Float, [System.Globalization.CultureInfo]::InvariantCulture, [ref]$parsedSpeed)) {
    throw "Invalid --speed value '$Speed'. Use a numeric value like 1.1 or 1.25."
}
if ($parsedSpeed -le 0) {
    throw "Invalid --speed value '$Speed'. Speed must be greater than 0."
}
$Speed = $parsedSpeed.ToString("0.###", [System.Globalization.CultureInfo]::InvariantCulture)

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
        $Speed
    )

    if ($Voice) {
        $commandArgs += @("--voice", $Voice)
    }

    & uv @commandArgs
    if ($LASTEXITCODE -ne 0) {
        throw "TTS generation failed for: $InputPath"
    }
}

function Resolve-LessonSelection {
    param(
        [string]$Selection,
        [int[]]$AvailableLessons
    )

    if (-not $Selection) {
        return $AvailableLessons
    }

    if ($AvailableLessons.Count -eq 0) {
        return @()
    }

    $minLesson = ($AvailableLessons | Measure-Object -Minimum).Minimum
    $maxLesson = ($AvailableLessons | Measure-Object -Maximum).Maximum
    $selectedLessons = @()

    foreach ($part in ($Selection -split ",")) {
        $item = $part.Trim()
        if (-not $item) {
            continue
        }

        if ($item -match "^(\d+)\+$") {
            $start = [int]$Matches[1]
            $end = $maxLesson
        }
        elseif ($item -match "^(\d+)-(\d+)$") {
            $start = [int]$Matches[1]
            $end = [int]$Matches[2]
        }
        elseif ($item -match "^(\d+)$") {
            $start = [int]$Matches[1]
            $end = $start
        }
        else {
            throw "Invalid --select value '$item'. Use examples like 23, 23+, or 23-36."
        }

        if ($start -gt $end) {
            throw "Invalid --select range '$item'. Start must be less than or equal to end."
        }

        $selectedLessons += $AvailableLessons | Where-Object { $_ -ge $start -and $_ -le $end }
    }

    $selectedLessons = @($selectedLessons | Sort-Object -Unique)
    if ($selectedLessons.Count -eq 0) {
        throw "Selection '$Selection' did not match any lesson folders. Available range is $minLesson-$maxLesson."
    }
    return $selectedLessons
}

$lessonDirs = Get-ChildItem -LiteralPath $LessonsDir -Directory |
    Where-Object { $_.Name -match "^lesson_(\d+)$" } |
    Sort-Object { [int]($_.Name -replace "^lesson_", "") }

$availableLessons = @($lessonDirs | ForEach-Object { [int]($_.Name -replace "^lesson_", "") })
$selectedLessons = Resolve-LessonSelection -Selection $Select -AvailableLessons $availableLessons
$selectedLookup = @{}
foreach ($lessonNumber in $selectedLessons) {
    $selectedLookup[$lessonNumber] = $true
}

foreach ($lessonDir in $lessonDirs) {
    $lessonNumber = [int]($lessonDir.Name -replace "^lesson_", "")
    if (-not $selectedLookup.ContainsKey($lessonNumber)) {
        continue
    }

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
