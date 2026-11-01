"""Coil: dimensioned cyberpunk induction grip; draft first, production second."""
import bpy, bmesh, math, json, sys
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
for folder in ('Design','Export','Textures'):(P/folder).mkdir(exist_ok=True)
DRAFT='--design' in sys.argv
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
TAU=math.tau;CX,CY=-.00045,-.00105
parts=[];rows=[]

def material(family,color,metal,rough):
    m=bpy.data.materials.new('M_Coil_'+family);m.use_nodes=True
    nodes=m.node_tree.nodes;links=m.node_tree.links;bs=nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough
    if not DRAFT:
        for kind in ('BaseColor','ORM','Normal'):
            tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(P/'Textures'/('T_Coil_'+family+'_'+kind+'.png')))
            tex.image.colorspace_settings.name='sRGB' if kind=='BaseColor' else 'Non-Color'
            if kind=='BaseColor':links.new(tex.outputs[0],bs.inputs['Base Color'])
            elif kind=='ORM':
                sep=nodes.new('ShaderNodeSeparateColor');links.new(tex.outputs[0],sep.inputs[0]);links.new(sep.outputs['Green'],bs.inputs['Roughness']);links.new(sep.outputs['Blue'],bs.inputs['Metallic'])
            else:
                n=nodes.new('ShaderNodeNormalMap');links.new(tex.outputs[0],n.inputs['Color']);links.new(n.outputs[0],bs.inputs['Normal'])
    rows.append(dict(slot=m.name,kind='pbr',family=family,tint=[1.,1.,1.],normal_strength=1.))
    return m
rubber=material('Rubber',(.004,.006,.009),.0,.64)
titanium=material('Titanium',(.065,.083,.105),.87,.33)
copper=material('Copper',(.52,.215,.085),.96,.29)
glow=bpy.data.materials.new('M_Coil_IonGlass');glow.use_nodes=True
bs=glow.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.045,.32,.42,1)
bs.inputs['Roughness'].default_value=.24;bs.inputs['Metallic'].default_value=.25
bs.inputs['Emission Color'].default_value=(.10,.8,1,1);bs.inputs['Emission Strength'].default_value=.8
rows.append(dict(slot=glow.name,kind='constant',base=[.045,.32,.42],roughness=.24,metallic=.25,emission=[.08,.64,.8]))

with bpy.data.libraries.load(str(P.parent/'StaticFieldGripV2/StaticField_Design.blend'),link=False) as (src,dst):
    dst.objects=['01_NativeUpperMatingLand','02_NativeLowerMatingLand']
for ob in dst.objects:
    bpy.context.collection.objects.link(ob);parts.append(ob)
    for i,m in enumerate(ob.data.materials):
        if m and 'NativeInterface' in m.name:m.name='M_Coil_NativeInterface'
        else:ob.data.materials[i]=titanium
rows.append(dict(slot='M_Coil_NativeInterface',kind='native'))

def point(a,z,r):return (CX+math.cos(a)*r,CY+math.sin(a)*r,z)
def mesh(name,vs,fs,mat,uv=None):
    me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.materials.append(mat);me.update()
    ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob);parts.append(ob)
    layer=me.uv_layers.new(name='UVMap')
    for f in me.polygons:
        f.use_smooth=len(f.vertices)<=4
        axes=sorted(range(3),key=lambda i:abs(f.normal[i]))[:2]
        for li in f.loop_indices:
            v=me.loops[li].vertex_index
            layer.data[li].uv=uv[v] if uv and len(f.vertices)<=4 else (vs[v][axes[0]]/.065,vs[v][axes[1]]/.065)
    return ob
def lathe(name,profile,mat,N=None):
    N=N or (64 if DRAFT else 128);vs=[];uv=[];fs=[]
    for z,r in profile:
        for j in range(N+1):
            a=TAU*j/N;vs.append(point(a,z,r));uv.append((a*.016/.065,z/.065))
    for k in range(len(profile)-1):
        for j in range(N):
            a=k*(N+1)+j;fs.append((a,a+1,a+N+2,a+N+1))
    fs.extend([tuple(reversed(range(N))),tuple((len(profile)-1)*(N+1)+j for j in range(N))])
    return mesh(name,vs,fs,mat,uv)
