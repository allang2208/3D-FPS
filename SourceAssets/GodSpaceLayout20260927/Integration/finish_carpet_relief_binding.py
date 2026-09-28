"""Resume only the density/binding step after the V2 shader assets were saved."""
import json,runpy
from pathlib import Path
import unreal as u
root=Path(__file__).parent
base='/Game/Props/GodSpaceLayout20260927'
receipt=root/'Receipts/navy-carpet-saved.json'
report=json.loads(receipt.read_text(encoding='utf8'))
expected=[base+'/Materials/M_GodSpaceNavyCarpet.M_GodSpaceNavyCarpet',base+'/Materials/MI_GodSpaceNavyCarpet.MI_GodSpaceNavyCarpet']
if not all(p in report['saved'] for p in expected):raise RuntimeError('Material production did not finish')
meshpath=base+'/Meshes/SM_GodSpaceStructure'
if meshpath in {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:raise RuntimeError('Preserve unsaved structure')
mesh=u.load_asset(meshpath);instance=u.load_asset(expected[1]);changed=[]
for i,slot in enumerate(mesh.get_editor_property('static_materials')):
    if str(slot.get_editor_property('imported_material_slot_name')).lower()=='blue grey stone inlay':mesh.set_material(i,instance);changed.append(i)
if len(changed)!=1:raise RuntimeError('Unexpected carpet slots')
report['previous_streaming_density']=runpy.run_path(str(root/'build_navy_carpet.py'))['configure_carpet_density'](mesh)
if not u.EditorLoadingAndSavingUtils.save_packages([mesh.get_outermost()],False):raise RuntimeError('Structure save failed')
report['saved'].append(mesh.get_path_name())
report.update(complete=True,revision='relief-v2',shader_compile_errors=[],material=instance.get_path_name(),changed_slots=changed,
    near_texture_lookups_max=14,far_texture_lookups=3,unique_textures=4,max_texture_size=2048,
    source_variant='Carpet 01 with normal-derived registered relief',added_triangles=0,added_material_slots=0,
    parallax_steps=8,parallax_refine_steps=2,relief_depth_cm=.38,relief_fade_cm=[220,650],
    streaming_density_cm=90.0,added_translucent_layers=0,simulation=False,
    existing_marble_and_brass_preserved=True,blue_stone_underside_preserved=True,map_changed=False,
    fab_asset_downloaded=False,library_source='Existing /Game/SubstrateMaterials; source library assets unchanged',
    shader_build_log='navy-carpet-relief-v2-build-02-engine.log',binding_resume=True)
receipt.write_text(json.dumps(report,indent=2),encoding='utf8')
print('CARPET_RELIEF_BINDING_SAVED '+json.dumps(report))
