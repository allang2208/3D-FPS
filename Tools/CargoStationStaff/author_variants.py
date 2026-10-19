"""Tailor station workwear on the preserved V13 male body and native rig.

Production/export only. No animation evaluation or preview renders.
"""
import bpy, bmesh, json, math
import numpy as np
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform

PROJECT=Path('D:/FPS3D/FPSGAME')
BASE=PROJECT/'SourceAssets/FacelessSecurity20261008'
ROOT=PROJECT/'SourceAssets/CargoStationStaff20261014/V01'
for d in ['Authoring','Delivery','Textures','Logs']:(ROOT/d).mkdir(parents=True,exist_ok=True)

def active(o):
    bpy.ops.object.select_all(action='DESELECT');o.hide_set(False);o.select_set(True)
    bpy.context.view_layer.objects.active=o

def apply(o,m):
    active(o);bpy.ops.object.modifier_apply(modifier=m.name)

def normals(o):
    if o.data.has_custom_normals:o.data.normals_split_custom_set([(0.,0.,0.)]*len(o.data.loops))
    bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
    for p in o.data.polygons:p.use_smooth=True
    o.data.update()

def bind(o,rows,rig):
    o.vertex_groups.clear()
    groups={n:o.vertex_groups.new(name=n) for n in sorted({n for row in rows for n in row})}
    for i,row in enumerate(rows):
        total=sum(row.values())
        for n,w in row.items():
            if w>1e-7:groups[n].add([i],w/total,'REPLACE')
    o.parent=rig;o.matrix_parent_inverse=rig.matrix_world.inverted()
    mod=o.modifiers.new('PreservedNativeSkin','ARMATURE');mod.object=rig

def surface(o,outer_only=False):
    o.data.calc_loop_triangles();p=[o.matrix_world@v.co for v in o.data.vertices]
    tris=[tuple(t.vertices) for t in o.data.loop_triangles if not outer_only or max(t.vertices)<len(p)//2]
    rows=[{o.vertex_groups[g.group].name:g.weight for g in v.groups} for v in o.data.vertices]
    return BVHTree.FromPolygons(p,tris,all_triangles=True),p,tris,rows

def sample(hit,surf):
    _,points,tris,rows=surf;ids=tris[hit[2]]
    abc=barycentric_transform(hit[0],*(points[i] for i in ids),Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))
    out={}
    for i,a in zip(ids,abc):
        for n,w in rows[i].items():out[n]=out.get(n,0)+max(0.,a)*w
    total=sum(out.values());return {n:w/total for n,w in out.items() if w>1e-7}

def mesh(name,verts,faces,mat):
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
    o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);me.materials.append(mat)
    uv=me.uv_layers.new(name='UVMap')
    for face in me.polygons:
        for li in face.loop_indices:
            p=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(p.x/.2,p.z/.2)
    normals(o);return o

def shell(o,thickness):
    mod=o.modifiers.new('SewnThickness','SOLIDIFY');mod.thickness=thickness;mod.offset=-1
    active(o)
    while o.modifiers[0]!=mod:bpy.ops.object.modifier_move_up(modifier=mod.name)
    apply(o,mod)
    normals(o)

def material(name,color,rough,kind='cloth',metal=0):
    size=1024;yy,xx=np.mgrid[:size,:size];u=xx/size;v=yy/size
    macro=.5*np.sin(2*math.pi*u*3)*np.sin(2*math.pi*v*5)+.23*np.sin(2*math.pi*(u+v)*11)
    if kind=='cloth':
        mask=((np.floor(u*256)+np.floor(v*256))%4<2)
        height=.28*np.where(mask,np.sin(2*math.pi*u*256),np.sin(2*math.pi*v*256))+.08*np.sin(2*math.pi*(u-v)*64)
    else:height=.018*np.sin(2*math.pi*u*270)+.01*macro
    dy,dx=np.gradient(height);normal=np.stack([-dx*.32,-dy*.32,np.ones_like(height)],axis=-1)
    normal/=np.linalg.norm(normal,axis=-1)[:,:,None]
    base=np.clip(np.array(color)[None,None,:]*(1+.075*height[:,:,None]+.07*macro[:,:,None]),0,1)
    orm=np.ones((size,size,3));orm[:,:,1]=np.clip(rough-.05*height+.025*macro,.15,.96);orm[:,:,2]=metal
    mat=bpy.data.materials.new(name);mat.use_nodes=True;n=mat.node_tree.nodes;l=mat.node_tree.links
    bs=next((node for node in n if node.type=='BSDF_PRINCIPLED'),None) or n.new('ShaderNodeBsdfPrincipled')
    output=next((node for node in n if node.type=='OUTPUT_MATERIAL'),None) or n.new('ShaderNodeOutputMaterial')
    l.new(bs.outputs['BSDF'],output.inputs['Surface'])
    bs.inputs['Sheen Weight'].default_value=.12 if kind=='cloth' else 0
    for suffix,array,data in [('BaseColor',base,False),('Normal',normal*.5+.5,True),('ORM',orm,True)]:
        im=bpy.data.images.new(name+'_'+suffix,width=size,height=size,alpha=False)
        if data:im.colorspace_settings.name='Non-Color'
        rgba=np.ones((size,size,4),np.float32);rgba[:,:,:3]=array;im.pixels.foreach_set(rgba.ravel())
        im.filepath_raw=str(ROOT/'Textures'/(im.name+'.png'));im.file_format='PNG';im.save()
        tex=n.new('ShaderNodeTexImage');tex.image=im
        if suffix=='BaseColor':l.new(tex.outputs['Color'],bs.inputs['Base Color'])
        elif suffix=='Normal':
            nm=n.new('ShaderNodeNormalMap');l.new(tex.outputs['Color'],nm.inputs['Color']);l.new(nm.outputs['Normal'],bs.inputs['Normal'])
        else:
            sep=n.new('ShaderNodeSeparateColor');l.new(tex.outputs['Color'],sep.inputs['Color'])
            l.new(sep.outputs['Green'],bs.inputs['Roughness']);l.new(sep.outputs['Blue'],bs.inputs['Metallic'])
    return mat

