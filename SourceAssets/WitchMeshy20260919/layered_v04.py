"""V04 editable layers: preserved Meshy identity, donor legs, projected robe,
native UE-retargeted locomotion. No preview or gameplay test is run here.
"""
import bpy, bmesh, json, math, shutil
import numpy as np
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'Authoring/LayeredV04'
DEL=ROOT/'Delivery/LayeredV04'
KEEP=OUT/'Preserved'
FPS=60
for d in [OUT,DEL,KEEP,OUT/'Textures',OUT/'Fitted',OUT/'Sources']:d.mkdir(parents=True,exist_ok=True)

def clear():bpy.ops.wm.read_factory_settings(use_empty=True)
def rig():return next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
def update():bpy.context.view_layer.update()
def frame(f):bpy.context.scene.frame_set(math.floor(f),subframe=f%1)
def smooth(x):x=max(0.,min(1.,x));return x*x*(3-2*x)
def rest(r):return {b.name:r.matrix_world@b.matrix_local for b in r.data.bones}
def neutral(r):
    r.animation_data_clear()
    for b in r.pose.bones:b.matrix_basis=Matrix.Identity(4)
    update()
def export(file,objects,anim=False):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:o.hide_set(False);o.select_set(True)
    bpy.context.view_layer.objects.active=next((o for o in objects if o.type=='ARMATURE'),objects[0])
    bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH','ARMATURE'},
        add_leaf_bones=False,use_armature_deform_only=False,bake_anim=anim,
        bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,
        bake_anim_force_startend_keying=True,bake_anim_simplify_factor=0,
        axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',
        mesh_smooth_type='FACE',path_mode='RELATIVE',embed_textures=False)

def subset(src,ids,name,r=None):
    polys=[src.data.polygons[i] for i in ids]
    old=sorted({int(i) for p in polys for i in p.vertices});remap={n:i for i,n in enumerate(old)}
    data=bpy.data.meshes.new(name)
    data.from_pydata([src.matrix_world@src.data.vertices[i].co for i in old],[],[[remap[int(i)] for i in p.vertices] for p in polys])
    ob=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(ob)
    for mat in src.data.materials:data.materials.append(mat)
    source_uv=src.data.uv_layers.active
    uv=data.uv_layers.new(name='UVMap') if source_uv else None
    for p,q in zip(polys,data.polygons):
        q.material_index=p.material_index;q.use_smooth=True
        if uv:
            for a,b in zip(p.loop_indices,q.loop_indices):uv.data[b].uv=source_uv.data[a].uv
    normals=[(src.matrix_world.to_3x3().inverted().transposed()@src.data.corner_normals[i].vector).normalized()
             for p in polys for i in p.loop_indices]
    data.normals_split_custom_set(normals)
    for group in src.vertex_groups:ob.vertex_groups.new(name=group.name)
    for i,n in enumerate(old):
        for g in src.data.vertices[n].groups:ob.vertex_groups[g.group].add([i],g.weight,'REPLACE')
    if r:
        mod=ob.modifiers.new('Skin','ARMATURE');mod.object=r
    ob['source_mesh']=src.name;ob['source_vertex_indices']=old
    return ob

def material(name,color,rough=.86):
    m=bpy.data.materials.new(name);m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=color;bs.inputs['Roughness'].default_value=rough
    return m

def save_part(file,objects):
    scene=bpy.data.scenes.new(file.stem)
    scene.unit_settings.system='METRIC';scene.render.fps=FPS
    included=set(objects)
    for obj in list(included):
        parent=obj.parent
        while parent:included.add(parent);parent=parent.parent
    for obj in included:scene.collection.objects.link(obj)
    bpy.data.libraries.write(str(file),{scene},fake_user=True,compress=True)
    bpy.data.scenes.remove(scene)

def store_asset(name,objects):
    save_part(KEEP/(name+'.blend'),objects)
    export(KEEP/(name+'.fbx'),objects)

