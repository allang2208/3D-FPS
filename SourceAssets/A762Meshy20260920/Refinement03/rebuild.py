"""A762 eye-side sight, complete upper fore-end and ADS shoulder reconstruction.
Authoring/export only. No game launch, renders, or acceptance tests.
"""
import ast,bpy,bmesh,json,math,shutil
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent; D=O/'Exports'; D.mkdir(exist_ok=True)
previous=O.parent/'Refinement02'; meta=json.loads((O.parent/'Integration/authoring.json').read_text(encoding='utf-8'))
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(previous/'A762_Reconstructed_Editable.blend'))
s=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima'];hands=bpy.data.objects['SK_Manny_Arms_Export']
r.animation_data.action=bpy.data.actions['A_A762_idle'];r.animation_data.action_slot=r.animation_data.action.slots[0]
r.data.pose_position='POSE';s.frame_set(0);bpy.context.view_layer.update()
root=r.pose.bones['WPN_root'].matrix.copy();rest={b.name:b.matrix_local.copy() for b in r.data.bones};pose={b.name:b.matrix.copy() for b in r.pose.bones}
cx=.00056;new=[];magazines=[];body=[];sights={'RearSight':[],'FrontSight':[]}
archive=bpy.data.collections.new('A762_BEFORE_REFINEMENT03');s.collection.children.link(archive)
made=bpy.data.collections.new('A762_CLOSED_SURFACES_03');s.collection.children.link(made)
report={'source':'Refinement02/A762_Reconstructed_Editable.blend','new_parts':{},'materials':{},'changes':{},'tests_run':False,'renders_run':False,
        'markers':meta['markers_blender_root'],'hinges':meta['hinges_ue_root']}

# Reuse only the known geometry-authoring functions, not the previous build's
# scene setup or mutations. Source remains alongside this revision.
functions={'select','regions','bind','primitive','extrude','box','lathe','tube','pin','rounded_rect','loop_prism'}
tree=ast.parse((previous/'rebuild.py').read_text(encoding='utf-8'))
module=ast.Module(body=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in functions],type_ignores=[])
exec(compile(module,str(previous/'rebuild.py'),'exec'),globals())
def hide_old(ob):
    ob.name+='_Before03'
    for c in list(ob.users_collection):c.objects.unlink(ob)
    archive.objects.link(ob);ob.hide_set(True);ob.hide_render=True
mats={key:bpy.data.materials['M_A762_'+key] for key in ['SightInner','Inside','FrontAssembly_Rebuilt','MagazineInside_Rebuilt']}
img=bpy.data.images['T_A762_RebuiltFinish']
(O/'Textures').mkdir(exist_ok=True)
shutil.copy2(previous/'Textures/T_A762_RebuiltFinish.png',O/'Textures/T_A762_RebuiltFinish.png')
recipes={
 'UpperReceiver03':((.021,.028,.040),.83,.34,.018),
 'Handguard03':((.013,.018,.025),0,.49,.026),
 'RearSight03':((.019,.026,.037),.79,.37,.014),
 'FactoryStock_Socket03':((.021,.028,.039),.86,.33,.018),
}
for key,(col,metal,rough,variation) in recipes.items():
    mat=bpy.data.materials.new('M_A762_'+key);mat.use_nodes=True;n=mat.node_tree.nodes;l=mat.node_tree.links;n.clear()
    bs=n.new('ShaderNodeBsdfPrincipled');out=n.new('ShaderNodeOutputMaterial');l.new(bs.outputs[0],out.inputs['Surface'])
    bs.inputs['Base Color'].default_value=(*col,1);bs.inputs['Metallic'].default_value=metal
    uv=n.new('ShaderNodeUVMap');uv.uv_map='UVMap';tx=n.new('ShaderNodeTexImage');tx.image=img;l.new(uv.outputs[0],tx.inputs[0])
    mul=n.new('ShaderNodeMath');mul.operation='MULTIPLY';mul.inputs[1].default_value=variation;l.new(tx.outputs['Color'],mul.inputs[0])
    add=n.new('ShaderNodeMath');add.operation='ADD';add.inputs[1].default_value=rough-variation/2;l.new(mul.outputs[0],add.inputs[0]);l.new(add.outputs[0],bs.inputs['Roughness'])
    mats[key]=mat;report['materials'][mat.name]={'base_color_linear':col,'metallic':metal,'roughness_center':rough,'roughness_variation':variation,'finish_texture':'Textures/T_A762_RebuiltFinish.png'}

