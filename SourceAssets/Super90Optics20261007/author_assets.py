"""Author rail shoes and the retained native mesh's factory sight section."""
import bpy,bmesh,json,math,shutil,sys
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent;P=O.parents[1];S=O.parent/'BenelliM4Super9020261006';X=O/'Exports';X.mkdir(exist_ok=True)
B=O/'Before';B.mkdir(exist_ok=True);sys.path.insert(0,str(O));from factory_sights import tag_factory_sights
file=S/'Exports/SK_Super90_V7.fbx';blend=S/'Super90_Gameplay_Editable.blend'
for path in (file,blend):
    if not (B/path.name).exists():shutil.copy2(path,B/path.name)
bpy.ops.wm.open_mainfile(filepath=str(blend));s=bpy.context.scene;r=bpy.data.objects['SK_Super90']
action=r.animation_data.action;slot=r.animation_data.action_slot;frame=s.frame_current;r.animation_data.action=None
for b in r.pose.bones:b.matrix_basis=Matrix.Identity(4)
parts=[bpy.data.objects['Super90_'+n] for n in ('body','bolt','loading_gate','trigger')]
count=tag_factory_sights(parts)
bpy.ops.object.select_all(action='DESELECT')
for ob in [r]+parts+[bpy.data.objects['12g_12gauge_0']]+[o for o in s.objects if o.type=='MESH' and o.name.startswith('Super90_V7_')]:ob.hide_set(False);ob.select_set(True)
bpy.context.view_layer.objects.active=r
bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
r.animation_data.action=action;r.animation_data.action_slot=slot;s.frame_set(frame)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(blend))
# Measured native receiver rail: y -8.750..5.123 cm, crown z -71.8131 cm.
# All shoes use canonical +X forward/+Z up, with cm conversion on FBX export.
specs={'holographic':(.078,.043,2.260,.68195),'panoramic_red_dot':(.062,.024,0.,.65),
       'prism_scope_2x':(.062,.024,0.,.65),'lpvo_1_6x':(.082,.024,1.4,.65),
       'eoth_holographic':(.085,.040,-2.6,.65)}
report={'rail_center_component_cm':[0.,1.81334,-71.813124],'forward_component':[0,-1,0],'up_component':[0,0,1],
        'factory_sight_faces':count,'mesh_fbx':str(file),'parts':{},'runtime_tested':False}
for key,(length,width,xoffset,zoffset) in specs.items():
    bpy.ops.wm.read_factory_settings(use_empty=True);objects=[]
    def extrude(name,x0,x1,profile):
        n=len(profile);vs=[(x,y,z) for x in (x0,x1) for y,z in profile]
        faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
        me=bpy.data.meshes.new(name);me.from_pydata(vs,[],faces);me.update()
        bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
        ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob);objects.append(ob)
    # Broad feet receive a thin sloped shoulder; the narrower lower jaws grip
    # the measured 15.06 mm rail without changing the optic's physical size.
    extrude('Sloped receiver saddle',-length/2,length/2,[(-.0060,0),(.0060,0),(width/2,.0048),(width/2,.0065),(-width/2,.0065),(-width/2,.0048)])
    jaw=[(.0058,.0002),(.0076,-.0019),(.0078,-.0039),(.0093,-.0039),(.0093,.0038),(.0061,.0038)]
    for x in (-.021,.021):
        for sign in (-1,1):
            extrude('Clamp jaw',x-.0045,x+.0045,[(sign*y,z) for y,z in jaw])
            bpy.ops.mesh.primitive_cylinder_add(vertices=16,radius=.0021,depth=.0014,location=(x,sign*.0098,-.0005),rotation=(math.pi/2,0,0))
            screw=bpy.context.object;bpy.ops.object.transform_apply(location=True,rotation=True,scale=True);objects.append(screw)
    for ob in objects:
        bpy.context.view_layer.objects.active=ob;bevel=ob.modifiers.new('Machined edge','BEVEL');bevel.width=.00016;bevel.segments=2;bpy.ops.object.modifier_apply(modifier=bevel.name)
    bpy.ops.object.select_all(action='DESELECT')
    for ob in objects:ob.select_set(True)
    bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join();ob=bpy.context.object;ob.name='SM_Super90_Rail_'+key
    tri=ob.modifiers.new('Tangent triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
    uv=ob.data.uv_layers.new(name='UV0')
    for face in ob.data.polygons:
        axes=sorted(range(3),key=lambda k:abs(face.normal[k]))[:2]
        for li in face.loop_indices:
            v=ob.data.vertices[ob.data.loops[li].vertex_index].co;uv.data[li].uv=(v[axes[0]]/.04+.5,v[axes[1]]/.04+.5)
    ob.data.materials.append(bpy.data.materials.new('Super90_RailSteel'))
    fb=X/(ob.name+'.fbx');bpy.ops.export_scene.fbx(filepath=str(fb),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,use_tspace=True,mesh_smooth_type='FACE')
    bpy.ops.wm.save_as_mainfile(filepath=str(X/(ob.name+'.blend')))
    report['parts'][key]={'fbx':str(fb),'optic_offset_cm':[xoffset,0,zoffset],'shoe_length_cm':length*100,'shoe_width_cm':width*100}
(O/'authoring.json').write_text(json.dumps(report,indent=2))
print('SUPER90_OPTICS_AUTHORED',count,len(specs),flush=True)
