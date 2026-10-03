param([string]$TaskScript = 'D:/FPS3D/FPSGAME/Tools/BlindSupplicantM07/import_assets.py')
$ErrorActionPreference = 'Stop'
$taskProject = 'D:/FPS3D/FPSGAME/FPSGAME.uproject'
$taskCmd = 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
while ($true) {
    $taskGuiEditors = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object { $_.CommandLine.Replace('\','/').IndexOf($taskProject,[StringComparison]::OrdinalIgnoreCase) -ge 0 })
    $taskInteractiveEditors = @($taskGuiEditors | Where-Object { $_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -notmatch '(?i)(?:^|\s)-game(?:\s|$)' })
    if ($taskInteractiveEditors.Count -gt 0) { throw 'An editor is running; M07 packages were left untouched. Use the existing batch bridge for loaded packages.' }
    if ($taskGuiEditors.Count -eq 0) { break }
    Write-Output 'Waiting for existing FPSGAME command/game processes to release loaded packages naturally.'
    foreach ($taskGuiEditor in $taskGuiEditors) {
        try { [Diagnostics.Process]::GetProcessById($taskGuiEditor.ProcessId).WaitForExit() } catch [ArgumentException] { }
    }
}
$taskLog = 'D:/FPS3D/FPSGAME/Saved/Logs/M07Import-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.log'
$taskArguments = '"' + $taskProject + '" -run=pythonscript -script="' + $TaskScript + '" -unattended -nop4 -nosplash -nosound -nullrhi -multiprocess -DDC=InstalledNoZenLocalFallback -abslog="' + $taskLog + '"'
$taskProcess = Start-Process -FilePath $taskCmd -ArgumentList $taskArguments -WindowStyle Hidden -PassThru
Write-Output ('M07 production commandlet PID=' + $taskProcess.Id + ' log=' + $taskLog)
$taskProcess.WaitForExit()
if ($taskProcess.ExitCode -ne 0) { throw ('M07 production commandlet exited ' + $taskProcess.ExitCode + '. Read production log: ' + $taskLog) }
$taskReceipt = if ([IO.Path]::GetFileName($TaskScript) -eq 'import_full_reference_gait_v21.py') {
    'SourceAssets/BlindSupplicantM07Meshy20261001/FullReferenceGaitV21/ue_full_reference_gait_delivery_v21.json'
} elseif ([IO.Path]::GetFileName($TaskScript) -eq 'import_palm_arm_motion_v20.py') {
    'SourceAssets/BlindSupplicantM07Meshy20261001/PalmArmMotionV20/ue_palm_arm_delivery_v20.json'
} elseif ([IO.Path]::GetFileName($TaskScript) -eq 'import_video_locomotion_v19.py') {
    'SourceAssets/BlindSupplicantM07Meshy20261001/VideoLocomotionV19/ue_video_locomotion_delivery_v19.json'
} elseif ([IO.Path]::GetFileName($TaskScript) -eq 'repair_navigation_load_v18.py') {
    'SourceAssets/BlindSupplicantM07Meshy20261001/BodyMotionV18/NavigationLoadRepair/ue_navigation_load_repair_v18.json'
} elseif ([IO.Path]::GetFileName($TaskScript) -eq 'repair_locomotion_export_v18.py') {
    'SourceAssets/BlindSupplicantM07Meshy20261001/BodyMotionV18/ue_locomotion_export_repair_v18.json'
} elseif ([IO.Path]::GetFileName($TaskScript) -eq 'import_body_motion_v18.py') {
    'SourceAssets/BlindSupplicantM07Meshy20261001/BodyMotionV18/ue_body_motion_delivery_v18.json'
} elseif ([IO.Path]::GetFileName($TaskScript) -eq 'import_leg_joints_v17.py') {
    'SourceAssets/BlindSupplicantM07Meshy20261001/LegJointsV17/ue_leg_joints_delivery_v17.json'
} elseif ([IO.Path]::GetFileName($TaskScript) -eq 'import_arm_sweep_v16.py') {
    'SourceAssets/BlindSupplicantM07Meshy20261001/ArmSweepV16/ue_arm_sweep_delivery_v16.json'
} elseif ([IO.Path]::GetFileName($TaskScript) -eq 'import_motion_recovery_v15.py') {
    'SourceAssets/BlindSupplicantM07Meshy20261001/MotionRecoveryV15/ue_motion_recovery_delivery_v15.json'
} elseif ([IO.Path]::GetFileName($TaskScript) -eq 'import_sweep_magic_v14.py') {
    'SourceAssets/BlindSupplicantM07Meshy20261001/CombatMagicV14/ue_combat_magic_delivery_v14.json'
} elseif ([IO.Path]::GetFileName($TaskScript) -eq 'import_original_recovery_v13.py') {
    'SourceAssets/BlindSupplicantM07Meshy20261001/RecoveryOriginalV13/ue_delivery_v13.json'
} elseif ([IO.Path]::GetFileName($TaskScript) -eq 'import_running_collision_v12.py') {
    'SourceAssets/BlindSupplicantM07Meshy20261001/RunningCollisionV12/ue_running_collision_delivery_v12.json'
} elseif ([IO.Path]::GetFileName($TaskScript) -eq 'import_original_hands_v11.py') {
    'SourceAssets/BlindSupplicantM07Meshy20261001/RecoveryHandsV11/ue_hand_arm_delivery_v11.json'
} elseif ([IO.Path]::GetFileName($TaskScript) -eq 'import_locomotion_v10.py') {
    'SourceAssets/BlindSupplicantM07Meshy20261001/LocomotionV10/ue_locomotion_delivery_v10.json'
} elseif ([IO.Path]::GetFileName($TaskScript) -eq 'import_original_gills_v09.py') {
    'SourceAssets/BlindSupplicantM07Meshy20261001/RecoveryOriginalV09/ue_gill_delivery_v09.json'
} elseif ([IO.Path]::GetFileName($TaskScript) -eq 'import_original_v08.py') {
    'SourceAssets/BlindSupplicantM07Meshy20261001/RecoveryOriginalV08/ue_original_delivery_v08.json'
} elseif ([IO.Path]::GetFileName($TaskScript) -eq 'repair_navigation_original_v08.py') {
    'SourceAssets/BlindSupplicantM07Meshy20261001/RecoveryOriginalV08/navigation/navigation_delivery_original_v08.json'
} elseif ([IO.Path]::GetFileName($TaskScript) -eq 'import_original_v07.py') {
    'SourceAssets/BlindSupplicantM07Meshy20261001/RecoveryOriginalV07/ue_original_delivery_v07.json'
} elseif ([IO.Path]::GetFileName($TaskScript) -eq 'import_original_v06.py') {
    'SourceAssets/BlindSupplicantM07Meshy20261001/RecoveryOriginalV06/ue_original_delivery_v06.json'
} elseif ([IO.Path]::GetFileName($TaskScript) -eq 'import_anatomy_v05.py') {
    'SourceAssets/BlindSupplicantM07Meshy20261001/RecoveryV05/ue_anatomy_delivery_v05.json'
} elseif ([IO.Path]::GetFileName($TaskScript) -eq 'import_anatomy_v04.py') {
    'SourceAssets/BlindSupplicantM07Meshy20261001/RecoveryV04/ue_anatomy_delivery_v04.json'
} elseif ([IO.Path]::GetFileName($TaskScript) -eq 'rollback_v03_read_frames.py') {
    'SourceAssets/BlindSupplicantM07Meshy20261001/RecoveryV04/rollback_v03_receipt.json'
} elseif ([IO.Path]::GetFileName($TaskScript) -eq 'import_anatomy_v03.py') {
    'SourceAssets/BlindSupplicantM07Meshy20261001/Authoring/AnatomyV03/ue_anatomy_delivery_v03.json'
} elseif ([IO.Path]::GetFileName($TaskScript) -eq 'import_unified_frame_v02.py' -or [IO.Path]::GetFileName($TaskScript) -eq 'import_fragment_repair_v02.py') {
    'SourceAssets/BlindSupplicantM07Meshy20261001/Authoring/FragmentRepairV02/ue_fragment_repair_delivery.json'
} else { 'SourceAssets/BlindSupplicantM07Meshy20261001/ue_delivery.json' }
Write-Output ('M07 production commandlet ended. Save receipt=' + $taskReceipt + '. Log=' + $taskLog)