def clip(poly,axis,value,greater=True):
    out=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da=(a[0][axis]-value)*(1 if greater else -1);db=(b[0][axis]-value)*(1 if greater else -1)
        if da>=0:out.append(a)
        if (da>=0)!=(db>=0):
            t=da/(da-db);out.append((a[0].lerp(b[0],t),a[1].lerp(b[1],t),a[2].lerp(b[2],t).normalized()))
    return out

def retained(ob,kind):
    bone=next(g.name for g in ob.vertex_groups if g.name.startswith('WPN_'))
    xf=root.inverted()@pose[bone]@rest[bone].inverted();nx=xf.to_3x3().inverted().transposed()
    vr=[xf@v.co for v in ob.data.vertices];srcuv=ob.data.uv_layers.active
    verts=[];faces=[];uvfaces=[];normals=[];mi=[];index={}
    for p in ob.data.polygons:
        poly=[(vr[ob.data.loops[li].vertex_index],srcuv.data[li].uv.copy(),(nx@ob.data.corner_normals[li].vector).normalized()) for li in p.loop_indices]
        if kind=='receiver':
            poly=clip(poly,1,-.1935);poly=clip(poly,1,.0880,False) if poly else []
            # Split exactly at the stepped casing interface, then trim height.
            low=clip(poly,1,.0330,False) if poly else []
            high=clip(poly,1,.0330) if poly else []
            pieces=[clip(low,2,.0776,False) if low else [],clip(high,2,.0380,False) if high else []]
        else:
            pieces=[clip(poly,1,.1280)]
        for poly in pieces:
            if len(poly)<3:continue
            ids=[]
            for v,uv,n in poly:
                key=tuple(round(c,8) for c in v)
                if key not in index:index[key]=len(verts);verts.append(tuple(v))
                ids.append(index[key])
            if len(set(ids))<3:continue
            faces.append(ids);uvfaces.append([q[1] for q in poly]);normals.extend(q[2] for q in poly);mi.append(p.material_index)
    me=bpy.data.meshes.new(ob.name+'_RetainedUV0');me.from_pydata(verts,[],faces);me.update()
    for mat in ob.data.materials:me.materials.append(mat)
    uv=me.uv_layers.new(name='UVMap')
    for p,uvs,slot in zip(me.polygons,uvfaces,mi):
        p.use_smooth=True;p.material_index=slot
        for li,value in zip(p.loop_indices,uvs):uv.data[li].uv=value
    me.normals_split_custom_set(normals);regions(me)
    if kind=='receiver':
        # Local planes only: retain markings, seams, other normals and UV0.
        v=np.array([tuple(p.co) for p in me.vertices]);oldgeo=[n.vector.copy() for n in me.vertex_normals]
        bm=bmesh.new();bm.from_mesh(me);bm.verts.ensure_lookup_table();pinned=np.zeros(len(v),dtype=bool)
        for e in bm.edges:
            if not e.is_manifold or e.calc_face_angle(0)>math.radians(35):
                for q in e.verts:pinned[q.index]=True
        bm.free();target=v.copy();fitted=0
        for sign in [-1,1]:
            mask=(sign*(v[:,0]-cx)>.0115)&(v[:,1]>-.164)&(v[:,1]<-.076)&(v[:,2]>.036)&(v[:,2]<.064)&(~pinned)
            mask&=np.array([sign*n.x>.93 for n in oldgeo]);ids=np.where(mask)[0]
            if len(ids)<12:continue
            q=v[ids];A=np.c_[q[:,1],q[:,2],np.ones(len(q))];coef=np.linalg.lstsq(A,q[:,0],rcond=None)[0]
            for unused in range(3):
                residual=abs(A@coef-q[:,0]);use=residual<max(.00015,float(np.median(residual))*2.5)
                coef=np.linalg.lstsq(A[use],q[use,0],rcond=None)[0]
            w=np.minimum.reduce([(q[:,1]+.164)/.008,(-.076-q[:,1])/.008,(q[:,2]-.036)/.004,(.064-q[:,2])/.004,np.ones(len(q))]).clip(0,1)
            target[ids,0]+=np.clip(A@coef-q[:,0],-.0003,.0003)*w;fitted+=len(ids)
        me.vertices.foreach_set('co',target.astype(np.float32).ravel());me.update()
        newgeo=[n.vector.copy() for n in me.vertex_normals]
        rotations=[a.rotation_difference(b) if a.length_squared and b.length_squared else None for a,b in zip(oldgeo,newgeo)]
        me.normals_split_custom_set([(rotations[loop.vertex_index]@normals[i]).normalized() if rotations[loop.vertex_index] else normals[i] for i,loop in enumerate(me.loops)])
        report['changes']['retained_side_panels']={'fitted_vertices':fitted,'max_displacement_m':.0003,'source_uv_and_structural_normal':'preserved'}
    name=ob.name;hide_old(ob);newob=bpy.data.objects.new(name,me);made.objects.link(newob);bind(newob,bone);body.append(newob)

