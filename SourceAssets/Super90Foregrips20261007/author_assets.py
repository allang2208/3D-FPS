"""Fit existing common grip bodies to a Super90 underside rail saddle."""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent;S=O.parent;X=O/'Exports';X.mkdir(exist_ok=True)
donors=json.loads((S/'M16UniversalAttachments20260920/authoring.json').read_text())['donors']
sources=json.loads((S/'ASH12UniversalAttachments20260919/sources.json').read_text())
ash=json.loads((S/'ASH12UniversalAttachments20260919/authoring_inputs.json').read_text())
record={'parts':{},'mount_component_cm':[0.,-16.,-80.15],'mount_native':[[0,-1,0,0],[1,0,0,.16],[0,0,1,-.8015],[0,0,0,1]],'runtime_tested':False}
bpy.context.preferences.filepaths.save_version=0
def select(obs):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in obs:ob.hide_set(False);ob.select_set(True)
    bpy.context.view_layer.objects.active=obs[-1]
def extrude(name,x0,x1,section,material):
    n=len(section);me=bpy.data.meshes.new(name)
    me.from_pydata([(x,y,z) for x in (x0,x1) for y,z in section],[],[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)])
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    me.materials.append(material);ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob)
    select([ob]);bevel=ob.modifiers.new('Machined saddle edge','BEVEL');bevel.width=.00018;bevel.segments=2;bpy.ops.object.modifier_apply(modifier=bevel.name)
    return ob
for key in ('vertical','tactical_vertical','canted','prism','angled'):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if key=='angled':
        file=S/'ResonanceGrip20260913/MeshyIntegration/M4/ResonanceGrip_Surface_Editable.blend'
        with bpy.data.libraries.load(str(file),link=False) as (src,dst):dst.objects=['SM_ResonanceGrip']
        ob=dst.objects[0];bpy.context.collection.objects.link(ob);ob.data.transform(ob.matrix_world);ob.parent=None;ob.matrix_world=Matrix.Identity(4)
        ob.data.transform(Matrix(ash['donors']['angled']['mount']).inverted())
    else:
        file=S/'TacticalVerticalForegrip20260919/Integration/M4/Export/SM_TacticalVerticalForegrip.fbx' if key=='tactical_vertical' else Path(sources[key]['fbx'])
        bpy.ops.import_scene.fbx(filepath=str(file),use_custom_normals=True)
        obs=[o for o in bpy.context.scene.objects if o.type=='MESH']
        for ob in obs:ob.data.transform(ob.matrix_world);ob.parent=None;ob.matrix_world=Matrix.Identity(4)
        select(obs)
        if len(obs)>1:bpy.ops.object.join()
        ob=bpy.context.object
    lift=0. if key=='tactical_vertical' else -max(v.co.z for v in ob.data.vertices)
    for v in ob.data.vertices:v.co.z+=lift
    # A 21 mm rail and curved shoe meet the original fore-end underside.
    # The source grip body's dimensions, material islands and UVs are retained.
    mat=bpy.data.materials.new('Super90_Foregrip_Saddle')
    rail=extrude('Underside rail',-.057,.057,[(-.008,0),(.008,0),(.0105,.0018),(.0105,.0035),(-.0105,.0035),(-.0105,.0018)],mat)
    curve=[(y,.03075-.025*math.sqrt(1-(y/.0213)**2)+.00015) for y in (.0105,.007,.0035,0,-.0035,-.007,-.0105)]
    saddle=extrude('Fore-end curved seat',-.057,.057,[(-.0105,.0034),(.0105,.0034)]+curve,mat)
    extras=[rail,saddle]
    for x in (-.041,.041):
        bpy.ops.mesh.primitive_cylinder_add(vertices=16,radius=.0025,depth=.001,location=(x,0,-.0003))
        screw=bpy.context.object;bpy.ops.object.transform_apply(location=True,rotation=True,scale=True);screw.data.materials.append(mat);extras.append(screw)
    for ex in extras:
        for i in range(max(1,len(ob.data.uv_layers))):
            layer=ex.data.uv_layers.get(ob.data.uv_layers[i].name if i<len(ob.data.uv_layers) else 'UVMap') or ex.data.uv_layers.new(name=ob.data.uv_layers[i].name if i<len(ob.data.uv_layers) else 'UVMap')
            for face in ex.data.polygons:
                axes=sorted(range(3),key=lambda k:abs(face.normal[k]))[:2]
                for li in face.loop_indices:
                    p=ex.data.vertices[ex.data.loops[li].vertex_index].co;layer.data[li].uv=(p[axes[0]]/.04+.5,p[axes[1]]/.04+.5)
    select([*extras,ob]);bpy.ops.object.join();ob.name='SM_Super90_'+key
    tri=ob.modifiers.new('Export tangent triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
    bpy.ops.export_scene.fbx(filepath=str(X/(ob.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,use_tspace=True,mesh_smooth_type='FACE')
    bpy.ops.wm.save_as_mainfile(filepath=str(X/(ob.name+'_Editable.blend')))
    family='vertical' if key=='tactical_vertical' else key
    hand=Matrix(donors[family]['hand_in_mount']);hand.translation.z+=lift
    record['parts'][key]={'family':family,'body_lift':lift,'hand_in_mount':list(map(list,hand)),'slots':[m.name for m in ob.data.materials],'source':str(file),'fbx':str(X/(ob.name+'.fbx'))}
    print('SUPER90_FOREGRIP_AUTHORED',key,flush=True)
(O/'models.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
