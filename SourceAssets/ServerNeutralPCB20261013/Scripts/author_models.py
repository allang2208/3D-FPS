"""Author and export all eight server collectibles; no preview or gameplay run."""
from pathlib import Path
import bpy, sys, json
from mathutils import Matrix, Vector

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Scripts'))
import mesh_helpers as H
from hardware_parts import pcb_uv
from models_storage import BUILDERS as STORAGE
from models_cards import BUILDERS as CARDS
BUILDERS={key:builder for key,builder in {**STORAGE,**CARDS}.items() if key in ('NIC','CPU','RAID')}
SPEC=H.SPEC
report=dict(stage='authoring',assets={},preview_rendered=False,runtime_tested=False)
for key,builder in BUILDERS.items():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.01
    H.REGIONS=SPEC['assets'][key]['regions'];H.PARTS=[];H.MAT=H.make_material(key);builder()
    source=ROOT/'Authored'/(SPEC['assets'][key]['mesh']+'_Source.blend')
    bpy.ops.object.select_all(action='DESELECT')
    for obj in H.PARTS:
        obj.select_set(True)
        if obj.get('pcb_surface'):pcb_uv(obj)
    bpy.context.view_layer.objects.active=H.PARTS[0]
    bpy.ops.wm.save_as_mainfile(filepath=str(source))
    deps=bpy.context.evaluated_depsgraph_get();parts=[]
    for obj in H.PARTS:
        mesh=bpy.data.meshes.new_from_object(obj.evaluated_get(deps),preserve_all_data_layers=True,depsgraph=deps)
        export=bpy.data.objects.new(obj.name+'_Export',mesh);bpy.context.collection.objects.link(export)
        export.matrix_world=obj.matrix_world.copy()
        if obj.modifiers:H.project_uv(export,obj['surface_region'])
        if obj.get('pcb_surface'):pcb_uv(export)
        parts.append(export)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in parts:obj.select_set(True)
    bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();game=bpy.context.object
    game.name=SPEC['assets'][key]['mesh'];game.data.transform(game.matrix_world);game.matrix_world=Matrix.Identity(4)
    game.data.materials.clear();game.data.materials.append(H.MAT)
    for face in game.data.polygons:face.material_index=0
    tri=game.modifiers.new('Stable export triangulation','TRIANGULATE');tri.quad_method='FIXED';tri.ngon_method='BEAUTY'
    bpy.ops.object.modifier_apply(modifier=tri.name)
    points=[v.co for v in game.data.vertices]
    low=Vector([min(v[i] for v in points) for i in range(3)]);high=Vector([max(v[i] for v in points) for i in range(3)])
    shift=Vector((-(low.x+high.x)*.5,-(low.y+high.y)*.5,-low.z))
    game.data.transform(Matrix.Translation(shift));low+=shift;high+=shift
    extent=high-low;game.data.calc_loop_triangles();triangles=len(game.data.loop_triangles)
    bpy.ops.mesh.primitive_cube_add(size=1,location=(low+high)*.5);collision=bpy.context.object
    collision.name='UCX_'+game.name+'_00';collision.scale=extent
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    H.select(game);collision.select_set(True)
    fbx=ROOT/'Export'/(game.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},global_scale=1,
        apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',axis_forward='-Y',axis_up='Z',
        bake_space_transform=True,mesh_smooth_type='FACE',use_mesh_modifiers=True,use_tspace=True,path_mode='STRIP',add_leaf_bones=False)
    H.select(game);game.scale=(.01,.01,.01);scene.unit_settings.scale_length=1
    glb=ROOT/'Export'/(game.name+'.glb')
    bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_materials='EXPORT')
    report['assets'][key]={**SPEC['assets'][key],
        'source':str(source),'fbx':str(fbx),'glb':str(glb),'triangles_lod0':triangles,
        'actual_dimensions_cm':list(extent),'source_components':len(H.PARTS),
        'collision':'one authored UCX box','pivot':'Game exports bottom centred, +Z up',
        'geometry_features':[obj.name for obj in H.PARTS]}
    (ROOT/'model_manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('SERVER_MODEL_EXPORTED',key,triangles,list(extent),flush=True)
report['stage']='sources_and_exports_saved'
(ROOT/'model_manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('SERVER_MODELS_COMPLETE',len(report['assets']),flush=True)
