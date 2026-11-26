"""Retain native interpolation and tune its shading to consistent black hair."""
import json
from pathlib import Path
import unreal as u
R=Path('D:/FPS3D/FPSGAME/SourceAssets/ChapelNun20261115/FaceOriginalRestoreR6')
BASE='/Game/Characters/ChapelNun20261115/HairReferenceR5/'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
report={'before':{},'after':{}}
mat=u.load_asset(BASE+'Materials/MI_Nun_Hair')
values={'hairMelanin':.95,'hairRedness':0.,'MelaninVariationFine':.12,'MelaninVariationRough':.08,'HairRoughness':.43}
report['before']['material']={k:L.get_material_instance_scalar_parameter_value(mat,k) for k in values}
for k,v in values.items():L.set_material_instance_scalar_parameter_value(mat,k,v)
L.set_material_instance_vector_parameter_value(mat,'hairDye',u.LinearColor(.08,.08,.08,1))
L.update_material_instance(mat)
if not E.save_loaded_asset(mat,False):raise RuntimeError('Hair material not saved')
report['after']['material']=values
for part in ('Core','Loose'):
 groom=u.load_asset(BASE+'Grooms/Nun_LowBun_'+part+'_R5')
 report['before'][part]={'global_interpolation':groom.get_editor_property('enable_global_interpolation'),'lod':[x.export_text() for x in groom.get_editor_property('hair_groups_lod')]}
 groom.set_editor_property('enable_global_interpolation',False)
 if not E.save_loaded_asset(groom,False):raise RuntimeError('Hair interpolation not saved')
 report['after'][part]={'global_interpolation':groom.get_editor_property('enable_global_interpolation')}
(R/'hair_render_settings.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('NUN_HAIR_RENDER_SETTINGS_SAVED',flush=True)
