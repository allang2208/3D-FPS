"""Four crafted crown revisions; background modelling/export only, no renders."""
import bpy, bmesh, json, math
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'Export'; TEX=OUT/'Textures'; TEX.mkdir(parents=True,exist_ok=True)
KEYS=['spike_crown','current_crown','wreath_crown','heat_crown']
SOURCE=ROOT.parent/'BarkRebuildV21/Staff_NaturalBark_V21.blend'
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
names=['SM_Staff_crown_'+k for k in KEYS]
names+=['SM_Staff_head_crystal_'+k for k in ['false','frozen_crystal','jade_spirit_crystal','magma_core','storm_core']]
with bpy.data.libraries.load(str(SOURCE),link=False) as (src,dst): dst.objects=names
originals={o.name:o for o in dst.objects}
reference=bpy.data.collections.new('Original_Interfaces'); bpy.context.scene.collection.children.link(reference)
for o in originals.values():
    reference.objects.link(o); o.name += '_Reference'; o.hide_render=True; o.hide_set(True)
trees=[BVHTree.FromPolygons([v.co for v in o.data.vertices],[list(p.vertices) for p in o.data.polygons])
       for n,o in originals.items() if 'head_crystal' in n]
def radial(a): return Vector((math.cos(a),math.sin(a),0))
def tangent(a): return Vector((-math.sin(a),math.cos(a),0))
def ray(tree,a,z):
    d=radial(a); p,_,_,_=tree.ray_cast(d*25+Vector((0,0,z)),-d,30)
    return p
def envelope(a,z,offset=.39):
    d=radial(a); points=[ray(t,a,z) for t in trees]
    rr=max([p.dot(d) for p in points if p is not None]+[2.6])
    return d*(rr+offset)+Vector((0,0,z))

# Shared original tileable microstructure, one normal and one packed surface map.
# 4 cm per repeat. Red=roughness variation, green=oxide/pits, blue=tooling grain.
N=512
y,x=np.mgrid[0:N,0:N].astype(np.float32)/N
rng=np.random.default_rng(4109)
height=np.zeros((N,N),np.float32)
for _ in range(35):
    fx,fy=rng.integers(2,70,2); phase=rng.uniform(0,math.tau)
    height+=np.sin(math.tau*(x*fx+y*fy)+phase)/(1+fx+fy)
height/=max(abs(height.min()),abs(height.max()))
grain=(np.sin(math.tau*(x*121+y*2))*.5+.5)**18
pits=np.clip((height-.35)*2.2,0,1)
rough=np.clip(.5+height*.24+grain*.09,0,1)
dx=(np.roll(height,-1,1)-np.roll(height,1,1))*.17
dy=(np.roll(height,-1,0)-np.roll(height,1,0))*.17
norm=np.dstack((-dx,-dy,np.ones_like(dx)));norm/=np.linalg.norm(norm,axis=2)[:,:,None]
def image(name,rgb,colorspace):
    im=bpy.data.images.new(name,width=N,height=N,alpha=True)
    im.colorspace_settings.name=colorspace
    im.pixels.foreach_set(np.dstack((rgb,np.ones((N,N)))).astype(np.float32).ravel())
    im.filepath_raw=str(TEX/(name+'.png'));im.file_format='PNG';im.save();im.pack();return im
