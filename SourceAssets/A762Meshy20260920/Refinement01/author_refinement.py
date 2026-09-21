"""A762 exterior refinement. No camera render or gameplay acceptance run."""
import bpy,bmesh,json,math,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;D=O/'Exports';D.mkdir(exist_ok=True)
I=O.parent/'Integration';meta=json.loads((I/'authoring.json').read_text(encoding='utf-8'))
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(I/'A762_Rigged_Editable.blend'))
s=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima'];hands=bpy.data.objects['SK_Manny_Arms_Export']
r.animation_data.action=bpy.data.actions['A_A762_idle'];r.animation_data.action_slot=r.animation_data.action.slots[0];s.frame_set(0);bpy.context.view_layer.update()
root=r.pose.bones['WPN_root'].matrix.copy();rest={b.name:b.matrix_local.copy() for b in r.data.bones};pose={b.name:b.matrix.copy() for b in r.pose.bones}
cx=.00056;new=[];sights={'RearSight':[],'FrontSight':[]};report={'changes':{},'new_parts':{},'materials':{},'sight_markers':meta['markers_blender_root'],'hinges':meta['hinges_ue_root'],'tests_run':False}
ref=bpy.data.collections.new('A762_BEFORE_REFINEMENT');s.collection.children.link(ref)
made=bpy.data.collections.new('A762_REFINED_GEOMETRY');s.collection.children.link(made)

def select(obs):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in obs:ob.hide_set(False);ob.select_set(True)
    bpy.context.view_layer.objects.active=obs[-1]

settings={
 'Receiver':((.021,.028,.040),.83,.32,.16,True),
 'Magazine':((.022,.030,.042),.88,.30,.18,True),
 'Handguard':((.013,.018,.025),0,.49,.10,True),
 'FactoryRearGrip':((.012,.017,.023),0,.53,.10,True),
 'FactoryStock':((.021,.028,.039),.86,.32,.12,True),
 'Bolt':((.038,.044,.052),.94,.26,.20,True),
 'Trigger':((.020,.025,.031),.90,.29,.10,True),
 'Buttpad':((.007,.010,.014),0,.72,.05,True),
 'MachinedSteel':((.021,.028,.040),.83,.32,0,False),
 'Rail':((.021,.028,.040),.83,.32,0,False),
 'Flash_Hider':((.021,.028,.039),.88,.30,0,False),
 'RearSight':((.019,.026,.037),.79,.37,0,False),
 'FrontSight':((.019,.026,.037),.79,.37,0,False),
 'SightInner':((.004,.006,.009),.08,.79,0,False),
 'Inside':((.006,.008,.012),.25,.68,0,False)}
textures={c:bpy.data.images.load(str(O.parent/f'Meshy/candidate01/downloads/texture_urls_0_{c}.png'),check_existing=True) for c in ['base_color','roughness','normal']}
for c,img in textures.items():
    if c!='base_color':img.colorspace_settings.name='Non-Color'
