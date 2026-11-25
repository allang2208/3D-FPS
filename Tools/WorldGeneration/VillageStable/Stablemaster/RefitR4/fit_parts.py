"""Refit the two Meshy sculpts using the uninterrupted collar of the rigged original."""
from pathlib import Path
import math,sys,json
import bmesh,bpy
import numpy as np
from mathutils import Matrix,Vector

PROJECT=Path(__file__).resolve().parents[5]
sys.path.insert(0,str(PROJECT/'Tools/VillageHerbalist/HeadR3'))
from assemble_neck import Surface,Ring,NORMAL_LAYER,smooth,copy_weights,write_weights
OLD=PROJECT/'SourceAssets/HillsVillageStable/StablemasterMeshyR3'
OUT=OLD.parent/'StablemasterMeshyR4'
OUT.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0

def load(path,kind):
    previous=set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path),disable_bone_shape=True)
    new=[o for o in bpy.data.objects if o not in previous]
    return [next(o for o in new if o.type==typ) for typ in kind]

def positions(mesh):
    data=np.empty(len(mesh.vertices)*3,'f');mesh.vertices.foreach_get('co',data)
    return data.reshape(-1,3)

def attach(obj,rig):
    obj.parent=rig;obj.matrix_parent_inverse=Matrix.Identity(4);obj.matrix_basis=Matrix.Identity(4)
    if not any(m.type=='ARMATURE' and m.object==rig for m in obj.modifiers):
        m=obj.modifiers.new('Meshy skin','ARMATURE');m.object=rig

rig,body=load(OLD/'Rig/Rig.glb',['ARMATURE','MESH'])
head,=load(OLD/'Head/Head.glb',['MESH'])
def joint(n):return rig.matrix_world@rig.data.bones[n].head_local
across=joint('LeftArm')-joint('RightArm');center=(joint('LeftFoot')+joint('RightFoot'))*.5
world=body.matrix_world.copy();z=[(world@v.co).z for v in body.data.vertices];center.z=min(z)
basis=Matrix.Scale(168./(max(z)-min(z)),4)@Matrix.Rotation(-math.atan2(across.y,across.x),4,'Z')@Matrix.Translation(-center)
body.data.transform(basis@world,shape_keys=True)
rw=rig.matrix_world.copy();rig.parent=None;rig.matrix_world=Matrix.Identity(4);rig.data.transform(basis@rw)
rig.name='Armature';rig.animation_data_clear();attach(body,rig);body.animation_data_clear()
hm=head.matrix_world.copy();head.parent=None;head.matrix_world=Matrix.Identity(4);head.data.transform(hm,shape_keys=True)
raw=positions(head.data);native=positions(body.data);h=raw[:,2]
unit=24.2/((h.max()-h.min())*(1.-13.65/30.));offset=168.-unit*h.max()
old=raw*unit;old[:,2]+=offset
def tip(v,c):
    band=v[(abs(v[:,0]-c)<2.4)&(v[:,2]>150.7)&(v[:,2]<154.9)]
    return np.percentile(band[band[:,1]<np.percentile(band[:,1],5)],50,axis=0)
delta=tip(native,rig.data.bones['Head'].head_local.x)-tip(old,0)
old[:,:2]+=delta[:2]
# Before refitting the sculpt, record the source surface for reference-to-atlas projection.
def surface_arrays(mesh):
    mesh.calc_loop_triangles()
    tris=np.asarray([t.vertices[:] for t in mesh.loop_triangles],dtype='i')
    corners=np.asarray([t.loops[:] for t in mesh.loop_triangles],dtype='i')
    uv=np.asarray([x.uv[:] for x in mesh.uv_layers[0].data],dtype='f')
    uv[:,1]=1.-uv[:,1]
    return tris,uv[corners]