def tube(name,pts,r,mat,N=8):
    vs=[];uv=[];fs=[];length=0
    for i,p in enumerate(pts):
        p=Vector(p);t=(Vector(pts[min(i+1,len(pts)-1)])-Vector(pts[max(0,i-1)])).normalized()
        n=Vector((p.x-CX,p.y-CY,0)).normalized();n=(n-t*n.dot(t)).normalized();b=t.cross(n)
        if i:length+=(p-Vector(pts[i-1])).length
        for j in range(N):
            a=TAU*j/N;vs.append(tuple(p+r*(math.cos(a)*n+math.sin(a)*b)));uv.append((j/N*.006/.065,length/.065))
    for i in range(len(pts)-1):
        for j in range(N):
            a=i*N+j;b=i*N+(j+1)%N;fs.append((a,b,b+N,a+N))
    fs.extend([tuple(reversed(range(N))),tuple((len(pts)-1)*N+j for j in range(N))])
    return mesh(name,vs,fs,mat,uv)
def sector(name,z0,z1,inner,outer,angle,width,mat,bevel=.00025):
    N=8 if DRAFT else 14;vs=[];uv=[];fs=[]
    for z,r in ((z0,inner),(z0,outer),(z1,inner),(z1,outer)):
        for j in range(N+1):
            a=angle+width*(j/N-.5);vs.append(point(a,z,r));uv.append((a*.016/.065,z/.065))
    n=N+1
    for j in range(N):
        fs.extend([(j,j+1,n+j+1,n+j),(2*n+j,3*n+j,3*n+j+1,2*n+j+1),
                   (j,2*n+j,2*n+j+1,j+1),(n+j,n+j+1,3*n+j+1,3*n+j)])
    fs.extend([(0,n,3*n,2*n),(N,2*n+N,3*n+N,n+N)])
    ob=mesh(name,vs,fs,mat,uv)
    mod=ob.modifiers.new('Machined edge radii','BEVEL');mod.width=bevel;mod.segments=2 if DRAFT else 3;mod.limit_method='ANGLE';mod.angle_limit=.5
    bpy.context.view_layer.objects.active=ob;bpy.ops.object.modifier_apply(modifier=mod.name)
    return ob

# Continuous solid inner body; independent upper and lower native lands remain exact.
lathe('03_SealedInsulationCore',[(-.081,.01495),(-.079,.0151),(.398,.0151),(.401,.01528)],rubber)
lathe('04_LowerMachinedCoupler',[(-.081,.01525),(-.0798,.01555),(-.078,.016),(-.073,.016),(-.071,.01555),(-.068,.01525)],titanium)
lathe('05_LowerCopperSeat',[(-.077,.01603),(-.0767,.01619),(-.0757,.01619),(-.0754,.01603)],copper)
# Six closed, grooved sleeves keep the hand-contact envelope at the original diameter.
for i in range(6):
    start=-.066+i*.0608;end=start+.0584
    profile=[(start,.01515),(start+.001,.01545)]
    for j in range(1,10):
        z=start+.003+j*.0054
        profile.extend([(z-.00045,.01545),(z-.00018,.01520),(z+.00018,.01520),(z+.00045,.01545)])
    profile.extend([(end-.001,.01545),(end,.01515)])
    lathe('06_InsulatedGripSleeve_%02d'%i,profile,rubber,48 if DRAFT else 96)
    if i<5:
        lathe('07_SleeveJoint_%02d'%i,[(end-.0001,.01510),(end+.0005,.01540),(end+.0019,.01540),(end+.0025,.01510)],titanium)
    for a in (-math.pi/2,math.pi/2):
        sector('08_RecessedCopperBus_%d_%s'%(i,a),start+.002,end-.002,.0151,.01553,a,.08,copper,.00008)
        # Short translucent indicators are flush in their dark seats.
        sector('09_ContactIndicator_%d_%s'%(i,a),end-.009,end-.003,.01544,.01557,a+.19,.042,glow,.00005)
