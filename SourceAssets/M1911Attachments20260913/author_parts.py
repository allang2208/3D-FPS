"""Preserve shared attachment geometry and UV0; add physical coating UVs."""
import bpy,bmesh,json,math
from pathlib import Path
O=Path(__file__).parent;bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.read_factory_settings(use_empty=True)
sources=json.loads((O/'sources.json').read_text())['parts'];report={}
def finish(ob):
    bpy.context.view_layer.objects.active=ob
    bevel=ob.modifiers.new('Machined adapter edge','BEVEL');bevel.width=.00035;bevel.segments=3
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    return ob
def block(name,center,size,material):
    bpy.ops.mesh.primitive_cube_add(size=1,location=center);ob=bpy.context.object;ob.name=name;ob.dimensions=size
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True);ob.data.materials.append(material)
    return finish(ob)
def tube(name,profile,material):
    n=96;verts=[(r*math.cos(2*math.pi*i/n),y,r*math.sin(2*math.pi*i/n)) for y,r in profile for i in range(n)]
    faces=[(j*n+i,j*n+(i+1)%n,((j+1)%len(profile))*n+(i+1)%n,((j+1)%len(profile))*n+i) for j in range(len(profile)) for i in range(n)]
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    for f in bm.faces:f.smooth=True
    for e in bm.edges:e.smooth=e.is_manifold and e.calc_face_angle(0)<.6
    bm.to_mesh(me);bm.free();ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob);me.materials.append(material)
    return finish(ob)
for key,info in sources.items():
    before=set(bpy.context.scene.objects);bpy.ops.import_scene.fbx(filepath=info['fbx'])
    obs=[o for o in bpy.context.scene.objects if o not in before and o.type=='MESH']
    bpy.ops.object.select_all(action='DESELECT')
    for ob in obs:ob.select_set(True)
    bpy.context.view_layer.objects.active=obs[0]
    if len(obs)>1:bpy.ops.object.join()
    ob=bpy.context.object;ob.name='M1911_'+key;bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    original_slots=[m.name for m in ob.data.materials]
    adapter=bpy.data.materials.get('M1911_AdapterSteel') or bpy.data.materials.new('M1911_AdapterSteel')
    parts=[ob]
    if key=='suppressor':
        # The common can's original 11 mm exit is opened to 13 mm for the .45 variant.
        for v in ob.data.vertices:
            r=math.hypot(v.co.x,v.co.z)
            if v.co.y>.165 and 0<r<.008:
                v.co.x*=((r+.001)/r);v.co.z*=((r+.001)/r)
        parts.append(tube('M1911_ThreadedBarrelExtension',[(-.0204,.0104),(-.019,.0107),(-.008,.0107),(-.006,.0112),(-.003,.0112),(-.003,.0065),(-.0204,.0065)],adapter))
        for y in [-.016,-.013,-.010]:
            parts.append(tube('M1911_ThreadCollar',[(y-.00035,.01065),(y-.00015,.011),(y+.00015,.011),(y+.00035,.01065)],adapter))
    else:
        # Raised rear-slide saddle clears the retained iron sight. Two feet bear
        # on the slide shoulders; the raised front leaves the ejection port open.
        holo=key=='holographic'
        parts.append(block('M1911_OpticPlatform',(.002,0,-.001),(.078 if holo else .046,.052 if holo else .042,.002),adapter))
        parts.append(block('M1911_SightReliefBridge',(-.003,0,-.0044),(.036,.032,.0048),adapter))
        for side in [-1,1]:
            parts.append(block('M1911_SlideClamp',(-.003,side*.0115,-.009),(.028,.003,.0045),adapter))
    # Join the adapter into each fitted variant; the shared source asset remains intact.
    bpy.ops.object.select_all(action='DESELECT')
    for part in parts:part.select_set(True)
    bpy.context.view_layer.objects.active=ob;bpy.ops.object.join()
    me=ob.data;coords=[v.co.copy() for v in me.vertices]
    uv_index=len(me.uv_layers);uv=me.uv_layers.new(name='M1911CoatingPhysicalUV')
    for face in me.polygons:
        axis=max(range(3),key=lambda i:abs(face.normal[i]));axes=([1,2] if axis==0 else [0,2] if axis==1 else [0,1])
        for li in face.loop_indices:
            v=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(v[axes[0]]/.1+.5,v[axes[1]]/.1+.5)
    me.uv_layers.active_index=0;me.uv_layers[0].active_render=True
    folder=O/'FBX';folder.mkdir(exist_ok=True);dest=folder/(key+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(dest),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
    report[key]={'file':str(dest),'uv_index':uv_index,'physical_tile_m':.1,'export_slots':[m.name for m in me.materials],
                 'source_export_slots':original_slots,'adapter_slot':'M1911_AdapterSteel',
                 'bounds_m':{'min':[min(v[i] for v in coords) for i in range(3)],'max':[max(v[i] for v in coords) for i in range(3)]}}
    ob.hide_set(True);ob.hide_render=True
(O/'authoring.json').write_text(json.dumps(report,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M1911_Attachments_Editable.blend'))
print('M1911_SHARED_PARTS_AUTHORED',flush=True)
