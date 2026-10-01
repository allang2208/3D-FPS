"""Compile private Refine03 graphs, import normal bakes, update existing SVD MIs.
No runtime/preview tests. All existing mesh bindings and wet self mappings stay
on the same instances. Existing instance source texture/UV choices are retained.
"""
import json,hashlib,shutil,sys
from pathlib import Path
import unreal as u
O=Path(__file__).parent
P=Path(u.Paths.project_dir()).resolve()
if P!=Path('D:/FPS3D/FPSGAME').resolve():raise RuntimeError('Wrong project')
sys.path.insert(0,str(O.parent))
import ws_graph as W
L,E,A=u.MaterialEditingLibrary,u.EditorAssetLibrary,u.AssetToolsHelpers.get_asset_tools()
ROOT='/Game/Weapons/SVDDragunov20260922/SurfaceStandard20261001'
DEST=ROOT+'/Refine03'
SATIN=ROOT+'/Master/M_SVD_WS_FactoryMagazineSatin02'
R=json.loads((O/'recipe.json').read_text());VERSION=R['version']
CAPTURE=json.loads((O/'Input/effective.json').read_text())
RP=O/'apply_receipt.json'
receipt=json.loads(RP.read_text()) if RP.exists() else {'version':VERSION,'masters':{},'textures':{},'instances':{},'complete':False,'tested':False,'mesh_changed':False,'wet_table_changed':False}
def record():RP.write_text(json.dumps(receipt,indent=1),encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def disk(path):return P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
def load(path):
 a=u.load_asset(path)
 if not a:raise RuntimeError('Missing '+path)
 return a
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
def input_of(m,n,name):
 pins=[str(p.get_editor_property('input_name')) for p in n.get_editor_property('inputs')]
 source=L.get_inputs_for_material_expression(m,n)[pins.index(name)]
 return source,str(L.get_input_node_output_name_for_material_expression(n,source))
def scalar(m,name,value):
 return W.node(m,u.MaterialExpressionScalarParameter,parameter_name=name,default_value=value,group='SVD Refine03')
def custom(m,name,code,inputs,size):
 W.CODE[name]=code
 return W.custom(m,name,inputs,size)

# Conflict guards are required to avoid overwriting another session's live work.
dirty=set()
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
 editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
 if editor and editor.get_game_world():raise RuntimeError('PIE active; preserve the current session')
 dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
weather=dict(load('/Game/Weapons/SVDDragunov20260922/Accessories20260923/DA_SVD_AttachmentWetMaterials').get_editor_property('wet_materials'))
for t in R['targets']:
 path=t['material'];package=path.split('.')[0]
 if package in dirty:raise RuntimeError('Unsaved target '+package)
 prior=receipt['instances'].get(path)
 expected=prior['saved_sha256'] if prior and prior.get('saved') else t['sha256']
 if sha(disk(path))!=expected:raise RuntimeError('Concurrent target change '+path)
 if weather.get(path)!=load(path):raise RuntimeError('Wet mapping changed '+path)
 row=CAPTURE['meshes'][t['mesh']];mesh=load(row['asset'])
 slots=mesh.get_editor_property('materials' if row['skeletal'] else 'static_materials')
 bound={str(s.material_slot_name):s.material_interface.get_path_name() if s.material_interface else None for s in slots}
 if bound.get(t['slot'])!=path:raise RuntimeError('Current mesh slot changed '+t['mesh']+' '+t['slot'])

textures={}
for name,spec in R['textures'].items():
 path=DEST+'/Textures/'+name
 if path in dirty:raise RuntimeError('Unsaved texture '+path)
 if name not in receipt['textures']:
  if E.does_asset_exist(path):raise RuntimeError('Unowned texture '+path)
  task=u.AssetImportTask();task.filename=spec['source'];task.destination_path=DEST+'/Textures'
  task.destination_name=name;task.automated=True;task.replace_existing=False;task.save=False
  A.import_asset_tasks([task])
  tex=load(path)
  tex.set_editor_property('srgb',False)
  tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP)
  tex.set_editor_property('flip_green_channel',True)
  tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WEAPON)
  E.set_metadata_tag(tex,'WeaponSurfaceVersion',VERSION);save(tex)
  receipt['textures'][name]={'path':path,'source':spec['source'],'sha256':spec['sha256']};record()
 textures[name]=load(path)

