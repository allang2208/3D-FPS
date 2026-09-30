"""Retain the existing finish recipe; new cover UVs get their own maps."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;P='/Game/Weapons/LMG201/ReferenceRepair38';F='/Game/Weapons/LMG201/FitFinish37'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();M=u.MaterialEditingLibrary
out={'materials':{},'maps':{},'status':'building','finish_recipe':'FitFinish37 retained; cover UV maps replaced'}
def load(path):
 a=u.load_asset(path)
 if not a:raise RuntimeError('Missing '+path)
 return a
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Cannot save '+a.get_path_name())
for kind in ['Normal','AO']:
 src=O/'Textures'/('T_LMG201_R38_Cover_'+kind+'.png');path=P+'/Textures/'+src.stem
 task=u.AssetImportTask();task.filename=str(src);task.destination_path=P+'/Textures';task.destination_name=src.stem;task.automated=True;task.replace_existing=True;task.save=False
 A.import_asset_tasks([task]);tex=load(path);tex.set_editor_property('srgb',False);tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WEAPON)
 tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if kind=='Normal' else u.TextureCompressionSettings.TC_MASKS)
 if kind=='Normal':tex.set_editor_property('flip_green_channel',True)
 save(tex);out['maps'][kind]=tex.get_path_name()
for role,old in [('Cover','Cover'),('Interior','CoverInterior'),('Satin','CoverSatin')]:
 name='M_LMG201_R38_'+role;path=P+'/Materials/'+name
 mat=u.load_asset(path) or E.duplicate_asset(F+'/Materials/M_LMG201_F37_'+old,path)
 if not mat:raise RuntimeError('Cannot duplicate '+path)
 replaced=[]
 for n in M.get_material_expressions(mat):
  if isinstance(n,u.MaterialExpressionTextureSample):
   tex=n.get_editor_property('texture')
   if tex:
    for kind in out['maps']:
     if tex.get_name()=='T_LMG201_F37_Cover_'+kind or tex.get_name()=='T_LMG201_R38_Cover_'+kind:n.set_editor_property('texture',load(out['maps'][kind]));replaced.append(kind)
 if set(replaced)!={'Normal','AO'}:raise RuntimeError('Missing cover texture channel '+path)
 mat.set_editor_property('two_sided',False)
 errors=M.recompile_material(mat)
 if errors:raise RuntimeError(str(errors))
 E.set_metadata_tag(mat,'201GeometryRevision','ReferenceRepair38: private normal/AO maps for traced visible cover; not visual acceptance')
 save(mat);out['materials'][name]=mat.get_path_name()
out['status']='compiled_and_saved';(O/'materials.json').write_text(json.dumps(out,indent=2));print('R38_MATERIALS_SAVED',out)