def cut_patch(source,name,predicate,offset,mat,rig):
    # Copy only the already-weighted outer face region; retain exact weights/UVs.
    o=source.copy();o.data=source.data.copy();bpy.context.collection.objects.link(o);o.name=name;o.modifiers.clear()
    bm=bmesh.new();bm.from_mesh(o.data)
    nouter=len(source.data.vertices)//2
    remove=[f for f in bm.faces if any(v.index>=nouter for v in f.verts) or not predicate(f.calc_center_median())]
    bmesh.ops.delete(bm,geom=remove,context='FACES');bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
    bm.normal_update()
    for v in bm.verts:v.co+=v.normal*offset
    bm.to_mesh(o.data);bm.free();o.data.materials.clear();o.data.materials.append(mat)
    for p in o.data.polygons:p.material_index=0
    shell(o,.0018);mod=o.modifiers.new('PreservedNativeSkin','ARMATURE');mod.object=rig
    return o

def fitted_patch(name,surf,xlo,xhi,zlo,zhi,depth,mat,rig,side='front'):
    verts=[];rows=[];nx=16;nz=18
    for j in range(nz+1):
        t=j/nz;z=zlo+(zhi-zlo)*t
        for i in range(nx+1):
            s=i/nx;x=xlo+(xhi-xlo)*s
            if side=='front':origin=Vector((x,-.5,z));direction=Vector((0,1,0))
            else:origin=Vector((x,.5,z));direction=Vector((0,-1,0))
            hit=surf[0].ray_cast(origin,direction,1.)
            if hit[0] is None:raise RuntimeError('Garment projection missing '+name+' '+str((x,z)))
            p=hit[0]-direction*(.003+depth*math.sin(math.pi*s)*math.sin(math.pi*t))
            verts.append(p);rows.append(sample(hit,surf))
    faces=[(j*(nx+1)+i,j*(nx+1)+i+1,(j+1)*(nx+1)+i+1,(j+1)*(nx+1)+i) for j in range(nz) for i in range(nx)]
    o=mesh(name,verts,faces,mat);bind(o,rows,rig);shell(o,.0015);return o

def export_skeletal(rig,objects,name):
    copies=[]
    for o in objects:
        d=o.copy();d.data=o.data.copy();bpy.context.collection.objects.link(d);d.hide_set(False);copies.append(d)
    active(copies[0])
    for o in copies:o.select_set(True)
    bpy.ops.object.join();merged=bpy.context.object;merged.name=name
    active(merged);rig.hide_set(False);rig.select_set(True);bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.fbx(filepath=str(ROOT/'Delivery'/(name+'.fbx')),use_selection=True,object_types={'ARMATURE','MESH'},
        add_leaf_bones=False,bake_anim=False,axis_forward='-Y',axis_up='Z',apply_unit_scale=True,
        use_armature_deform_only=False,mesh_smooth_type='FACE',use_mesh_modifiers=False)
    info=dict(file=name+'.fbx',triangles=sum(len(p.vertices)-2 for p in merged.data.polygons),materials=[m.name for m in merged.data.materials])
    bpy.data.objects.remove(merged,do_unlink=True);return info

