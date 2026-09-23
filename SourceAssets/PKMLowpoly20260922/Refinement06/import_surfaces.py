import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;P='/Game/Weapons/PKMLowpoly20260922/Refinement06';A=u.AssetToolsHelpers.get_asset_tools();L=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
saved=[];materials={}
def save(a):
 if not L.save_loaded_asset(a,False):raise RuntimeError('Could not save '+a.get_path_name())
 saved.append(a.get_path_name())
def texture(file,name,channel,gl=True):
 task=u.AssetImportTask();task.filename=str(file);task.destination_path=P+'/Textures';task.destination_name=name;task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task])
 if not task.imported_object_paths:raise RuntimeError('No imported texture '+name)
 tex=u.load_asset(task.destination_path+'/'+name);tex.set_editor_property('srgb',channel=='BaseColor')
 if channel=='Normal':tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP);tex.set_editor_property('flip_green_channel',gl)
 if channel=='Roughness':tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_GRAYSCALE)
 save(tex);return tex
def node(mat,cls,**props):
 n=M.create_material_expression(mat,cls)
 for k,v in props.items():n.set_editor_property(k,v)
 return n
def wire(a,b,pin,out=''):M.connect_material_expressions(a,out,b,pin)
for label in ['PKM_LaminatedWood','PKM_WoodGripPanel','PKM_BluedSteel','PKM_InteriorSteel','PKM_AmmoBoxPaint']:
 wood=label=='PKM_LaminatedWood';name='M_'+label+'_06';mat=u.load_asset(P+'/Materials/'+name)
 if not mat:mat=A.create_asset(name,P+'/Materials',u.Material,u.MaterialFactoryNew())
 M.delete_all_material_expressions(mat);M.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
 for channel in ['BaseColor','Normal','Roughness']:
  if wood:
   source={'BaseColor':'Color','Normal':'NormalDX','Roughness':'Roughness'}[channel]
   file=O.parent.parent/'AKMIntegration20260910/Redwood/Wood051'/('Wood051_2K-JPG_'+source+'.jpg')
  else:file=O/'Textures'/(label+'_'+channel+'.png')
  tex=texture(file,'T_'+label+'_06_'+channel,channel,not wood)
  n=node(mat,u.MaterialExpressionTextureSample,texture=tex,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE if channel=='Roughness' else u.MaterialSamplerType.SAMPLERTYPE_COLOR)
  output='RGB' if channel!='Roughness' else 'R'
  if wood:
   if channel=='BaseColor':
    tint=node(mat,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(1.05,.50,.26,1));mul=node(mat,u.MaterialExpressionMultiply);wire(n,mul,'A','RGB');wire(tint,mul,'B');n=mul
   elif channel=='Roughness':
    mul=node(mat,u.MaterialExpressionMultiply,const_b=.22);wire(n,mul,'A','R');add=node(mat,u.MaterialExpressionAdd,const_b=.30);wire(mul,add,'A');n=add
   else:
    flat=node(mat,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(0,0,1,1));mix=node(mat,u.MaterialExpressionLinearInterpolate,const_alpha=.16);wire(flat,mix,'A');wire(n,mix,'B','RGB');n=mix
   output=''
  if channel=='Normal':
   normal=node(mat,u.MaterialExpressionNormalize);wire(n,normal,'VectorInput',output);n=normal;output=''
  M.connect_material_property(n,output,{'BaseColor':u.MaterialProperty.MP_BASE_COLOR,'Normal':u.MaterialProperty.MP_NORMAL,'Roughness':u.MaterialProperty.MP_ROUGHNESS}[channel])
 metal=node(mat,u.MaterialExpressionConstant,r=1.0 if 'Steel' in label else 0.0);M.connect_material_property(metal,'',u.MaterialProperty.MP_METALLIC)
 M.recompile_material(mat);save(mat);materials[label]=mat.get_path_name()
(O/'surface_import.json').write_text(json.dumps({'saved':saved,'bindings':materials},indent=2));print('PKM06 materials saved.')
