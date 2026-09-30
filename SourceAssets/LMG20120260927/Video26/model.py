"""Video-led 201 lid and iron-sight art. Author high and game-resolution parts.

All coordinates describe this project's game mesh in WPN_root local metres.
They are interface-preserving art proportions, not manufacturing dimensions.
"""
import bpy, bmesh, math, json, re, hashlib
from pathlib import Path
from mathutils import Vector, Matrix

O = Path(__file__).parent
(O/'Exports').mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'Surface25/LMG201_Surface25_Editable.blend'), use_scripts=False)
sc = bpy.context.scene
rig = bpy.data.objects['SK_M4_Infima']
rig.animation_data_clear(); rig.data.pose_position = 'REST'
root = rig.data.bones['WPN_root'].matrix_local.copy()
cx = .0008
remove = []
regions = {}
for ob in list(sc.objects):
    if ob.type != 'MESH': continue
    replace = (ob.name.startswith('LMG201_Refine12_') or
        ob.name.startswith(('LMG201_ReferenceRailSpine','LMG201_ReferenceRailTooth_',
        'LMG201_ReferenceRearDustCover','LMG201_ReferenceFrontSight','LMG201_ReferenceRearSight')))
    if replace:
        remove.append(ob.name)
        for poly in ob.data.polygons:
            slot = re.sub(r'\.\d+$','',ob.data.materials[poly.material_index].name)
            points = regions.setdefault(slot, set())
            for i in poly.vertices:
                p = ob.matrix_world @ ob.data.vertices[i].co
                points.add((round(p.x*100,3),round(-p.y*100,3),round(p.z*100,3)))
        bpy.data.objects.remove(ob,do_unlink=True)
    elif ob.name in ['LMG201_FrontSight','LMG201_RearSight']:
        bpy.data.objects.remove(ob,do_unlink=True)
    else: ob.hide_render=True
(O/'replace_regions.json').write_text(json.dumps({'objects':remove,'vertices_by_slot':{k:sorted(v) for k,v in regions.items()}},separators=(',',':')))
package=O.parents[2]/'Content/Weapons/LMG201/Cover10/SK_LMG201_Cover10.uasset'
(O/'source_package.json').write_text(json.dumps({'path':str(package),'sha256':hashlib.sha256(package.read_bytes()).hexdigest()},indent=2))

# Bevel faces get only intermittent wear. Broad faces keep a restrained finish.
def material(name, color, metallic, roughness, worn=False):
    m=bpy.data.materials.new('V26_'+name); m.use_nodes=True
    n=m.node_tree.nodes; l=m.node_tree.links; n.clear()
    out=n.new('ShaderNodeOutputMaterial'); bs=n.new('ShaderNodeBsdfPrincipled')
    l.new(bs.outputs['BSDF'],out.inputs['Surface'])
    bs.inputs['Base Color'].default_value=(*color,1)
    bs.inputs['Metallic'].default_value=metallic
    bs.inputs['Roughness'].default_value=roughness
    tc=n.new('ShaderNodeTexCoord'); noise=n.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value=3400;noise.inputs['Detail'].default_value=2
    l.new(tc.outputs['Position'] if 'Position' in tc.outputs else tc.outputs['Object'],noise.inputs['Vector'])
    rough=n.new('ShaderNodeMapRange');rough.inputs['From Min'].default_value=0
    rough.inputs['From Max'].default_value=1;rough.inputs['To Min'].default_value=roughness-.018
    rough.inputs['To Max'].default_value=roughness+.018
    l.new(noise.outputs['Fac'],rough.inputs['Value']);l.new(rough.outputs[0],bs.inputs['Roughness'])
    if worn:
        wear=n.new('ShaderNodeTexNoise');wear.inputs['Scale'].default_value=900
        wear.inputs['Detail'].default_value=2;l.new(tc.outputs['Object'],wear.inputs['Vector'])
        ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.43
        ramp.color_ramp.elements[0].color=(*color,1);ramp.color_ramp.elements[1].position=.8
        ramp.color_ramp.elements[1].color=(.105,.108,.109,1)
        l.new(wear.outputs['Fac'],ramp.inputs[0]);l.new(ramp.outputs[0],bs.inputs['Base Color'])
    m.diffuse_color=(*color,1);m['metallic']=metallic;m['roughness']=roughness
    return m

