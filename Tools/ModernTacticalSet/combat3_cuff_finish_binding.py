"""Remove inherited finger influence from the actual forearm-only sleeve meshes."""
import sys,json,hashlib,shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from combat3_cuff_solver import C,R,read,write,strip_sleeve_finger_weights
report={};promoted=read(C/'promoted.json') if (C/'promoted.json').exists() else None
for row in read(R/'fp-authored.json')['rows']:
    file=C/'Authored'/('shirt_fp_'+row['rig']+'.json');d=read(file);result=strip_sleeve_finger_weights(d)
    if result['vertices']:
        backup=C/'BeforeFingerBinding'/file.name;backup.parent.mkdir(exist_ok=True)
        if not backup.exists():shutil.copy2(file,backup)
        write(file,d);target=R/'Authored'/file.name;shutil.copy2(file,target)
        if promoted:
            entry=next(r for r in promoted['sources'] if Path(r['file']).name==file.name);entry['sha256']=hashlib.sha256(target.read_bytes()).hexdigest()
    report[row['rig']]=result
if promoted:write(C/'promoted.json',promoted)
write(C/'Review/sleeve-finger-binding.json',report)
print('SLEEVE_FINGER_BINDING_REMOVED',report,flush=True)