active=[]
for name in ['A762_REFINED_GEOMETRY','A762_RECONSTRUCTED_02']:active.extend(list(bpy.data.collections[name].objects))
for ob in active:
    if ob.type!='MESH':continue
    if ob.name in ['A762_Receiver','A762_FactoryStock']:
        retained(ob,'receiver' if ob.name=='A762_Receiver' else 'stock');continue
    if ob.name in ['A762_Handguard','SM_A762_RearSight','A762_R02_Handguard_EndFerrule'] or ob.name.startswith('A762_Stock_Collar_'):
        hide_old(ob);continue
    if ob.name!='SM_A762_FrontSight':body.append(ob)

def loft(name,sections,key='UpperReceiver03',bevel=.00022):
    # All outlines have the same cyclic indexing. Close both end faces.
    v=[];f=[];n=len(sections[0][1])
    for y,outline in sections:v.extend((x,y,z) for x,z in outline)
    for j in range(len(sections)-1):f.extend((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i) for i in range(n))
    f.extend([tuple(range(n-1,-1,-1)),tuple(range((len(sections)-1)*n,len(sections)*n))])
    return primitive(name,v,f,key,bevel)

def section(hw,z0,z1,ch=.002):
    return [(cx-hw+ch,z0),(cx+hw-ch,z0),(cx+hw,z0+ch),(cx+hw,z1-ch),(cx+hw-ch,z1),(cx-hw+ch,z1),(cx-hw,z1-ch),(cx-hw,z0+ch)]

# One complete polymer fore-end. Its former top border consisted of disconnected
# triangles shared with the receiver; a new closed surface removes that split.
def dense_section(hw,hh,rad):
    base=rounded_rect(hw,hh,rad,8);out=[]
    for a,b in zip(base,base[1:]+base[:1]):
        length=math.dist(a,b);count=12 if length>.010 else 1
        for t in np.linspace(0,1,count,endpoint=False):out.append((a[0]*(1-t)+b[0]*t,a[1]*(1-t)+b[1]*t))
    return out
# Fixed topology normalized to the central rounded profile; scaled smoothly at
# the end shoulders. Recesses are geometry, not transparent or two-sided cards.
base=dense_section(.0230,.0270,.0060)
knots=np.array([[-.368,.0120,.0160,.0610],[-.360,.0140,.0200,.0585],[-.350,.0207,.0255,.0570],[-.338,.0230,.0270,.0570],[-.212,.0230,.0270,.0570],[-.198,.0220,.0260,.0565],[-.192,.0205,.0240,.0565]])
ys=np.unique(np.r_[knots[:,0],np.linspace(-.368,-.192,96)]);v=[];f=[];n=len(base)
for y in ys:
    hw,hh,zc=[float(np.interp(y,knots[:,0],knots[:,i])) for i in [1,2,3]]
    for u,w in base:
        x=u*hw/.023;z=zc+w*hh/.027
        cap_y=min(max(float(y),-.326),-.216)
        radius=math.sqrt(((y-cap_y)/.009)**2+((z-.0710)/.0068)**2)
        amount=np.clip((1-radius)/.25,0,1);amount=amount*amount*(3-2*amount)
        side=np.clip((abs(u)/.023-.92)/.08,0,1)
        x-=math.copysign(.00145*amount*side,x)
        v.append((cx+x,float(y),z))