packed=image('T_Crown_Surface',np.dstack((rough,pits,grain)),'Non-Color')
normal=image('T_Crown_Normal',norm*.5+.5,'Non-Color')
SPECS={
 'Steel':dict(color=[.105,.135,.155],metallic=.92,roughness=.37,emission=0),
 'Silver':dict(color=[.48,.53,.57],metallic=.95,roughness=.25,emission=0),
 'Bronze':dict(color=[.30,.16,.058],metallic=.88,roughness=.34,emission=0),
 'Ice':dict(color=[.10,.32,.44],metallic=0,roughness=.22,emission=.12),
 'Electric':dict(color=[.18,.054,.32],metallic=.06,roughness=.26,emission=.5),
 'Leaf':dict(color=[.028,.175,.066],metallic=.08,roughness=.31,emission=.04),
 'Heat':dict(color=[.45,.064,.012],metallic=.05,roughness=.33,emission=.32),
}
MATS={}
for key,s in SPECS.items():
    mat=bpy.data.materials.new('M_StaffCrown_'+key);mat.use_nodes=True
    bs=mat.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value=(*s['color'],1)
    bs.inputs['Metallic'].default_value=s['metallic'];bs.inputs['Roughness'].default_value=s['roughness']
    tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=normal
    nm=mat.node_tree.nodes.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=1
    mat.node_tree.links.new(tex.outputs['Color'],nm.inputs['Color']);mat.node_tree.links.new(nm.outputs['Normal'],bs.inputs['Normal'])
    nodes=mat.node_tree.nodes;links=mat.node_tree.links
    surface=nodes.new('ShaderNodeTexImage');surface.image=packed
    channels=nodes.new('ShaderNodeSeparateColor');links.new(surface.outputs['Color'],channels.inputs['Color'])
    vertex=nodes.new('ShaderNodeVertexColor');vertex.layer_name='CraftMask'
    mask=nodes.new('ShaderNodeSeparateColor');links.new(vertex.outputs['Color'],mask.inputs['Color'])
    def mathnode(operation,a,b):
        n=nodes.new('ShaderNodeMath');n.operation=operation
        for socket,value in zip(n.inputs,[a,b]):
            if isinstance(value,(float,int)):socket.default_value=value
            else:links.new(value,socket)
        return n.outputs[0]
    def mixnode(a,b,t):
        n=nodes.new('ShaderNodeMixRGB');n.blend_type='MIX';links.new(t,n.inputs[0])
        for socket,value in zip(list(n.inputs)[1:],[a,b]):
            if isinstance(value,list):socket.default_value=(*value,1)
            else:links.new(value,socket)
        return n.outputs[0]
    patina=mathnode('MULTIPLY',channels.outputs['Green'],.46 if s['metallic']>.5 else .19)
    base=mixnode(s['color'],[v*.34 for v in s['color']],patina)
    edge=[min(.75,v*1.26+.025) for v in s['color']]
    base=mixnode(base,edge,mathnode('MULTIPLY',mask.outputs['Red'],.55))
    links.new(base,bs.inputs['Base Color'])
    rough=mathnode('ADD',s['roughness']-.07,mathnode('MULTIPLY',channels.outputs['Red'],.14))
    links.new(mathnode('ADD',rough,mathnode('MULTIPLY',channels.outputs['Green'],.10)),bs.inputs['Roughness'])
    metal=mathnode('MULTIPLY',s['metallic'],mathnode('SUBTRACT',1,mathnode('MULTIPLY',patina,.46)))
    links.new(metal,bs.inputs['Metallic'])
    bs.inputs['Emission Color'].default_value=(*s['color'],1)
    links.new(mathnode('MULTIPLY',mask.outputs['Blue'],s['emission']),bs.inputs['Emission Strength'])
    mat.diffuse_color=(*s['color'],1); MATS[key]=mat

parts=[]
def activate(o):
    bpy.ops.object.select_all(action='DESELECT');o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o
def mesh(name,vs,fs,mat,smooth=False,wear=.08,glow=0):
    me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.update()
    obj=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(obj);me.materials.append(MATS[mat])
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    for p in me.polygons:p.use_smooth=smooth
    color=me.color_attributes.new(name='CraftMask',type='FLOAT_COLOR',domain='CORNER')
    for c in color.data:c.color=(wear,0,glow,1)
    parts.append(obj);return obj
