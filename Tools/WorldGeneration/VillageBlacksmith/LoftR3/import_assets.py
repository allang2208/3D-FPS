"""Save the loft structural revision using the accepted village furniture PBR family."""
import json,os
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[4];OUT=Path(os.environ.get('SMITH_LOFT_SOURCE',str(ROOT/'SourceAssets/HillsVillageBlacksmith20261117/LoftR3')))
DEST='/Game/WorldGeneration/TemperateHills/VillageBlacksmith/LoftR3'
E,A=u.EditorAssetLibrary,u.AssetToolsHelpers.get_asset_tools()
S=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
def get(path):
    asset=u.load_asset(path)
    if not asset:raise RuntimeError(path)
    return asset
def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save '+asset.get_path_name())
firepath=DEST+'/Materials/M_LoftFirebrick'
fire=get(firepath) if E.does_asset_exist(firepath) else E.duplicate_asset('/Game/Props/BlastFurnace20260923/Materials/M_BlastFurnace_Firebrick',firepath)
if not fire:raise RuntimeError('Firebrick material copy')
fire.set_editor_property('used_with_instanced_static_meshes',True);save(fire)
mats={'Oak':get('/Game/WorldGeneration/TemperateHills/VillageBlacksmith/ArtPassR2/Materials/M_VillageR2_Oak'),
 'Stone':get('/Game/WorldGeneration/TemperateHills/VillageBlacksmith/ArtPassR2/Materials/M_VillageR2_HearthStone'),
 'Iron':get('/Game/Props/CastingStation20260926/RealismV5/MI_DarkForgedIron'),'Firebrick':fire,
 'HouseStone':get('/Game/UnrealNormandy/MaterialInstances/MI_Main_StoneWall_00A'),
 'HouseMortar':get('/Game/UnrealNormandy/MaterialInstances/MI_Main_Mortar_00A')}
report={'saved':[],'gameplay_started':False,'rendered':False}
selected=os.environ.get('SMITH_LOFT_IMPORT_ROLE')
receipt=OUT/('assets-saved-'+selected+'.json' if selected else 'assets-saved.json')
for row in json.loads((OUT/'model-manifest.json').read_text())['assets']:
    if selected and row['role']!=selected:continue
    path=DEST+'/Meshes/'+row['name']
    if E.does_asset_exist(path):raise RuntimeError('Preserve existing revision; resume only at recorded boundary: '+path)
    task=u.AssetImportTask();task.filename=row['lods'][0]['file'];task.destination_path=DEST+'/Meshes';task.destination_name=row['name'];task.automated=True;task.replace_existing=False
    opt=u.FbxImportUI();opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_as_skeletal=False
    opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    data=opt.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True;data.transform_vertex_to_absolute=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS;task.options=opt;task.factory=u.FbxFactory();A.import_asset_tasks([task]);m=get(path)
    for i,slot in enumerate(m.static_materials):m.set_material(i,mats[str(slot.material_slot_name)])
    for lod in row['lods'][1:]:
        if S.import_lod(m,lod['level'],lod['file'])!=lod['level']:raise RuntimeError('LOD import '+path)
    S.set_lod_screen_sizes(m,[1.,.2,.06])
    body=m.get_editor_property('body_setup');agg=body.get_editor_property('agg_geom');boxes=[]
    for part in row['collision_boxes']:
        box=u.KBoxElem();box.set_editor_property('center',u.Vector(*part['center']));pitch,yaw,roll=part['rotation'];box.set_editor_property('rotation',u.Rotator(pitch=pitch,yaw=yaw,roll=roll))
        for axis,value in zip(('x','y','z'),part['size']):box.set_editor_property(axis,value)
        boxes.append(box)
    agg.set_editor_property('box_elems',boxes);agg.set_editor_property('convex_elems',[]);body.set_editor_property('agg_geom',agg);body.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
    slots=list(m.static_materials)
    for slot in slots:
        info=slot.get_editor_property('uv_channel_data');info.set_editor_property('bOverrideDensities',not row.get('preserve_source_uv',False))
        if not row.get('preserve_source_uv',False):info.set_editor_property('LocalUVDensities',[100.,0.,0.,0.])
    m.set_editor_property('static_materials',slots)
    E.set_metadata_tag(m,'VillageLoftOwner','BlacksmithLoftR3_20261117');save(m)
    report['saved'].append({'path':path,'role':row['role'],'source_triangles':row['lods'][0]['triangles'],'lods':3,'collision_boxes':len(boxes)})
    receipt.write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('BLACKSMITH_LOFT_R3_ASSETS_SAVED '+str(len(report['saved'])))
