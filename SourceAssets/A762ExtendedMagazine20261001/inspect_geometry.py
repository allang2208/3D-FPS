"""User-requested curve/seam inspection, offline geometry only; no gameplay."""
import bpy,bmesh,json,sys,math
from pathlib import Path
import numpy as np
from mathutils import Matrix,Vector
O=Path(__file__).parent;P=O.parents[1]
sys.path.insert(0,str(O));import curve as C
bpy.ops.wm.open_mainfile(filepath=str(O/'A762_ExtMag_Continuous07.blend'))
new=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith('A762_')]
for ob in list(bpy.context.scene.objects):
    if ob not in new:bpy.data.objects.remove(ob,do_unlink=True)
F=json.loads((P/'SourceAssets/A762Meshy20260920/Accessories05/authoring_frames.json').read_text())
X=Matrix(F['mag_idle_from_root'])
stats={'curve':C.report(),'geometry':{},'runtime_tested':False,'render':'offline author mesh, same scale and lighting'}
for ob in new:
    if ob.type!='MESH':continue
    bm=bmesh.new();bm.from_mesh(ob.data)
    stats['geometry'][ob.name]={'vertices':len(bm.verts),'faces':len(bm.faces),
        'boundary_edges':sum(e.is_boundary for e in bm.edges),
        'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),
        'zero_area_faces':sum(f.calc_area()<1e-13 for f in bm.faces)}
    ob.data.calc_loop_triangles()
    loops=np.array([t.loops for t in ob.data.loop_triangles])
    uv0=np.array([v.uv[:] for v in ob.data.uv_layers[0].data])[loops]
    a=uv0[:,1]-uv0[:,0];b=uv0[:,2]-uv0[:,0]
    uv_area=np.abs(a[:,0]*b[:,1]-a[:,1]*b[:,0])*.5
    stats['geometry'][ob.name]['collapsed_uv_triangles']=int(np.sum(uv_area<1e-12))
    if ob.name=='A762_ContinuousMagazineShell':
        unseen=set(bm.verts);components=0
        while unseen:
            components+=1;stack=[unseen.pop()]
            while stack:
                for e in stack.pop().link_edges:
                    for v in e.verts:
                        if v in unseen:unseen.remove(v);stack.append(v)
        stats['geometry'][ob.name]['connected_components']=components
    bm.free()
    normals=[(X.inverted().to_3x3().inverted().transposed()@n.vector).normalized() for n in ob.data.corner_normals]
    ob.data.transform(X.inverted());ob.data.normals_split_custom_set(normals)
    ob.location.y=.16+.098

with open(O/'Input/A762_ext_mag.bin','rb') as f:
    h=json.loads(f.readline());v=h['vertices'];t=h['triangles']
    pos=np.fromfile(f,np.float32,v*3).reshape(v,3)*[.01,-.01,.01]
    tri=np.fromfile(f,np.int32,t*3).reshape(t,3)
    mid=np.fromfile(f,np.int32,t)
    uv=np.fromfile(f,np.float32,t*6).reshape(t,3,2)
    n=np.fromfile(f,np.float32,t*9).reshape(t,3,3)*[1,-1,1]
face=np.cross(pos[tri[:,1]]-pos[tri[:,0]],pos[tri[:,2]]-pos[tri[:,0]])
order=[0,1,2] if np.mean(np.sum(face*n.mean(1),1)>0)>=.5 else [0,2,1]
tri=tri[:,order];n=n[:,order];uv=uv[:,order]
me=bpy.data.meshes.new('Old_runtime_mesh');me.from_pydata(pos.tolist(),[],tri.tolist());me.update()
for label in h['slots']:me.materials.append(bpy.data.materials[label])
me.polygons.foreach_set('material_index',mid);me.shade_smooth();me.normals_split_custom_set(n.reshape(-1,3).tolist())
nn=[(X.inverted().to_3x3().inverted().transposed()@p.vector).normalized() for p in me.corner_normals]
me.transform(X.inverted());me.normals_split_custom_set(nn)
old=bpy.data.objects.new('Old_runtime_mesh',me);bpy.context.scene.collection.objects.link(old);old.location.y=-.16+.098

# Angle/width continuity at the retained-to-authored transition. These are
# geometric diagnostics, not a claim about subjective in-game appearance.
i=int(np.searchsorted(C.S,C.KEEP));d=np.diff(C.NEW,axis=0);angle=np.unwrap(np.arctan2(d[:,0],d[:,1]))
stats['curve']['maximum_adjacent_tangent_change_deg']=float(np.max(np.abs(np.diff(angle)))*180/math.pi)
stats['curve']['join_tangent_change_deg']=float(abs(angle[i]-angle[i-1])*180/math.pi)
(O/'inspection.json').write_text(json.dumps(stats,indent=2))
if '--measure-only' in sys.argv:
    print('A762_EXTMAG_GEOMETRY_INSPECTION',json.dumps(stats['geometry']),flush=True)
    sys.exit(0)

scene=bpy.context.scene
scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
try:
    pref=bpy.context.preferences.addons['cycles'].preferences;pref.compute_device_type='OPTIX';pref.get_devices()
    for dev in pref.devices:dev.use=dev.type!='CPU'
    if any(d.use for d in pref.devices):scene.cycles.device='GPU'
except Exception:pass
scene.world=bpy.data.worlds.new('InspectionWorld');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.4,.4,.4,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.55
def area(name,loc,power,size,target):
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size
    ob=bpy.data.objects.new(name,data);scene.collection.objects.link(ob);ob.location=loc
    ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()
area('Key',(.35,-.15,.3),65,.42,(0,0,-.08))
area('Fill',(.25,.35,-.03),30,.38,(0,0,-.08))
area('Strip',(.15,-.4,-.2),25,.3,(0,0,-.08))
camdata=bpy.data.cameras.new('Side');cam=bpy.data.objects.new('Side',camdata);scene.collection.objects.link(cam)
cam.location=(.9,0,-.075);cam.rotation_euler=(Vector((0,0,-.075))-cam.location).to_track_quat('-Z','Y').to_euler()
camdata.type='ORTHO';camdata.ortho_scale=.65;scene.camera=cam
textmat=bpy.data.materials.new('Labels');textmat.diffuse_color=(.04,.05,.07,1)
textmat.use_nodes=True;textmat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.04,.05,.07,1)
for label,y in [('BEFORE',-.16),('REVISED',.16)]:
    data=bpy.data.curves.new(label,'FONT');data.body=label;data.size=.016;data.align_x='CENTER'
    ob=bpy.data.objects.new(label,data);scene.collection.objects.link(ob);ob.location=(.06,y,.071)
    ob.rotation_euler=Matrix(((0,0,1),(1,0,0),(0,1,0))).to_euler();data.materials.append(textmat)
scene.render.resolution_x=1400;scene.render.resolution_y=850;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
scene.view_settings.view_transform='AgX';scene.render.filepath=str(O/'curve_comparison.png')
bpy.ops.render.render(write_still=True)
print('A762_EXTMAG_INSPECTED',json.dumps(stats['geometry']),flush=True)
