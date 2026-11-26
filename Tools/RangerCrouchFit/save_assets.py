"""Save two fitted shirt bodies and three scoped trouser underlayers."""
import gc,importlib.util,json
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/RangerCrouchFit20261021';DEST='/Game/Characters/ModularOutfit20260924/RangerCrouchFit20261021'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
status=read(R/'status.json')
if status.get('state')!='ready_for_asset_save':raise RuntimeError('Current crouch-fit candidate is not cleared for game asset replacement; continue the recorded overlap diagnosis')
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    level=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if level and level.is_in_play_in_editor():raise RuntimeError('End PIE before saving the crouch waist repair')
spec=importlib.util.spec_from_file_location('ranger_crouch_native_writer',str(P/'Tools/GarmentSleeveRepair/save_assets.py'));io=importlib.util.module_from_spec(spec);spec.loader.exec_module(io)
io.R=R;io.DEST=DEST;io.receipt_path=R/'saved_assets.json';io.receipt=read(io.receipt_path) if io.receipt_path.exists() else dict(saved={},runtime_tested=False)
io.receipt['completed']=False;io.record();inputs=read(R/'inputs.json');manifest=read(R/'authored.json')
spec=importlib.util.spec_from_file_location('ranger_crouch_materials',str(P/'Tools/RangerCrouchFit/materials.py'));surfaces=importlib.util.module_from_spec(spec);spec.loader.exec_module(surfaces)
for row in manifest['records']:
    profile=row['profile'];item=row['item']
    if item=='ue_field_sweater':
        path=inputs['recipe'][item]['owner_body_meshes']['Jason'] if profile=='Owner_Jason' else inputs['recipe'][item]['rig_meshes']['Jason']
    else:path=inputs['recipe']['ue_leather_pants']['rig_meshes']['Jason']
    asset=u.load_asset(path);mats=[(surfaces.make(m.material_interface) if item=='ue_field_sweater' and i%6!=5 else m.material_interface).get_path_name() for i,m in enumerate(asset.materials)];slots=[str(m.material_slot_name) for m in asset.materials]
    desc=R/'SaveInputs'/(profile+'.json');desc.parent.mkdir(exist_ok=True);desc.write_text(json.dumps(dict(materials=mats,material_slots=slots)),encoding='utf-8')
    io.write_mesh(dict(profile=profile,item=item,file=str(desc)))
    gc.collect();u.SystemLibrary.collect_garbage()
io.receipt.update(completed=True,geometry_assets=5,scope='Ranger top waist + shirt-specific leather underlayers',runtime_tested=False);io.record()
surfaces.receipt()
print('RANGER_CROUCH_ASSETS_SAVED',len(io.receipt['saved']),flush=True)
