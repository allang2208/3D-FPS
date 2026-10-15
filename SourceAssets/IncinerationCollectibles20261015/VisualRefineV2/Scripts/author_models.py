"""Create editable manufactured parts and game exports. Does not render or run the game."""
from pathlib import Path
import bpy, sys, json
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Scripts'))
import geometry as H
from models import BUILDERS
for folder in ('Authored','Export','Receipts'):(ROOT/folder).mkdir(exist_ok=True)
report={'stage':'authoring','assets':{},'preview_rendered':False,'runtime_tested':False,'inventory_integrated':False}
for key,builder in BUILDERS.items():
    print('INCINERATION_MODEL_START',key,flush=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.01
    H.PARTS=[];H.COLLISIONS=[];H.MAT=H.material(key)
    builder();bpy.context.view_layer.update()
    spec=H.SPEC['assets'][key]
    source=ROOT/'Authored'/(spec['mesh']+'_Source.blend')
    scene['asset_stage']='Editable manufactured master; no visual or runtime acceptance'
    scene['unit_contract']='centimetres; +Z up; game pivot bottom centre'
    bpy.ops.wm.save_as_mainfile(filepath=str(source))
    deps=bpy.context.evaluated_depsgraph_get();exports=[]
    features=[o.name for o in H.PARTS]
    for o in H.PARTS:
        data=bpy.data.meshes.new_from_object(o.evaluated_get(deps),preserve_all_data_layers=True,depsgraph=deps)
        e=bpy.data.objects.new(o.name+'_Export',data);bpy.context.collection.objects.link(e);e.matrix_world=o.matrix_world.copy()
        H.select(e)
        part_tri=e.modifiers.new('Triangulate before surface projection','TRIANGULATE');part_tri.keep_custom_normals=True
        bpy.ops.object.modifier_apply(modifier=part_tri.name)
        if not o.get('authored_decal'):H.uv(e,o['surface_region'])
        exports.append(e)
    bpy.ops.object.select_all(action='DESELECT')
    for e in exports:e.select_set(True)
    bpy.context.view_layer.objects.active=exports[0];bpy.ops.object.join();game=bpy.context.object;game.name=spec['mesh']
    game.data.transform(game.matrix_world);game.matrix_world=Matrix.Identity(4)
    game.data.materials.clear();game.data.materials.append(H.MAT)
    for f in game.data.polygons:f.material_index=0
    tri=game.modifiers.new('Production triangulation','TRIANGULATE');tri.quad_method='FIXED';tri.ngon_method='BEAUTY';tri.keep_custom_normals=True
    bpy.ops.object.modifier_apply(modifier=tri.name)
    game.data.calc_tangents(uvmap=game.data.uv_layers.active.name)
    pts=[v.co for v in game.data.vertices]
    lo=Vector([min(p[k] for p in pts) for k in range(3)]);hi=Vector([max(p[k] for p in pts) for k in range(3)])
    shift=Vector((-(lo.x+hi.x)/2,-(lo.y+hi.y)/2,-lo.z))
    game.data.transform(Matrix.Translation(shift));dimensions=hi-lo
    game.data.calc_loop_triangles();triangles=len(game.data.loop_triangles)
    collisions=[]
    for i,desc in enumerate(H.COLLISIONS):
        p,size=desc[:2];bpy.ops.mesh.primitive_cube_add(size=1,location=Vector(p)+shift)
        c=bpy.context.object;c.name='UCX_'+game.name+'_'+str(i).zfill(2);c.scale=size
        if len(desc)>2:c.rotation_euler['XYZ'.index(desc[2][0])]=desc[2][1]
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);collisions.append(c)
    H.select(game)
    for c in collisions:c.select_set(True)
    fbx=ROOT/'Export'/(game.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},global_scale=1,apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_ALL',axis_forward='-Y',axis_up='Z',bake_space_transform=True,
        mesh_smooth_type='FACE',use_mesh_modifiers=True,use_tspace=True,path_mode='STRIP',add_leaf_bones=False)
    H.select(game);scene.unit_settings.scale_length=1;game.scale=(.01,.01,.01)
    glb=ROOT/'Export'/(game.name+'.glb')
    bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_materials='EXPORT')
    report['assets'][key]={**spec,'source':str(source),'fbx':str(fbx),'glb':str(glb),'triangles_lod0':triangles,
         'source_components':len(H.PARTS),'actual_dimensions_cm':list(dimensions),'collision_hulls':len(collisions),
         'geometry_features':features,'pivot':'bottom centre','nanite_requested':True}
    (ROOT/'model_manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print('INCINERATION_MODEL_EXPORTED',key,triangles,list(dimensions),flush=True)
report['stage']='sources_and_exports_saved'
(ROOT/'model_manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('INCINERATION_MODELS_COMPLETE',len(report['assets']),flush=True)
