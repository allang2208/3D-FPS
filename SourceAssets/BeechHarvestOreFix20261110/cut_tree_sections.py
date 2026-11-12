"""Author matching lower/upper tree sections from the retained editor source FBXs."""
import bpy,bmesh,json
from pathlib import Path
from mathutils import Matrix
ROOT=Path(__file__).parent;OUT=ROOT/'FellingCut'/'Delivery';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
report={};end=bpy.data.materials.new('CutEndGrain')
for kind in 'ABCD':
    before=set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(ROOT/'FellingCut'/('SourceTree_'+kind+'.fbx')),use_anim=False)
    created=set(bpy.data.objects)-before;meshes=[o for o in created if o.type=='MESH']
    bpy.ops.object.select_all(action='DESELECT')
    for obj in meshes:
        matrix=obj.matrix_world.copy();obj.parent=None;obj.data.transform(matrix);obj.matrix_world=Matrix.Identity(4)
        obj.modifiers.clear();obj.select_set(True)
    bpy.context.view_layer.objects.active=meshes[0]
    if len(meshes)>1:bpy.ops.object.join()
    source=bpy.context.object;source.name='OriginalFullTree_'+kind
    # Stable channel names keep the first source UV as UV0 through FBX import.
    for index,uv in enumerate(source.data.uv_layers):uv.name='UVMap' if index==0 else 'UVMap_'+str(index)
    source.data.uv_layers.active_index=0;source.data.uv_layers[0].active_render=True
    pieces=[]
    for upper in (False,True):
        obj=source.copy();obj.data=source.data.copy();bpy.context.collection.objects.link(obj)
        obj.name=('SM_CutUpper_' if upper else 'SM_CutStump_')+kind
        cap_index=len(obj.data.materials);obj.data.materials.append(end)
        bm=bmesh.new();bm.from_mesh(obj.data)
        bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,
            plane_co=(0,0,.42),plane_no=(0,0,1),clear_inner=upper,clear_outer=not upper)
        bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-5)
        edges=[e for e in bm.edges if e.is_boundary and all(abs(v.co.z-.42)<1e-5 for v in e.verts)]
        caps=bmesh.ops.holes_fill(bm,edges=edges,sides=0)['faces']
        if not caps:raise RuntimeError('Cannot cap '+obj.name)
        boundary={v for f in caps for v in f.verts}
        cx=(min(v.co.x for v in boundary)+max(v.co.x for v in boundary))*.5
        cy=(min(v.co.y for v in boundary)+max(v.co.y for v in boundary))*.5
        diameter=max(max(v.co.x for v in boundary)-min(v.co.x for v in boundary),max(v.co.y for v in boundary)-min(v.co.y for v in boundary))
        layers=list(bm.loops.layers.uv.values());bm.normal_update()
        for face in caps:
            face.material_index=cap_index;face.smooth=False
            if (upper and face.normal.z>0) or (not upper and face.normal.z<0):face.normal_flip()
            # End-grain mapping is valid in every channel, including lightmap/wind
            # channels inherited from the tree. Bark UV data is left intact.
            for loop in face.loops:
                for uv in layers:loop[uv].uv=(.5+(loop.vert.co.x-cx)/diameter,.5+(loop.vert.co.y-cy)/diameter)
        bmesh.ops.triangulate(bm,faces=caps,quad_method='BEAUTY',ngon_method='BEAUTY')
        bm.to_mesh(obj.data);bm.free();obj.data.update()
        bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
        # Restore the source's custom tree normals on the retained surface.
        normals=obj.modifiers.new('PreserveSourceNormals','DATA_TRANSFER');normals.object=source
        normals.use_loop_data=True;normals.data_types_loops={'CUSTOM_NORMAL'};normals.loop_mapping='POLYINTERP_NEAREST'
        bpy.ops.object.modifier_apply(modifier=normals.name)
        values=[n.vector[:] for n in obj.data.corner_normals]
        for face in obj.data.polygons:
            if face.material_index==cap_index:
                for index in face.loop_indices:values[index]=(0,0,-1 if upper else 1)
        obj.data.normals_split_custom_set(values)
        # FBX may drop unused foliage slots; import bindings use slot names.
        bpy.ops.export_scene.fbx(filepath=str(OUT/(obj.name+'.fbx')),use_selection=True,object_types={'MESH'},
            apply_unit_scale=True,axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE')
        report[obj.name]={'triangles':sum(len(f.vertices)-2 for f in obj.data.polygons),
            'materials':[m.name for m in obj.data.materials],'cut_height_cm':42,'upper':upper,
            'dimensions_m':list(obj.dimensions)}
        pieces.append(obj)
    source.hide_set(True);source.hide_render=True
bpy.ops.wm.save_as_mainfile(filepath=str(OUT.parent/'MatchedTreeSections.blend'))
(OUT/'authoring.json').write_text(json.dumps(report,indent=2))
print('MATCHED_TREE_SECTIONS_AUTHORED',json.dumps(report),flush=True)
