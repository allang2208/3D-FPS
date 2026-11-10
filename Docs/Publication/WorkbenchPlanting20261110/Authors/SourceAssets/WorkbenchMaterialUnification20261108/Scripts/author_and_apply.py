"""Offline material authoring. No geometry, map, gameplay, or external asset changes."""
import json, hashlib, shutil, re
from pathlib import Path
import unreal as u
R=Path('D:/FPS3D/FPSGAME/SourceAssets/WorkbenchMaterialUnification20261108')
P=R.parents[1]; DEST='/Game/Building/WorkbenchSurfaces20261108'
E,L=u.EditorAssetLibrary,u.MaterialEditingLibrary
A=u.AssetToolsHelpers.get_asset_tools(); REV='WorkbenchSurfaceUnification_20261108_R1'
audit=json.loads((R/'Receipts/audit.json').read_text(encoding='utf8'))
report={'revision':REV,'stage':'preflight','created':[],'bindings':[],'palette_changes':[], 'tests_run':False,'renders_run':False}
def record(): (R/'Receipts/upgrade.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
def asset_path(folder,name):return folder+'/'+name+'.'+name
V4='/Game/Building/WoodworkingBenchV4/Materials'; WBK='/Game/Dungeons/AtmosphereV2/RoomInteriors/WorkbenchKit/Materials'; PW='/Game/Building/PotionWorkbench20261015/V1/Materials'; GW='/Game/Building/GunWorkbenchApproved20261006/Materials'
# Authoring UVs and textures remain unchanged. Common surfaces use common bindings.
specs=[
 ('M_WBU_BenchWood',asset_path(V4,'M_WSBench_BenchWood'),(.38,.85,1.,.35)),
 ('M_WBU_EndGrain',asset_path(V4,'M_WSBench_EndGrain'),(.52,.90,1.,.30)),
 ('M_WBU_RackPaint',asset_path(V4,'M_WSDetail_RackPaint'),(.40,.82,.70,.35)),
 ('M_WBU_MachinedSteel',asset_path(V4,'M_WSSculpt_Machined'),(.25,.62,.70,.50)),
 ('M_WBU_RubberGrip',asset_path(V4,'M_WSSculpt_RubberGrip'),(.58,.92,.65,.35)),
 ('M_WBU_UsedWood',asset_path(WBK,'M_WBK_Wood'),(.38,.85,1.,.35)),
 ('M_WBU_WoodworkingProps',asset_path(V4,'M_WW_PropsAtlas'),(.22,.90,.90,.40)),
 ('M_WBU_GunProps',asset_path(GW,'M_GWDesign_PropsPBR'),(.22,.90,.90,.40)),
 ('M_WBU_PotionProps',asset_path(PW,'M_PW_SurfaceAtlas'),(.22,.90,.90,.40)),
 ('M_WBU_SiliconePad',asset_path('/Game/Building/GunWorkbenchPolish20260928/Materials','M_GW3_Mat'),(.55,.90,.80,.35)),
]
mapping={}
def mapped(old,new):mapping[old]=DEST+'/'+new+'.'+new
for name,source,profile in specs:
 if name!='M_WBU_UsedWood':mapped(source,name)
for old,name in [('M_PW_wood','M_WBU_BenchWood'),('M_PW_endgrain','M_WBU_EndGrain')]:mapped(asset_path(PW,old),name)
for old,name in [('WSBench_EndGrain','M_WBU_EndGrain'),('WSDetail_RackPaint','M_WBU_RackPaint'),('WSSculpt_Machined','M_WBU_MachinedSteel'),('WSSculpt_RubberGrip','M_WBU_RubberGrip')]:mapped(asset_path(WBK+'/InUse','MI_WBK_'+old),name)
old_used=asset_path(WBK+'/InUse','MI_WBK_WSBench_BenchWood_R3')
mapped(old_used,'MI_WBU_UsedBenchWood')
# Workbench kit instances used in other rooms are NOT altered.
meshes={}
for path,info in audit['meshes'].items():
 if 'ArcaneWorkbench' in path or '/Props/CastingStation' in path:continue
 # RuntimeV2 Body is historical; ThermometerV9 is the current body.
 if '/RuntimeV2/Meshes/SM_AlchemyBody.' in path:continue
 if not any(s['material'] in mapping for s in info['slots']):continue
 mesh=u.load_asset(path)
 if not isinstance(mesh,u.StaticMesh):raise RuntimeError('Missing target '+path)
 current=[s.material_interface.get_path_name() if s.material_interface else None for s in mesh.static_materials]
 expected=[s['material'] for s in info['slots']]
 if len(current)!=len(expected) or any(a not in (b,mapping.get(b)) for a,b in zip(current,expected)):
  raise RuntimeError('Concurrent material binding change; preserve '+path)
 meshes[path]=mesh
palette=u.load_asset('/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette')
rows=list(palette.get_editor_property('components'))
for row in rows:
 if str(row.get_editor_property('id')) in ('workbench_table','gun_workbench_table'):
  surface=row.get_editor_property('surface')
  if not surface or surface.get_path_name() not in (old_used,mapping[old_used]):raise RuntimeError('Palette surface changed; preserve it')
owned=set(meshes)|{palette.get_path_name()}
if any(p.get_path_name() in {x.split('.')[0] for x in owned} or p.get_path_name().startswith(DEST) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Unsaved target packages')
# Recoverable exact package backups, with immutable first-run hashes.
backup=[]; disk_hashes={}
for path in sorted(owned):
 rel=Path(path.split('.')[0].replace('/Game/',''))
 source=(P/'Content'/rel).with_suffix('.uasset');target=(R/'Before'/rel).with_suffix('.uasset')
 if not source.exists():raise RuntimeError('No source package '+str(source))
 target.parent.mkdir(parents=True,exist_ok=True)
 disk_hashes[path]=hashlib.sha256(source.read_bytes()).hexdigest()
 if not target.exists():shutil.copy2(source,target)
 backup.append({'package':path,'before':str(target),'sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
(R/'Receipts/backups.json').write_text(json.dumps(backup,indent=2),encoding='utf8')
def save(obj):
 path=obj.get_path_name()
 if path in disk_hashes:
  disk=(P/'Content'/Path(path.split('.')[0].replace('/Game/',''))).with_suffix('.uasset')
  if hashlib.sha256(disk.read_bytes()).hexdigest()!=disk_hashes[path]:raise RuntimeError('Package changed concurrently; preserve '+path)
 if not E.save_loaded_asset(obj,False):raise RuntimeError('Save failed '+obj.get_path_name())
def node(m,cls):return L.create_material_expression(m,cls)
def parameter(m,name,value):
 n=node(m,u.MaterialExpressionScalarParameter);n.set_editor_property('parameter_name',name);n.set_editor_property('default_value',value);return n

def link(a,out,b,pin):
 if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Cannot connect '+pin)
def custom(m,code,names,values,output):
 n=node(m,u.MaterialExpressionCustom);n.set_editor_property('code',code);n.set_editor_property('output_type',output)
 pins=[]
 for name in names:
  pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
 n.set_editor_property('inputs',pins)
 for name,(source,out) in zip(names,values):link(source,out,n,name)
 return n
def connect_output(m,n,prop,front_pin=None):
 if not L.connect_material_property(n,'',prop):raise RuntimeError('Cannot connect output '+str(prop))
 front=L.get_material_property_input_node(m,u.MaterialProperty.MP_FRONT_MATERIAL)
 if front and front_pin:
  if not isinstance(front,u.MaterialExpressionSubstrateShadingModels):raise RuntimeError('Unexpected Substrate graph')
  link(n,'',front,front_pin)
def wrap(m,profile):
 low,high,strength,specular=profile
 rough=L.get_material_property_input_node(m,u.MaterialProperty.MP_ROUGHNESS)
 if not rough:raise RuntimeError('Missing roughness source')
 rout=L.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_ROUGHNESS)
 adjusted=custom(m,'return clamp(R,Min,Max);',['R','Min','Max'],[(rough,rout),(parameter(m,'WBU_RoughnessMin',low),''),(parameter(m,'WBU_RoughnessMax',high),'')],u.CustomMaterialOutputType.CMOT_FLOAT1)
 connect_output(m,adjusted,u.MaterialProperty.MP_ROUGHNESS,'Roughness')
 normal=L.get_material_property_input_node(m,u.MaterialProperty.MP_NORMAL)
 if normal:
  out=L.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_NORMAL)
  adjusted=custom(m,'return normalize(float3(N.xy*Strength,max(N.z,0.01)));',['N','Strength'],[(normal,out),(parameter(m,'WBU_NormalStrength',strength),'')],u.CustomMaterialOutputType.CMOT_FLOAT3)
  connect_output(m,adjusted,u.MaterialProperty.MP_NORMAL,'Normal')
 connect_output(m,parameter(m,'WBU_Specular',specular),u.MaterialProperty.MP_SPECULAR,'Specular')
 E.set_metadata_tag(m,'WorkbenchSurfaceRevision',REV)
 E.set_metadata_tag(m,'WorkbenchSurfaceOriginal',source)
 L.layout_material_expressions(m);L.recompile_material(m);save(m)
for name,source,profile in specs:
 target=DEST+'/'+name;m=u.load_asset(target)
 if m:
  if E.get_metadata_tag(m,'WorkbenchSurfaceRevision')!=REV:raise RuntimeError('Unowned material '+target)
 else:
  m=E.duplicate_asset(source.split('.')[0],target)
  if not isinstance(m,u.Material):raise RuntimeError('Source is not an opaque base material '+source)
  if m.get_editor_property('blend_mode')!=u.BlendMode.BLEND_OPAQUE:raise RuntimeError('Preserve transparent surface')
  wrap(m,profile)
 report['created'].append({'asset':m.get_path_name(),'source':source,'roughness_min':profile[0],'roughness_max':profile[1],'normal_multiplier':profile[2],'specular':profile[3]});record()
mi=u.load_asset(DEST+'/MI_WBU_UsedBenchWood')
if not mi:
 mi=E.duplicate_asset(old_used.split('.')[0],DEST+'/MI_WBU_UsedBenchWood')
 if not isinstance(mi,u.MaterialInstanceConstant):raise RuntimeError('Wood instance duplicate failed')
 L.set_material_instance_parent(mi,u.load_asset(DEST+'/M_WBU_UsedWood'));L.update_material_instance(mi)
 E.set_metadata_tag(mi,'WorkbenchSurfaceRevision',REV);save(mi)
elif E.get_metadata_tag(mi,'WorkbenchSurfaceRevision')!=REV:raise RuntimeError('Unowned wood instance')
report['created'].append({'asset':mi.get_path_name(),'source':old_used,'retains':'original tabletop wear, dust, local masks'})
(R/'material_mapping.json').write_text(json.dumps({'revision':REV,'mapping':mapping,'target_meshes':list(meshes),'palette_ids':['workbench_table','gun_workbench_table']},indent=2),encoding='utf8')
report['stage']='materials_saved';record()
for path,mesh in meshes.items():
 edits=[]
 for i,slot in enumerate(mesh.static_materials):
  old=slot.material_interface.get_path_name() if slot.material_interface else None
  if old in mapping:
   mat=u.load_asset(mapping[old])
   if not mat:raise RuntimeError('Missing authored material')
   mesh.set_material(i,mat);edits.append({'slot':i,'name':str(slot.material_slot_name),'before':old,'after':mat.get_path_name()})
 if edits:
  save(mesh)
  if [mesh.get_num_triangles(i) for i in range(mesh.get_num_lods())]!=audit['meshes'][path]['triangles']:raise RuntimeError('Unexpected geometry change')
  report['bindings'].append({'mesh':path,'changes':edits});record()
for row in rows:
 id=str(row.get_editor_property('id'))
 if id in ('workbench_table','gun_workbench_table'):
  old=row.get_editor_property('surface').get_path_name()
  if old==old_used:
   row.set_editor_property('surface',mi);report['palette_changes'].append({'id':id,'before':old,'after':mi.get_path_name()})
if report['palette_changes']:
 palette.modify();palette.set_editor_property('components',rows);save(palette)
report['stage']='saved';report['mesh_count']=len(report['bindings']);report['slot_count']=sum(len(x['changes']) for x in report['bindings']);record()
print('WORKBENCH_UNIFICATION_SAVED '+json.dumps({'materials':len(report['created']),'meshes':report['mesh_count'],'slots':report['slot_count'],'palette_entries':len(report['palette_changes'])}))