tris,uv=surface_arrays(head.data)
np.savez_compressed(OUT/'face_projection.npz',positions=old,triangles=tris,uv=uv)
# Sculpt in the old projection basis, then fit the volume between the raised
# collar and crown. The point measurements are from the two R2 head elevations.
x,y,z=old.T
def bell(a,c,s):return np.exp(-.5*((a-c)/s)**2)
side=x-.38
front=np.clip((-y-1.0)/5.5,0.,1.)
brow=bell(abs(side),3.15,1.8)*bell(z,156.2,1.25)*front
nose=bell(side,0.,1.42)*bell(z,151.7,1.6)*front
mouth=bell(side,0.,2.5)*bell(z,148.65,.95)*front
jaw=bell(z,146.9,1.8)*np.clip((abs(side)-2.7)/3,0.,1.)
points=old.copy()
points[:,0]=.3+(x-.38)*.888-np.sign(side)*.25*jaw
points[:,1]=.45+(y-.45)*.906-.26*nose+.12*mouth
points[:,2]=146.13+(z-144.0)*.885-.33*brow-.29*nose-.14*mouth
head.data.vertices.foreach_set('co',np.ascontiguousarray(points,'f').ravel());head.data.update()
# Fresh custom normals start from the fitted geometry rather than the old wide face.
head.data.normals_split_custom_set_from_vertices([v.normal[:] for v in head.data.vertices])
attach(head,rig)
for g in body.vertex_groups:head.vertex_groups.new(name=g.name)
for obj,role in [(body,'Body'),(head,'Head')]:
    obj.name='SK_Stablemaster_'+role;obj.data.materials[0].name='M_Stablemaster_'+role+'_0'

class Section(Surface):
    def __init__(self,ob,upper,base,slope):
        self.obj=ob;self.base=base;self.slope=slope
        m=ob.data;a=np.empty(len(m.loops)*3,'f');m.corner_normals.foreach_get('vector',a)
        attr=m.attributes.new(NORMAL_LAYER,'FLOAT_VECTOR','CORNER');attr.data.foreach_set('vector',a)
        bm=self.bm=bmesh.new();bm.from_mesh(m)
        self.nl=bm.loops.layers.float_vector[NORMAL_LAYER]
        self.deform=bm.verts.layers.deform.verify()
        self.groups={g.index:g.name for g in ob.vertex_groups};self.groups_by_name={n:i for i,n in self.groups.items()}
        bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00007)
        n=Vector((0.,-slope,1.)).normalized();o=Vector((0.,0.,base))
        bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=o,plane_no=n,dist=.000002)
        # Keep bun tips with their head or discard them with the donor head, even
        # if they dip through the neck plane. Only the connected trunk is body.
        below={f for f in bm.faces if (f.calc_center_median()-o).dot(n)<-1.e-7}
        low=min(below,key=lambda f:f.calc_center_median().z);trunk={low};todo=[low]
        while todo:
            for edge in todo.pop().edges:
                for f in edge.link_faces:
                    if f in below and f not in trunk:trunk.add(f);todo.append(f)
        if not upper:
            # Disconnected buttons, pouches and soles below the neck also belong to the costume.
            remainder=below-trunk
            while remainder:
                f=remainder.pop();patch={f};stack=[f]
                while stack:
                    for edge in stack.pop().edges:
                        for other in edge.link_faces:
                            if other in remainder:remainder.remove(other);patch.add(other);stack.append(other)
                if any((f.calc_center_median()-o).dot(n)<-4. for f in patch):trunk.update(patch)
        drop=trunk if upper else set(bm.faces)-trunk
        bmesh.ops.delete(bm,geom=list(drop),context='FACES')
        edges=[e for e in bm.edges if e.is_boundary and all(abs((v.co-o).dot(n))<.00008 for v in e.verts)]
        self.ring=Ring(self,edges)

BODY_BASE,BODY_SLOPE=144.75,.20
bod=Section(body,False,BODY_BASE,BODY_SLOPE);top=Section(head,True,144.20,.32)
br,hr=bod.ring,top.ring
if max(v.y for v in br.coords)>7.5 or max(v.y for v in hr.coords)>8.:
    raise ValueError('Neck edge includes the bun; lower the posterior section')
