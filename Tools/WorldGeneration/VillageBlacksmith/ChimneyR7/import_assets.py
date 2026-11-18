"""Fresh R6 assets, explicit vertex colors and all LODs imported in one operation."""
import json
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'SourceAssets/HillsVillageBlacksmith20261117/ChimneyR7'
DEST='/Game/WorldGeneration/TemperateHills/VillageBlacksmith/ChimneyR7'
E,A=u.EditorAssetLibrary,u.AssetToolsHelpers.get_asset_tools()
S=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Preserve active PIE')
def get(path):
 obj=u.load_asset(path)
 if not obj:raise RuntimeError('Missing '+path)
 return obj
def save(obj):
 if not E.save_loaded_asset(obj,False):raise RuntimeError('Save '+obj.get_path_name())
r2='/Game/WorldGeneration/TemperateHills/VillageBlacksmith/ArtPassR2/Materials/'
mats={'Oak':get(r2+'M_VillageR2_Oak'),'Stone':get(r2+'M_VillageR2_HearthStone'),
 'Iron':get('/Game/Props/CastingStation20260926/RealismV5/MI_DarkForgedIron'),
 'Soot':get(DEST+'/Materials/MI_ChimneyFlueSoot'),'HouseStone':get('/Game/UnrealNormandy/MaterialInstances/MI_Main_StoneWall_00A'),
 'HouseMortar':get('/Game/UnrealNormandy/MaterialInstances/MI_Main_Mortar_00A'),
 'Sign':get('/Game/WorldGeneration/TemperateHills/VillageBlacksmith/DetailR6/Materials/M_BlacksmithBrushSign')}
receipt=OUT/'assets-saved.json'
report=json.loads(receipt.read_text()) if receipt.exists() else {'saved':[],'gameplay_started':False,'rendered':False}
completed={r['path'] for r in report['saved']}
for row in json.loads((OUT/'model-manifest.json').read_text())['assets']:
 path=DEST+'/Meshes/'+row['name']
 if path in completed:continue
 if not E.does_asset_exist(path):
  task=u.AssetImportTask();task.filename=row['lod_bundle'];task.destination_path=DEST+'/Meshes';task.destination_name=row['name'];task.automated=True;task.replace_existing=False
  opt=u.FbxImportUI();opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_as_skeletal=False
  opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
  data=opt.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True;data.transform_vertex_to_absolute=True
  data.auto_generate_collision=False;data.generate_lightmap_u_vs=False;data.import_mesh_lods=True
  data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
  data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
  task.options=opt;task.factory=u.FbxFactory();A.import_asset_tasks([task])
 m=get(path)
 for i,slot in enumerate(m.static_materials):m.set_material(i,mats[str(slot.material_slot_name)])
 count=S.get_lod_count(m)
 if count!=3:raise RuntimeError('Incomplete LOD-group import '+path+' count='+str(count))
 S.set_lod_screen_sizes(m,[1.,.2,.06])
 body=m.get_editor_property('body_setup');agg=body.get_editor_property('agg_geom');boxes=[]
 for part in row['collision_boxes']:
  b=u.KBoxElem();b.set_editor_property('center',u.Vector(*part['center']))
  pitch,yaw,roll=part['rotation'];b.set_editor_property('rotation',u.Rotator(pitch=pitch,yaw=yaw,roll=roll))
  for axis,value in zip(('x','y','z'),part['size']):b.set_editor_property(axis,value)
  boxes.append(b)
 agg.set_editor_property('box_elems',boxes);agg.set_editor_property('convex_elems',[])
 body.set_editor_property('agg_geom',agg);body.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
 slots=list(m.static_materials)
 for slot in slots:
  info=slot.get_editor_property('uv_channel_data');info.set_editor_property('bOverrideDensities',True);info.set_editor_property('LocalUVDensities',[100.,100.,0.,0.])
 m.set_editor_property('static_materials',slots)
 E.set_metadata_tag(m,'VillageDetailOwner','BlacksmithChimneyR7_20261117');save(m)
 report['saved'].append({'path':path,'role':row['role'],'lods':count,'source_triangles':row['lods'][0]['triangles'],'collision_boxes':len(boxes),'materials':[s.material_interface.get_path_name() for s in m.static_materials]})
 receipt.write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('SMITH_CHIMNEY_R7_MESHES_SAVED '+str(len(report['saved'])))
