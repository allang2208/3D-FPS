param([ValidateSet('Author','Reapply','Readback')][string]$Stage='Reapply')
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'Unreal is active. Do not overlap asset writes; use the project mutex bridge in a running editor.'}
$script=@{Author='author_and_apply.py';Reapply='reapply_after_import.py';Readback='readback.py'}[$Stage]
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
& 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' 'D:\FPS3D\FPSGAME\FPSGAME.uproject' -run=pythonscript "-script=$root\Scripts\$script" -unattended -nop4 -nosplash -nullrhi -nosound -NoLiveCoding -stdout -FullStdOutLogOutput "-abslog=$root\Receipts\$Stage-$stamp.log" *> "$root\Receipts\$Stage-$stamp.console.log"
exit $LASTEXITCODE
