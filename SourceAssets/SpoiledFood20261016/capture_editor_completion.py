"""Attach the already-running project Editor build to this delivery after completion."""
import hashlib,json,shutil
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path('D:/FPS3D/FPSGAME')
OUT=Path(__file__).resolve().parent
SOURCE=ROOT/'SourceAssets/AlchemyManualPersistentLeaves20261016/20261016-210205'
log=SOURCE/'FPSGAMEEditor.log'
text=log.read_text(encoding='utf-8-sig',errors='replace')
if 'Result: Succeeded' not in text:
    raise RuntimeError('The observed Editor build has not reported success; preserve the blocked receipt.')
destination=OUT/'20261016-210205-editor-completion'
destination.mkdir(exist_ok=False)
shutil.copy2(log,destination/log.name)
binary=ROOT/'Binaries/Win64/UnrealEditor-FPSGAME.dll'
result={'attempt':destination.name,'builds':'Succeeded','targets':['FPSGAMEEditor'],
    'build_log_source':str(log.relative_to(ROOT)),
    'build_status_source':'UnrealBuildTool log Result: Succeeded',
    'build_execution':'Existing project-wide background build reused; no duplicate build launched',
    'shell_exit_code_captured_by_this_chat':False,
    'binary':str(binary.relative_to(ROOT)),
    'binary_modified_utc':datetime.fromtimestamp(binary.stat().st_mtime,timezone.utc).isoformat(),
    'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),
    'game_run':False,'editor_launched_by_this_chat':False}
(destination/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
shutil.copy2(OUT/'delivery.json',OUT/'delivery-before-editor-completion.json')
print(json.dumps(result,ensure_ascii=False))
