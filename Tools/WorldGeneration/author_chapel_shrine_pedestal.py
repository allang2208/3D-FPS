"""Build the requested round weathered stone plinth. Asset production only."""
import json
import math
import os
import runpy
from pathlib import Path
import unreal as u

ROOT=Path(os.environ.get('CHAPEL_SHRINE_SOURCE_ROOT',u.Paths.convert_relative_path_to_full(u.Paths.project_dir())))
OUT=Path(os.environ.get('CHAPEL_SHRINE_OUTPUT',str(ROOT/'SourceAssets/ChapelShrineForecourt20261116/WallStoneR3')))
OUT.mkdir(parents=True,exist_ok=True)
DEST='/Game/WorldGeneration/HillsNightRaid/SM_ChapelShrineRockPedestal'
OWNER='ChapelShrineForecourt20261116'
E=u.EditorAssetLibrary
report={'gameplay_started':False,'saved':[],'statue_scale':2.,'shrines':[],
        'pedestal_height_cm':34.,'buried_cm':4.,'position_chapel_local_cm':[-3140.,0.]}

for row in json.loads((ROOT/'Content/ColdSteelData/shrines.json').read_text(encoding='utf-8'))['statues']:
    statue=u.load_asset(row['mesh'])
    if not statue:raise RuntimeError('Missing shrine dependency '+row['mesh'])
    b=statue.get_bounding_box()
    footprint=math.hypot((b.max.x-b.min.x)*.5,(b.max.y-b.min.y)*.5)*2.
    report['shrines'].append({'id':row['id'],'min':[b.min.x,b.min.y,b.min.z],
        'max':[b.max.x,b.max.y,b.max.z],'new_height_cm':(b.max.z-b.min.z)*2.,
        'pedestal_radius_cm':max(180.,(footprint+25.)/.82)})
stone=runpy.run_path(str(ROOT/'Tools/WorldGeneration/chapel_pedestal_material.py'))['build']()
asset=u.load_asset(DEST) if E.does_asset_exist(DEST) else None
if asset and E.get_metadata_tag(asset,'ChapelShrinePedestalOwner')!=OWNER:
    raise RuntimeError('Preserve unowned pedestal asset')

geometry=runpy.run_path(str(ROOT/'Tools/WorldGeneration/chapel_pedestal_stone_blocks.py'))['build']()
vertices,normals,uv0,uv1,triangles=(geometry[k] for k in ('vertices','normals','uv0','uv1','triangles'))
buffers=u.GeometryScriptSimpleMeshBuffers()
buffers.vertices=[u.Vector(*v) for v in vertices]
buffers.normals=[u.Vector(*n) for n in normals]
buffers.uv0=[u.Vector2D(*v) for v in uv0]
buffers.uv1=[u.Vector2D(*v) for v in uv1]
buffers.vertex_colors=[u.LinearColor(*v) for v in geometry['colors']]
buffers.triangles=[u.IntVector(*t) for t in triangles]
dynamic=u.DynamicMesh()
u.GeometryScript_MeshEdits.append_buffers_to_mesh(dynamic,buffers)
if asset:
    _,result=u.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(dynamic,asset,
        u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True),u.GeometryScriptMeshWriteLOD())
else:
    asset,result=u.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(dynamic,DEST,
        u.GeometryScriptCreateNewStaticMeshAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True,
            enable_collision=True,enable_nanite=False))
if not asset or result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Pedestal mesh creation: '+str(result))
asset.set_material(0,stone)
# Physical UV density lets streaming select clear near-field stone mips.
materials=list(asset.get_editor_property('static_materials'))
info=materials[0].get_editor_property('uv_channel_data')
report['uv_density_before']={k:str(info.get_editor_property(k)) for k in ('bOverrideDensities','LocalUVDensities')}
info.set_editor_property('bOverrideDensities',True)
info.set_editor_property('LocalUVDensities',[50.,34.,0.,0.])
asset.set_editor_property('static_materials',materials)
saved_uv=asset.get_editor_property('static_materials')[0].get_editor_property('uv_channel_data')
report['uv_density']={k:str(saved_uv.get_editor_property(k)) for k in ('bOverrideDensities','LocalUVDensities')}
if not saved_uv.get_editor_property('bOverrideDensities') or list(saved_uv.get_editor_property('LocalUVDensities'))!=[50.,34.,0.,0.]:
    raise RuntimeError('Stone UV streaming density did not persist')
body=asset.get_editor_property('body_setup')
body.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
E.set_metadata_tag(asset,'ChapelShrinePedestalOwner',OWNER)
package=u.load_package(DEST)
if not u.EditorLoadingAndSavingUtils.save_packages([package],False):raise RuntimeError('Pedestal save failed')
report['saved'].append(asset.get_path_name())
report['material']=stone.get_path_name();report['triangles']=len(triangles)
report['revision']='WallStoneR3';report['stone_courses']=geometry['rows'];report['winding']='engine_static_mesh_clockwise'
(OUT/'pedestal-mesh-source.json').write_text(json.dumps(geometry),encoding='utf-8')
(OUT/'authoring-receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('CHAPEL_SHRINE_PEDESTAL_SAVED '+json.dumps(report,ensure_ascii=False))
