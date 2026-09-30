"""Restore only this run's oversized stable-grip intermediate after failed import."""
from pathlib import Path
import hashlib,json,shutil,subprocess
O=Path(__file__).parent
receipt=json.loads((O/'delivery.json').read_text())
name='/Game/Weapons/LMG201/Accessories22/Meshes/SM_LMG201_stable_antislip_reargrip'
path=O.parents[2]/'Content/Weapons/LMG201/Accessories22/Meshes/SM_LMG201_stable_antislip_reargrip.uasset'
saved=receipt['saved'].get(name)
if saved:
    active=subprocess.check_output(['powershell','-NoProfile','-Command',"@(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue).Count"],text=True).strip()
    if active!='0':raise RuntimeError('UE active; current asset retained')
    if hashlib.sha256(path.read_bytes()).hexdigest()!=saved['sha256']:raise RuntimeError('Changed current asset retained')
    before=Path(receipt['backups'][name]['bytes'])
    if hashlib.sha256(before.read_bytes()).hexdigest()!=receipt['backups'][name]['sha256']:raise RuntimeError('Backup changed')
    shutil.copy2(before,path)
    receipt['replaced_authoring_intermediate']={name:saved}
    del receipt['saved'][name]
    (O/'delivery.json').write_text(json.dumps(receipt,indent=2))
    print('J44_INTERMEDIATE_RESTORED')
