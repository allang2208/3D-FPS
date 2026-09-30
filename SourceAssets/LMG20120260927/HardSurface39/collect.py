import unreal as u,json,hashlib
from pathlib import Path
O=Path(__file__).parent;P=O.parents[2];(O/'Exports').mkdir(exist_ok=True);out={}
targets={'Body':'/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10','BipodBase':'/Game/Weapons/LMG201/Production20260927/SM_LMG201_BipodBase','BipodLegA':'/Game/Weapons/LMG201/Production20260927/SM_LMG201_BipodLegA','BipodLegB':'/Game/Weapons/LMG201/Production20260927/SM_LMG201_BipodLegB'}
for key,path in targets.items():
 a=u.load_asset(path)
 if not a:raise RuntimeError('Missing '+path)
 slots=a.materials if isinstance(a,u.SkeletalMesh) else a.static_materials
 out[key]={'asset':path,'sha256':hashlib.sha256((P/'Content'/(path.removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest(),'slots':[{'slot':str(s.material_slot_name),'material':s.material_interface.get_path_name() if s.material_interface else None} for s in slots]}
 ex=u.AssetExportTask();ex.object=a;ex.filename=str(O/'Exports'/('Before_'+key+'.fbx'));ex.automated=True;ex.prompt=False;ex.replace_identical=True;ex.options=u.FbxExportOption();ex.options.level_of_detail=False;ex.options.export_morph_targets=False;ex.options.bake_material_inputs=u.FbxMaterialBakeMode.DISABLED
 if not u.Exporter.run_asset_export_task(ex):raise RuntimeError('Cannot export '+path)
out['Wet']={'asset':'/Game/Weapons/LMG201/Accessories22/DA_LMG201_AttachmentWetMaterials'}
out['Wet']['sha256']=hashlib.sha256((P/'Content/Weapons/LMG201/Accessories22/DA_LMG201_AttachmentWetMaterials.uasset').read_bytes()).hexdigest()
(O/'capture.json').write_text(json.dumps(out,indent=2));print('R39_CAPTURED',flush=True)