mats={}
for key,(col,metal,rough,mix,use_source) in settings.items():
    name='M_A762_'+key
    old=bpy.data.materials.get(name)
    if old:old.name=name+'_Before'
    mat=bpy.data.materials.new(name);mat.use_nodes=True;n=mat.node_tree.nodes;l=mat.node_tree.links;n.clear()
    bs=n.new('ShaderNodeBsdfPrincipled');out=n.new('ShaderNodeOutputMaterial');l.new(bs.outputs[0],out.inputs['Surface'])
    bs.inputs['Base Color'].default_value=(*col,1);bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough
    uv=n.new('ShaderNodeUVMap');uv.uv_map='UVMap'
    if use_source:
        tx=n.new('ShaderNodeTexImage');tx.image=textures['base_color'];l.new(uv.outputs[0],tx.inputs[0])
        m=n.new('ShaderNodeMixRGB');m.blend_type='MIX';m.inputs[0].default_value=mix;m.inputs[1].default_value=(*col,1);l.new(tx.outputs[0],m.inputs[2]);l.new(m.outputs[0],bs.inputs['Base Color'])
        # Preserve complete structural normal data in its existing UV0 tangent frame.
        tx=n.new('ShaderNodeTexImage');tx.image=textures['normal'];l.new(uv.outputs[0],tx.inputs[0]);nm=n.new('ShaderNodeNormalMap');nm.uv_map='UVMap';nm.inputs['Strength'].default_value=1;l.new(tx.outputs[0],nm.inputs['Color']);l.new(nm.outputs[0],bs.inputs['Normal'])
        tx=n.new('ShaderNodeTexImage');tx.image=textures['roughness'];l.new(uv.outputs[0],tx.inputs[0]);mul=n.new('ShaderNodeMath');mul.operation='MULTIPLY';mul.inputs[1].default_value=.12;l.new(tx.outputs[0],mul.inputs[0]);add=n.new('ShaderNodeMath');add.operation='ADD';add.inputs[1].default_value=rough-.06;l.new(mul.outputs[0],add.inputs[0]);l.new(add.outputs[0],bs.inputs['Roughness'])
    if key=='Flash_Hider':
        regions=n.new('ShaderNodeVertexColor');regions.layer_name='SurfaceRegions';sep=n.new('ShaderNodeSeparateColor');l.new(regions.outputs['Color'],sep.inputs['Color'])
        mixinner=n.new('ShaderNodeMixRGB');mixinner.inputs[1].default_value=(*col,1);mixinner.inputs[2].default_value=(.004,.006,.009,1);l.new(sep.outputs['Red'],mixinner.inputs[0]);l.new(mixinner.outputs[0],bs.inputs['Base Color'])
        rr=n.new('ShaderNodeMapRange');rr.inputs['From Min'].default_value=0;rr.inputs['From Max'].default_value=1;rr.inputs['To Min'].default_value=rough;rr.inputs['To Max'].default_value=.79;l.new(sep.outputs['Red'],rr.inputs['Value']);l.new(rr.outputs['Result'],bs.inputs['Roughness'])
    mats[key]=mat
    report['materials'][name]={'base_color_linear':col,'metallic':metal,'roughness_center':rough,'source_color_mix':mix,'source_uv0_normal':use_source,'normal_strength':1,'roughness_variation':.12 if use_source else 0}

def assign_regions(me,indices=None):
    layer=me.color_attributes.get('SurfaceRegions') or me.color_attributes.new(name='SurfaceRegions',type='FLOAT_COLOR',domain='CORNER')
    me.color_attributes.active_color=layer
    for p in me.polygons:
        value=1.0 if indices and p.index in indices else 0.0
        for li in p.loop_indices:layer.data[li].color=(value,0,0,1)

def bind(ob,bone='WPN_root'):
    # Author in the fitted idle root frame, then return to the original rest frame.
    xf=rest[bone]@pose[bone].inverted()@root
    ns=[(xf.to_3x3().inverted().transposed()@n.vector).normalized() for n in ob.data.corner_normals]
    ob.data.transform(xf);ob.data.normals_split_custom_set(ns)
    ob.parent=r;ob.matrix_parent_inverse=Matrix.Identity(4);ob.matrix_basis=Matrix.Identity(4)
    ob.vertex_groups.clear();ob.vertex_groups.new(name=bone).add(list(range(len(ob.data.vertices))),1,'REPLACE')
    ob.modifiers.new('A762 original mechanical binding','ARMATURE').object=r

