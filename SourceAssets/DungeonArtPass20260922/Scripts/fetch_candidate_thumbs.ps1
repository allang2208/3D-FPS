param(
    [string]$Token = $env:SKETCHFAB_TOKEN,
    [string]$OutDir = 'D:\FPS3D\_sketchfab_goddess\artpass\thumbs',
    [string]$Proxy = ''
)
# Downloads preview thumbnails for the shortlisted candidates so the fit can be judged
# visually instead of from names alone.
$ErrorActionPreference = 'Stop'
if (-not $Token) { throw 'Token required' }
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$curl = Join-Path $env:SystemRoot 'System32\curl.exe'
$proxyArgs = @()
if ($Proxy) { $proxyArgs = @('-x', $Proxy) }
$auth = "Authorization: Token $Token"

$picks = [ordered]@{
    '01_CratesAndBarrels'      = '5ae3c72285474862a89d69c2f2ad2246'
    '02_JerryCans'             = '01fea903b3464194a4d0eec7d9a1a5d1'
    '03_AmmoCrate'             = '6a834e917e4f4194a29e9f66e6915d8a'
    '04_RustedBucket'          = 'ca0755cc9e2d4dfd920e51b6ca9e1243'
    '05_OilBarrel'             = 'c879b42696634752892c7f5e747c4ae4'
    '06_CrushedOilDrum'        = 'b1394e96fb1b4ebdb96a76524224358f'
    '07_FireExtinguisherScan'  = '70a4fdec06c64372ba3a96ae49257ce1'
    '08_HangarPipes'           = '94889355601e4dbb90b14d460407ac96'
    '09_IndustrialPipePack'    = 'a10a6011334e4d11a7023d67705ac1d4'
    '10_PipeWheelScan'         = '5b8d5bb5ecdd4d8a80f71eabd4d08249'
    '11_ValveWheelScan'        = '0264beb63c214817be93b57b23b6e6b3'
    '12_BreakerPanelBox'       = '4b12b4e00fc14f95beb55d7016eaf28d'
    '13_CableSpool'            = '22ddb8e02f944fb7b5662f14fdc50e5e'
    '14_ChainlinkFence'        = '777e50cd6e5d4db99d70bf7b20370f7a'
    '15_HangingCeilingLights'  = '0a84b3898bcc4ec4be6aa0f5b638fcbe'
    '16_FluorescentLamp'       = 'af6ccbb048594b848f2af232307cab60'
    '17_ShipWindlass'          = 'c16e5ae35a0249b882f9c18904cd40a6'
    '18_Pallets'               = '18fbfb830f294b44aa8dff530cc2ea12'
    '19_BrokenMedievalColumn'  = '962ed874cf9a4db5bc5405584c29b664'
    '20_GreekColumnDebris'     = '1ad492ad20164a108d6d37c83adba223'
    '21_AncientRuins'          = '105c85f4668245208fe71cac4861cf8c'
    '22_StoneArchPillars'      = 'a1a8e633c9aa40c08b4d2a0631ac61d2'
    '23_GardenUrn'             = 'c0c7f5fa24704a23b0f3cbdd689b8176'
    '24_NeckAmphoraCC0'        = '0bb2525bdd734bf69d5a7b2b051928ad'
    '25_SarcophagusCC0'        = '25391e3700c144d29649103d222c7efc'
    '26_AmenhotepFragmentCC0'  = 'e21e8e13aab64a17b92c6ec4daca7d39'
    '27_RomanPotteryWorkshop'  = '43246b1645584eada1409a2908b7ba09'
    '28_LionCorbel'            = '00a1f9e2cff54d07995f091693cc07f2'
    '29_CobwebsPack'           = '2dd4798676d84bc7af5d2a8f5834563a'
    '30_AnimalSkulls'          = '2938b8237531482d9750ce2717fbe099'
    '31_BonePile'              = '5ec580b41a934cea86d4297980d1378f'
    '32_AntiqueCandleHolder'   = 'cce3a987bda2410993fbc7a24db70eb5'
    '33_RailroadOilLamps'      = '62f6c24afc4d438fa0742fe0294bee87'
    '34_RustyOilLantern'       = 'de28cba29f58414c914298f648da90bf'
    '35_GravelPile'            = 'd39e598e7c2d4a03b649e61d8952f692'
    '36_RubbleLowPoly'         = '9a180893d6454f68a764e62be3fc5c92'
    '37_ApocalypseExtinguisher'= 'b163e81ebaa74397b6ccc4ec7e50722b'
    '38_SandPileScan'          = '7a7533e1ecab4b1d96da55cc3ad9ad98'
}

$index = @()
foreach ($k in $picks.Keys) {
    $uid = $picks[$k]
    $dest = Join-Path $OutDir "$k.jpg"
    $meta = Join-Path $OutDir "$k.json"
    if (-not (Test-Path $dest)) {
        & $curl -s --fail --max-time 45 @proxyArgs -H $auth -H 'Accept: application/json' `
            -o $meta "https://api.sketchfab.com/v3/models/$uid" 2>$null
        if ($LASTEXITCODE -ne 0) { Write-Output "FAIL meta $k"; continue }
        $d = Get-Content $meta -Raw -Encoding UTF8 | ConvertFrom-Json
        $thumb = ($d.thumbnails.images | Sort-Object width | Select-Object -Last 1).url
        & $curl -s --fail --max-time 45 @proxyArgs -o $dest $thumb 2>$null
        if ($LASTEXITCODE -ne 0) { Write-Output "FAIL thumb $k"; continue }
        $index += [pscustomobject]@{
            key = $k; name = $d.name; uid = $uid; faces = $d.faceCount
            license = $d.license.label; user = $d.user.displayName
            likes = $d.likeCount; textures = $d.textureCount
            download_size_mb = if ($d.downloadableSize) { [math]::Round($d.downloadableSize / 1MB, 1) } else { $null }
            url = $d.viewerUrl
        }
    }
}
$index | Export-Csv (Join-Path $OutDir 'index.csv') -NoTypeInformation -Encoding UTF8
$index | ForEach-Object { "{0,-26} {1,-30} {2,8} tris {3,5} likes  tex={4}" -f $_.key, $_.name, $_.faces, $_.likes, $_.textures }
Write-Output ("downloaded: {0}" -f $index.Count)