coat=material('CoatedSteel',(.027,.029,.031),.82,.41)
edge=material('EdgeRub',(.029,.031,.033),.88,.34,True)
dark=material('InnerDarkSteel',(.012,.014,.015),.72,.5)
pinmat=material('SatinHardware',(.063,.066,.068),.93,.3)
antiglare=material('SightRecess',(.008,.009,.010),.48,.56)
parts=[]; quality='Game'; prefix='G26_'; seg=48

def select(obs):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in obs: ob.hide_set(False);ob.select_set(True)
    bpy.context.view_layer.objects.active=obs[-1]

def mesh(name,vs,fs,mat=coat,group='Body',bone='WPN_root',radius=.0003):
    me=bpy.data.meshes.new(prefix+name);me.from_pydata(vs,[],fs);me.materials.append(mat);me.materials.append(edge);me.update()
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    ob=bpy.data.objects.new(prefix+name,me);sc.collection.objects.link(ob)
    ob['group']=group;ob['bone']=bone;ob['radius']=radius;ob['quality']=quality
    parts.append(ob);return ob

def sweep(name,rows,mat=coat,group='Body',bone='WPN_root',radius=.0003):
    n=len(rows[0][1]);vs=[(cx+x,y,z) for y,p in rows for x,z in p]
    fs=[tuple(range(n-1,-1,-1)),tuple((len(rows)-1)*n+i for i in range(n))]
    fs.extend((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i) for j in range(len(rows)-1) for i in range(n))
    return mesh(name,vs,fs,mat,group,bone,radius)

def box(name,c,size,mat=coat,group='Body',bone='WPN_root',radius=.0003):
    x,y,z=c;a,b,h=[v/2 for v in size]
    pr=[(x-cx-a,z-h),(x-cx+a,z-h),(x-cx+a,z+h),(x-cx-a,z+h)]
    return sweep(name,[(y-b,pr),(y+b,pr)],mat,group,bone,radius)

def cylinder(name,c,r,length,axis='X',mat=pinmat,group='Body',bone='WPN_root',radius=.00012,n=None):
    n=n or seg;other={'X':(1,2,0),'Y':(0,2,1),'Z':(0,1,2)}[axis];a,b,k=other
    vs=[]
    for sign in [-1,1]:
        for i in range(n):
            p=list(c);p[k]+=sign*length/2;p[a]+=r*math.cos(i*math.tau/n);p[b]+=r*math.sin(i*math.tau/n);vs.append(p)
    fs=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]
    fs.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n))
    return mesh(name,vs,fs,mat,group,bone,radius)

def loop_tube(name,center,rx,rz,thickness,depth,mat=coat,group='FrontSight',bone='WPN_root',n=None):
    n=n or seg; x,y,z=center;vs=[]
    for yy in [y-depth/2,y+depth/2]:
        for inner in [False,True]:
            for i in range(n):
                a=math.tau*i/n
                vs.append((x+(rx-thickness*inner)*math.cos(a),yy,z+(rz-thickness*inner)*math.sin(a)))
    fs=[]
    for i in range(n):
        j=(i+1)%n
        fs.extend([(i,j,n+j,n+i),(2*n+i,3*n+i,3*n+j,2*n+j),
            (i,2*n+i,2*n+j,j),(n+i,n+j,3*n+j,3*n+i)])
    return mesh(name,vs,fs,mat,group,bone,.00022)

def subtract(ob,cutter):
    select([ob]);m=ob.modifiers.new('Local blind machining','BOOLEAN');m.operation='DIFFERENCE';m.solver='EXACT';m.object=cutter
    bpy.ops.object.modifier_apply(modifier=m.name);parts.remove(cutter);bpy.data.objects.remove(cutter,do_unlink=True)

