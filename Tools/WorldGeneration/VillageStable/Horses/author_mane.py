"""Build a weighted neck mane from samples of the actual Warhorse crest, then export a companion skin."""
import bpy, math, random, sys
import numpy as np
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [sys.argv[-1]]
dest=Path(args[0]); dest.mkdir(exist_ok=True,parents=True)
style=args[1] if len(args)>1 else 'Original'
if style not in ('Original','Crop','Sweep','Parted'):raise ValueError(style)
project=Path(__file__).resolve().parents[4]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system='METRIC'
bpy.ops.import_scene.gltf(filepath=str(project/'SourceAssets/HillsVillageStable/HorsesR7/Originals/WarhorseLite.glb'))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
body=next(o for o in bpy.context.scene.objects if o.type=='MESH' and o.find_armature()==rig)
rig.animation_data_clear()
for bone in rig.pose.bones: bone.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
# Blender's glTF importer maps +Z (forward) to -Y; use a forward-positive authoring frame.
coords=[Vector((p.x,-p.y,p.z)) for v in body.data.vertices for p in [body.matrix_world@v.co]]
polys=[tuple(p.vertices) for p in body.data.polygons]
bvh=BVHTree.FromPolygons(coords,polys)
def surface(x,z):
    p,_,face,_=bvh.ray_cast(Vector((x,z,3.)),Vector((0,0,-1)))
    if p is None: raise ValueError(('Outside neck surface',x,z))
    return p,face
def weights(p,face):
    ids=polys[face]; a,b,c=(coords[i] for i in ids)
    v0=b-a;v1=c-a;v2=p-a
    d00=v0.dot(v0);d01=v0.dot(v1);d11=v1.dot(v1);d20=v2.dot(v0);d21=v2.dot(v1)
    den=max(1e-12,d00*d11-d01*d01)
    v=(d11*d20-d01*d21)/den; w=(d00*d21-d01*d20)/den
    result={}
    for idx,bary in zip(ids,(1-v-w,v,w)):
        for g in body.data.vertices[idx].groups:
            name=body.vertex_groups[g.group].name
            result[name]=result.get(name,0.)+max(0.,bary)*g.weight
    kept=sorted(result.items(),key=lambda q:-q[1])[:4];total=sum(t for _,t in kept)
    return {k:t/total for k,t in kept if t>0}
verts=[];faces=[];uv=[];phases=[];vweights=[]
rng=random.Random(7631)
# The ridge is directly under the mounted camera. Lay a continuous pelt over the
# coarse original crest before adding separated locks. Its UVs run along the hair.
def patch_vertex(x, fwd, h, tex, phase, weight):
    verts.append((x,-fwd,h))
    uv.append(tex); phases.append(phase); vweights.append(weight)

def strip_row(base, row, columns):
    if row:
        last=base+(row-1)*columns
        for k in range(columns-1):
            a=last+k
            faces.append((a,a+1,a+1+columns,a+columns))

rows,columns=110,13
for j in range(rows):
    u=j/(rows-1); fwd=.196+.777*u
    taper=.18+.82*math.sin(math.pi*u)**.52
    half=.053*taper
    top,_=surface(0,fwd)
    for k in range(columns):
        a=2*k/(columns-1)-1
        x=(a+.09*math.sin(13*u))*half
        p,face=surface(x,fwd)
        # Raise the parting above the original opaque ridge; blend the margins into the coat.
        envelope=1-a*a
        z=max(p.z+.001,top.z-.72*abs(x))+.009*envelope
        z-=.006*(abs(a)**6+(1-math.sin(math.pi*u))**12)
        patch_vertex(x,fwd,z,(.752+.246*k/(columns-1),.008+.984*u),(.37,.5),weights(p,face))
    strip_row(0,j,columns)

# Roots cross the parting; narrower ribbons overlap irregularly around the bend
# and shorter broken strands soften the outline. No strip has a straight-cut tip.
for layer,count in enumerate((104,78,103,70)):
    for i in range(count):
        u=(i+rng.uniform(.05,.95))/count
        forward=.208+.753*u
        side=-1 if layer==0 else 1 if layer==1 else rng.choice((-1,1))
        if style=='Sweep' and layer!=1:side=1
        if style=='Parted' and layer>=2:side=1 if i%2 else -1
        x=(-side if layer==2 else side)*rng.uniform(.003,.020)
        top,face=surface(x,forward)
        weight=weights(top,face)
        scale=.26+.74*math.sin(math.pi*u)**.58
        length=(.155,.113,.107,.135)[layer]*scale*rng.uniform(.62,1.36)
        length*={'Original':1.,'Crop':.56,'Sweep':1.06,'Parted':1.22}[style]
        half=(.013,.012,.010,.006)[layer]*rng.uniform(.55,1.35)
        sweep=length*rng.uniform(.58,.98)
        phase=rng.random();base=len(verts);variant=rng.randrange(8)
        lean=rng.uniform(.001,.011)
        for j in range(10):
            t=j/9
            fwd=forward-sweep*t
            crest=surface(0,fwd)[0].z
            height=crest+.012+.014*math.sin(math.pi*t)-length*.60*t**1.55
            hit,_,_,_=bvh.ray_cast(Vector((side*.65,fwd,height)),Vector((-side,0,0)),1.15)
            flank=abs(hit.x) if hit and side*hit.x>=0 else .009
            drift=max(flank+.004,length*.29*math.sin(math.pi*.8*t))
            mix=1-(1-t)**3
            cx=x*(1-mix)+side*(drift+lean*t)*mix
            for k in range(3):
                w=(k-1)*half*(1-.92*t**1.8)
                # At the crown the strip spans the neck. At the flank it spans
                # fore-aft, so it stays visible from both above and the side.
                px=cx+w*(1-mix); pf=fwd+w*mix
                patch_vertex(px,pf,height+w*.28*mix+.0018*(1-abs(k-1)),
                    ((variant+.02+.96*k/2)*.75/8,1-t),
                    (phase,0.0 if side>0 else 1.0),weight)
            strip_row(base,j,3)