def build(source):
 target=DEST+'/Master/M_SVD_R03_'+hashlib.sha1(source.encode()).hexdigest()[:10]+'_g2'
 if source in receipt['masters']:return load(target)
 if E.does_asset_exist(target):raise RuntimeError('Unowned private master '+target)
 if target in dirty:raise RuntimeError('Unsaved master '+target)
 m=E.duplicate_asset(source,target)
 if not m:raise RuntimeError('Duplicate failed '+source)
 cs={str(n.get_editor_property('description')):n for n in L.get_material_expressions(m) if isinstance(n,u.MaterialExpressionCustom)}
 wetnormal=cs['WS_WetNormal'];oldnormal=input_of(m,wetnormal,'Base')
 uv=W.node(m,u.MaterialExpressionTextureCoordinate,coordinate_index=0)
 sample=W.node(m,u.MaterialExpressionTextureSampleParameter2D,parameter_name='R03_EdgeNormal',
  texture=load('/Engine/EngineMaterials/DefaultNormal'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL,group='SVD Refine03')
 W.wire(uv,sample,'UVs')
 edge=W.node(m,u.MaterialExpressionStaticSwitchParameter,parameter_name='R03_UseEdgeNormal',default_value=False,group='SVD Refine03')
 W.wire((sample,'RGB'),edge,'True')
 flat=W.node(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(0,0,1,1));W.wire(flat,edge,'False')
 normal=custom(m,'SVD R03 manufactured bevel and source detail',(O/'LayerNormal.hlsl').read_text(),
  {'N':oldnormal,'Edge':edge,'SourceStrength':scalar(m,'R03_SourceNormalStrength',.92),
  'EdgeStrength':scalar(m,'R03_EdgeNormalStrength',.7)},3)
 W.wire(normal,wetnormal,'Base')
 # Replace only the dry merge node, retaining every original region and colour.
 merge=cs['SVD WS1 preserve polymer rubber cheekpad and PSO interior']
 inputs={n:input_of(m,merge,n) for n in ('Base','Rough','Finish','Region')}
 inputs['Exterior']=input_of(m,cs['SVD WS1 exposed weather coverage'],'Exterior')
 inputs['Dielectric']=scalar(m,'R03_DielectricFinish',0.)
 refined=custom(m,'SVD R03 differentiated dielectric finish',(O/'DielectricFinish.hlsl').read_text(),inputs,4)
 W.wire(refined,cs['WS_Wet'],'CR')
 E.set_metadata_tag(m,'WeaponSurfaceGraph',VERSION)
 E.set_metadata_tag(m,'WeaponSurfaceSourceGraph',source)
 errors=L.recompile_material(m)
 if errors:raise RuntimeError('Material compile failed '+target+' '+str(errors))
 save(m);receipt['masters'][source]={'path':target};record()
 print('SVD_R03_MASTER_SAVED',target,flush=True)
 return m

for t in R['targets']:
 path=t['material']
 if receipt['instances'].get(path,{}).get('saved'):continue
 mi=load(path)
 rel=path.split('.')[0].removeprefix('/Game/')+'.uasset'
 backup=O/'Before'/rel;backup.parent.mkdir(parents=True,exist_ok=True)
 if not backup.exists():shutil.copy2(disk(path),backup)
 # Both magazines share the shallow pressing graph, but keep their own UV0/UV1
 # surface-mask assignments and original atlas parameters on the instances.
 source=SATIN if t['magazine'] else t['base']
 parent=build(source)
 L.set_material_instance_parent(mi,parent)
 for name,value in t['scalars'].items():L.set_material_instance_scalar_parameter_value(mi,name,float(value))
 for name,value in t['vectors'].items():L.set_material_instance_vector_parameter_value(mi,name,u.LinearColor(*value,1))
 L.set_material_instance_static_switch_parameter_value(mi,'R03_UseEdgeNormal',bool(t['normal']))
 if t['normal']:L.set_material_instance_texture_parameter_value(mi,'R03_EdgeNormal',textures[t['normal']])
 L.update_material_instance(mi);E.set_metadata_tag(mi,'WeaponSurfaceRevision',VERSION);save(mi)
 receipt['instances'][path]={'saved':True,'saved_sha256':sha(disk(path)),'backup':str(backup),
  'parent':parent.get_path_name(),'category':t['category'],'scalars':t['scalars'],'vectors':t['vectors'],'edge_normal':t['normal']}
 record()
receipt['complete']=True;record()
print('SVD_R03_SAVED',len(receipt['instances']),len(receipt['masters']),len(receipt['textures']),'tested=False',flush=True)