# Solid transitions to the induction collar; no open holes facing the shaft.
lathe('10_InductionLowerShoulder',[(.297,.01515),(.300,.0161),(.303,.0175),(.306,.01825),(.310,.01825),(.312,.0162)],titanium)
lathe('11_SealedCoilFormer',[(.307,.0161),(.309,.0164),(.387,.0164),(.390,.0161)],rubber)
lathe('12_InductionUpperShoulder',[(.387,.0162),(.389,.01825),(.394,.01825),(.396,.0176),(.398,.0161),(.400,.01543)],titanium)
for z in (.308,.391):
    lathe('13_CopperCollector_'+str(z),[(z-.001,.0170),(z-.00065,.01835),(z+.00065,.01835),(z+.001,.0170)],copper)
# Single continuous winding. Tangential leads dive into actual solid collector rings.
steps=288 if DRAFT else 672
pts=[point(TAU*16*j/steps,.314+.071*j/steps,.01692) for j in range(steps+1)]
tube('14_ContinuousCopperWinding',pts,.00083,copper,8 if DRAFT else 10)
for end,z in ((0,.314),(1,.385)):
    pts=[point(-TAU*.17*t,z+(-.006 if end==0 else .006)*t,.01692+.0009*t) for t in [j/24 for j in range(25)]]
    tube('15_SeatedCoilTerminal_'+str(end),pts,.00083,copper)
for i in range(4):
    a=i*TAU/4
    sector('16_ContinuousCoilGuard_%d'%i,.305,.395,.0170,.0190,a,.34,titanium,.0006)
    sector('17_GuardLightWell_%d'%i,.320,.381,.01896,.01902,a,.12,rubber,.00016)
    sector('18_BlueWhiteIonSlot_%d'%i,.323,.378,.01899,.01908,a,.052,glow,.00012)
    for z in (.312,.388):
        # Flush copper fastener surrounds, not protruding studs.
        sector('19_GuardClamp_%d_%s'%(i,z),z-.0015,z+.0015,.0188,.01915,a,.19,copper,.00035)

for ob in parts:
    if ob.name.startswith(('01_','02_')):continue
    bm=bmesh.new();bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-8)
    bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-10)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free()
collection=bpy.data.collections.new('Coil_EditableParts');bpy.context.scene.collection.children.link(collection)
for ob in parts:
    for c in list(ob.users_collection):c.objects.unlink(ob)
    collection.objects.link(ob)
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(P/('Coil_DesignDraft.blend' if DRAFT else 'Coil_Design.blend')))
(P/'material_manifest.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print('COIL_DESIGN_AUTHORED' if DRAFT else 'COIL_PRODUCTION_AUTHORED',len(parts),flush=True)

if DRAFT:
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
    scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.film_transparent=False
    scene.world=bpy.data.worlds.new('NeutralStudio');scene.world.use_nodes=True
    bg=scene.world.node_tree.nodes.get('Background');bg.inputs[0].default_value=(.025,.033,.045,1);bg.inputs[1].default_value=.4
    scene.view_settings.view_transform='AgX'
    def light(name,loc,power,size):
        d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size
        o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.location=loc;o.rotation_euler=(Vector((0,0,.15))-o.location).to_track_quat('-Z','Y').to_euler()
    light('Softbox',(-.32,-.44,.55),10,.45);light('Rim',(.26,.22,.36),16,.30);light('Fill',(.27,-.24,-.15),4,.30)
    data=bpy.data.cameras.new('DesignCamera');data.type='ORTHO'
    camera=bpy.data.objects.new('DesignCamera',data);scene.collection.objects.link(camera);scene.camera=camera
    shots=[('Front',(0,-1,.16),.16,.54,500,1600),('Side',(1,0,.16),.16,.54,500,1600),('Rear',(0,1,.16),.16,.54,500,1600),('CoilDetail',(.15,-.28,.39),.350,.105,1000,1000)]
    for name,pos,target,scale,w,h in shots:
        camera.location=pos;camera.rotation_euler=(Vector((CX,CY,target))-camera.location).to_track_quat('-Z','Y').to_euler();data.ortho_scale=scale
        scene.render.resolution_x=w;scene.render.resolution_y=h;scene.render.resolution_percentage=100
        scene.render.filepath=str(P/'Design'/(name+'.png'));bpy.ops.render.render(write_still=True)
    print('COIL_DESIGN_VIEWS_SAVED',flush=True)