def helmet(role,mat,trim,rig):
    cy=-.015;parts=[];N=72;verts=[]
    rings=[(.101,.119,1.756),(.105,.124,1.780),(.099,.119,1.820),(.080,.099,1.854),(.043,.057,1.875),(.003,.004,1.881)]
    for rx,ry,z in rings:
        for i in range(N):
            a=2*math.pi*i/N;verts.append((rx*math.sin(a),cy-ry*math.cos(a),z))
    faces=[(j*N+i,j*N+(i+1)%N,(j+1)*N+(i+1)%N,(j+1)*N+i) for j in range(len(rings)-1) for i in range(N)]
    faces.append(tuple((len(rings)-1)*N+i for i in range(N)))
    crown=mesh(role+'_HelmetShell',verts,faces,mat);shell(crown,.003);parts.append(crown)
    verts=[]
    for t in [0.,.25,.5,.75,1.]:
        for i in range(N):
            a=2*math.pi*i/N;front=max(0.,math.cos(a))**5
            verts.append(((.101+.014*t)*math.sin(a),cy-(.119+.017*t+.026*t*front)*math.cos(a),1.757-.004*t))
    faces=[(j*N+i,j*N+(i+1)%N,(j+1)*N+(i+1)%N,(j+1)*N+i) for j in range(4) for i in range(N)]
    brim=mesh(role+'_HelmetBrim',verts,faces,mat);shell(brim,.003);parts.append(brim)
    # Raised longitudinal protective rib, sharing the shell profile.
    verts=[]
    for x in [-.006,.006]:
        for j in range(41):
            a=-1.18+2.36*j/40;verts.append((x,cy+.108*math.sin(a),1.785+.099*math.cos(a)))
    rib=mesh(role+'_HelmetRib',verts,[(i,i+1,42+i,41+i) for i in range(40)],mat);shell(rib,.004);parts.append(rib)
    verts=[]
    for z in [1.757,1.767]:
        for i in range(N):
            a=2*math.pi*i/N;verts.append((.1015*math.sin(a),cy-.120*math.cos(a),z))
    band=mesh(role+'_HelmetInnerBand',verts,[(i,(i+1)%N,N+(i+1)%N,N+i) for i in range(N)],trim);shell(band,.002);parts.append(band)
    active(crown)
    for p in parts:p.select_set(True)
    bpy.ops.object.join();cap=bpy.context.object;cap.name='SM_'+role+'_Helmet_V01'
    active(cap);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(island_margin=.015);bpy.ops.object.mode_set(mode='OBJECT')
    me=bpy.data.meshes.new('HelmetConvex');me.from_pydata(verts+[(rx*math.sin(2*math.pi*i/24),cy-ry*math.cos(2*math.pi*i/24),z) for rx,ry,z in rings[:-1] for i in range(24)],[],[])
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.convex_hull(bm,input=list(bm.verts),use_existing_faces=False);bm.to_mesh(me);bm.free()
    col=bpy.data.objects.new('UCX_'+cap.name+'_00',me);bpy.context.collection.objects.link(col);col.hide_render=True
    ref=json.loads((BASE/'V11/neck_source.json').read_text(encoding='utf-8'))['ue_head_reference']
    q=ref['rotation_xyzw'];rotation=Quaternion((q[3],q[0],q[1],q[2]));origin=Vector(ref['translation_cm'])
    pivot=Vector((0,-cy*100,179.1));local_pivot=rotation.inverted()@(pivot-origin)
    # Persist anatomical prop source before converting the export to head-local space.
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring'/(role+'_WithHelmet_V01.blend')))
    for o in [cap,col]:
        for v in o.data.vertices:
            p=v.co;ue=Vector((p.x*100,-p.y*100,p.z*100));local=rotation.inverted()@(ue-origin)-local_pivot
            v.co=Vector((local.x,-local.y,local.z))/100
        normals(o)
    active(cap);col.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(ROOT/'Delivery'/(cap.name+'.fbx')),use_selection=True,object_types={'MESH'},
        bake_anim=False,axis_forward='-Y',axis_up='Z',apply_unit_scale=True,mesh_smooth_type='FACE')
    return dict(name=cap.name,relative_location_cm=list(local_pivot),triangles=sum(len(p.vertices)-2 for p in cap.data.polygons))

