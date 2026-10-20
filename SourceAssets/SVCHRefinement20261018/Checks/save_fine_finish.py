import json
from pathlib import Path
import unreal as u
O=Path(__file__).parent
ROOT='/Game/Weapons/SVCH/Refined20261018'
SURFACE=ROOT+'/SurfaceV4'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
saved=[];textures={}
for kind in ('Metal','Polymer','Rubber'):
    task=u.AssetImportTask();task.filename=str(O.parent/'Textures'/('T_SVCH_'+kind+'_N.png'))
    task.destination_path=SURFACE+'/Textures';task.automated=True;task.replace_existing=False;task.save=False
    A.import_asset_tasks([task])
    tex=u.load_asset(SURFACE+'/Textures/T_SVCH_'+kind+'_N')
    tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP)
    tex.set_editor_property('srgb',False)
    if not E.save_loaded_asset(tex,False):raise RuntimeError('Texture save failed')
    saved.append(tex.get_path_name())
    textures[kind]=tex
mesh=u.load_asset(ROOT+'/SK_SVCH_Refined_R4')
slots=list(mesh.get_editor_property('materials'))
for slot in slots[:9]:
    part=str(slot.material_slot_name).removeprefix('SVCH_')
    metal=part not in ('Polymer','Magazine','Rubber')
    mi=u.load_asset(SURFACE+'/Materials/MI_SVCH_'+part) or A.duplicate_asset('MI_SVCH_'+part,SURFACE+'/Materials',slot.material_interface)
    kind='Metal' if metal else 'Rubber' if part=='Rubber' else 'Polymer'
    L.set_material_instance_texture_parameter_value(mi,'SurfaceNormal',textures[kind])
    for key,value in {'GrainTileCm':3.,'GrainRoughness':.012 if metal else .02,'MottleRoughness':0. if metal else .005}.items():
        L.set_material_instance_scalar_parameter_value(mi,key,value)
    if not E.save_loaded_asset(mi,False):raise RuntimeError('Material save failed')
    saved.append(mi.get_path_name())
    slot.material_interface=mi
mesh.set_editor_property('materials',slots)
if not E.save_loaded_asset(mesh,False):raise RuntimeError('R4 mesh save failed')
saved.append(mesh.get_path_name())
(O/'fine_finish_save.json').write_text(json.dumps({'saved':saved,'normal_rms':{'Metal':.012,'Polymer':.045,'Rubber':.04},'grain_tile_cm':3},indent=1))
print('SVCH_FINE_FINISH_SAVED',len(saved),flush=True)
