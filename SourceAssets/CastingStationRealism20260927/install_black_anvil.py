"""Save a dedicated matte black anvil material and bind only the anvil sections."""
from pathlib import Path
import datetime
import importlib
import json
import sys
import unreal as u

root=Path(u.Paths.project_dir())
here=root/'SourceAssets/CastingStationRealism20260927'
sys.path.insert(0,str(here))
import materials
importlib.reload(materials)

destination='/Game/Props/CastingStation20260926'
meshes=[destination+'/SM_CastingStation',destination+'/SM_CastingAnvil']
target=materials.DEST+'/M_BlackenedAnvil'
dirty={str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty.intersection(set(meshes)|{target}):
    raise RuntimeError('Unsaved anvil target edits; preserving editor work')

material=materials.anvil(True)
errors=u.MaterialEditingLibrary.recompile_material(material)
if errors:
    raise RuntimeError('Black anvil material compilation failed: '+str(errors))
if not u.EditorAssetLibrary.save_loaded_asset(material,False):
    raise RuntimeError('Could not save black anvil material')
saved=[material.get_path_name()]
bindings=[]
for path in meshes:
    mesh=u.load_asset(path)
    if mesh is None:
        raise RuntimeError('Missing anvil mesh '+path)
    slots=[]
    for index,slot in enumerate(mesh.get_editor_property('static_materials')):
        name=str(slot.material_slot_name).split('.')[0]
        if name in ('AnvilSteel','AnvilForge','AnvilFace','AnvilHorn'):
            mesh.set_material(index,material)
            slots.append(name)
    if not slots:
        raise RuntimeError('No anvil material slot in '+path)
    if not u.EditorAssetLibrary.save_loaded_asset(mesh,False):
        raise RuntimeError('Could not save '+path)
    saved.append(mesh.get_path_name())
    bindings.append({'mesh':path,'slots':slots})

receipt={'saved':saved,'bindings':bindings,'appearance':'matte black oxide body; subdued worn face',
         'geometry_changed':False,'runtime_tested':False,'rendered':False}
(here/('black-anvil-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'.json')).write_text(
    json.dumps(receipt,indent=2),encoding='utf-8')
print('BLACK_ANVIL_SAVED '+json.dumps(receipt),flush=True)
