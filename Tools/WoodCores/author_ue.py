"""Save new-only wood-core assets in an isolated UE host; no game or test map."""
from pathlib import Path
import json
import unreal as u
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'SourceAssets/WoodCoreMaterials20261026'
if Path(u.Paths.project_dir()).resolve()!=(OUT/'AssetHost').resolve():raise RuntimeError('Isolated AssetHost required')
BASE='/Game/Items/WoodCores20261026';E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
cores=json.loads((OUT/'cores.json').read_text(encoding='utf-8'))
E.make_directory(BASE)
def node(m,cls):return L.create_material_expression(m,cls)
def link(a,o,b,i):
 if not L.connect_material_expressions(a,o,b,i):raise RuntimeError('Material pin '+str(i))
def prop(a,o,p):
 if not L.connect_material_property(a,o,p):raise RuntimeError('Material property '+str(p))
def scalar(m,name,val):
 n=node(m,u.MaterialExpressionScalarParameter);n.set_editor_property('parameter_name',name);n.set_editor_property('default_value',val);return n
def vector(m,name,val):
 n=node(m,u.MaterialExpressionVectorParameter);n.set_editor_property('parameter_name',name);n.set_editor_property('default_value',u.LinearColor(*val,1));return n
m=E.load_asset(BASE+'/M_WoodCore') if E.does_asset_exist(BASE+'/M_WoodCore') else None
build_master=m is None
if build_master:m=A.create_asset('M_WoodCore',BASE,u.Material,u.MaterialFactoryNew())
if not m:raise RuntimeError('New wood material already exists or failed')
if build_master:
 m.set_editor_property('tangent_space_normal',False)
 world=node(m,u.MaterialExpressionWorldPosition);local=node(m,u.MaterialExpressionTransformPosition)
 local.set_editor_property('transform_source_type',u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD);local.set_editor_property('transform_type',u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_LOCAL);link(world,'',local,'')
 normal=node(m,u.MaterialExpressionVertexNormalWS);roles=node(m,u.MaterialExpressionVertexColor)
 shader=(ROOT/'SourceAssets/WoodworkingSurfaceV2_20261026/stock_surface.hlsl').read_text(encoding='utf-8')
 shader=shader.replace('radius * 2.85','radius * 2.85 * GrainScale').replace('float3(.24,.122,.052), float3(.40,.243,.113)','WoodDark, WoodLight').replace('clamp(.77 + fibers','clamp(.77 + RoughnessOffset + fibers')
 shader=shader.replace('return saturate(base);','float spirit = smoothstep(.985, 1.0, growth) * smoothstep(.58, .8, broad);\nEmissive = float3(.10,.38,.22) * spirit * SpiritGlow;\nreturn saturate(base);')
 (OUT/'wood_core_surface.hlsl').write_text(shader,encoding='utf-8')
 custom=node(m,u.MaterialExpressionCustom);custom.set_editor_property('code',shader);custom.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
 inputs={'LocalPosition':local,'WorldPosition':world,'GeometricNormal':normal,'SurfaceData':roles,'WoodDark':vector(m,'WoodDark',cores[0]['low']),'WoodLight':vector(m,'WoodLight',cores[0]['high']),'GrainScale':scalar(m,'GrainScale',1),'RoughnessOffset':scalar(m,'RoughnessOffset',0),'SpiritGlow':scalar(m,'SpiritGlow',0)}
 pins=[]
 for name in inputs:
  p=u.CustomInput();p.set_editor_property('input_name',name);pins.append(p)
 custom.set_editor_property('inputs',pins)
 outputs=[]
 for name,typ in [('Roughness',u.CustomMaterialOutputType.CMOT_FLOAT1),('SurfaceNormal',u.CustomMaterialOutputType.CMOT_FLOAT3),('Emissive',u.CustomMaterialOutputType.CMOT_FLOAT3)]:
  o=u.CustomOutput();o.set_editor_property('output_name',name);o.set_editor_property('output_type',typ);outputs.append(o)
 custom.set_editor_property('additional_outputs',outputs)
 for name,n in inputs.items():link(n,'RGB' if name in ('WoodDark','WoodLight') else '',custom,name)
 for output,p in [('',u.MaterialProperty.MP_BASE_COLOR),('Roughness',u.MaterialProperty.MP_ROUGHNESS),('SurfaceNormal',u.MaterialProperty.MP_NORMAL),('Emissive',u.MaterialProperty.MP_EMISSIVE_COLOR)]:prop(custom,output,p)
 prop(scalar(m,'Metallic',0),'',u.MaterialProperty.MP_METALLIC);prop(scalar(m,'Specular',.22),'',u.MaterialProperty.MP_SPECULAR)
 L.recompile_material(m)
 if not E.save_loaded_asset(m,False):raise RuntimeError('Cannot save master material')
saved=[m.get_path_name()]
meshlib=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
for c in cores:
 mi=E.load_asset(BASE+'/MI_WoodCore_'+c['key']) if E.does_asset_exist(BASE+'/MI_WoodCore_'+c['key']) else A.create_asset('MI_WoodCore_'+c['key'],BASE,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew());L.set_material_instance_parent(mi,m)
 for k,v in [('WoodDark',c['low']),('WoodLight',c['high'])]:L.set_material_instance_vector_parameter_value(mi,k,u.LinearColor(*v,1))
 for k,v in [('GrainScale',c['grain']),('RoughnessOffset',c['rough']),('SpiritGlow',c['glow'])]:L.set_material_instance_scalar_parameter_value(mi,k,v)
 L.update_material_instance(mi);E.save_loaded_asset(mi,False)
 name='SM_WoodCore_'+c['key'];task=u.AssetImportTask();task.set_editor_property('filename',str(OUT/'Export'/f'{name}.fbx'));task.set_editor_property('destination_path',BASE);task.set_editor_property('destination_name',name);task.set_editor_property('automated',True);task.set_editor_property('replace_existing',True);task.set_editor_property('save',True)
 opts=u.FbxImportUI();opts.set_editor_property('import_as_skeletal',False);opts.set_editor_property('import_materials',False);opts.set_editor_property('import_textures',False);opts.set_editor_property('mesh_type_to_import',u.FBXImportType.FBXIT_STATIC_MESH)
 data=opts.get_editor_property('static_mesh_import_data');data.set_editor_property('auto_generate_collision',True);data.set_editor_property('vertex_color_import_option',u.VertexColorImportOption.REPLACE);data.set_editor_property('normal_import_method',u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
 task.set_editor_property('options',opts);A.import_asset_tasks([task]);mesh=E.load_asset(BASE+'/'+name)
 if not isinstance(mesh,u.StaticMesh):raise RuntimeError('FBX mesh import failed '+name)
 mesh.set_material(0,mi)
 if not E.save_loaded_asset(mesh,False):raise RuntimeError('Mesh save failed '+name)
 saved.extend([mi.get_path_name(),mesh.get_path_name()])
(OUT/'ue-authoring.json').write_text(json.dumps({'saved_assets':saved,'host':str(u.Paths.project_dir()),'runtime_test':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('WOOD_CORE_ASSETS_SAVED '+str(len(saved)))