def screw(name,c,r,length,axis='X',group='Body',bone='WPN_root',slotted=True):
    ob=cylinder(name,c,r,length,axis,pinmat,group,bone,.0001)
    if slotted:
        x,y,z=c
        if axis=='X': size=(length*1.1,r*1.25,.00045);c2=(x+(-1 if x<cx else 1)*length*.42,y,z)
        elif axis=='Z':size=(r*1.2,.00045,length*1.1);c2=(x,y,z-length*.42)
        else:size=(r*1.2,length*1.1,.00045);c2=(x,y+length*.42,z)
        subtract(ob,box(name+'SlotCut',c2,size,dark,group,bone,0))
    return ob

def profile(w,bottom,top,chamfer=.002):
    return [(-w,bottom),(w,bottom),(w,top-chamfer),(w-chamfer,top),(-w+chamfer,top),(-w,top-chamfer)]

def build():
    lid='LMG201_Cover'
    # Continuous formed shell with its own inner surface and closed wall ends.
    rows=[(-.2375,.0275,.0630,.0712),(-.230,.0330,.0605,.0770),
          (-.221,.0363,.0602,.0810),(-.207,.0368,.0602,.0820),
          (-.160,.0361,.0602,.0818),(-.122,.0326,.0604,.0797),
          (-.108,.0300,.0610,.0776),(-.097,.0262,.0625,.0745)]
    vs=[]
    def section(w,b,t):return [(-w,b),(-w,t-.0033),(-w+.0045,t),(w-.0045,t),(w,t-.0033),(w,b)]
    for y,w,b,t in rows:
        vs.extend((cx+x,y,z) for x,z in section(w,b,t)+section(w-.0028,b,t-.0028))
    fs=[];inner=[]
    for j in range(len(rows)-1):
        a=j*12;b=(j+1)*12
        for k in range(5):
            fs.append((a+k,b+k,b+k+1,a+k+1));inner.append(False)
            fs.append((a+6+k,a+7+k,b+7+k,b+6+k));inner.append(True)
        fs.extend([(a,a+6,b+6,b),(a+5,b+5,b+11,a+11)]);inner.extend([False,False])
    for j in [0,len(rows)-1]:
        a=j*12
        for k in range(5):fs.append((a+k,a+k+1,a+k+7,a+k+6));inner.append(False)
    shell=mesh('FoldedLidShell',vs,fs,coat,'Body',lid,.00062)
    shell.data.materials.append(dark)
    for p,i in zip(shell.data.polygons,inner):
        if i:p.material_index=2
    # Small planar inset recess, defined as a blind cut rather than a floating plate.
    cut=box('CrownRecess',(cx,-.165,.08275),(.047,.063,.0032),radius=0)
    select([cut]);m=cut.modifiers.new('Inset corner fillet','BEVEL');m.width=.004;m.segments=4
    bpy.ops.object.modifier_apply(modifier=m.name);subtract(shell,cut)
    # Shallow shoulder pockets and stepped side reveals visible in the reference.
    for side in [-1,1]:
        for y,z,length in [(-.155,.0680,.053),(-.158,.0743,.037)]:
            x=cx+side*.0358
            c=box('SideRecess',(x,y,z),(.003,length,.0022),radius=0)
            select([c]);m=c.modifiers.new('Rounded recess ends','BEVEL');m.width=.0006;m.segments=3;bpy.ops.object.modifier_apply(modifier=m.name)
            subtract(shell,c)
        for y,z,r in [(-.205,.0675,.0032),(-.184,.0694,.0027)]:
            cylinder('LidBoss',(cx+side*.0365,y,z),r+.00065,.0012,'X',coat,'Body',lid)
            screw('LidPin',(cx+side*.0372,y,z),r,.00115,'X','Body',lid)
        # Side return follows the lower shell boundary without projecting above it.
        sweep('FoldedLowerLip',[(y,[(side*w-.0007,.061),(side*w+.0007,.061),(side*w+.0007,.0623),(side*w-.0007,.0623)])
            for y,w in [(-.223,.0356),(-.207,.0365),(-.160,.0358),(-.122,.0323),(-.106,.0293)]],coat,'Body',lid,.0002)
        cylinder('MovingHingeKnuckle',(cx+side*.025,-.232,.0698),.0051,.008,'X',coat,'Body',lid,.0003)
        screw('FixedHingeEnd',(cx+side*.0300,-.232,.0698),.0036,.0016,'X')
    cylinder('FixedHingeAxle',(cx,-.232,.0698),.0038,.06,'X',pinmat)
    # Rear press pad, broad enough to read from the normal first-person view.
    pad=box('RearPressPad',(cx,-.0995,.0718),(.0235,.0064,.0142),dark,'Body',lid,.00075)
    for i in range(8):
        box('PressPadRib_%02d'%i,(cx,-.09595,.0661+i*.00158),(.0218,.00085,.00065),coat,'Body',lid,.00022)
    box('PressPadTopLip',(cx,-.098,.0792),(.0215,.0042,.00135),edge,'Body',lid,.00035)
    # Cover inner face: stepped backplate, side channels and visible roller forms.
    # These are visual surfaces copied from frames, not functional mechanism design.
    inner_outline=[(-.024,.0635),(.024,.0635),(.024,.068),(.021,.071),(-.021,.071),(-.024,.068)]
    sweep('InnerReturnFrame',[(-.211,inner_outline),(-.119,inner_outline)],dark,'Body',lid,.00035)
    # A shallow inset leaves a continuous floor and visible broad perimeter.
    frame=parts[-1]
    subtract(frame,box('InnerFrameInset',(cx,-.165,.0618),(.039,.073,.0095),dark,'Body',lid,0))
    box('InnerBackingPlate',(cx,-.163,.0726),(.038,.078,.0022),dark,'Body',lid,.0004)
    for side in [-1,1]:
        box('InnerGuide',(cx+side*.0165,-.16,.067),(.0022,.072,.0038),coat,'Body',lid,.00045)
        for y in [-.19,-.128]:
            box('InnerGuideEnd',(cx+side*.0158,y,.0653),(.0067,.0042,.003),coat,'Body',lid,.00035)
    box('UpperPressureBlock',(cx+.0068,-.125,.0646),(.020,.025,.010),coat,'Body',lid,.001)
    for y in [-.137,-.114]:
        cylinder('PressureCrossPin',(cx,y,.0605),.002,.040,'X',pinmat,'Body',lid,.00016)
    cylinder('InnerLongRoller',(cx-.0022,-.163,.0645),.0046,.026,'Y',pinmat,'Body',lid,.00035)
    for y in [-.1785,-.1468]:
        cylinder('RollerCollar',(cx-.0022,y,.0645),.0053,.0024,'Y',coat,'Body',lid,.00016)
    for x,y in [(cx-.013,-.121),(cx+.017,-.151),(cx-.013,-.197)]:
        screw('InnerFastener',(x,y,.0621),.00265,.002,'Z','Body',lid,False)
    # Slender latch shapes on the inside echo the visible bent shoulders.
    box('InnerSideLever',(cx+.020,-.155,.062),(.0058,.025,.0046),coat,'Body',lid,.0007)
    cylinder('InnerLeverPivot',(cx+.020,-.15,.0588),.0035,.0016,'Z',pinmat,'Body',lid,.00015)
    for x in [-.010,.010]:box('HingeInnerTab',(cx+x,-.218,.0625),(.003,.013,.005),coat,'Body',lid,.0005)

    # Fixed rear dust cover and rail preserve the current optical mounting crown.
    sweep('RearDustCover',[(y,profile(w,.0629,t,.0022)) for y,w,t in
        [(-.096,.0255,.0716),(-.084,.0216,.0716),(-.065,.0205,.0716),(.056,.020,.0716),(.074,.0185,.0702)]],coat,radius=.00065)
    rail=[(-.010,.0714),(.010,.0714),(.010,.074),(.013,.076),(.013,.078),(-.013,.078),(-.013,.076),(-.010,.074)]
    sweep('FixedRailSpine',[(-.082,rail),(.028,rail)],dark,radius=.00025)
    for i in range(13):
        y=-.078+i*.0081
        pr=[(-.011,.0772),(.011,.0772),(.012,.080),(.0107,.082),(-.0107,.082),(-.012,.080)]
        sweep('RailCrossbar_%02d'%i,[(y-.0025,pr),(y+.0025,pr)],coat,radius=.00025)
    # Fixed saddles are part of the gun; sight leaves retain their original pivots.
    for tag,y,z,width in [('Front',-.54212,.0648,.018),('Rear',.04252,.0855,.023)]:
        bottom=.0714 if tag=='Rear' else z-.0045
        box(tag+'FixedSaddle',(cx,y,(bottom+z+.0025)/2),(width,.021,z+.0025-bottom),coat,radius=.00065)
        for side in [-1,1]:
            box(tag+'HingeCheek',(cx+side*(width/2-.0018),y,z+.0007),(.0036,.010,.008),coat,radius=.0008)
        cylinder(tag+'FixedHingePin',(cx,y,z),.0022,width+.0012,'X',pinmat)

    # Front: narrow lower window and a real thin oval guard around the fine post.
    fy=-.54212; fh=.0648; fz=.11362
    for side in [-1,1]:
        sweep('FrontStemSide',[(fy-.0032,[(side*.0048-.00125,fh+.001),(side*.0048+.00125,fh+.001),
            (side*.0038+.0011,fz-.008),(side*.0038-.0011,fz-.008)]),
            (fy+.0032,[(side*.0048-.00125,fh+.001),(side*.0048+.00125,fh+.001),
            (side*.0038+.0011,fz-.008),(side*.0038-.0011,fz-.008)])],coat,'FrontSight',radius=.0004)
    box('FrontStemBridge',(cx,fy,fh+.005),(.011,.007,.008),coat,'FrontSight',radius=.0005)
    box('FrontWindowShelf',(cx,fy,fz-.012),(.0094,.0068,.0034),coat,'FrontSight',radius=.0004)
    loop_tube('FrontOvalGuard',(cx,fy,fz+.0020),.0090,.0100,.00155,.0036,coat,'FrontSight')
    post=[(-.0011,fz-.0075),(.0011,fz-.0075),(.00048,fz),(-.00048,fz)]
    sweep('FrontFinePost',[(fy-.0015,post),(fy+.0015,post)],antiglare,'FrontSight',radius=.0001)
    cylinder('FrontPostSocket',(cx,fy,fz-.0072),.0024,.0032,'Z',coat,'FrontSight',radius=.00018)
    for i in range(3):box('FrontStemBand',(cx,fy+.0037,fh+.013+i*.0018),(.007,.00065,.0005),edge,'FrontSight',radius=.0001)
    for side in [-1,1]:screw('FrontHingeEnd',(cx+side*.0064,fy,fh+.003),.0025,.0013,'X','FrontSight',slotted=False)

    # Rear: square U notch, protective wings, transverse adjuster and folding foot.
    ry=.04252;rh=.0855;rz=.11362
    box('RearFoldingFoot',(cx,ry,rh+.004),(.015,.014,.009),coat,'RearSight',radius=.0007)
    cylinder('RearWindageDrum',(cx,ry,rz-.0083),.0037,.020,'X',dark,'RearSight',radius=.0003)
    # Concave polygon explicitly traces the notch; no full-width cap can block ADS.
    pr=[(-.0078,rz-.010),(.0078,rz-.010),(.0078,rz+.0048),(.0058,rz+.0058),
        (.0046,rz+.0050),(.0033,rz+.001),(.0011,rz+.001),(.0011,rz),
        (-.0011,rz),(-.0011,rz+.001),(-.0033,rz+.001),(-.0046,rz+.0050),(-.0058,rz+.0058),(-.0078,rz+.0048)]
    sweep('RearNotchLeaf',[(ry-.0032,pr),(ry+.0032,pr)],antiglare,'RearSight',radius=.00022)
    for side in [-1,1]:
        x=side*.0104
        pr=[(x-.0017,rh+.004),(x+.0017,rh+.004),(x+.0017,rz+.006),(x+.0007,rz+.008),
            (x-.0007,rz+.008),(x-.0017,rz+.006)]
        sweep('RearProtectiveWing',[(ry-.0063,pr),(ry+.0038,pr)],coat,'RearSight',radius=.0007)
        screw('RearAdjusterCap',(cx+side*.0094,ry,rz-.0057),.0038,.003,'X','RearSight',slotted=True)
        for i in range(12):
            a=math.tau*i/12
            cylinder('RearKnurl',(cx+side*.0102,ry+.0038*math.cos(a),rz-.0057+.0038*math.sin(a)),.00032,.0015,'X',coat,'RearSight',radius=.00006,n=8)
    box('RearLowerCrossbar',(cx,ry+.004,rh+.009),(.019,.004,.0038),coat,'RearSight',radius=.00065)
    # Fine centered witness stripe on the rear-facing notch wall, not luminous paint.
    box('RearNotchWitness',(cx,ry+.00327,rz-.0013),(.00035,.00018,.0018),pinmat,'RearSight',radius=.00005)