def tube(name,pts,r,mat,sides=10,taper=None,wear=.15,glow=0):
    pts=[Vector(p) for p in pts];vs=[];fs=[]
    for i,p in enumerate(pts):
        d=(pts[min(i+1,len(pts)-1)]-pts[max(i-1,0)]).normalized()
        across=d.cross(Vector((0,1,0)))
        if across.length<.05:across=d.cross(Vector((1,0,0)))
        across.normalize();up=d.cross(across).normalized(); rr=r*(taper[i] if taper else 1)
        for j in range(sides):
            a=j*math.tau/sides;vs.append(p+rr*(across*math.cos(a)+up*math.sin(a)))
        if i:
            for j in range(sides):
                a=(i-1)*sides+j;b=(i-1)*sides+(j+1)%sides
                fs.append((a,b,i*sides+(j+1)%sides,i*sides+j))
    fs += [tuple(reversed(range(sides))),tuple((len(pts)-1)*sides+j for j in range(sides))]
    return mesh(name,vs,fs,mat,sides>8,wear,glow)
def bead(name,center,r,mat,axis=None,length=None):
    axis=Vector(axis or (0,0,1)).normalized(); length=length or r*1.5
    pts=[Vector(center)+axis*t*length for t in [-.5,-.38,.38,.5]]
    return tube(name,pts,r,mat,12,[.79,1,1,.79],.5)
def leaf(name,a,z,length,width,mat,curve=.09,thick=.055):
    vs=[];fs=[]; rows=13; cols=9
    def point(t,s,back=False):
        aa=a+curve*math.sin(t*math.pi*.9)
        center=envelope(aa,z+t*length,.49+.10*math.sin(t*math.pi))
        w=width*(max(.012,math.sin(math.pi*t))**.72)*(1-.25*t)
        bulge=.135*(1-abs(s))*(math.sin(math.pi*t)**.6)
        return center+tangent(aa)*w*s+radial(aa)*(bulge if not back else -thick)
    for back in [False,True]:
        for j in range(rows):
            for k in range(cols):vs.append(point(j/(rows-1),-1+2*k/(cols-1),back))
    layer=rows*cols
    for side in range(2):
        for j in range(rows-1):
            for k in range(cols-1):
                p=side*layer+j*cols+k;f=(p,p+1,p+cols+1,p+cols)
                fs.append(f if side==0 else tuple(reversed(f)))
    boundary=list(range(cols))+[j*cols+cols-1 for j in range(1,rows)]+list(range(layer-2,layer-cols-1,-1))+[j*cols for j in range(rows-2,0,-1)]
    for p,q in zip(boundary,boundary[1:]+boundary[:1]):fs.append((q,p,p+layer,q+layer))
    obj=mesh(name,vs,fs,mat,True,.09)
    return point

