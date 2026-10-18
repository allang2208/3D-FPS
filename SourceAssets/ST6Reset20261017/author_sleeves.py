"""Restore the initial 2026-10-06 sleeve surface on every existing native rig."""
import copy,hashlib,importlib.util,json,shutil
from pathlib import Path
import numpy as np
O=Path(__file__).parent;R=O.parents[1];OLD=O.parent/'BenelliM4Super9020261006'
OUT=O/'Authored';OUT.mkdir(exist_ok=True)
spec=importlib.util.spec_from_file_location('st6_native_transport',O.parent/'HardKnuckleRepair20261017/native_transport.py')
transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)
transport.Y=OUT;transport.ITEM='ue_st6_sleeves'
source=json.loads((OLD/'EquipmentSources/source_shirt.json').read_text())
canonical=transport.fit(source,{n:np.linalg.inv(m) for n,m in transport.warp.items()},
    lambda n:transport.target_name(transport.old_name(n),transport.REF_BONES),transport.ref,'M4',transport.ITEM)
transport.derive(canonical)
# Preserve the source artist's exact geometry and binding on Super90/M870.
native={k:copy.deepcopy(source[k]) for k in ('positions','triangles','normals','uv','weights','triangle_materials','materials','material_slots')}
native.update(profile='Super90',item=transport.ITEM,binding_source=transport.source_rig['source'])
(OUT/'Super90_ue_st6_sleeves.json').write_text(json.dumps(native,separators=(',',':')))
cfg=json.loads((R/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
manifest=[]
for profile,asset in cfg['items'][transport.ITEM]['rig_meshes'].items():
    file=OUT/(profile+'_'+transport.ITEM+'.json');d=json.loads(file.read_text())
    original=OLD/'EquipmentAuthored'/file.name;backup=O/'Before/EquipmentAuthored'/file.name
    backup.parent.mkdir(exist_ok=True)
    if not backup.exists():shutil.copy2(original,backup)
    manifest.append(dict(profile=profile,asset=asset,file=str(file),vertices=len(d['positions']),triangles=len(d['triangles']),
                         previous_source_sha256=hashlib.sha256(original.read_bytes()).hexdigest()))
(O/'sleeve_manifest.json').write_text(json.dumps(manifest,indent=2))
print('ST6_ORIGINAL_SLEEVES_AUTHORED',len(manifest),flush=True)
