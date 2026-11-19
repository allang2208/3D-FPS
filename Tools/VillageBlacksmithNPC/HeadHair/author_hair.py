"""Build a close swept-back crop, tapered sideburns, moustache and a short jaw beard."""
from pathlib import Path
import bpy
import gzip
import json
import math
import random
import os
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

BASE=Path(__file__).resolve().parents[3]/'SourceAssets/VillageBlacksmithNPC20261118/HeadHair'
draft=os.environ.get('SMITH_DESIGN_GROOM')=='1'
ROOT=BASE/'DesignGroom' if draft else BASE
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
integrated=read(ROOT/'fit.json').get('integrated_meshy_hair',False)
if not integrated:
    geom=np.load(ROOT/'surface.npz')
    pos=geom['p'];tris=geom['tri']
    bvh=BVHTree.FromPolygons(pos.tolist(),tris[:,::-1].tolist(),all_triangles=True)
    rng=random.Random(185019)
    V=lambda a:Vector(a)
    p=[];n=[];uv=[];faces=[]
    crown_center=V((0,1.05,169.2))
    basisZ=V((0,0,1))
    def shoot(origin,dir):
        loc,normal,_,_=bvh.ray_cast(origin,dir,45)
        if loc is None:return None,None
        if normal.dot(dir)<0:normal=-normal
        return loc,normal.normalized()
    def scalp(a,phi):
        d=V((math.sin(phi)*math.sin(a), math.sin(phi)*math.cos(a), math.cos(phi)))
        return shoot(crown_center,d)
    def limit(a):
        return np.interp(abs(a),[0,.40,.69,.94,1.18,1.47,1.68,2.00,2.60,math.pi],[1.16,1.13,1.02,1.12,1.42,1.64,1.60,1.80,2.04,2.16])
    def vert(pt,norm,xy):
        j=len(p);p.append(list(pt));n.append(list(norm));uv.append(list(xy));return j
    def tri(a,b,c):
        right=(V(p[b])-V(p[a])).cross(V(p[c])-V(p[a]))
        faces.append([a,c,b] if right.dot(V(n[a]))>0 else [a,b,c])

    # Close-fit scalp backing gives a readable cropped silhouette at distance.
    # Keep the backing inside the tuft roots; the individual cards soften its boundary.
    ring=[]
    for j in range(98):
        a=(j%97)/97*math.tau-math.pi;column=[]
        for k in range(31):
            phi=(k/30)*(limit(a)-.055)+.002
            q,norm=scalp(a,phi)
            if q is None: raise ValueError(f'Scalp backing misses Meshy at {a:.2f}, {phi:.2f}')
            column.append(vert(q+norm*(.075+.10*(1-k/30)),norm,(.751+.247*((j%10)/10),.97-k/30*.94)))
        ring.append(column)
    for j in range(97):
        for k in range(30):
            a,b=ring[j][k:k+2];c,d=ring[j+1][k:k+2]
            tri(a,b,c);tri(b,d,c)

    def lock(root,normal,direction,length,width,tile,puff,curl):
        tang=direction-normal*direction.dot(normal)
        if tang.length<.01:return
        tang.normalize();cross=normal.cross(tang).normalized()
        prev=None
        for i in range(5):
            t=i/4;lift=.04+puff*math.sin(math.pi*t)+puff*.3*t
            loc=root+length*t*tang+lift*normal+cross*(curl*t*t)
            # Geometry narrows slightly near the tip. The atlas resolves individual fibres.
            half=width*(1.-.32*t)*.5
            start=vert(loc-cross*half,normal,((tile+.005)/4,.982-.963*t))
            end=vert(loc+cross*half,normal,((tile+.995)/4,.982-.963*t))
            if prev:tri(prev[0],prev[1],start);tri(prev[1],end,start)
            prev=(start,end)

    for i in range(4800):
        a=rng.uniform(-math.pi,math.pi);phi=math.acos(rng.uniform(math.cos(limit(a)),1))
        q,norm=scalp(a,phi)
        if q is None:continue
        side=max(0,min(1,(abs(a)-.75)/.70))
        edge=max(0,min(1,(phi-.93)/.75))
        fade=side*edge
        # Crown direction sweeps away from the forehead and turns down the nape.
        direction=V((.19+.14*math.cos(a),-1.0,-.33-.93*fade))
        if -a>2.4:direction.x=-.16
        length=rng.uniform(1.28,2.23)*(1.-.66*fade)
        tile=1 if rng.random()<(.13+.67*fade) else 0
        lock(q,norm,direction,length,rng.uniform(.33,.65)*(1-.34*fade),tile,.13+.13*(1-fade),rng.uniform(-.18,.18))

    # Cast from inside the mandible onto the actual commissioned face at each elevation.
    # Dense dark fibres and short silver clusters leave both lip margins and ears clear.
    for i in range(6300):
        a=rng.uniform(-1.55,1.55)
        ab=abs(a)
        low=np.interp(ab,[0,.52,.95,1.3,1.55],[157.65,157.7,158.65,160.20,162.10])
        high=np.interp(ab,[0,.34,.58,1.05,1.36,1.55],[162.0,162.0,162.45,164.1,165.45,166.8])
        z=rng.uniform(low,high)
        d=V((math.sin(a),math.cos(a),0))
        q,norm=shoot(V((0,1.,z)),d)
        if q is None:continue
        if ab<.52 and q.y<7.3:continue
        if ab>.94 and q.y<2.4:continue
        if abs(q.x)<2.8 and 160.42<q.z<162.34:continue
        # Avoid a hard, painted-on cheek line.
        fade=min(1,(z-low)/.36,(high-z)/.46)
        if rng.random()>fade:continue
        if ab>.94 and rng.random()<.24:continue
        silver=(.46 if abs(q.x)<4.4 and z<160.7 else .26)+.1*(ab>1.12)
        lock(q,norm,V((math.sin(a)*-.12,-.22,-1.)),rng.uniform(.33,.73),rng.uniform(.12,.31),1 if rng.random()<silver else 2,rng.uniform(.025,.09),rng.uniform(-.065,.065))
    # Moustache fans sideways toward corners and leaves a small philtrum gap.
    for k in range(540):
        a=rng.choice((-1.,1.))*rng.uniform(.025,.4)
        z=162.35+rng.random()*.8-.50*abs(a)/.40
        q,norm=shoot(V((0,1,z)),V((math.sin(a),math.cos(a),0)))
        if q is None or abs(q.x)>3.0:continue
        side=1 if a>0 else -1
        lock(q,norm,V((side*.85,-.15,-.55)),rng.uniform(.36,.65),rng.uniform(.13,.28),1 if rng.random()<.23 else 2,.08,side*rng.uniform(.01,.07))

    idx=read(ROOT/'fit.json')['rigid_head_index']
    with gzip.open(ROOT/'hair.json.gz','wt',encoding='utf8',compresslevel=3) as stream:
        json.dump(dict(p=np.round(p,6).tolist(),n=np.round(n,6).tolist(),uv=np.round(uv,6).tolist(),tri=faces,rigid=idx),stream,separators=(',',':'))