for j in range(len(ys)-1):f.extend((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i) for i in range(n))
f.extend([tuple(range(n-1,-1,-1)),tuple(range((len(ys)-1)*n,len(ys)*n))])
primitive('A762_R03_Handguard_ClosedRecessedShell',v,f,'Handguard03',0)

# Full-width structural cover and its continuous side skirts bridge the guard
# to the rail. Ribs are solid rings over this surface, with no sky behind them.
loft('A762_R03_ForeEnd_ClosedUpperCover',[
    (-.371,section(.0105,.0770,.0900,.0018)),
    (-.365,section(.0128,.0765,.0920,.0020)),
    (-.349,section(.0160,.0757,.0920,.0030)),
    (-.330,section(.0168,.0755,.0920,.0030)),
    (-.205,section(.0168,.0755,.0920,.0030)),
    (-.189,section(.0175,.0745,.0920,.0030))])
for i,y in enumerate([-.3635,-.3545,-.3455,-.3365]):
    outer=[(cx+x,.0850+z) for x,z in rounded_rect(.0164,.0140,.0030,6)]
    inner=[(cx+x,.0850+z) for x,z in rounded_rect(.0134,.0105,.0020,6)]
    loop_prism('A762_R03_ForwardCover_Rib_%02d'%i,outer,inner,y-.0019,y+.0019,key='UpperReceiver03')
loft('A762_R03_ForeEnd_NeckFerrule',[
    (-.370,[(cx+x,.0608+z) for x,z in rounded_rect(.0123,.0170,.004,8)]),
    (-.367,[(cx+x,.0603+z) for x,z in rounded_rect(.0127,.0180,.004,8)]),
    (-.363,[(cx+x,.0590+z) for x,z in rounded_rect(.0136,.0202,.004,8)])])

# Main roof replaces the rough, incomplete strips visible beside the rail.
roof=[(cx-.0175,.0758),(cx+.0175,.0758),(cx+.0175,.0818),(cx+.0115,.0914),(cx-.0115,.0914),(cx-.0175,.0818)]
extrude('A762_R03_Receiver_ContinuousRoof',roof,-.1980,.0360,key='UpperReceiver03',bevel=.00035)
for side in [-1,1]:
    box('A762_R03_Receiver_FoldedSideBead_'+str(side),(cx+side*.0165,-.0785,.0802),(.0024,.228,.0034),'UpperReceiver03',.0006)

# Rear shoulder and stock junction are re-authored as complete hard-surface
# shells. Wide smooth planes have explicit bevels instead of scanned dents.
loft('A762_R03_Receiver_RearShoulder',[
    (.031,section(.0177,.0362,.0932,.0023)),
    (.039,section(.0182,.0340,.0962,.0023)),
    (.060,section(.0188,.0310,.0962,.0023)),
    (.080,section(.0188,.0290,.0958,.0023)),
    (.086,section(.0177,.0285,.0910,.0023)),
    (.099,section(.0121,.0290,.0830,.0021)),
    (.118,section(.0108,.0300,.0820,.0021))],bevel=.00036)
for z,rad in [(.074,.0062),(.042,.0058)]:
    tube('A762_R03_StockSocket_'+str(z),.109,.128,z,rad,'FactoryStock_Socket03')
    tube('A762_R03_StockSocket_Lip_'+str(z),.124,.128,z,rad+.00055,'FactoryStock_Socket03')
for side in [-1,1]:
    pin('A762_R03_RearShoulder_Fastener_'+str(side),(cx+side*.0187,.073,.0610),.0025,'UpperReceiver03')

