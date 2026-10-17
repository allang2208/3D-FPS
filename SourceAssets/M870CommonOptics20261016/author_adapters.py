"""M870 native-rail saddles. Optic shells, glass, markings and rig stay intact."""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;X=O/'Exports';X.mkdir(exist_ok=True)
C=json.loads((O/'inputs.json').read_text())
# Metres in the optical frame. Existing feet are centered on the usable rail;
# body height permits the original jaws to wrap around the saddle's shoulders.
SPECS={
 'holographic':(.01386495,.0015,-.0480,.0202,.001929),
 'eoth_holographic':(-.00315245,.0055,-.0320,.0390,.001374),
 'panoramic_red_dot':(0,.0015,-.0231,.0231,.0025),
 'prism_scope_2x':(0,.0015,-.0253,.0253,.00125),
 'lpvo_1_6x':(.014,.0015,-.0480,.0200,.00125),
 'thermal_scope':(0,.0035,-.0216,.0216,0),
}
R={'parts':{},'rail_center_component_cm':[0,1.88748126,-70.752369],
   'rail_crown_half_width_mm':7.254785,'rail_wing_half_width_mm':9.64036,
   'usable_rail_length_mm':90.7226354,'gameplay_tested':False}
def active(o):
 bpy.ops.object.select_all(action='DESELECT');o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o
def mesh(name,vs,fs):
 me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.update()
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
 ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob);return ob
def extrude(name,x0,x1,profile):
 n=len(profile)
 return mesh(name,[(x,y,z) for x in (x0,x1) for y,z in profile],
  [tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)])
def finish(ob,width=.00004):
 active(ob);b=ob.modifiers.new('Machined edge radius','BEVEL');b.width=width;b.segments=2
 bpy.ops.object.modifier_apply(modifier=b.name)
 for f in ob.data.polygons:f.use_smooth=True
 ob.data.set_sharp_from_angle(angle=math.radians(38))
 n=ob.modifiers.new('Planar normals','WEIGHTED_NORMAL');n.keep_sharp=True
 bpy.ops.object.modifier_apply(modifier=n.name)
def source_tree(key):
 bpy.ops.import_scene.fbx(filepath=C['assets'][key]['fbx'],use_anim=False,use_custom_normals=True)
 obs=[o for o in bpy.context.scene.objects if o.type=='MESH']
 vs=[];fs=[]
 for ob in obs:
  start=len(vs);vs.extend(tuple(ob.matrix_world@v.co) for v in ob.data.vertices)
  fs.extend(tuple(start+i for i in p.vertices) for p in ob.data.polygons)
 return BVHTree.FromPolygons(vs,fs),obs
ys=[-.0103,-.0100,-.0093,-.0090,-.0086,-.0083,-.0080,-.006,0,.006,.0080,.0083,.0086,.0090,.0093,.0100,.0103]
for key,(dx,dz,x0,x1,roof) in SPECS.items():
 bpy.ops.wm.read_factory_settings(use_empty=True);tree,donors=source_tree(key)
 # A ruled saddle follows the underside of the *actual* foot. Its central
 # roof cap keeps release channels open; downward samples form the pockets
 # for the source recoil bar. This does not scale or alter the optic mesh.
 count=math.ceil((x1-x0)/.0005)+1;vs=[];n=len(ys)+2
 for i in range(count):
  x=x0+(x1-x0)*i/(count-1)
  profile=[(-.0069,-.00002)]
  for y in ys:
   hit=tree.ray_cast(Vector((x,y,-.020)),Vector((0,0,1)),.04)[0]
   z=min(roof,hit.z if hit else roof)+dz+.000015
   profile.append((y,z))
  profile.append((.0069,-.00002))
  vs.extend((x+dx,y,z) for y,z in profile)
 fs=[tuple(range(n-1,-1,-1)),tuple(range((count-1)*n,count*n))]
 for i in range(count-1):
  fs.extend((i*n+j,i*n+(j+1)%n,(i+1)*n+(j+1)%n,(i+1)*n+j) for j in range(n))
 core=mesh('Foot-matched dovetail saddle',vs,fs);finish(core,.000025);parts=[core]
 # Two short clamp pairs match the native trapezoidal rail, not Super90's
 # narrower rail. Their inner sloping face bears on the 19.28 mm rail wing.
 for x in (x0+dx+.007,x1+dx-.007):
  for side in (-1,1):
   profile=[(side*y,z) for y,z in [(.00724,.00004),(.00963,-.00255),(.00966,-.00335),(.0115,-.00335),(.0115,.0007),(.00724,.0007)]]
   ob=extrude('Rail clamp jaw',x-.0035,x+.0035,profile);finish(ob,.00007);parts.append(ob)
   bpy.ops.mesh.primitive_cylinder_add(vertices=12,radius=.00125,depth=.0011,
    location=(x,side*.0117,-.00125),rotation=(math.pi/2,0,0))
   ob=bpy.context.object;ob.name='Captive clamp screw';bpy.ops.object.transform_apply(location=True,rotation=True,scale=True);finish(ob,.00007);parts.append(ob)
 bpy.ops.object.select_all(action='DESELECT')
 for ob in parts:ob.select_set(True)
 bpy.context.view_layer.objects.active=core;bpy.ops.object.join();core.name='SM_M870_OpticSeat_'+key
 tri=core.modifiers.new('Export triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
 uv=core.data.uv_layers.new(name='UV0')
 for face in core.data.polygons:
  axes=sorted(range(3),key=lambda k:abs(face.normal[k]))[:2]
  for li in face.loop_indices:
   p=core.data.vertices[core.data.loops[li].vertex_index].co;uv.data[li].uv=(p[axes[0]]/.04+.5,p[axes[1]]/.04+.5)
 core.data.materials.clear();mat=bpy.data.materials.new('M870_AdapterSteel');mat.diffuse_color=(.035,.041,.046,1);core.data.materials.append(mat)
 fb=X/(core.name+'.fbx')
 bpy.ops.export_scene.fbx(filepath=str(fb),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,use_tspace=True,mesh_smooth_type='FACE')
 # Editable fitted assembly in the same local reference frame, no renders.
 for ob in donors:ob.location+=Vector((dx,0,dz))
 bpy.context.preferences.filepaths.save_version=0
 bpy.ops.wm.save_as_mainfile(filepath=str(X/('M870_'+key+'_Editable.blend')))
 R['parts'][key]={'fbx':str(fb),'optic_offset_cm':[dx*100,0,dz*100],
  'bearing_length_mm':(x1-x0)*1000,'triangles':len(core.data.polygons)}
 print('M870_ADAPTER_AUTHORED',key,flush=True)
(O/'authoring.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