# Pack the actual authored pieces and their material maps in an editable DCC file.
bpy.ops.wm.read_factory_settings(use_empty=True)
def mat(name,bc,normal=None,rough=None,mask=False):
    m=bpy.data.materials.new(name);m.use_nodes=True
    nodes=m.node_tree.nodes;link=m.node_tree.links;bs=nodes.get('Principled BSDF')
    maps=[(bc,'Base Color','sRGB'),(rough,'Roughness','Non-Color'),(normal,'Normal','Non-Color')]
    for path,socket,space in maps:
        if not path or not path.exists():continue
        tx=nodes.new('ShaderNodeTexImage');tx.image=bpy.data.images.load(str(path),check_existing=True)
        tx.image.colorspace_settings.name=space;tx.image.pack();out=tx.outputs['Color']
        if socket=='Normal':
            nm=nodes.new('ShaderNodeNormalMap');link.new(out,nm.inputs['Color']);out=nm.outputs[0]
        link.new(out,bs.inputs[socket])
        if mask and socket=='Base Color':link.new(tx.outputs['Alpha'],bs.inputs['Alpha'])
    return m
tex=BASE/'Textures'
project=Path(__file__).resolve().parents[3]
native=project/'SourceAssets/JasonStrong20261117/R2_LongLegs/textures'
bodytex=BASE.parent/'BodyOutfit/Textures/T_Smith_Skin_head_BC.png'
neck_tex=bodytex if bodytex.exists() else tex/'T_Smith_Neck_BC.png'
if not neck_tex.exists():raise ValueError('Smith neck albedo unavailable')
if not integrated:hairmat=mat('Salt and pepper fibres',tex/'T_Smith_Fibres.png',mask=True)
if not draft:
    facemat=mat('Original Meshy face',tex/'T_Smith_Face_BC.png',tex/'T_Smith_Face_N.png',tex/'T_Smith_Face_R.png')
    neckmat=mat('Native collar',neck_tex,native/'T_Head_LOD2_N.png')
