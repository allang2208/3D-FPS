import unreal as u,json
from pathlib import Path
R=Path('D:/FPS3D/FPSGAME/SourceAssets/ChapelNun20261115/FaceHairFixR1')
mat=u.load_asset('/Game/Characters/ChapelNun20261115/Materials/MI_Nun_Hair')
L=u.MaterialEditingLibrary
for key,value in {'hairMelanin':.90,'hairRedness':0.0,'HairRoughness':.46,'Roughness':.46}.items():
 L.set_material_instance_scalar_parameter_value(mat,key,value)
 if abs(L.get_material_instance_scalar_parameter_value(mat,key)-value)>1e-5:raise RuntimeError('Parameter update failed '+key)
L.set_material_instance_vector_parameter_value(mat,'hairDye',u.LinearColor(.025,.025,.025,1))
color=L.get_material_instance_vector_parameter_value(mat,'hairDye')
if max(abs(color.r-.025),abs(color.g-.025),abs(color.b-.025))>1e-5:raise RuntimeError('Hair dye update failed')
L.update_material_instance(mat)
if not u.EditorAssetLibrary.save_loaded_asset(mat,False):raise RuntimeError('Hair material save failed')
(R/'hair_saved.json').write_text(json.dumps({'asset':mat.get_path_name(),'hairMelanin':L.get_material_instance_scalar_parameter_value(mat,'hairMelanin'),'hairRedness':L.get_material_instance_scalar_parameter_value(mat,'hairRedness'),'hairDye':str(L.get_material_instance_vector_parameter_value(mat,'hairDye')),'saved':True},indent=2),encoding='utf8')
# The actual idle pose leans the face about 9 cm forward; include its measured envelope.
head=u.load_asset('/Game/Characters/ChapelNun20261115/Meshes/SK_Nun_Head')
head.set_editor_property('positive_bounds_extension',u.Vector(3,12,3))
head.set_editor_property('negative_bounds_extension',u.Vector(3,3,7))
if not u.EditorAssetLibrary.save_loaded_asset(head,False):raise RuntimeError('Head bounds save failed')
(R/'head_bounds_saved.json').write_text(json.dumps({'asset':head.get_path_name(),'positive_cm':[3,12,3],'negative_cm':[3,3,7],'reason':'Actual idle pose extends forward to Y=20.60 cm and down to Z=126.69 cm','saved':True},indent=2),encoding='utf8')
print('NUN_BLACK_HAIR_AND_HEAD_BOUNDS_SAVED',flush=True)
