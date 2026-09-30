"""Read the active cloth-box consumers for this scoped authoring revision."""
import unreal as u,json,hashlib
from pathlib import Path
O=Path(__file__).parent;PROJECT=O.parents[2];(O/'Inputs').mkdir(exist_ok=True)
paths={'Body':'/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10','Props':'/Game/Weapons/LMG201/ClothFeed33/Parts/SK_LMG201_Cloth33_Props','Wet':'/Game/Weapons/LMG201/Accessories22/DA_LMG201_AttachmentWetMaterials'};out={}
for key,path in paths.items():
    a=u.load_asset(path)
    if not a:raise RuntimeError('Missing '+path)
    row={'asset':path,'sha256':hashlib.sha256((PROJECT/'Content'/(path.removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest()};out[key]=row
    if key=='Wet':continue
    row['slots']=[{'name':str(s.material_slot_name),'material':s.material_interface.get_path_name() if s.material_interface else None} for s in a.materials]
    if key=='Props':
        ex=u.AssetExportTask();ex.object=a;ex.filename=str(O/'Inputs/CurrentProps.fbx');ex.automated=True;ex.prompt=False;ex.replace_identical=True;ex.options=u.FbxExportOption();ex.options.level_of_detail=False;ex.options.collision=False;ex.options.export_morph_targets=False;ex.options.bake_material_inputs=u.FbxMaterialBakeMode.DISABLED
        if not u.Exporter.run_asset_export_task(ex):raise RuntimeError('Cannot export props')
(O/'capture.json').write_text(json.dumps(out,indent=2));print('C45_CAPTURED',len(out),flush=True)