def editable(name,ps,ns,triangles,uvs,mats,material_ids=None):
    me=bpy.data.meshes.new(name)
    # Same +Y-facing authoring coordinates as the R4 source armature; UE winds clockwise.
    positions=np.asarray(ps,dtype=np.float32)*.01
    ccw=np.asarray(triangles)[:,::-1].copy()
    me.from_pydata(positions.tolist(),[],ccw.tolist());me.update()
    ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob)
    for m in mats:me.materials.append(m)
    layers=me.uv_layers.new(name='UVMap')
    arr=np.array(uvs,dtype=np.float32);arr[:,1]=1-arr[:,1]
    layers.data.foreach_set('uv',arr[ccw.ravel()].ravel())
    if material_ids is not None:me.polygons.foreach_set('material_index',np.asarray(material_ids,dtype=np.int32))
    me.polygons.foreach_set('use_smooth',np.ones(len(me.polygons),dtype=bool))
    me.normals_split_custom_set_from_vertices(ns)
    ob['UE_reference_skeleton']='/Game/AsianMale_Jason/Mesh/Body/SKM_Jason_body_Skeleton'
    return ob
if not draft:
    with gzip.open(ROOT/'face.json.gz','rt',encoding='utf8') as stream:head=json.load(stream)
    head_obj=editable('SK_Smith_Head',head['p'],head['n'],head['tri'],head['uv'],[facemat,neckmat],head['m'])
    blend=head_obj.data.attributes.new('SmithNeckBlend','FLOAT','POINT')
    amount=np.clip((np.asarray(head['p'])[:,2]-150.4)/(155.30-150.4),0,1)
    blend.data.foreach_set('value',np.asarray(amount*amount*(3-2*amount),np.float32))
    nodes=neckmat.node_tree.nodes;links=neckmat.node_tree.links
    bs=nodes.get('Principled BSDF');base=bs.inputs['Base Color'].links[0].from_socket
    attr=nodes.new('ShaderNodeAttribute');attr.attribute_name='SmithNeckBlend'
    mix=nodes.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY'
    mix.inputs[2].default_value=(*read(ROOT/'fit.json')['neck_tint_upper_linear'],1)
    links.new(attr.outputs['Fac'],mix.inputs[0]);links.new(base,mix.inputs[1]);links.new(mix.outputs[0],bs.inputs['Base Color'])
if not integrated:hair_obj=editable('SK_Smith_Hair',p,n,faces,uv,[hairmat])
body_source=project/'SourceAssets/JasonStrong20261117'
with bpy.data.libraries.load(str(body_source/'R4_PoseRefined/Jason_StrongTall_R4.blend'),link=False) as (available,requested):
    requested.objects=['Jason_NativeSkeleton']
armature=requested.objects[0]
bpy.context.collection.objects.link(armature)
armature.location=(0,0,0)
armature.rotation_euler=(0,0,0)
armature.hide_render=True
bones=read(body_source/'R3_ArmsRefined/AnatomyReview/derived_saved_mesh.json')['bones']
def bind(obj,weights=None):
    obj.parent=armature
    mod=obj.modifiers.new('R4 skeleton','ARMATURE');mod.object=armature
    if weights is None:
        group=obj.vertex_groups.new(name=bones[idx]['name'])
        group.add(list(range(len(obj.data.vertices))),1.,'REPLACE')
    else:
        groups={index:obj.vertex_groups.new(name=bones[index]['name']) for index in sorted({i for pairs in weights for i,w in pairs})}
        for vi,pairs in enumerate(weights):
            for i,w in pairs:groups[i].add([vi],w,'REPLACE')
if not integrated:bind(hair_obj)
if not draft:bind(head_obj,head['w'])
if draft:hair_obj['fit_status']='Design-sheet groom study; final roots must conform to the actual Meshy scalp and jaw.'
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/('Smith_Hair_Design.blend' if draft else 'Smith_Head_Hair.blend')),compress=True)
print('SMITH_EDITABLE_HEAD_AND_HAIR_SAVED','Integrated Meshy scalp and beard' if integrated else len(faces),flush=True)