def preserved():
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authoring/Witch_Rigged_Candidate_v01.blend'))
    r=rig();neutral(r)
    src=max((o for o in bpy.context.scene.objects if o.type=='MESH'),key=lambda o:len(o.data.vertices))
    poses=rest(r); groups={g.index:g.name for g in src.vertex_groups}
    parts={n:[] for n in ['Hat','Head_Hair','Hand_Left','Hand_Right','UpperRobe','LowerRobe_Reference']}
    for p in src.data.polygons:
        center=sum((src.matrix_world@src.data.vertices[i].co for i in p.vertices),Vector())/len(p.vertices)
        weights={}
        for i in p.vertices:
            for g in src.data.vertices[i].groups:weights[groups[g.group]]=weights.get(groups[g.group],0)+g.weight/len(p.vertices)
        role=None
        for side in ['Left','Right']:
            wrist=poses[side+'Hand'].translation;axis=(wrist-poses[side+'ForeArm'].translation).normalized()
            if (center-wrist).dot(axis)>-.025 and (center-wrist).length<.21 and weights.get(side+'ForeArm',0)+weights.get(side+'Hand',0)>.4:
                role='Hand_'+side;break
        if role is None:
            if center.z>=1.594:role='Hat'
            elif center.z>1.36 and weights.get('Head',0)+weights.get('neck',0)>.6:role='Head_Hair'
            elif center.z<.925 and sum(w for n,w in weights.items() if 'Arm' in n or 'Hand' in n)<.4:role='LowerRobe_Reference'
            else:role='UpperRobe'
        parts[role].append(p.index)
    index={}
    for name,ids in parts.items():
        ob=subset(src,ids,'Witch_'+name,r)
        store_asset(name,[r,ob]);index[name]={'faces':len(ids),'vertices':len(ob.data.vertices),'source_polygon_indices':ids}
        bpy.data.objects.remove(ob,do_unlink=True)
    (KEEP/'source_partition.json').write_text(json.dumps(index),encoding='utf-8')
    save_part(KEEP/'Original_Uncut.blend',[r,src])
    # Preserve original props and original PBR maps independently as well.
    for name,source in [('Staff',ROOT/'Authoring/CloudGripV02/Witch_StaffGripV02.blend'),('PoisonBottle',ROOT/'Authoring/Witch_PoisonBottle_Candidate_v01.blend')]:
        bpy.ops.wm.open_mainfile(filepath=str(source));objs=[o for o in bpy.context.scene.objects if o.type in {'MESH','ARMATURE'}]
        bpy.ops.file.pack_all();store_asset(name,objs)
    for path in (ROOT/'Meshy/body/downloads').glob('texture_urls_0_*.png'):shutil.copy2(path,KEEP/path.name)
    return index

MAP={'pelvis':'Hips','spine_01':'Spine02','spine_02':'Spine02','spine_03':'Spine01','spine_04':'Spine','spine_05':'Spine','neck_01':'neck','neck_02':'neck','head':'Head'}
for side,suf in [('Left','l'),('Right','r')]:
    for src,dst in [('thigh','UpLeg'),('calf','Leg'),('foot','Foot'),('ball','ToeBase')]:MAP[src+'_'+suf]=side+dst
ENDS={'pelvis':'spine_01','thigh_l':'calf_l','calf_l':'foot_l','foot_l':'ball_l','thigh_r':'calf_r','calf_r':'foot_r','foot_r':'ball_r'}
TENDS={'Hips':'Spine02','LeftUpLeg':'LeftLeg','LeftLeg':'LeftFoot','LeftFoot':'LeftToeBase','RightUpLeg':'RightLeg','RightLeg':'RightFoot','RightFoot':'RightToeBase'}

def donor_data(file,kind):
    clear();bpy.ops.import_scene.fbx(filepath=str(file));r=rig();neutral(r)
    src=max((o for o in bpy.context.scene.objects if o.type=='MESH'),key=lambda o:len(o.data.vertices))
    def keep(p):
        zs=[(src.matrix_world@src.data.vertices[i].co).z for i in p.vertices]
        return (max(zs)<.36 and p.material_index==3) if kind=='Feet' else (min(zs)>.26 and max(zs)<1.02)
    ob=subset(src,[p.index for p in src.data.polygons if keep(p)],kind)
    wr=rest(r);mapped={}
    for g in ob.vertex_groups:
        b=r.data.bones.get(g.name)
        while b and b.name not in MAP:b=b.parent
        mapped[g.index]=b.name if b else 'pelvis'
    vertices=[{'p':v.co.copy(),'w':[(mapped[g.group],g.weight) for g in v.groups]} for v in ob.data.vertices]
    return {'vertices':vertices,'faces':[tuple(p.vertices) for p in ob.data.polygons],
        'uv':[x.uv.copy() for x in ob.data.uv_layers.active.data],'rest':wr}