report={'source':'FacelessSecurity V13 body/outfit and native skeleton; no animation changes','rendered':False,'runtime_tested':False,'variants':{}}
for role,number in [('CargoPorter','M-01'),('CargoTechnician','M-01')]:
    bpy.ops.wm.open_mainfile(filepath=str(BASE/'V13/Authoring/FacelessSecurity_V13.blend'))
    rig=bpy.data.objects['root'];rig.animation_data_clear()
    for b in rig.pose.bones:b.matrix_basis=Matrix.Identity(4)
    bpy.context.scene.frame_set(0);bpy.context.view_layer.update()
    body=bpy.data.objects['Security_CompleteBody'];display=bpy.data.objects['Security_OutfitBody']
    shirt=bpy.data.objects['Security_Uniform_SewnNeck_V11'];pants=bpy.data.objects['Security_Trousers_Continuous']
    # Remove police-only attachments. Preserve body, sleeves, cuffs and boot coverage.
    remove=['Security_Tie','Security_TieClip','Security_IDPlate','Security_IDLetters','Security_BackLettering','Security_FrontPlacket']
    for o in list(bpy.context.scene.objects):
        if o.name in remove or o.name.startswith(('Security_Epaulette','Security_ShirtButton','Security_PocketButton','Security_ChestPocket','Security_PocketFlap')):
            bpy.data.objects.remove(o,do_unlink=True)
    porter=role=='CargoPorter'
    wear=material(role+'_Workwear',(.075,.086,.087) if porter else (.075,.145,.175),.83)
    cloth=material(role+'_Vest' if porter else role+'_Reinforcement',(.83,.225,.029) if porter else (.032,.048,.060),.80)
    tape=material(role+'_Reflective',(.63,.67,.64),.36,'reflective',.24)
    plastic=material(role+'_Helmet',(.91,.64,.055) if porter else (.77,.78,.735),.38,'plastic')
    trim=bpy.data.materials['Security_Trim']
    for o in bpy.context.scene.objects:
        if o.type!='MESH':continue
        for i,m in enumerate(o.data.materials):
            if m.name in ['Security_Uniform','Security_Trousers']:o.data.materials[i]=wear
    shirt_surf=surface(shirt,True);pants_surf=surface(pants)
    if porter:
        def vest_region(p):
            return (1.08<p.z<1.55 and abs(p.x)<(.225 if p.z<1.32 else .205 if p.z<1.43 else .19)
                    and (p.z<1.48 or abs(p.x)>.085))
        vest=cut_patch(shirt,role+'_HighVisibilityVest',vest_region,.007,cloth,rig)
        for low,high in [(1.18,1.23),(1.31,1.36)]:
            cut_patch(shirt,role+'_ReflectiveWrap_'+str(low),lambda p,lo=low,hi=high:vest_region(p) and lo<p.z<hi,.0095,tape,rig)
        cut_patch(shirt,role+'_ReflectiveShoulders',lambda p:vest_region(p) and p.z>1.35 and .075<abs(p.x)<.115,.0095,tape,rig)
        for s in [-1,1]:
            fitted_patch(role+'_VestPocket_'+str(s),shirt_surf,min(s*.05,s*.16),max(s*.05,s*.16),1.09,1.17,.018,cloth,rig)
    else:
        cut_patch(shirt,role+'_ShoulderYoke',lambda p:1.455<p.z<1.53 and abs(p.x)<.25,.0035,cloth,rig)
        cut_patch(shirt,role+'_ChestReflective',lambda p:1.41<p.z<1.435 and abs(p.x)<.20,.005,tape,rig)
        for s in [-1,1]:
            fitted_patch(role+'_ChestPocket_'+str(s),shirt_surf,min(s*.06,s*.155),max(s*.06,s*.155),1.29,1.39,.012,wear,rig)
    # A fitted zipper replaces the security tie and button placket.
    fitted_patch(role+'_ZipperTape',shirt_surf,-.009,.009,1.09,1.46,.008 if porter else .002,trim,rig)
    for s in [-1,1]:
        fitted_patch(role+'_KneePatch_'+str(s),pants_surf,min(s*.105,s*.18),max(s*.105,s*.18),.46,.63,.006,cloth if not porter else wear,rig)
        if porter or s<0:
            fitted_patch(role+'_ThighPocket_'+str(s),pants_surf,min(s*.075,s*.19),max(s*.075,s*.19),.76,.91,.024,cloth if not porter else wear,rig)
    # The technician carries a fabric tool organizer, integral to the clothing rig.
    if not porter:
        fitted_patch(role+'_ToolOrganizer',pants_surf,.085,.19,.84,1.015,.030,trim,rig)
        for x in [.098,.125,.152,.179]:
            fitted_patch(role+'_ToolLoop_'+str(x),pants_surf,x-.005,x+.005,.91,.98,.034,wear,rig)
    clothes=[o for o in bpy.context.scene.objects if o.type=='MESH' and o not in [body,display]]
    body.hide_render=True;body.hide_set(True)
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring'/(role+'_V01.blend')))
    info=dict(number=number,clothing_parts=len(clothes),outfit=export_skeletal(rig,[display]+clothes,'SK_'+role+'_V01'),
              clothing=export_skeletal(rig,clothes,'SK_'+role+'_Clothing_V01'))
    info['helmet']=helmet(role,plastic,trim,rig)
    report['variants'][role]=info
    (ROOT/'authoring_receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('CARGO_AUTHORED '+role+' '+str(info['outfit']['triangles']),flush=True)
