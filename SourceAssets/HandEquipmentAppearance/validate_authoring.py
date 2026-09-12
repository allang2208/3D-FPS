"""Rebake in a temporary folder; prove accepted textures and source mesh stay intact."""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

OUT=Path(__file__).parent
BLENDER=Path('E:/Program Files/Blender Foundation/Blender 5.1/blender.exe')
SOURCE=OUT.parent/'M4HK416Replica20260910/M4_HK416_Adapted_Editable.blend'
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
before=digest(SOURCE)
textures=['T_Manny_GloveMask.png','T_Manny_LeatherRegions.png','T_Manny_StitchNormal.png',
          'T_Manny_ForearmRegions.png','T_Manny_Cuff3cmField.png','T_Manny_Cuff3cmRollNormal.png']
expected={name:digest(OUT/name) for name in textures}
# Sibling temp path preserves each script's relative source-model lookup.
with tempfile.TemporaryDirectory(prefix='.hand-appearance-check-',dir=OUT.parent) as temp:
    test=Path(temp)
    scripts=['inspect_regions.py','bake_glove_mask.py','inspect_leather.py','bake_leather_regions.py',
             'export_surface.py','bake_forearm_regions.py','bake_rolled_edge.py']
    for name in scripts:shutil.copy2(OUT/name,test/name)
    for name in scripts:
        script=test/name
        command=[str(BLENDER),'--background','--python',str(script)] if name in ('inspect_regions.py','inspect_leather.py','export_surface.py') else [sys.executable,str(script)]
        result=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',errors='replace')
        (OUT/('validate-'+name+'.log')).write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
        assert result.returncode==0,(name,result.returncode)
        print('AUTHORING_STEP_PASS',name,flush=True)
    actual={name:digest(test/name) for name in textures}
    assert expected==actual,{'expected':expected,'actual':actual}
assert digest(SOURCE)==before,'Source blend was modified'
report={'texture_sha256':actual,'byte_identical_to_accepted':True,
        'source_blend_sha256':before,'source_blend_unchanged':True,
        'scripts_exercised':scripts}
(OUT/'authoring_validation.json').write_text(json.dumps(report,indent=2))
print('HAND_APPEARANCE_AUTHORING_PASS')
