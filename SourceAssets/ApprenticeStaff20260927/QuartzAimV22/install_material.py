"""Compile, bind and save the clouded quartz in the current editor or commandlet."""
import unreal as u,json,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parent
BASE='/Game/Weapons/ApprenticeStaff20260927'
paths=[BASE+group+name for group in ('/Meshes/','/BarkRebuildV21/Meshes/') for name in ('SM_Staff_Base','SM_Staff_head_crystal_false')]
targets=set(paths)|{BASE+'/QuartzAimV22/Materials/M_Staff_QuartzDenseV22'}
conflicts=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_name() in targets]
if conflicts:raise RuntimeError('Unsaved target staff assets: '+', '.join(conflicts))
meshes=[u.load_asset(p) for p in paths]
if not all(meshes):raise RuntimeError('Expected existing staff meshes')
receipt={'revision':22,'complete':False,'tested':False,'preview_rendered':False,'bindings':[]}
for mesh in meshes:
    for i,slot in enumerate(mesh.static_materials):
        old=slot.material_interface
        if old and old.get_name() in ('M_Staff_QuartzMilkV20','M_Staff_QuartzDenseV22'):
            receipt['bindings'].append({'mesh':mesh.get_path_name(),'slot':i,'previous':old.get_path_name()})
if len(receipt['bindings'])!=4:raise RuntimeError('Expected exactly four quartz material slots')
previous=ROOT/'previous_bindings.json'
if not previous.exists():previous.write_text(json.dumps(receipt['bindings'],indent=2),encoding='utf-8')
m=runpy.run_path(str(ROOT/'ue_quartz_material.py'))['build_quartz_material'](rebuild=True)
receipt['material']=m.get_path_name();receipt['saved']=[m.get_path_name()]
for entry in receipt['bindings']:
    mesh=u.load_asset(entry['mesh']);mesh.set_material(entry['slot'],m)
    if not u.EditorAssetLibrary.save_loaded_asset(mesh,False):raise RuntimeError('Cannot save '+entry['mesh'])
    receipt['saved'].append(mesh.get_path_name())
    (ROOT/'install-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
receipt['complete']=True
(ROOT/'install-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('STAFF_QUARTZ_V22_SAVED '+json.dumps({'material':receipt['material'],'meshes':4,'tested':False}))