bv=br.subdivide(hr.params);hv=hr.subdivide(br.params)
# Both halves have the same positions, deformation weights and shading normals
# along the shared skin-only loop. Original UV islands continue right to the edge.
for v in top.bm.verts:
    if v in hv:continue
    d=v.co.z-top.slope*v.co.y-top.base
    if d>=4.5:
        write_weights(v,top.deform,{top.groups_by_name['Head']:1.});continue
    t=hr.by_direction(v.co);original,_,_=hr.sample(t);dest,_,weights=br.sample(t)
    radius=(original.xy-Vector(hr.center[:2])).length
    radial=(v.co.xy-Vector(hr.center[:2])).length
    local=1.-smooth((radial-radius-.2)/1.35)
    v.co+=(dest-original)*local*(1.-smooth(d/3.2))
    mix=copy_weights({'Head':1.},weights,local*(1.-smooth(d/4.2)))
    write_weights(v,top.deform,{top.groups_by_name[k]:w for k,w in mix.items()})
def exact(surface,mapping):
    for v,t in mapping.items():
        co,normal,w=br.sample(t);v.co=co
        write_weights(v,surface.deform,{surface.groups_by_name[k]:val for k,val in w.items()})
        for l in v.link_loops:l[surface.nl]=normal
exact(bod,bv);exact(top,hv)
top.bm.normal_update()
for v in top.bm.verts:
    if v in hv:continue
    d=v.co.z-BODY_SLOPE*v.co.y-BODY_BASE
    if 0<d<2.4:
        t=hr.by_direction(v.co);co,normal,_=br.sample(t)
        if (v.co.xy-co.xy).length<1.8:
            n=normal.lerp(v.normal,smooth(d/2.4)).normalized()
            for l in v.link_loops:l[top.nl]=n
def rim_uv(surface,verts):
    # Each edge supplies its own two UVs. Never interpolate between distant atlas islands.
    uv=surface.bm.loops.layers.uv.active;rows=[]
    for e in surface.bm.edges:
        if not e.is_boundary or not all(v in verts for v in e.verts):continue
        l=e.link_loops[0];k=l.link_loop_next
        rows.append([list(l.vert.co),list(k.vert.co),list(l[uv].uv),list(k[uv].uv)])
    return rows
rim={'Body':rim_uv(bod,bv),'Head':rim_uv(top,hv)}
(OUT/'rim_samples.json').write_text(json.dumps(rim,separators=(',',':')))
bod.finish();top.finish()
tris,uv=surface_arrays(head.data)
np.savez_compressed(OUT/'neck_projection.npz',positions=positions(head.data),triangles=tris,uv=uv)
rig.data.pose_position='POSE'
for b in rig.pose.bones:b.matrix_basis=Matrix.Identity(4)
for o in list(bpy.context.scene.objects):
    if o not in (head,body,rig):bpy.data.objects.remove(o,do_unlink=True)
bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=.01
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'StablemasterR4.blend'),compress=True)
for ob in (body,head):
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True);ob.select_set(True);bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.fbx(filepath=str(OUT/(ob.name+'.fbx')),use_selection=True,object_types={'ARMATURE','MESH'},add_leaf_bones=False,use_armature_deform_only=False,armature_nodetype='NULL',bake_anim=False,apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='Y',axis_up='Z',use_mesh_modifiers=False,mesh_smooth_type='FACE',path_mode='STRIP',embed_textures=False)
(OUT/'fit.json').write_text(json.dumps(dict(scale_xyz=[.888,.906,.885],chin_z_cm=146.13,crown_z_cm=float(points[:,2].max()),paired_ring_vertices=len(hv),body_ring_vertices=len(bv),neck_base=BODY_BASE,neck_slope=BODY_SLOPE),indent=2))
