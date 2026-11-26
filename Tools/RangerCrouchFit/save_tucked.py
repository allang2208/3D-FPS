"""Save the two pair-specific tucked bodies, reusing the current surface assets."""
import gc,importlib.util,json
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/RangerCrouchFit20261021/TuckedPairV2';DEST='/Game/Characters/ModularOutfit20260924/RangerCrouchFit20261021/TuckedPairV2'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    level=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if level and level.is_in_play_in_editor():raise RuntimeError('End play before saving tucked body variants')
spec=importlib.util.spec_from_file_location('ranger_tucked_writer',str(P/'Tools/GarmentSleeveRepair/save_assets.py'));io=importlib.util.module_from_spec(spec);spec.loader.exec_module(io)
io.R=R;io.DEST=DEST;io.receipt_path=R/'saved_assets.json';io.receipt=read(io.receipt_path) if io.receipt_path.exists() else dict(saved={},runtime_tested=False);io.receipt['completed']=False;io.record()
inputs=read(R/'inputs.json');authored=read(R/'authored.json')
for row in authored['records']:
    profile=row['profile'];source=inputs['recipe']['ue_field_sweater']['owner_body_meshes']['Jason'] if profile=='Owner_Jason' else inputs['recipe']['ue_field_sweater']['rig_meshes']['Jason'];asset=u.load_asset(source)
    desc=R/'SaveInputs'/(profile+'.json');desc.parent.mkdir(exist_ok=True);desc.write_text(json.dumps(dict(materials=[m.material_interface.get_path_name() for m in asset.materials],material_slots=[str(m.material_slot_name) for m in asset.materials])),encoding='utf-8')
    io.write_mesh(dict(profile=profile,item='ue_field_sweater',file=str(desc)));gc.collect();u.SystemLibrary.collect_garbage()
io.receipt.update(completed=True,geometry_assets=2,materials_preserved=True,runtime_tested=False);io.record();print('RANGER_TUCKED_SAVED two paired shirt bodies',flush=True)