def finish(ob):
    select([ob]);me=ob.data
    bm=bmesh.new();bm.from_mesh(me)
    bmesh.ops.dissolve_degenerate(bm,dist=1e-8,edges=list(bm.edges))
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    for f in bm.faces:f.smooth=True
    for e in bm.edges:e.smooth=not(e.is_manifold and e.calc_face_angle(0)>math.radians(35))
    bm.to_mesh(me);bm.free();me.update()
    radius=ob['radius']
    if radius:
        bevel=ob.modifiers.new('High fillet' if quality=='High' else 'Game fillet','BEVEL')
        bevel.width=radius;bevel.segments=8 if quality=='High' else 3
        bevel.limit_method='ANGLE';bevel.angle_limit=math.radians(32);bevel.use_clamp_overlap=True
        bevel.harden_normals=True;bevel.material=1
        bpy.ops.object.modifier_apply(modifier=bevel.name)
    weighted=ob.modifiers.new('Manufactured plane normals','WEIGHTED_NORMAL')
    weighted.keep_sharp=True;weighted.weight=45;bpy.ops.object.modifier_apply(modifier=weighted.name)
    ob.vertex_groups.new(name=ob['bone']).add(list(range(len(me.vertices))),1,'REPLACE')


objects={};report={'revision':'Video26','removed_objects':remove,'groups':{}}
for quality,prefix,seg in [('Game','G26_',48),('High','H26_',112)]:
    parts=[];build();new=parts[:]
    for ob in new:finish(ob)
    grouped={group:[ob for ob in new if ob['group']==group] for group in ['Body','FrontSight','RearSight']}
    for group in ['Body','FrontSight','RearSight']:
        selected=grouped[group]
        select(selected);bpy.ops.object.join();ob=bpy.context.object;ob.name=prefix+group
        ob['group']=group;ob['quality']=quality
        # Triangulate after final normals; keep custom normals and stable diagonals.
        tri=ob.modifiers.new('Stable triangles','TRIANGULATE');tri.keep_custom_normals=True
        bpy.ops.object.modifier_apply(modifier=tri.name)
        objects[quality+'_'+group]=ob
        report['groups'][quality+'_'+group]={'vertices':len(ob.data.vertices),'triangles':len(ob.data.polygons)}
        if quality=='Game':
            select([ob]);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.uv.smart_project(angle_limit=math.radians(68),island_margin=.004,area_weight=.5,correct_aspect=True,scale_to_bounds=True)
            bpy.ops.object.mode_set(mode='OBJECT')
            ob.data.uv_layers.active.name='Video26UV'
for key,ob in objects.items():ob.hide_render=key.startswith('High');ob.hide_set(key.startswith('High'))
rig['AuthoringScope']='Video26 lid, fixed rail and iron sights with Surface25 body. Geometry only; use current native UE arms and Magazine24 animations.'
bpy.ops.wm.save_as_mainfile(filepath=str(O/'LMG201_Video26_HighLow.blend'))
(O/'model_authoring.json').write_text(json.dumps(report,indent=2))
print('VIDEO26_HIGH_LOW_AUTHORED',json.dumps(report['groups']),flush=True)
