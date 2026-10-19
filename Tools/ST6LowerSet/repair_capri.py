"""Tailor the existing cloth source; keep its native skin patches unscaled."""
import json,sys,runpy
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/SmokeGreyCapri20261004'
sys.path.insert(0,str(P/'Tools/SmokeGreyCapri'))
from waist_fit import repair
p=R/'Jason_SmokeGreyCapri_Garment.json';d=repair(json.loads(p.read_text()));p.write_text(json.dumps(d,separators=(',',':')),encoding='utf-8')
runpy.run_path(str(P/'Tools/SmokeGreyCapri/prepare_runtime.py'),run_name='__main__')
# Keep the original procedural authoring route fitted on subsequent rebuilds.
p=P/'Tools/SmokeGreyCapri/author_geometry.py';text=p.read_text()
if 'from waist_fit import fitted_torso' not in text:
    text=text.replace('import importlib.util,json,math','import importlib.util,json,math,sys')
    at=text.index('def torso(z,t,offset=0):');end=text.index('\ndef leg(',at)
    text=text[:at]+"sys.path.insert(0,str(P/'Tools/SmokeGreyCapri'))\nfrom waist_fit import fitted_torso\ndef torso(z,t,offset=0):\n    return fitted_torso(z,t,offset)\n"+text[end:]
    text=text.replace("data.update(source=native['source']", "data.update(source=native['source']")
    text=text.replace('SmokeGreyCapri20261004 CrotchSeamFix20261005: native Jason;', 'SmokeGreyCapri20261004 CrotchSeamFix20261005 NativeWaistFit20261018: native Jason;')
    p.write_text(text,encoding='utf-8')
print('CAPRI_WAIST_TAILORING_AUTHORED',flush=True)
