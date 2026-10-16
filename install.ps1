# Install the skills in this repo.
#   .\install.ps1                                   link skills\* into ~\.claude\skills
#   .\install.ps1 -Project <path> -ProjectName <n>  link project-skills\<n>\* into <path>\.claude\skills
#   .\install.ps1 -Zip                              write dist\<skill>.zip for claude.ai upload
# Links are directory junctions, which need no admin rights.
param(
    [string]$Project,
    [string]$ProjectName,
    [switch]$Zip
)
$ErrorActionPreference = 'Stop'
$repo = $PSScriptRoot

function Link-Skills($sourceDir, $targetDir) {
    New-Item -ItemType Directory -Force -Path $targetDir | Out-Null
    Get-ChildItem -Directory $sourceDir | ForEach-Object {
        $dest = Join-Path $targetDir $_.Name
        if (Test-Path $dest) {
            Write-Host "skip  $($_.Name): $dest already exists (move it away, then rerun)"
        } else {
            New-Item -ItemType Junction -Path $dest -Target $_.FullName | Out-Null
            Write-Host "link  $($_.Name) -> $dest"
        }
    }
}

if ($Zip) {
    $dist = Join-Path $repo 'dist'
    New-Item -ItemType Directory -Force -Path $dist | Out-Null
    $folders = @(Get-ChildItem -Directory (Join-Path $repo 'skills'))
    $folders += Get-ChildItem -Directory (Join-Path $repo 'project-skills') | ForEach-Object { Get-ChildItem -Directory $_.FullName }
    foreach ($f in $folders) {
        $out = Join-Path $dist "$($f.Name).zip"
        Compress-Archive -Path $f.FullName -DestinationPath $out -Force
        Write-Host "zip   $out"
    }
} elseif ($Project) {
    if (-not $ProjectName) { throw 'Pass -ProjectName, the folder under project-skills\ to install.' }
    Link-Skills (Join-Path $repo "project-skills\$ProjectName") (Join-Path $Project '.claude\skills')
} else {
    Link-Skills (Join-Path $repo 'skills') (Join-Path $HOME '.claude\skills')
}