def fit_donor(data,kind,r):
    wr=rest(r);sr=data['rest'];vs=[];weights=[]
    for v in data['vertices']:
        p=Vector();out={};total=sum(w for n,w in v['w']) or 1
        for n,w in v['w']:
            dst=MAP.get(n,'Hips');a=sr[n].translation;b=wr[dst].translation
            end=ENDS.get(n)
            if end and end in sr and dst in TENDS:
                d=sr[end].translation-a;t=wr[TENDS[dst]].translation-b
                q=d.rotation_difference(t);scale=t.length/d.length
            else:q=Matrix.Identity(3).to_quaternion();scale=.82
            p+=(b+(q@(v['p']-a))*scale)*(w/total)
            out[dst]=out.get(dst,0)+w/total
        vs.append(p);weights.append(out)
    # Ground the actual donor soles in the bind pose; no fabricated cylinder feet.
    if kind=='Feet':
        floor=min(p.z for p in vs)
        for p in vs:p.z-=floor
    data_mesh=bpy.data.meshes.new('Witch_'+kind);data_mesh.from_pydata(vs,[],data['faces'])
    ob=bpy.data.objects.new('Witch_'+kind,data_mesh);bpy.context.collection.objects.link(ob)
    uv=data_mesh.uv_layers.new(name='UVMap')
    for a,b in zip(uv.data,data['uv']):a.uv=b
    for name in wr:ob.vertex_groups.new(name=name)
    for i,w in enumerate(weights):
        for n,value in w.items():ob.vertex_groups[n].add([i],value,'REPLACE')
    mod=ob.modifiers.new('Skin','ARMATURE');mod.object=r
    for p in data_mesh.polygons:p.use_smooth=True
    if kind=='Feet':
        mat=material('M_Witch_V04_Feet',(.12,.11,.09,1))
        tex=next((OUT/'Sources').glob('*BaseColor.tga'),None)
        if tex:
            node=mat.node_tree.nodes.new('ShaderNodeTexImage');node.image=bpy.data.images.load(str(tex));node.image.pack()
            tint=mat.node_tree.nodes.new('ShaderNodeMixRGB');tint.blend_type='MULTIPLY';tint.inputs[0].default_value=1;tint.inputs[2].default_value=(.56,.59,.5,1)
            mat.node_tree.links.new(node.outputs['Color'],tint.inputs[1]);mat.node_tree.links.new(tint.outputs[0],mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
    else:mat=material('M_Witch_V04_InnerBody',(.018,.017,.014,1))
    data_mesh.materials.append(mat)
    ob['source']='Local Nurse female bare feet/calf skin' if kind=='Feet' else 'Local Epic Quinn hidden thigh/knee topology'
    return ob

def robe(src,r,ids):
    # A continuous open garment with uniform rows replaces fused leg/robe skin.
    source=subset(src,ids,'Witch_Robe_ProjectionSource')
    source.data.calc_loop_triangles()
    triangles=list(source.data.loop_triangles)
    verts=[v.co.copy() for v in source.data.vertices]
    tris=[tuple(t.vertices) for t in triangles]
    uv=source.data.uv_layers.active
    tuv=[[Vector((uv.data[i].uv.x,uv.data[i].uv.y,0)) for i in t.loops] for t in triangles]
    bvh=BVHTree.FromPolygons(verts,tris,all_triangles=True)
    N=80;R=32;top=.945;bottom=.09;points=[];reference=[]
    def surface(theta,z):
        direction=Vector((math.sin(theta),-math.cos(theta),0));center=Vector((0,.045,z))
        hit,normal,idx,dist=bvh.ray_cast(center+direction*.75,-direction,1.0)
        if hit is None:hit,normal,idx,dist=bvh.find_nearest(center+direction*.245)
        return hit,normal,idx
    for j in range(R+1):
        t=j/R;z=top+(bottom-top)*t
        for i in range(N):
            theta=i/N*math.tau;hit,normal,idx=surface(theta,z)
            p=hit.copy();p.z=z
            # Extra walking room below the hip, with the waist overlap fixed.
            radial=Vector((p.x,p.y-.045,0));radius=radial.length
            if radius>0:p+=radial.normalized()*(.022*smooth((.8-z)/.30))
            # A short irregular hem retains the ragged character silhouette.
            p.z+=smooth((t-.85)/.15)*(.008*math.sin(theta*7)+.006*math.sin(theta*13+.4))
            points.append(p);reference.append(hit)
    faces=[]
    for j in range(R):
        for i in range(N):faces.append((j*N+i,(j+1)*N+i,(j+1)*N+(i+1)%N,j*N+(i+1)%N))
    me=bpy.data.meshes.new('Witch_Robe_Cloth');me.from_pydata(points,[],faces)
    ob=bpy.data.objects.new('Witch_Robe_Cloth',me);bpy.context.collection.objects.link(ob)
    layer=me.uv_layers.new(name='RobeUV')
    for p in me.polygons:
        j=p.index//N;i=p.index%N
        coords=[(i/N,1-j/R),(i/N,1-(j+1)/R),((i+1)/N,1-(j+1)/R),((i+1)/N,1-j/R)]
        for l,co in zip(p.loop_indices,coords):layer.data[l].uv=co
        p.use_smooth=True
    hips=ob.vertex_groups.new(name='Hips');hips.add(list(range(len(points))),1,'REPLACE')
    pin=ob.vertex_groups.new(name='Cloth_Pin')
    for i,p in enumerate(points):pin.add([i],1-smooth((top-p.z-.03)/.11),'REPLACE')
    arm=ob.modifiers.new('Skin','ARMATURE');arm.object=r
    # Reproject the original surface PBR to this garment UV. CPU sampling only;
    # this is texture authoring, not a preview render or acceptance test.
    size=1024
    coords=np.empty((size*size,2),dtype=np.float32)
    for y in range(size):
        z=bottom+(top-bottom)*(y+.5)/size
        for x in range(size):
            hit,no,idx=surface((x+.5)/size*math.tau,z)
            tri=tris[idx];q=barycentric_transform(hit,*[verts[k] for k in tri],*tuv[idx]);coords[y*size+x]=q.x,q.y
        if y%256==0:print('V04_ROBE_PROJECT',y,flush=True)
    maps={}
    for channel in ['base_color','roughness','metallic']:
        file=ROOT/'Meshy/body/downloads'/('texture_urls_0_'+channel+'.png')
        im=bpy.data.images.load(str(file),check_existing=True)
        if channel!='base_color':im.colorspace_settings.name='Non-Color'
        array=np.empty(len(im.pixels),dtype=np.float32);im.pixels.foreach_get(array)
        w,h=im.size;array=array.reshape(h,w,4)
        xx=np.clip(coords[:,0]*(w-1),0,w-1);yy=np.clip(coords[:,1]*(h-1),0,h-1)
        x0=xx.astype(int);y0=yy.astype(int);x1=np.minimum(x0+1,w-1);y1=np.minimum(y0+1,h-1)
        fx=(xx-x0)[:,None];fy=(yy-y0)[:,None]
        pixels=(array[y0,x0]*(1-fx)+array[y0,x1]*fx)*(1-fy)+(array[y1,x0]*(1-fx)+array[y1,x1]*fx)*fy
        image=bpy.data.images.new('T_Witch_RobeV04_'+channel,width=size,height=size,alpha=True)
        if channel!='base_color':image.colorspace_settings.name='Non-Color'
        image.pixels.foreach_set(pixels.astype(np.float32).ravel());image.filepath_raw=str(OUT/'Textures'/(image.name+'.png'));image.file_format='PNG';image.save();image.pack();maps[channel]=image
    mat=material('M_Witch_V04_RobeCloth',(.06,.05,.04,1));bs=mat.node_tree.nodes['Principled BSDF']
    for channel,socket in [('base_color','Base Color'),('roughness','Roughness'),('metallic','Metallic')]:
        tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=maps[channel];mat.node_tree.links.new(tex.outputs['Color'],bs.inputs[socket])
    # Original tangent-space normals cannot simply be copied across new UVs.
    # Mesh folds are geometry; fine fabric grain uses the projected roughness.
    bump=mat.node_tree.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.15;bump.inputs['Distance'].default_value=.0015
    grain=mat.node_tree.nodes.new('ShaderNodeTexImage');grain.image=maps['roughness'];mat.node_tree.links.new(grain.outputs['Color'],bump.inputs['Height']);mat.node_tree.links.new(bump.outputs['Normal'],bs.inputs['Normal'])
    me.materials.append(mat);ob['cloth']='Chaos simulation section; hip-pinned upper band; real leg collisions'
    save_part(OUT/'Fitted/Witch_Robe_ProjectionSource.blend',[source])
    bpy.data.objects.remove(source,do_unlink=True)
    return ob

def create_body(parts,feet,body):
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authoring/CloudGripV02/Witch_GripBodyV02.blend'))
    r=rig();neutral(r)
    src=max((o for o in bpy.context.scene.objects if o.type=='MESH'),key=lambda o:len(o.data.vertices))
    objects=[]
    for name in ['Hat','Head_Hair','Hand_Left','Hand_Right','UpperRobe']:
        ob=subset(src,parts[name]['source_polygon_indices'],'Witch_'+name,r);objects.append(ob)
    objects.extend([fit_donor(feet,'Feet',r),fit_donor(body,'InnerBody',r)])
    garment=robe(src,r,parts['LowerRobe_Reference']['source_polygon_indices']);objects.append(garment)
    bpy.data.objects.remove(src,do_unlink=True)
    for ob in list(bpy.context.scene.objects):
        if ob not in objects+[r]:bpy.data.objects.remove(ob,do_unlink=True)
    bpy.context.scene.render.fps=FPS
    bpy.ops.file.pack_all()
    for ob in objects:
        save_part(OUT/'Fitted'/(ob.name+'.blend'),[r,ob])
        export(OUT/'Fitted'/(ob.name+'.fbx'),[r,ob])
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Witch_LayeredBodyV04.blend'))
    export(DEL/'SK_Witch_LayeredV04.fbx',[r]+objects)
    return {'layers':{o.name:len(o.data.vertices) for o in objects},'bones':len(r.data.bones)}

def cache_cloud(role):
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/f'Authoring/CloudGripV02/Witch_{role}_CloudGripV02.blend'))
    r=rig();a=r.animation_data.action;start,end=a.frame_range;fps=bpy.context.scene.render.fps
    duration=(end-start)/fps;count=round(duration*FPS)
    samples=[]
    for i in range(count+1):
        frame(start+(end-start)*i/count)
        samples.append({b.name:b.matrix_basis.copy() for b in r.pose.bones})
    return samples,duration