if style!='Original':
    # Trace each wisp against the tail of the production scan. Root-to-tip weights
    # come from the underlying surface, so these locks follow the existing tail animation.
    tail_ids={g.index for g in body.vertex_groups if g.name.startswith('tail_')}
    tail_points=np.array([tuple(p) for v,p in zip(body.data.vertices,coords)
                          if sum(g.weight for g in v.groups if g.group in tail_ids)>.80])
    heights=np.linspace(tail_points[:,2].min()+.045,tail_points[:,2].max()-.03,36)
    centres=[]
    for h in heights:
        ring=tail_points[np.argsort(abs(tail_points[:,2]-h))[:26],:2]
        centres.append(.5*(ring.min(0)+ring.max(0)))
    centres=np.array(centres)
    rng=random.Random(23811)
    for i in range(104):
        angle=i*2.399963+ rng.uniform(-.10,.10)
        top=rng.uniform(.29,1.);end=max(0.,top-rng.uniform(.25,.67))
        phase=rng.random();variant=rng.randrange(8);half=rng.uniform(.003,.008)
        lock=[]
        for j in range(9):
            t=j/8;h=heights[0]+(heights[-1]-heights[0])*(top+(end-top)*t)
            centre=Vector((np.interp(h,heights,centres[:,0]),np.interp(h,heights,centres[:,1]),h))
            a=angle+.16*math.sin(t*math.pi+phase*5)
            axis=Vector((math.cos(a),math.sin(a),0.));tan=Vector((-axis.y,axis.x,0.))
            point,_,face,_=bvh.ray_cast(centre+axis*.19,-axis,.32)
            if point is None or not any(name.startswith('tail_') for name in weights(point,face)):break
            lock.append((point+axis*(.001+.009*t*t),tan,weights(point,face)))
        if len(lock)!=9:continue
        base=len(verts)
        for j,(pt,tan,weight) in enumerate(lock):
            t=j/8
            for k in range(3):
                v=pt+tan*((k-1)*half*(1-.94*t*t))
                patch_vertex(*v,((variant+.02+.96*k/2)*.75/8,1-t),(phase,.30),weight)
            strip_row(base,j,3)

mesh=bpy.data.meshes.new('StableMane');mesh.from_pydata(verts,[],faces);mesh.update()
skin=bpy.data.objects.new('StableMane',mesh);bpy.context.collection.objects.link(skin)
skin.parent=rig;skin.matrix_world=Matrix.Identity(4)
mod=skin.modifiers.new('Horse neck','ARMATURE');mod.object=rig
for b in rig.data.bones:
    skin.vertex_groups.new(name=b.name)
for i,row in enumerate(vweights):
    for b,v in row.items(): skin.vertex_groups[b].add([i],v,'REPLACE')
uvmap=mesh.uv_layers.new(name='HairUV')
lockmap=mesh.uv_layers.new(name='LockPhase')
for poly in mesh.polygons:
    poly.use_smooth=True
    for l in poly.loop_indices:
        idx=mesh.loops[l].vertex_index
        uvmap.data[l].uv=uv[idx]
        lockmap.data[l].uv=phases[idx]
mesh.materials.append(bpy.data.materials.new('StableMane'))
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);skin.select_set(True)
rig.name='Armature';bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(dest/('SK_Warhorse_Mane.fbx' if style=='Original' else 'SK_Hair_'+style+'.fbx')),use_selection=True,add_leaf_bones=False,
    use_armature_deform_only=False,apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',
    axis_forward='-Y',axis_up='Z',use_mesh_modifiers=False,path_mode='STRIP',bake_anim=False,
    mesh_smooth_type='OFF' if style=='Original' else 'FACE')
print('Mane',len(verts),len(faces),'crest',[(round(float(z),2),round(surface(0,z)[0].z,3)) for z in (.22,.45,.72,.955)])