def primitive(name,vertices,faces,key='MachinedSteel',bevel=.00015,inner=None,group=None):
    me=bpy.data.meshes.new(name);me.from_pydata(vertices,[],faces);me.update();me.materials.append(mats[key])
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    for f in bm.faces:f.smooth=True
    for e in bm.edges:e.smooth=not(e.is_manifold and e.calc_face_angle(0)>math.radians(38))
    bm.to_mesh(me);bm.free()
    if inner and key!='Flash_Hider':
        me.materials.append(mats['SightInner'])
        for i in inner:me.polygons[i].material_index=1
    uv=me.uv_layers.new(name='UVMap')
    for p in me.polygons:
        axis=max(range(3),key=lambda a:abs(p.normal[a]));a,b=[k for k in range(3) if k!=axis]
        for li in p.loop_indices:
            v=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(v[a]*50,v[b]*50)
    assign_regions(me,inner if key=='Flash_Hider' else None)
    ob=bpy.data.objects.new(name,me);made.objects.link(ob);select([ob])
    if bevel:
        mod=ob.modifiers.new('Small controlled edge radius','BEVEL');mod.width=bevel;mod.segments=3;mod.limit_method='ANGLE';mod.angle_limit=math.radians(38);mod.use_clamp_overlap=True;mod.harden_normals=True;bpy.ops.object.modifier_apply(modifier=mod.name)
    mod=ob.modifiers.new('Weighted planes with split hard edges','WEIGHTED_NORMAL');mod.keep_sharp=True;mod.weight=50;bpy.ops.object.modifier_apply(modifier=mod.name)
    report['new_parts'][name]={'faces':len(ob.data.polygons),'material':key,'sight':group,'bevel_m':bevel}
    if group:sights[group].append(ob)
    else:new.append(ob)
    return ob

