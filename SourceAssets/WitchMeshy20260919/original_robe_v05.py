"""V05: retain original visible robe; author separate cloth driver and body layers.
No preview render, game launch, test or acceptance run is performed.
"""
import bpy,bmesh,json,math,sys
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import layered_v04 as common
OUT=ROOT/'Authoring/OriginalRobeV05';DEL=ROOT/'Delivery/OriginalRobeV05'
for d in [OUT,DEL,OUT/'Parts',OUT/'MotionLayers']:d.mkdir(parents=True,exist_ok=True)
FPS=60

def set_weights(ob,index,weights):
    for g in list(ob.data.vertices[index].groups):ob.vertex_groups[g.group].remove([index])
    total=sum(weights.values())
    for name,value in weights.items():
        group=ob.vertex_groups.get(name) or ob.vertex_groups.new(name=name)
        if value>1e-7:group.add([index],value/total,'REPLACE')

def foot_partition(src,lower):
    """Use actual source skin texels and ankle landmarks; preserve source faces."""
    im=bpy.data.images.load(str(ROOT/'Meshy/body/downloads/texture_urls_0_base_color.png'),check_existing=True)
    pix=np.asarray(im.pixels[:],dtype=np.float32).reshape(im.size[1],im.size[0],4)
    uv=src.data.uv_layers.active
    candidates={};seeds=set();adj={};faces=set(lower)
    for idx in lower:
        p=src.data.polygons[idx]
        c=sum((src.matrix_world@src.data.vertices[i].co for i in p.vertices),Vector())/len(p.vertices)
        if not (.04<abs(c.x)<.29 and -.245<c.y<.005 and c.z<.145):continue
        colors=[]
        for li in p.loop_indices:
            t=uv.data[li].uv;colors.append(pix[min(im.size[1]-1,max(0,int(t.y*im.size[1]))),min(im.size[0]-1,max(0,int(t.x*im.size[0])))][:3])
        color=np.mean(colors,axis=0);light=float(color@np.array([.2126,.7152,.0722]))
        candidates[idx]=(c,light)
        if c.z<.10 and light>.38:seeds.add(idx)
        for vi in p.vertices:adj.setdefault(vi,[]).append(idx)
    selected=set(seeds);queue=list(seeds)
    while queue:
        idx=queue.pop()
        for vi in src.data.polygons[idx].vertices:
            for other in adj.get(vi,[]):
                if other in selected:continue
                c,light=candidates[other]
                if light>.25 or (c.z<.044 and .075<abs(c.x)<.24 and c.y<-.048):
                    selected.add(other);queue.append(other)
    if not selected:raise RuntimeError('No source feet could be separated; retained source remains untouched')
    return sorted(selected),sorted(faces-selected)

def proxy(robe,r):
    robe.data.calc_loop_triangles()
    positions=[v.co.copy() for v in robe.data.vertices]
    tree=BVHTree.FromPolygons(positions,[tuple(t.vertices) for t in robe.data.loop_triangles],all_triangles=True)
    N=64;R=30;top=.955;bottom=.024
    pts=[]
    for j in range(R+1):
        z=top+(bottom-top)*j/R
        for i in range(N):
            a=i/N*math.tau;d=Vector((math.sin(a),-math.cos(a),0));c=Vector((0,.045,z))
            p,no,idx,dist=tree.ray_cast(c+d*.65,-d,.95)
            if p is None:p,no,idx,dist=tree.find_nearest(c+d*.26)
            p=p.copy();p.z=z;pts.append(p)
    # Smooth only the invisible simulation cage, leaving all visible source
    # vertices, UV islands, normals, holes and ragged hems unchanged.
    for _ in range(2):
        prev=[p.copy() for p in pts]
        for j in range(1,R):
            for i in range(N):
                k=j*N+i
                mean=(prev[j*N+(i-1)%N]+prev[j*N+(i+1)%N]+prev[(j-1)*N+i]+prev[(j+1)*N+i])*.25
                pts[k]=prev[k].lerp(mean,.3);pts[k].z=prev[k].z
    quads=[(j*N+i,(j+1)*N+i,(j+1)*N+(i+1)%N,j*N+(i+1)%N) for j in range(R) for i in range(N)]
    data=bpy.data.meshes.new('Witch_Robe_SimProxy');data.from_pydata(pts,[],quads)
    ob=bpy.data.objects.new('Witch_Robe_SimProxy',data);bpy.context.collection.objects.link(ob)
    mat=bpy.data.materials.new('M_Witch_V05_SimProxy');mat.use_nodes=True
    shader=mat.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
    shader.inputs['Base Color'].default_value=(0,.3,.8,1)
    output=mat.node_tree.nodes.new('ShaderNodeOutputMaterial')
    mat.node_tree.links.new(shader.outputs['BSDF'],output.inputs['Surface']);data.materials.append(mat)
    hips=ob.vertex_groups.new(name='Hips');hips.add(list(range(len(pts))),1,'REPLACE')
    mod=ob.modifiers.new('Skin','ARMATURE');mod.object=r
    ob['role']='Hidden simulation source. Remove this render section after extracting cloth data.'
    ob.hide_render=True;ob.display_type='WIRE'
    return ob