def native_walk():
    clear();bpy.ops.import_scene.fbx(filepath=str(OUT/'RetargetedRaw/A_Witch_Raw_Walk01Forward.fbx'))
    r=rig();a=r.animation_data.action
    raw_rest=rest(r);raw_rest['Hips']=r.matrix_world.copy()
    # FBX represents the root Hips as the animated armature object itself.
    samples=[]
    for i in range(197):
        frame(float(a.frame_range[0])+i*.5)
        s={b.name:r.matrix_world@b.matrix for b in r.pose.bones};s['Hips']=r.matrix_world.copy();samples.append(s)
    return raw_rest,samples,98/30

def author_motion(role,cloud,native,idle):
    bpy.ops.wm.open_mainfile(filepath=str(OUT/'Witch_LayeredBodyV04.blend'))
    r=rig();neutral(r);wr=rest(r);inv=r.matrix_world.inverted();scene=bpy.context.scene;scene.render.fps=FPS
    r.animation_data_create();r.animation_data.action=bpy.data.actions.new('A_Witch_'+role+'_LayeredV04')
    for b in r.pose.bones:b.rotation_mode='QUATERNION'
    feet=next(o for o in scene.objects if o.name=='Witch_Feet')
    duration=native[2] if role=='Walk' else cloud[1];count=round(duration*FPS)
    last={};speed=0
    if role=='Walk':
        rr,ns,_=native;drift=ns[-1]['Hips'].translation-ns[0]['Hips'].translation;drift.z=0;speed=drift.length/duration
    for i in range(count+1):
        scene.frame_set(i)
        if role=='Walk':
            samples=native[1];s=samples[i];world={}
            for b in r.data.bones:
                n=b.name;q=s[n].to_quaternion()@native[0][n].to_quaternion().inverted()@wr[n].to_quaternion()
                if not b.parent:pos=s[n].translation-drift*i/count
                else:pos=world[b.parent.name]@(wr[b.parent.name].inverted()@wr[n]).translation
                world[n]=Matrix.LocRotScale(pos,q,wr[n].to_scale())
                r.pose.bones[n].matrix=inv@world[n]
                update()
            # Retain donor pelvis/spine/shoulder dynamics; arms carry the props
            # using the cloud idle reference, without freezing the torso.
            ref=idle[0][i%(len(idle[0])-1)]
            for side in ['Left','Right']:
                for segment in ['Arm','ForeArm','Hand']:
                    pb=r.pose.bones[side+segment];loc,q,sc=pb.matrix_basis.decompose();_,iq,_=ref[pb.name].decompose()
                    blend=.78 if side=='Left' else .65
                    pb.matrix_basis=Matrix.LocRotScale(loc,q.slerp(iq,blend),sc)
            update()
        else:
            for b in r.pose.bones:b.matrix_basis=cloud[0][i][b.name]
            update()
        # Sole height comes from the actual deformed donor foot mesh. Retain
        # the swing-foot arc; translate only the pelvis to place the lowest sole.
        if role!='DeathBackward':
            dg=bpy.context.evaluated_depsgraph_get();ev=feet.evaluated_get(dg);me=ev.to_mesh()
            low=min((ev.matrix_world@v.co).z for v in me.vertices);ev.to_mesh_clear()
            hip=r.pose.bones['Hips'];m=r.matrix_world@hip.matrix;m.translation.z-=low;hip.matrix=inv@m;update()
        for b in r.pose.bones:
            if b.name in last and b.rotation_quaternion.dot(last[b.name])<0:b.rotation_quaternion.negate()
            last[b.name]=b.rotation_quaternion.copy()
            for ch in ['location','rotation_quaternion','scale']:b.keyframe_insert(ch,frame=i,group=b.name)
        if i%60==0:print('V04_ANIMATION',role,i,flush=True)
    scene.frame_start=0;scene.frame_end=count;scene.frame_set(0)
    for name,seconds in ({'Release':.535714} if role=='CastPoison' else {'Release':.75} if role=='ThrowPoisonBottle' else {}).items():scene.timeline_markers.new(name,frame=round(seconds*FPS))
    scene['source']='UE native IK retarget + prop carry layer + actual sole placement' if role=='Walk' else 'Existing Meshy cloud V02 action + actual sole placement'
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/f'Witch_{role}_LayeredV04.blend'))
    export(DEL/f'A_Witch_{role}_LayeredV04.fbx',[r],True)
    return {'seconds':duration,'speed_cm_s':speed*100 if role=='Walk' else None,'frames':count+1}

if __name__=='__main__':
    import sys
    stage=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'all'
    if stage in ['all','body']:
        parts=preserved()
        nurse=OUT/'Sources/Nurse_SourceSkinWalk.fbx'
        if not nurse.exists():shutil.copy2(Path('D:/FPS3D/FPSGAME/Saved/NurseZombie/ANMS_ZombieFemaleWalk01Forward.fbx'),nurse)
        feet=donor_data(nurse,'Feet')
        body=donor_data(OUT/'Sources/SKM_Quinn_Simple.fbx','InnerBody')
        report=create_body(parts,feet,body)
        (OUT/'body_manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    if stage in ['all','motion']:
        roles=['Idle','Walk','CastPoison','ThrowPoisonBottle','DeathBackward']
        clouds={n:cache_cloud(n) for n in roles if n!='Walk'};native=native_walk()
        records={n:author_motion(n,clouds.get(n),native,clouds['Idle']) for n in roles}
        (OUT/'motion_manifest.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
    print('WITCH_V04_AUTHORING_SAVED',stage,flush=True)
