$ErrorActionPreference='Stop'
$blenderExe='E:/Program Files/Blender Foundation/Blender 5.1/blender.exe'
& $blenderExe --factory-startup -b -t 4 --python (Join-Path $PSScriptRoot 'repair_authored.py') --python (Join-Path $PSScriptRoot 'apply_entry_clearance.py') --python (Join-Path $PSScriptRoot 'apply_arm_reference.py') --python (Join-Path $PSScriptRoot 'triangle_contact_probe.py') --python (Join-Path $PSScriptRoot 'probe_body.py') --python (Join-Path $PSScriptRoot 'verify_contract.py')
if ($LASTEXITCODE -ne 0) { throw 'Candidate authoring failed' }
