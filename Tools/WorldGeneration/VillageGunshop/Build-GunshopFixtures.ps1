$ErrorActionPreference = 'Stop'
$author = Join-Path $PSScriptRoot 'gunshop_furnish_author.py'
& "$PSScriptRoot/../VillageBakery/Save-BakeryLevel.ps1" -Work 'F:/FPSGAMEData/ArtProduction/VillageGunshop/Fixtures' -AuthorScript $author
