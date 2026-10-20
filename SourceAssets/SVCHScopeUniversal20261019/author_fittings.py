"""Retain the package optic; author only host interfaces and icon source."""
import bpy,bmesh,json,math,runpy
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;P=O.parents[1];X=O/'Exports';X.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(O/'KVScope_Source_Editable.blend'),load_ui=False)
bpy.context.preferences.filepaths.save_version=0
base=bpy.data.objects['SM_KVScope_Common'];base.name='KVScope_Source';base.hide_render=False
report={'meshes':{},'runtime_tested':False,'source_geometry_preserved':True}
source=json.loads((O/'source_report.json').read_text())
points={k:Vector((source[k][0]*.01,-source[k][1]*.01,source[k][2]*.01)) for k in ('SightRear','SightFront')}
points['SightUp']=points['SightRear']+Vector((0,0,.01))
steel=bpy.data.materials.new('KV_AdapterSteel');steel.use_nodes=True
steel.node_tree.nodes.clear();bs=steel.node_tree.nodes.new('ShaderNodeBsdfPrincipled');out=steel.node_tree.nodes.new('ShaderNodeOutputMaterial');steel.node_tree.links.new(bs.outputs[0],out.inputs[0]);bs.inputs['Base Color'].default_value=(.028,.032,.036,1);bs.inputs['Roughness'].default_value=.38;bs.inputs['Metallic'].default_value=.8
def active(obs):
    bpy.ops.object.select_all(action='DESELECT')
    for o in obs:o.hide_set(False);o.select_set(True)
    bpy.context.view_layer.objects.active=obs[0]
def finish(o):
    active([o]);m=o.modifiers.new('Machined edges','BEVEL');m.width=.00012;m.segments=3;bpy.ops.object.modifier_apply(modifier=m.name)
    uv=o.data.uv_layers.new(name='UV0')
    for f in o.data.polygons:
        axes=sorted(range(3),key=lambda k:abs(f.normal[k]))[:2]
        for li in f.loop_indices:
            p=o.data.vertices[o.data.loops[li].vertex_index].co;uv.data[li].uv=(p[axes[0]]/.04,p[axes[1]]/.04)
    o.data.materials.append(steel);return o
def box(name,pos,size):
    bpy.ops.mesh.primitive_cube_add(size=1,location=pos);o=bpy.context.object;o.name=name;o.scale=size
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True);return finish(o)
def extrude(name,x0,x1,profile):
    n=len(profile);v=[(x,y,z) for x in (x0,x1) for y,z in profile];f=[tuple(range(n-1,-1,-1)),tuple(range(n,n*2))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    me=bpy.data.meshes.new(name);me.from_pydata(v,[],f);me.update();bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);return finish(o)
def export(key,obs,T=Matrix.Identity(4),optic=True):
    active(obs)
    if len(obs)>1:bpy.ops.object.join()
    o=bpy.context.object;o.name='SM_KVScope_'+key;o.data.transform(T)
    f=X/(o.name+'.fbx');bpy.ops.export_scene.fbx(filepath=str(f),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
    bpy.data.libraries.write(str(X/(o.name+'.blend')),{o},fake_user=True)
    report['meshes'][key]={'fbx':str(f),'name':o.name,'sockets':{k:[(T@p).x*100,-(T@p).y*100,(T@p).z*100] for k,p in points.items()} if optic else {}}
    o.hide_render=True;o.hide_set(True)
def copybody():
    o=base.copy();o.data=base.data.copy();bpy.context.collection.objects.link(o);o.hide_set(False);o.hide_render=False;return o
export('Common',[copybody()])
# M16's existing carry-handle frame is retained, including its locking shoe.
parts=[copybody(),box('Carry handle rail',(0,0,-.003),(.17,.021,.006)),box('Carry handle saddle',(.012,0,-.0075),(.105,.013,.005)),box('Handle locking shoe',(.008,0,-.016),(.024,.018,.004))]
for x in [-.060,-.032,-.004,.024,.052,.080]:parts.append(box('Rail lug',(x,0,-.0008),(.009,.023,.0016)))
export('M16',parts)
# ASH carry-handle crown is 2.95 mm below its optical reference; support both feet.
parts=[copybody()]
for x0,x1 in [(-.0247,.021),(.055,.0842)]:
    parts.append(box('ASH crown shoe',((x0+x1)*.5,0,-.001475),(x1-x0,.0209,.00295)))
export('ASH12',parts)
# HK416 assets use whole-weapon component coordinates, not the common frame.
H=json.loads((P/'SourceAssets/HK416Reworked20260930/authoring.json').read_text())
T=Matrix.Rotation(-math.pi/2,4,'Z');T.translation=Matrix(H['source_to_weapon_root'])@Vector((0,.001,.0297297));T.translation.y-=.028
export('HK416',[copybody()],Matrix(H['root_matrix'])@T)
# Full-size scope feet span 108.9 mm; these 120 mm upper rails bridge the
# short native rails. Lower jaw profiles come from each accepted host authoring.
profiles={
 'RSH12':[(.0056,.00005),(.0084,-.00195),(.00715,-.00425),(.0105,-.00425),(.0110,.0018),(.0080,.0030)],
 'M870':[(.00724,.00004),(.00963,-.00255),(.00966,-.00335),(.0115,-.00335),(.0115,.0007),(.00724,.0007)],
 'Super90':[(.0058,.0002),(.0076,-.0019),(.0078,-.0039),(.0093,-.0039),(.0093,.0038),(.0061,.0038)]}
for key,profile in profiles.items():
    parts=[extrude('Continuous rail web',-.060,.060,[(-.0069,.00005),(.0069,.00005),(.0071,.0052),(-.0071,.0052)])]
    # The common body is shifted -29.75 mm to center its two feet on the host.
    # Upper teeth leave real recoil slots, including beneath both source shoes.
    for i in range(12):
        x=-.055+i*.010
        parts.append(extrude('Upper rail tooth',x-.0029,x+.0029,[(-.007,.005),(.007,.005),(.0106,.006),(.0101,.008),(-.0101,.008),(-.0106,.006)]))
    for x in (-.0184,.0184):
        for side in (-1,1):
            parts.append(extrude('Native clamp',x-.0045,x+.0045,[(side*y,z) for y,z in profile]))
            bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=.0017,depth=.0012,location=(x,side*(max(y for y,z in profile)+.0005),-.0006),rotation=(math.pi/2,0,0))
            o=bpy.context.object;bpy.ops.object.transform_apply(location=True,rotation=True,scale=True);parts.append(finish(o))
    export('Seat'+key,parts,optic=False)
(O/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
# A single real-model side source for the new shared gunsmith icon.
base.hide_set(False);base.hide_render=False
G=runpy.run_path(str(P/'skills/ue5-weapon-workflow/scripts/apply_modification_icon_grayscale.py'))
G['apply_grayscale']([base]);s=bpy.context.scene;G['neutral_output'](s)
s.render.resolution_x=s.render.resolution_y=1024;s.cycles.samples=48
c=s.camera;c.location=(0,.5,.035);c.rotation_euler=(Vector((-.015,0,.035))-c.location).to_track_quat('-Z','Y').to_euler();c.data.ortho_scale=.29
s.render.filepath=str(O/'scope_icon_source.png');bpy.ops.wm.save_as_mainfile(filepath=str(O/'KVScope_Fittings_Editable.blend'));bpy.ops.render.render(write_still=True)
print('KV_SCOPE_FITTINGS_AUTHORED',len(report['meshes']),flush=True)
