"""Record only this iteration's integration delta, never the shared file baseline."""
import ast,difflib,hashlib,json
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1]
paths=['Source/FPSGAME/Weapons/VerticalGripAnimationFamily.h','Source/FPSGAME/Weapons/AKMAttachmentVisual.h','Config/DefaultGame.ini']
patch=[];baseline=[]
for name in paths:
 old=(O/'IntegrationBaseline'/name).read_bytes();new=(P/name).read_bytes()
 patch.extend(difflib.unified_diff([x+'\n' for x in old.decode('utf-8-sig').splitlines()],[x+'\n' for x in new.decode('utf-8-sig').splitlines()],fromfile='a/'+name,tofile='b/'+name,n=2))
 baseline.append({'path':name,'before_sha256':hashlib.sha256(old).hexdigest(),'after_sha256':hashlib.sha256(new).hexdigest()})
(O/'runtime-integration.patch').write_text(''.join(patch),encoding='utf-8',newline='\n')
(O/'integration_manifest.json').write_text(json.dumps(baseline,indent=2))
scripts=sorted(O.glob('*.py'))
for p in scripts:ast.parse(p.read_text(encoding='utf-8-sig'),filename=str(p))
files=scripts+[O/'run.ps1',O/'README.md',O/'runtime-integration.patch',O/'integration_manifest.json',O/'donor_export.json',O/'retarget_direction_audit.json',O/'opening_comparison.json']
files += [O/'Final'/n for n in ['build.json','asset_validation.json','source_validation.json','validation.json','delivery_manifest.json']]
files += [O/f'Final/{w}/vertical/geometry.json' for w in ['m4','akm']]
files += [P/'skills/ue5-fps-arms-animation/references'/n for n in ['vertical-front-grasp.md','github-grasp-donor.md']]
assert all(p.is_file() for p in files)
(O/'publication_files.txt').write_text('\n'.join(p.relative_to(P).as_posix() for p in files)+'\n')
print('AUTHOR_SCRIPTS_CHECKED',len(scripts),'PUBLICATION_FILES',len(files))
