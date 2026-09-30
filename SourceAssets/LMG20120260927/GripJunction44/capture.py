import unreal as u,json,hashlib
from pathlib import Path
O=Path(__file__).parent;PROJECT=O.parents[2];BODY='/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10';WET='/Game/Weapons/LMG201/Accessories22/DA_LMG201_AttachmentWetMaterials';paths={'Body':BODY,'Wet':WET};paths.update({k:'/Game/Weapons/LMG201/Accessories22/Meshes/SM_LMG201_'+n+'_reargrip' for k,n in [('stable','stable_antislip'),('balanced','balanced'),('phantom','phantom')]});out={}
for k,p in paths.items():
 a=u.load_asset(p);r={'asset':p,'sha256':hashlib.sha256((PROJECT/'Content'/(p.removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest()};out[k]=r
 if k!='Wet':r['slots']=[{'name':str(s.material_slot_name),'material':s.material_interface.get_path_name() if s.material_interface else None} for s in (a.materials if k=='Body' else a.static_materials)]
(O/'capture.json').write_text(json.dumps(out,indent=2));print('J44_CAPTURED',len(out),flush=True)