manifest=[]
for key in KEYS:
    parts=[]; source=originals['SM_Staff_crown_'+key]
    elm={'spike_crown':'Ice','current_crown':'Electric','wreath_crown':'Leaf','heat_crown':'Heat'}[key]
    metal='Bronze' if key in ['wreath_crown','heat_crown'] else 'Steel'
    trim='Bronze' if key=='wreath_crown' else 'Silver'
    # Preserve both complete original closed base-band components, vertex for vertex.
    bm=bmesh.new();bm.from_mesh(source.data);remaining=set(bm.verts);components=[]
    while remaining:
        todo=[remaining.pop()];component=set(todo)
        while todo:
            for edge in todo.pop().link_edges:
                for v in edge.verts:
                    if v in remaining:remaining.remove(v);component.add(v);todo.append(v)
        if max(v.co.z for v in component)<64.30:components.append(component)
    for ci,comp in enumerate(components):
        vlist=list(comp);index={v:i for i,v in enumerate(vlist)}
        faces={f for v in vlist for f in v.link_faces}
        mid=next(iter(faces)).material_index
        mesh('Retained_MatingBand_'+str(ci),[v.co.copy() for v in vlist],
             [tuple(index[v] for v in f.verts) for f in faces],metal if mid==0 else elm,True,.08,.08 if mid else 0)
    bm.free()
    if len(components)<2:raise RuntimeError('Original closed mating bands were not found')
    ct=BVHTree.FromPolygons([v.co for v in source.data.vertices],[list(p.vertices) for p in source.data.polygons])
    def band(a,z,off=.018):
        p=ray(ct,a,z)
        if p is None:raise RuntimeError('Missing retained crown contact')
        return p+radial(a)*off
    # Thin raised lip and interrupted engraved chevrons follow the real mount.
    for z in [62.72,64.09]:
        tube('RolledMountLip',[band(i*math.tau/128,z) for i in range(129)],.042,trim,8,wear=.55)
    for i in range(16):
        a=i*math.tau/16
        tube('RecessDivider',[band(a-.04,63.30),band(a,63.48),band(a+.04,63.30)],.025,metal,6)
    for i in range(8):
        a=i*math.tau/8
        start=band(a,64.04,-.025)
        pts=[start]+[envelope(a,z) for z in [64.45,64.85,65.25,65.65,66.05,66.45,66.72]]
        tube('ForgedRib',pts,.15 if key!='wreath_crown' else .12,metal,12)
        # Fastener seated against the retained band, with a fine tool slot.
        riv=band(a,63.86,.09);bead('PeenedRivet',riv,.108,trim,radial(a),.13)
        tube('RivetToolSlot',[riv+radial(a)*.074-tangent(a)*.065,riv+radial(a)*.074+tangent(a)*.065],.012,metal,6)
        if key=='spike_crown':
            h=2.13+(i%2)*.42
            centers=[envelope(a+.025*t,66+t*h,.43+.1*t) for t in [0,.10,.35,.81,1]]
            tube('HewnIcePrism',centers,.35,'Ice',6,[.72,1,.89,.46,.025],.05)
            bead('HexProngCollar',centers[1],.375,'Steel',(centers[2]-centers[0]),.23)
            for j in [-1,1]:
                tube('SilverSettingClaw',[centers[0]+tangent(a)*j*.28,
                    centers[1]+tangent(a)*j*.33+radial(a)*.12,
                    centers[2]+tangent(a)*j*.20+radial(a)*.17],.045,'Silver',8,wear=.65)
            # Short subordinate shard rooted in the same metal setting.
            p=centers[0]+tangent(a)*.25
            tube('SecondaryIceFacet',[p,p+tangent(a)*.22+Vector((0,0,.45)),p+tangent(a)*.42+Vector((0,0,.93))],.15,'Ice',5,[1,.7,.035])
        elif key=='current_crown':
            path=[envelope(a+aa,z,.48) for aa,z in [(0,66),(-.08,66.8),(.075,67.2),(-.055,67.73),(.015,68.43)]]
            tube('ForgedLightningConductor',path,.185,'Silver',8,[1,1,.92,.78,.3],.55)
            for j in range(3):
                p=envelope(a,65.26+j*.24,.44)
                bead('CeramicInsulator',p,.224,'Electric',(pts[5]-pts[3]),.18)
                bead('InsulatorCopperRim',p,.232,'Steel',(pts[5]-pts[3]),.045)
            # Fine bifilar coil wraps the lower support, not floating particles.
            coil=[]
            for j in range(73):
                t=j/72; p=envelope(a,64.57+t*.68,.4)
                coil.append(p+tangent(a)*.192*math.cos(t*math.tau*4)+radial(a)*.192*math.sin(t*math.tau*4))
            tube('WoundConductor',coil,.027,'Silver',6,wear=.55)
            tube('InsetVioletChannel',[p+radial(a)*.17 for p in path],.039,'Electric',6,[1,1,1,.8,.12],glow=.45)
            bead('TerminalContact',path[-1],.112,'Silver',length=.19)
        elif key=='wreath_crown':
            point=leaf('SculptedEnamelLeaf',a,66.02,2.36+(i%2)*.12,.62,'Leaf',curve=.115)
            mid=[point(t,0)+radial(a)*.019 for t in [j/20 for j in range(21)]]
            tube('LeafMidrib',mid,.024,'Bronze',6,[max(.17,1-j/22) for j in range(21)],.5)
            for side in [-1,1]:
                tube('FoldedLeafRim',[point(j/24,side)+radial(a)*.015 for j in range(25)],.018,'Bronze',6,wear=.6)
                for j in range(1,6):
                    t=.11+j*.11
                    vein=[point(t+s*.10,side*s*.86)+radial(a)*.024 for s in [0,.25,.5,.75,1]]
                    tube('BranchingLeafVein',vein,.011,'Bronze',5,wear=.3)
            bead('LeafRootCollar',pts[-2],.18,'Bronze',length=.22)
        else:
            point=leaf('SweptFlameBlade',a,65.98,2.83+(i%2)*.1,.45,'Bronze',curve=.18,thick=.085)
            for side in [-1,1]:
                tube('HammeredFlameLip',[point(j/24,side)+radial(a)*.025 for j in range(25)],.037,'Silver',8,wear=.48)
            # Narrow inset ember has its own depth and ends before the metal tip.
            firepath=[point(.12+j*.72/16,0)+radial(a)*.026 for j in range(17)]
            tube('RecessedEmberInlay',firepath,.067,'Heat',8,[math.sin(math.pi*(.08+j*.84/16)) for j in range(17)],glow=.36)
            for j in range(3):
                t=.22+j*.17
                tube('FlameChasedFlute',[point(t+s*.10,-.7+s*1.4)+radial(a)*.029 for s in [0,.25,.5,.75,1]],.018,'Bronze',6,wear=.65)
            bead('FlameRootFerrule',pts[-2],.202,'Steel',length=.28)
    coll=bpy.data.collections.new(key+'_Editable');bpy.context.scene.collection.children.link(coll)
    for o in parts:
        # Dominant-plane mapping avoids pinched UVs on thin facets/caps; 4 cm tile.
        uv=o.data.uv_layers.new(name='UVMap')
        for p in o.data.polygons:
            n=p.normal;axis=max(range(3),key=lambda k:abs(n[k]));axes=[k for k in range(3) if k!=axis]
            for li in p.loop_indices:
                co=o.data.vertices[o.data.loops[li].vertex_index].co
                uv.data[li].uv=(co[axes[0]]/4,co[axes[1]]/4)
        for c in list(o.users_collection):c.objects.unlink(o)
        coll.objects.link(o)
    copies=[]
    for o in parts:
        c=o.copy();c.data=o.data.copy();bpy.context.scene.collection.objects.link(c);copies.append(c)
    activate(copies[0])
    for c in copies:c.select_set(True)
    bpy.ops.object.join();joined=bpy.context.object;joined.name='SM_Staff_crown_'+key
    bpy.context.scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    filename=OUT/(joined.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(filename),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
        bake_anim=False,mesh_smooth_type='FACE',use_tspace=False,apply_scale_options='FBX_SCALE_ALL',path_mode='AUTO',embed_textures=False)
    manifest.append(dict(name=joined.name,id=key,fbx=str(filename),materials=[m.name for m in joined.data.materials],
        triangles=sum(len(p.vertices)-2 for p in joined.data.polygons),retained_mount_components=len(components),
        authored_parts=len(parts),bounds_cm=[[min(v.co[i] for v in joined.data.vertices) for i in range(3)],
                                          [max(v.co[i] for v in joined.data.vertices) for i in range(3)]]))
    joined.hide_render=True;joined.hide_set(True)
    for o in parts:o.hide_set(key!='spike_crown');o.hide_render=key!='spike_crown'
    print('CROWN_AUTHORED '+key,flush=True)

scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
scene['coordinates']='Existing V21 staff local cm; original complete lower bands retained'
scene['surface']='Opaque mineral/enamel; raised metal edges, fine 4cm physical microstructure'
for area in (bpy.context.screen.areas if bpy.context.screen else []):
    if area.type=='VIEW_3D':
        area.spaces.active.region_3d.view_location=Vector((0,0,65.8));area.spaces.active.region_3d.view_distance=19
(OUT/'meshes.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
(OUT/'materials.json').write_text(json.dumps(SPECS,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Staff_CraftedCrowns.blend'))
(ROOT/'author-receipt.json').write_text(json.dumps(dict(complete=True,source=str(SOURCE),meshes=manifest,
    blend=str(ROOT/'Staff_CraftedCrowns.blend'),textures=2,rendered=False,runtime_tested=False),indent=2),encoding='utf-8')
print('STAFF_CROWNS_AUTHORED meshes=4 rendered=false',flush=True)