# Eye-side sight from the new close reference: open protective cheeks, an
# independent narrow aperture leaf, transverse axle and round side adjusters.
# Remove the previous large square tunnel and the unrelated top blade.
rear=Vector(meta['markers_blender_root']['WPN_RearSight']);key='RearSight03';group='RearSight'
base=[(cx-.0116,.0948),(cx+.0116,.0948),(cx+.0116,.0988),(cx+.0090,.1000),(cx-.0090,.1000),(cx-.0116,.0988)]
extrude('A762_R03_RearSight_ProfiledBase',base,rear.y-.029,rear.y+.010,key=key,bevel=.00036,group=group)
# A clean sloped forward ramp matches the reference mounting shoe.
for side in [-1,1]:
    outline=[(rear.y-.027,.0980),(rear.y-.007,.0980),(rear.y-.007,.1055),(rear.y-.020,.1040)]
    extrude('A762_R03_RearSight_ForwardShoe_'+str(side),outline,cx+side*.0087-.0013,cx+side*.0087+.0013,axis=0,key=key,bevel=.00032,group=group)
    # Rounded top, sloping shoulder, open space between cheeks, no overhead bar.
    outline=[(rear.y-.007,.0985),(rear.y+.0080,.0985),(rear.y+.0080,.1146),(rear.y+.0064,.1170),(rear.y+.0023,.1175),(rear.y-.0011,.1158),(rear.y-.0043,.1060)]
    extrude('A762_R03_RearSight_ProtectiveCheek_'+str(side),outline,cx+side*.0091-.0014,cx+side*.0091+.0014,axis=0,key=key,bevel=.00048,group=group)
    # Axle knobs sit beneath the sight line and remain separate from the hole.
    pin('A762_R03_RearSight_RoundAdjuster_'+str(side),(cx+side*.0110,rear.y-.0020,.1041),.0041,key,group)
    pin('A762_R03_RearSight_AxleCap_'+str(side),(cx+side*.0088,rear.y+.0020,.1000),.0020,key,group)
# The aperture leaf is small and rounded rather than a square rear wall.
outer=[];inner=[]
for i in range(96):
    a=math.tau*i/96;dx=.0058*math.cos(a);dz=.0058*math.sin(a)
    outer.append((cx+dx,rear.z+dz))
    inner.append((cx+.0038*math.cos(a),rear.z+.0038*math.sin(a)))
loop_prism('A762_R03_RearSight_ApertureLeaf',outer,inner,rear.y-.0012,rear.y+.0012,key=key,group=group)
extrude('A762_R03_RearSight_LeafStem',[(cx-.0036,.1000),(cx+.0036,.1000),(cx+.0026,.1060),(cx-.0026,.1060)],rear.y-.0012,rear.y+.0012,key=key,bevel=.00022,group=group)
# Surface grip ribs on the forward adjustment shoe, safely below the sight line.
for i,y in enumerate(np.linspace(rear.y-.023,rear.y-.010,6)):
    box('A762_R03_RearSight_AdjustmentRib_%02d'%i,(cx,float(y),.1020),(.0120,.0010,.0016),key,.00018,group)

parts=sights['RearSight'];select(parts);active=parts[0];bpy.context.view_layer.objects.active=active;bpy.ops.object.join();active.name='SM_A762_RearSight'
h=meta['hinges_ue_root']['RearSight'];h=Vector((h[0],-h[1],h[2]));active.data.transform(Matrix.Translation(-h))
select([active]);bpy.ops.export_scene.fbx(filepath=str(D/'SM_A762_RearSight.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
active.data.transform(Matrix.Translation(h));bind(active);active['independent_folding_head']=True
for ob in new:bind(ob)
body.extend(new)
r.data.pose_position='REST';bpy.context.view_layer.update()
select(body+[hands,r]);bpy.ops.export_scene.fbx(filepath=str(D/'SK_A762_Manny.fbx'),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
r.data.pose_position='POSE';s.frame_set(0);bpy.context.view_layer.update();archive.hide_viewport=True;archive.hide_render=True
shutil.copy2(previous/'Exports/SM_A762_FrontSight.fbx',D/'SM_A762_FrontSight.fbx')
report['changes'].update({
 'rear_sight':'Reference-shaped open cheeks, profiled mounting shoe, recessed round side adjusters and narrow independent peep leaf; original sight center and hinge retained.',
 'fore_end':'Replace shared scanned handguard/receiver top border with a complete closed recessed polymer shell, continuous full-width steel upper cover and solid external ribs.',
 'ads_surfaces':'New continuous receiver roof, clean rear shoulders and stock socket lips; controlled bevels and split normals, independent UV0 PBR on reconstructed faces.',
 'preserved':'Original magazine, front sight, muzzle assembly, rail crown, mechanical bones, 11 animations and AKM audio.'})
report['editable']='A762_ADS_Surfaces_Editable.blend';report['exports']=['Exports/SK_A762_Manny.fbx','Exports/SM_A762_RearSight.fbx','Exports/SM_A762_FrontSight.fbx']
(O/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(O/'A762_ADS_Surfaces_Editable.blend'))
print('A762_REFINEMENT03_AUTHORED',flush=True)
