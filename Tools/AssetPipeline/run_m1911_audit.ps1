param(
    [string]$ProjectRoot='D:/FPS3D/FPSGAME',
    [string]$Editor='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe',
    [string]$RunId=(Get-Date -Format 'yyyyMMddHHmmss'),
    [switch]$LoadExisting,
    [switch]$MeasureBounds
)
$ErrorActionPreference='Stop'
if($RunId -notmatch '^[A-Za-z0-9_-]{1,40}$'){throw 'RunId must be a simple isolated save label'}
$m1911Log=Join-Path $ProjectRoot ('Saved/M1911Audit/'+$RunId+$(if($LoadExisting){'-load.log'}else{'-run.log'}))
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $m1911Log) | Out-Null
$m1911Args=@(('"'+$ProjectRoot+'/FPSGAME.uproject"'),'/Game/Weapons/M4InfimaRigV4/Preview/L_M4RigValidation',
    '-game','-windowed','-RenderOffscreen','-ResX=1280','-ResY=720','-ForceRes','-unattended','-nosplash','-nosound',
    '-M1911Audit',('-ColdSteelProfile=M1911Audit_'+$RunId),('-abslog="'+$m1911Log+'"'),
    '-ExecCmds="t.MaxFPS 30,r.Streaming.PoolSize 512"')
if($LoadExisting){$m1911Args+='-M1911AuditLoad'}
if($MeasureBounds){$m1911Args+='-M1911MeasureBounds'}
$m1911Started=Get-Date
$m1911Process=Start-Process -FilePath $Editor -ArgumentList $m1911Args -PassThru -WindowStyle Hidden
$m1911Process.WaitForExit()
Write-Output "M1911 audit exit=$($m1911Process.ExitCode) log=$m1911Log"
$m1911Result=Join-Path $ProjectRoot ('Saved/M1911Audit/ColdSteel_M1911Audit_'+$RunId+'/'+$(if($LoadExisting){'load-result.txt'}else{'result.txt'}))
if(!(Test-Path -LiteralPath $m1911Result) -or (Get-Item -LiteralPath $m1911Result).LastWriteTime -lt $m1911Started){throw 'No fresh audit receipt; see process log'}
if((Get-Content -LiteralPath $m1911Result -First 1) -notmatch '^checks=\d+ failures=0$'){throw "Audit reported failures: $m1911Result"}
exit 0