def prism(name,outline,y0,y1,key='MachinedSteel',bevel=.00015,group=None):
    n=len(outline);v=[(x,y,z) for y in [y0,y1] for x,z in outline]
    f=[tuple(range(n-1,-1,-1)),tuple(range(n,n*2))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return primitive(name,v,f,key,bevel,group=group)

def box(name,center,size,key='MachinedSteel',bevel=.00015,group=None):
    x,y,z=center;dx,dy,dz=[n/2 for n in size]
    return prism(name,[(x-dx,z-dz),(x+dx,z-dz),(x+dx,z+dz),(x-dx,z+dz)],y-dy,y+dy,key,bevel,group)

def lathe(name,center,sections,key='MachinedSteel',inner_start=999,n=96,group=None,axis=1):
    # Closed radial section. Annuli retain their hole; no center fan is generated.
    v=[];f=[];mi=[]
    for radius,t in sections:
        for i in range(n):
            a=math.tau*i/n;p=[0,0,0];other=[k for k in range(3) if k!=axis];p[axis]=t;p[other[0]]=radius*math.cos(a);p[other[1]]=radius*math.sin(a);v.append(tuple(center[k]+p[k] for k in range(3)))
    for j in range(len(sections)):
        for i in range(n):
            f.append((j*n+i,j*n+(i+1)%n,((j+1)%len(sections))*n+(i+1)%n,((j+1)%len(sections))*n+i))
            if j>=inner_start:mi.append(len(f)-1)
    return primitive(name,v,f,key,0,mi,group)

def tube(name,y0,y1,z,radius,key='MachinedSteel',group=None,axis=1,x=cx):
    d=.00022
    return lathe(name,(x,0,z),[(radius-d,y0),(radius,y0+d),(radius,y1-d),(radius-d,y1),(max(.0002,radius-.0014),y1),(max(.0002,radius-.0014),y0)],key,4,64,group,axis)

# Existing broad shapes keep original UVs and split normals. Local regularisation
# is bounded in metres, feature and open-boundary vertices remain stationary.
for old in list(s.objects):
    if old.type!='MESH' or 'A762' not in old.name:continue
    name=old.name;key=name.replace('SM_A762_','').replace('A762_','');bone=next(g.name for g in old.vertex_groups if g.name.startswith('WPN_'))
    old.name=name+'_Before'
    for c in list(old.users_collection):c.objects.unlink(old)
    ref.objects.link(old);old.hide_set(True);old.hide_render=True
    if key in ['RearSight','FrontSight','Flash_Hider']:
        report['changes'][key]={'operation':'reconstructed exterior geometry'};continue
    xf=root.inverted()@pose[bone]@rest[bone].inverted();normalxf=xf.to_3x3().inverted().transposed()
    v=np.array([tuple(xf@p.co) for p in old.data.vertices],dtype=np.float64)
    ids=[]
    for p in old.data.polygons:
        c=v[list(p.vertices)].mean(0);x,y,z=c
        cut=(key=='Receiver' and ((-.327<y<.034 and z>.0902) or (-.465<y<-.374 and z>.0415))) or (key=='FactoryStock' and .116<y<.284 and z>.027)
        if not cut:ids.append(p.index)
    sourceverts=sorted({vi for fi in ids for vi in old.data.polygons[fi].vertices});index={vi:i for i,vi in enumerate(sourceverts)}
    me=bpy.data.meshes.new(name+'_Refined');me.from_pydata(v[sourceverts].tolist(),[],[[index[vi] for vi in old.data.polygons[fi].vertices] for fi in ids]);me.update()
    me.materials.append(mats[key]);me.materials.append(mats['Inside'])
    if key=='FactoryStock':me.materials.append(mats['Buttpad'])
    uv=me.uv_layers.new(name='UVMap');srcuv=old.data.uv_layers.active;ns=[]
    for p,fi in zip(me.polygons,ids):
        src=old.data.polygons[fi];p.use_smooth=True;p.material_index=1 if src.material_index==1 else 0
        if key=='FactoryStock' and v[list(src.vertices),1].mean()>.316:p.material_index=2
        for li,sl in zip(p.loop_indices,src.loop_indices):uv.data[li].uv=srcuv.data[sl].uv;ns.append((normalxf@old.data.corner_normals[sl].vector).normalized())
    me.normals_split_custom_set(ns);assign_regions(me)
    ob=bpy.data.objects.new(name,me);made.objects.link(ob)
    before=np.array([tuple(p.co) for p in me.vertices]);newpos=before.copy();oldgeo=[n.vector.copy() for n in me.vertex_normals]
    bm=bmesh.new();bm.from_mesh(me);bm.verts.ensure_lookup_table()
    pinned=np.zeros(len(before),dtype=bool)
    for e in bm.edges:
        if not e.is_manifold or e.calc_face_angle(0)>math.radians(38):
            for p in e.verts:pinned[p.index]=True
    bm.free()
    ed=np.array([tuple(e.vertices) for e in me.edges],dtype=int);counts=np.bincount(ed.ravel(),minlength=len(before));counts=np.maximum(counts,1)
    limit=.00016 if key in ['Receiver','Magazine'] else .00020
    for iteration in range(4):
        acc=np.zeros_like(newpos);np.add.at(acc,ed[:,0],newpos[ed[:,1]]);np.add.at(acc,ed[:,1],newpos[ed[:,0]])
        delta=(acc/counts[:,None]-newpos)*.22;delta[pinned]=0;candidate=newpos+delta;disp=candidate-before
        length=np.linalg.norm(disp,axis=1);disp*=np.minimum(1,limit/np.maximum(length,1e-12))[:,None];newpos=before+disp
    # Large right receiver side: flatten only near-planar patch interiors.
    flattened=0
    if key=='Receiver':
        mask=(before[:,0]>.012)&(before[:,1]>-.167)&(before[:,1]<-.062)&(before[:,2]>.036)&(before[:,2]<.062)&(~pinned)
        chosen=np.where(mask & (np.array([n.x for n in oldgeo])>.96))[0]
        if len(chosen)>50:
            q=before[chosen];coef=np.linalg.lstsq(np.c_[q[:,1],q[:,2],np.ones(len(q))],q[:,0],rcond=None)[0]
            target=np.c_[q[:,1],q[:,2],np.ones(len(q))]@coef
            w=np.minimum.reduce([(q[:,1]+.167)/.008,(-.062-q[:,1])/.008,(q[:,2]-.036)/.005,(.062-q[:,2])/.005,np.ones(len(q))]).clip(0,1)
            newpos[chosen,0]+=np.clip(target-newpos[chosen,0],-.00035,.00035)*w;flattened=len(chosen)
    me.vertices.foreach_set('co',newpos.astype(np.float32).ravel());me.update()
    newgeo=[n.vector.copy() for n in me.vertex_normals];rot=[a.rotation_difference(b) if a.length_squared>0 and b.length_squared>0 else None for a,b in zip(oldgeo,newgeo)]
    me.normals_split_custom_set([(rot[loop.vertex_index]@ns[i]).normalized() if rot[loop.vertex_index] else ns[i] for i,loop in enumerate(me.loops)])
    report['changes'][key]={'source_faces':len(old.data.polygons),'retained_faces':len(me.polygons),'local_regularisation_limit_m':limit,'planar_patch_vertices':flattened,'preserved_uv0':True,'preserved_split_normal_differences':True}
    bind(ob,bone);new.append(ob)

# Continuous exterior barrel/gas-tube silhouettes and collars.
tube('A762_Barrel_Exterior',-.471,-.369,.0544,.0074)
tube('A762_GasTube_Exterior',-.470,-.368,.0804,.0065)
for y in [-.465,-.376]:
    tube('A762_Barrel_Collar_'+str(y),y-.0028,y+.0028,.0544,.0086)
    tube('A762_GasTube_Collar_'+str(y),y-.0022,y+.0022,.0804,.0075)

# Uniform rail teeth; the installation crown stays on the existing .0995 plane.
outline=[(cx-.0090,.0895),(cx+.0090,.0895),(cx+.0090,.0936),(cx+.0109,.0956),(cx-.0109,.0956),(cx-.0090,.0936)]
prism('A762_Rail_ContinuousSeat',outline,-.329,.035,'Rail',.00018)
crown=[(cx-.0109,.0952),(cx+.0109,.0952),(cx+.0109,.0979),(cx+.0091,.0995),(cx-.0091,.0995),(cx-.0109,.0979)]
for i,y in enumerate(np.arange(-.326,.034,.0096)):
    prism('A762_Rail_Tooth_%02d'%i,crown,float(y),float(min(y+.0058,.035)),'Rail',.00013)

# Twin stock tubes retain their original endpoints and open space between rods.
tube('A762_Stock_UpperTube',.113,.286,.0740,.0046)
tube('A762_Stock_LowerTube',.113,.286,.0420,.0042)
for z,rr in [(.074,.0057),(.042,.0053)]:
    tube('A762_Stock_Collar_'+str(z),.112,.122,z,rr)

# Open visual muzzle bore, chamfered lip and annular shoulders. No filled disk.
lathe('A762_Flash_Hider_Precision',(cx,0,.0544),[(.0108,-.5115),(.0134,-.513),(.0134,-.572),(.0144,-.574),(.0144,-.5818),(.0133,-.5855),(.0129,-.58648),(.0051,-.58648),(.0046,-.5858),(.0046,-.513),(.0060,-.5115)],'Flash_Hider',7,128)

# Both heads are authored around existing markers and exported about original hinges.
rear=Vector(meta['markers_blender_root']['WPN_RearSight']);front=Vector(meta['markers_blender_root']['WPN_FrontSight'])
def aperture(name,c,rin,rout,depth,key,group):
    d=.00018
    return lathe(name,tuple(c),[(rin+d,depth/2),(rout-d,depth/2),(rout,depth/2-d),(rout,-depth/2+d),(rout-d,-depth/2),(rin+d,-depth/2),(rin,-depth/2+d),(rin,depth/2-d)],key,5,128,group)

aperture('A762_Rear_TrueAperture',rear,.0048,.0076,.0040,'RearSight','RearSight')
box('A762_Rear_Mount',(cx,rear.y-.008,.0980),(.025,.052,.0044),'RearSight',.00025,'RearSight')
prism('A762_Rear_Pedestal',[(cx-.0055,.0985),(cx+.0055,.0985),(cx+.0031,.1055),(cx-.0031,.1055)],rear.y-.0022,rear.y+.0022,'RearSight',.00016,'RearSight')
for side in [-1,1]:
    prism('A762_Rear_Ear_'+str(side),[(cx+side*.0075,.099),(cx+side*.0108,.102),(cx+side*.0108,.1128),(cx+side*.0093,.1163),(cx+side*.0081,.1163),(cx+side*.0081,.106)],rear.y-.0018,rear.y+.0018,'RearSight',.00018,'RearSight')
aperture('A762_Front_OpenGuard',front+Vector((0,0,.0005)),.0078,.0094,.0038,'FrontSight','FrontSight')
box('A762_Front_HingeBase',(cx,-.481,.0749),(.022,.034,.0052),'FrontSight',.00025,'FrontSight')
prism('A762_Front_Tower',[(cx-.0059,.0745),(cx+.0059,.0745),(cx+.0044,.092),(cx+.0030,.1018),(cx-.0030,.1018),(cx-.0044,.092)],front.y-.0028,front.y+.0028,'FrontSight',.00022,'FrontSight')
prism('A762_Front_FlatPost',[(cx-.00125,.0998),(cx+.00125,.0998),(cx+.0005,front.z),(cx-.0005,front.z)],front.y-.0008,front.y+.0008,'SightInner',.000055,'FrontSight')
for group,center in [('RearSight',(cx,rear.y,.1001)),('FrontSight',(cx,-.49144,.0774))]:
    # Small recessed circular fasteners on both sides, outside the sight opening.
    for side in [-1,1]:
        c=(cx+side*.011,center[1],center[2]);sections=[(.0021,-.0007),(.0026,-.0004),(.0026,.0005),(.0022,.0007),(.0009,.0007),(.0009,-.0007)]
        lathe('A762_'+group+'_Pin_'+str(side),c,sections,group,4,64,group,axis=0)

# Export the sights in their original hinge-local axes, then restore source rigging.
for key,parts in sights.items():
    select(parts);active=parts[0];bpy.context.view_layer.objects.active=active;bpy.ops.object.join();active.name='SM_A762_'+key
    hinge=meta['hinges_ue_root'][key];h=Vector((hinge[0],-hinge[1],hinge[2]));active.data.transform(Matrix.Translation(-h))
    select([active]);bpy.ops.export_scene.fbx(filepath=str(D/(active.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
    active.data.transform(Matrix.Translation(h));bind(active);active['independent_folding_head']=True

# Bind new rigid exterior details, preserving all old mechanical/rest contracts.
for ob in new:
    if not ob.parent:bind(ob)
r.data.pose_position='REST';bpy.context.view_layer.update()
select(new+[hands,r]);bpy.ops.export_scene.fbx(filepath=str(D/'SK_A762_Manny.fbx'),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
r.data.pose_position='POSE';s.frame_set(0);bpy.context.view_layer.update()
ref.hide_viewport=True;ref.hide_render=True
report['sight_geometry']={'rear_open_aperture_diameter_m':.0096,'front_guard_open_diameter_m':.0156,'front_tip_width_m':.001,'rear_marker_preserved':list(rear),'front_marker_preserved':list(front),'rail_crown_m':.0995,'sight_hinges_preserved':True}
report['editable']='A762_Refined_Editable.blend';report['exports']=[str(p.relative_to(O)) for p in D.glob('*.fbx')]
(O/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(O/'A762_Refined_Editable.blend'))
print('A762_REFINEMENT_AUTHORED',flush=True)