def body():
    # Reuse only the hidden donor anatomy, never V04's replacement visible skirt.
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authoring/LayeredV04/Witch_LayeredBodyV04.blend'))
    donor=[]
    for name in ['Witch_InnerBody','Witch_Feet']:
        src=bpy.data.objects[name]
        ids=[p.index for p in src.data.polygons if name!='Witch_Feet' or min(src.data.vertices[i].co.z for i in p.vertices)>.125]
        ob=common.subset(src,ids,'Witch_InnerCalves' if name=='Witch_Feet' else name)
        if name=='Witch_Feet':ob.data.materials.clear();ob.data.materials.append(bpy.data.objects['Witch_InnerBody'].data.materials[0])
        path=OUT/'Parts'/(ob.name+'_Donor.blend');common.save_part(path,[ob]);donor.append(path)
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authoring/CloudGripV02/Witch_GripBodyV02.blend'))
    r=common.rig();common.neutral(r);wr=common.rest(r)
    src=max((o for o in bpy.context.scene.objects if o.type=='MESH'),key=lambda o:len(o.data.vertices))
    parts=json.loads((ROOT/'Authoring/LayeredV04/Preserved/source_partition.json').read_text())
    foot_ids,robe_ids=foot_partition(src,parts['LowerRobe_Reference']['source_polygon_indices'])
    objects=[]
    for name in ['Hat','Head_Hair','Hand_Left','Hand_Right','UpperRobe']:
        ob=common.subset(src,parts[name]['source_polygon_indices'],'Witch_'+name,r);objects.append(ob)
        if name=='UpperRobe':
            # The same waist collar as the fixed cloth band keeps cut vertices
            # together. Above it, retain the original torso/arm skin.
            for v in ob.data.vertices:
                old={ob.vertex_groups[g.group].name:g.weight for g in v.groups}
                arms=sum(w for n,w in old.items() if 'Arm' in n or 'Hand' in n)
                if v.co.z<1.05 and arms<.4:
                    t=common.smooth((v.co.z-.965)/.085)
                    weights={n:w*t for n,w in old.items()};weights['Hips']=weights.get('Hips',0)+1-t
                    set_weights(ob,v.index,weights)
    garment=common.subset(src,robe_ids,'Witch_OriginalRobe_Render',r)
    # Distinct material slot, original material nodes and textures.
    mat=garment.data.materials[0].copy();mat.name='M_Witch_V05_OriginalRobe'
    garment.data.materials.clear();garment.data.materials.append(mat)
    for p in garment.data.polygons:p.material_index=0
    for v in garment.data.vertices:set_weights(garment,v.index,{'Hips':1})
    garment['role']='Visible original Meshy robe. Original vertex positions, polygons, UVs and split normals retained.'
    feet=common.subset(src,foot_ids,'Witch_OriginalFeet',r)
    for v in feet.data.vertices:
        side='Left' if v.co.x>=0 else 'Right';ankle=wr[side+'Foot'].translation;toe=wr[side+'ToeBase'].translation
        along=(v.co-ankle).dot((toe-ankle).normalized())
        t=.75*common.smooth((along-.035)/.060)
        set_weights(feet,v.index,{side+'Foot':1-t,side+'ToeBase':t})
    objects.extend([garment,feet,proxy(garment,r)])
    for path in donor:
        with bpy.data.libraries.load(str(path),link=False) as (data,out):out.objects=data.objects
        for ob in out.objects:
            if ob.type!='MESH':continue
            bpy.context.collection.objects.link(ob)
            for m in list(ob.modifiers):
                if m.type=='ARMATURE':ob.modifiers.remove(m)
            mod=ob.modifiers.new('Skin','ARMATURE');mod.object=r;objects.append(ob)
    bpy.data.objects.remove(src,do_unlink=True)
    for ob in list(bpy.context.scene.objects):
        if ob not in objects+[r]:bpy.data.objects.remove(ob,do_unlink=True)
    bpy.context.scene.render.fps=FPS
    bpy.ops.file.pack_all()
    for ob in objects:
        common.save_part(OUT/'Parts'/(ob.name+'.blend'),[r,ob])
        common.export(OUT/'Parts'/(ob.name+'.fbx'),[r,ob])
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Witch_OriginalRobeV05.blend'))
    # Keep the cloth extraction source separate. The delivered render FBX must
    # contain no simulation cage geometry, regardless of UE section flags.
    cage=next(o for o in objects if 'SimProxy' in o.name);cage.hide_render=False
    common.export(DEL/'SK_Witch_OriginalRobeV05_ClothBuildSource.fbx',[r]+objects)
    cage.hide_render=True
    common.export(DEL/'SK_Witch_OriginalRobeV05.fbx',[r]+[o for o in objects if o!=cage])
    manifest={'revision':'OriginalRobeV05','parts':{o.name:len(o.data.vertices) for o in objects},
        'original_visible_robe_faces':len(robe_ids),'original_foot_faces':len(foot_ids),
        'robe_source_polygons':robe_ids,'feet_source_polygons':foot_ids,
        'rest_sole_z_cm':min(v.co.z for v in feet.data.vertices)*100,
        'visible_robe_geometry':'Original Meshy polygons, positions, UVs and split normals; only material slot and skin weights changed',
        'tested':False}
    (OUT/'body_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('V05_BODY_AUTHORED '+json.dumps({k:v for k,v in manifest.items() if not k.endswith('_polygons')}),flush=True)

def sample(samples,t):
    f=t*(len(samples)-1);a=math.floor(f);b=min(a+1,len(samples)-1);w=f-a
    result={}
    for n in samples[a]:
        la,qa,sa=samples[a][n].decompose();lb,qb,sb=samples[b][n].decompose()
        result[n]=Matrix.LocRotScale(la.lerp(lb,w),qa.slerp(qb,w),sa.lerp(sb,w))
    return result

UPPER={'Spine02':.12,'Spine01':.35,'Spine':.60,'neck':.80,'Head':.85,'head_end':.85,'headfront':.85,
       'LeftShoulder':.9,'LeftArm':1.,'LeftForeArm':1.,'LeftHand':1.,
       'RightShoulder':.75,'RightArm':.92,'RightForeArm':.95,'RightHand':1.}

def write_keys(r,samples,name,file,meshes=True):
    r.animation_data_clear();r.animation_data_create();a=bpy.data.actions.new(name);r.animation_data.action=a
    last={}
    for i,s in enumerate(samples):
        for b in r.pose.bones:
            b.rotation_mode='QUATERNION';b.matrix_basis=s[b.name]
            if b.name in last and b.rotation_quaternion.dot(last[b.name])<0:b.rotation_quaternion.negate()
            last[b.name]=b.rotation_quaternion.copy()
            for ch in ['location','rotation_quaternion','scale']:b.keyframe_insert(ch,frame=i,group=b.name)
    a.use_fake_user=True
    scene=bpy.context.scene;scene.frame_start=0;scene.frame_end=len(samples)-1;scene.frame_set(0);common.update()
    bpy.ops.wm.save_as_mainfile(filepath=str(file))
    common.export(file.with_suffix('.fbx'),[r],True)

def motions():
    roles=['Idle','Walk','CastPoison','ThrowPoisonBottle','DeathBackward']
    clouds={n:common.cache_cloud(n) for n in roles if n!='Walk'}
    native=common.native_walk();rr,raw,duration=native
    drift=raw[-1]['Hips'].translation-raw[0]['Hips'].translation;drift.z=0
    speed=drift.length/duration
    report={}
    for role in roles:
        bpy.ops.wm.open_mainfile(filepath=str(OUT/'Witch_OriginalRobeV05.blend'))
        r=common.rig();common.neutral(r);wr=common.rest(r);inv=r.matrix_world.inverted()
        scene=bpy.context.scene;scene.render.fps=FPS
        feet=bpy.data.objects['Witch_OriginalFeet']
        seconds=duration if role=='Walk' else clouds[role][1];count=round(seconds*FPS)
        lower=[];carry=[];final=[]
        for i in range(count+1):
            scene.frame_set(i)
            if role=='Walk':
                s=raw[i];world={}
                for b in r.data.bones:
                    n=b.name;q=s[n].to_quaternion()@rr[n].to_quaternion().inverted()@wr[n].to_quaternion()
                    pos=s[n].translation-drift*i/count if not b.parent else world[b.parent.name]@(wr[b.parent.name].inverted()@wr[n]).translation
                    world[n]=Matrix.LocRotScale(pos,q,wr[n].to_scale());r.pose.bones[n].matrix=inv@world[n];common.update()
                lower.append({p.name:p.matrix_basis.copy() for p in r.pose.bones})
                # One full carry/breathing cycle per stride. No modulo reset at
                # two seconds, and no unrelated upper-body pose at loop end.
                reference=sample(clouds['Idle'][0],i/count)
                carry.append(reference)
                for n,weight in UPPER.items():
                    p=r.pose.bones[n];loc,q,sc=p.matrix_basis.decompose();rl,rq,rs=reference[n].decompose()
                    p.matrix_basis=Matrix.LocRotScale(loc.lerp(rl,weight),q.slerp(rq,weight),sc.lerp(rs,weight))
            else:
                for p in r.pose.bones:p.matrix_basis=clouds[role][0][i][p.name]
            common.update()
            if role!='DeathBackward':
                deps=bpy.context.evaluated_depsgraph_get();ev=feet.evaluated_get(deps);mesh=ev.to_mesh()
                low=min((ev.matrix_world@v.co).z for v in mesh.vertices);ev.to_mesh_clear()
                # Keep the lowest real sole on the authored floor while leaving
                # the source swing arc and knee bend intact.
                h=r.pose.bones['Hips'];m=r.matrix_world@h.matrix;m.translation.z-=low;h.matrix=inv@m;common.update()
            final.append({p.name:p.matrix_basis.copy() for p in r.pose.bones})
        if role=='Walk':
            write_keys(r,lower,'Witch_Locomotion_Source',OUT/'MotionLayers/Witch_LowerBody_Source.blend')
            write_keys(r,carry,'Witch_UpperBody_Carry',OUT/'MotionLayers/Witch_UpperBody_Carry.blend')
        write_keys(r,final,'A_Witch_'+role+'_OriginalRobeV05',OUT/f'Witch_{role}_OriginalRobeV05.blend')
        common.export(DEL/f'A_Witch_{role}_OriginalRobeV05.fbx',[r],True)
        report[role]={'seconds':seconds,'frames':len(final),'speed_cm_s':speed*100 if role=='Walk' else None}
        print('V05_ACTION_AUTHORED',role,flush=True)
    (OUT/'motion_manifest.json').write_text(json.dumps({'actions':report,'upper_bone_mask':UPPER,'root_owner':'locomotion','tested':False},indent=2),encoding='utf-8')

if __name__=='__main__':
    stage=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'all'
    if stage in ['all','body']:body()
    if stage in ['all','motion']:motions()
    print('WITCH_ORIGINAL_ROBE_V05_SAVED',stage,flush=True)
