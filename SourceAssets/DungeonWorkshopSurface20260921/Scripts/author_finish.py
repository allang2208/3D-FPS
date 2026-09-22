"""Local rework of drawer storage, tools, pegboard and socket. No render or play test."""
from pathlib import Path
import bpy,bmesh,json,math,random,re
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Authored';SCULPT=ROOT.parent/'DungeonWorkshopSculpt20260921';ROOM=ROOT.parent/'DungeonRoomInteriors20260921';R=random.Random(20210921)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
MATS={};recipes=json.loads((OUT/'material-manifest.json').read_text());regions=json.loads((OUT/'labels.json').read_text())
aliases=json.loads((SCULPT/'Authored/manifest.json').read_text())['material_aliases']
oldassets=json.loads((SCULPT/'Receipts/asset-import.json').read_text())
for k,p in oldassets['materials'].items():aliases['WSSculpt_'+k]=p
for key,r in recipes.items():
    m=bpy.data.materials.new('WSFinish_'+key);m.use_nodes=True;p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    p.inputs['Metallic'].default_value=r['metallic'];p.inputs['Roughness'].default_value=r.get('roughness',.6)
    if 'color' in r:p.inputs['Base Color'].default_value=(*r['color'],1)
    for ch,path in r.get('maps',{}).items():
        t=m.node_tree.nodes.new('ShaderNodeTexImage');t.image=bpy.data.images.load(path,check_existing=True)
        if ch!='BaseColor':t.image.colorspace_settings.name='Non-Color'
        if ch=='Normal':
            n=m.node_tree.nodes.new('ShaderNodeNormalMap');n.inputs['Strength'].default_value=r.get('normal_strength',1);m.node_tree.links.new(t.outputs['Color'],n.inputs['Color']);m.node_tree.links.new(n.outputs['Normal'],p.inputs['Normal'])
        else:m.node_tree.links.new(t.outputs['Color'],p.inputs[{'BaseColor':'Base Color','Roughness':'Roughness','Metallic':'Metallic'}[ch]])
    # Match the engine's authored roughness/tint controls in the editable Blender source.
    nt=m.node_tree
    if r.get('color_tint'):
        prev=p.inputs['Base Color'].links[0].from_socket;mix=nt.nodes.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1;mix.inputs[2].default_value=(*r['color_tint'],1);nt.links.new(prev,mix.inputs[1]);nt.links.new(mix.outputs[0],p.inputs['Base Color'])
    if 'roughness_scale' in r:
        prev=p.inputs['Roughness'].links[0].from_socket;mul=nt.nodes.new('ShaderNodeMath');mul.operation='MULTIPLY';mul.inputs[1].default_value=r['roughness_scale'];nt.links.new(prev,mul.inputs[0])
        addn=nt.nodes.new('ShaderNodeMath');addn.operation='ADD';addn.inputs[1].default_value=r['roughness_bias'];nt.links.new(mul.outputs[0],addn.inputs[0]);nt.links.new(addn.outputs[0],p.inputs['Roughness'])
    if r.get('imperfection_mask'):
        mask=nt.nodes.new('ShaderNodeTexImage');mask.image=bpy.data.images.load(r['imperfection_mask'],check_existing=True);mask.image.colorspace_settings.name='Non-Color'
        sep=nt.nodes.new('ShaderNodeSeparateColor');nt.links.new(mask.outputs['Color'],sep.inputs[0])
        factor=nt.nodes.new('ShaderNodeMath');factor.operation='MULTIPLY';factor.inputs[1].default_value=.20;nt.links.new(sep.outputs['Red'],factor.inputs[0])
        inv=nt.nodes.new('ShaderNodeMath');inv.operation='SUBTRACT';inv.inputs[0].default_value=1;nt.links.new(factor.outputs[0],inv.inputs[1])
        prev=p.inputs['Base Color'].links[0].from_socket;mix=nt.nodes.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1;nt.links.new(prev,mix.inputs[1]);nt.links.new(inv.outputs[0],mix.inputs[2]);nt.links.new(mix.outputs[0],p.inputs['Base Color'])
        prev=p.inputs['Roughness'].links[0].from_socket;mix=nt.nodes.new('ShaderNodeMixRGB');mix.inputs[0].default_value=.32;nt.links.new(prev,mix.inputs[1]);nt.links.new(sep.outputs['Green'],mix.inputs[2]);nt.links.new(mix.outputs[0],p.inputs['Roughness'])
        fac=nt.nodes.new('ShaderNodeMath');fac.operation='MULTIPLY';fac.inputs[1].default_value=.32;nt.links.new(sep.outputs['Red'],fac.inputs[0])
        prev=p.inputs['Metallic'].links[0].from_socket;mix=nt.nodes.new('ShaderNodeMixRGB');mix.inputs[2].default_value=(.40,.40,.40,1);nt.links.new(fac.outputs[0],mix.inputs[0]);nt.links.new(prev,mix.inputs[1]);nt.links.new(mix.outputs[0],p.inputs['Metallic'])
    MATS[key]=m
MATS['Machined']=MATS['GroundSteel'];MATS['ToolLabels']=MATS['Labels']
exec(compile((ROOT/'Scripts/modeling.py').read_text(),'modeling.py','exec'),globals())
WORLD=Matrix(((-1,0,0,10),(0,-1,0,0),(0,0,1,0),(0,0,0,1)))
def label_new(g,c,w,key):
    rect=regions[key]['rect'];left,top,pw,ph=rect;h=w*ph/pw;f=Frame(c,(0,1,0),(0,0,1))
    ob=part(g,'Paper insert '+key,[f.p(-w/2,-h/2),f.p(w/2,-h/2),f.p(w/2,h/2),f.p(-w/2,h/2)],[(0,1,2,3)],'Labels')
    for li,uv in zip(ob.data.polygons[0].loop_indices,[(left/2048,1-(top+ph)/2048),((left+pw)/2048,1-(top+ph)/2048),((left+pw)/2048,1-top/2048),(left/2048,1-top/2048)]):ob.data.uv_layers.active.data[li].uv=uv
    return h
def frontal_uv(ob,c,width,height):
    for face in ob.data.polygons:
        for li in face.loop_indices:
            p=ob.data.vertices[ob.data.loops[li].vertex_index].co
            ob.data.uv_layers.active.data[li].uv=((p.y-c[1])/width+.5,(p.z-c[2])/height+.5)
def holder(g,x,y,z,w,h):
    # Front-facing frame is physically clear of the underlying painted face.
    box(g,'Stamped label-holder back',(x,y,z),(.0008,w+.006,h+.005),'GroundSteel',.00035)
    for yy in (y-w/2-.0015,y+w/2+.0015):box(g,'Label frame folded side',(x+.001,yy,z),(.0018,.0025,h+.004),'GroundSteel',.0004)
    for zz in (z-h/2-.001,z+h/2+.001):box(g,'Label frame lip',(x+.001,y,zz),(.0018,w+.006,.0018),'GroundSteel',.0004)

# Rebuild the organizer with functional drawer gaps, thin returned faces and front-mounted labels.
g='Organizer';x=.235;y=3.32;z=1.324;w=.73;h=.266;depth=.126
box(g,'Folded cabinet backing',(x-.060,y,z),(.003,w,h),'SheetPaint',.001)
for yy in (y-w/2,y+w/2):box(g,'Cabinet side return',(x,yy,z),(depth,.003,h),'SheetPaint',.0012)
for zz in (z-h/2,z+h/2):box(g,'Folded cabinet cap',(x,y,zz),(depth,w,.003),'SheetPaint',.0012)
for row in range(3):
    for col in range(4):
        idx=row*4+col;yy=y-w/2+.092+col*.182;zz=z-h/2+.045+row*.088;opening=.020 if idx==6 else 0
        xx=x+depth/2+opening
        ob=box(g,'Drawer face '+str(idx+1),(xx,yy,zz),(.0024,.177,.082),'DrawerPaint'+str((row+col)%3),.0011);frontal_uv(ob,(xx,yy,zz),.177,.082)
        for sy in (-1,1):box(g,'Drawer side',(x+opening,yy+sy*.082,zz-.003),(depth-.007,.002,.071),'SheetPaint',.0007)
        box(g,'Drawer bottom',(x+opening,yy,zz-.039),(depth-.005,.166,.002),'SheetPaint',.0007)
        box(g,'Drawer inner back',(x-depth/2+opening,yy,zz-.003),(.002,.166,.071),'SheetPaint',.0007)
        for dy in (-.029,.029):
            cylinder(g,'Pull mounting bush',(xx+.0013,yy+dy,zz-.012),(xx+.0045,yy+dy,zz-.012),.0042,'GroundSteel',48)
            cylinder(g,'Pull screw recess',(xx+.0045,yy+dy,zz-.012),(xx+.0047,yy+dy,zz-.012),.0014,'Recess',24)
        sweep(g,'Formed rounded drawer pull',[(xx+.005,yy-.029,zz-.012),(xx+.014,yy-.028,zz-.018),(xx+.016,yy,zz-.020),(xx+.014,yy+.028,zz-.018),(xx+.005,yy+.029,zz-.012)],.0025,'GroundSteel',24)
        lw=.066;lh=lw/regions['drawer'+str(idx)]['aspect'];lx=xx+.0027;lz=zz+.022
        holder(g,lx,yy,lz,lw,lh)
        label_new('ToolMarkings',(lx+.0010,yy,lz),lw,'drawer'+str(idx))
        # A few contact scuffs along the folded lower edge, never all-over camouflage.
        for k in range(2+idx%3):
            cyy=yy+R.uniform(-.070,.070);length=R.uniform(.003,.012)
            sweep(g,'Localized lower drawer edge scuff',[(xx+.00135,cyy,zz-.040),(xx+.00135,cyy+length,zz-.040)],.00020,'ExposedEdge',8,False)

# Perforated sheet is genuinely thin, with rounded punched lips and smooth hole walls.
g='Toolboard';vs=[];fs=[];mi=[];smooth=[];N=48
for iz in range(9):
    for iy in range(19):
        cy=1.70+iy*.11;cz=1.22+iz*.11;start=len(vs)
        for ringid in range(6):
            for i in range(N):
                a=-3*math.pi/4+i*math.tau/N;co,si=math.cos(a),math.sin(a)
                rad=.055/max(abs(co),abs(si)) if ringid in (0,5) else [.0,.0084,.0079,.0079,.0082][ringid]
                xx=[.177,.177,.1766,.1750,.1747,.1747][ringid];vs.append((xx,cy+co*rad,cz+si*rad))
        for layer in range(5):
            for i in range(N):
                j=(i+1)%N;fs.append((start+layer*N+i,start+layer*N+j,start+(layer+1)*N+j,start+(layer+1)*N+i));mi.append(0);smooth.append(layer in (1,2,3))
ob=part(g,'Pressed perforated steel sheet with rolled hole edges',vs,fs,'SheetPaint')
for face,s in zip(ob.data.polygons,smooth):face.use_smooth=s
bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.remove_doubles(bm,verts=bm.verts,dist=.000005);bm.to_mesh(ob.data);bm.free()
for zz in (1.16,2.21):box(g,'Folded perforated-panel horizontal rail',(.171,2.69,zz),(.044,2.20,.028),'SheetPaint',.003)
for yy in (1.61,3.78):box(g,'Folded perforated-panel vertical rail',(.171,yy,1.685),(.044,.028,1.07),'SheetPaint',.003)
for yy in (1.64,3.74):
    for zz in (1.185,2.185):bolt(g,(.198,yy,zz),(1,0,0),.005)
# Sparse contact streaks beneath repeatedly used tool hooks.
for yy,zz in [(1.77,1.86),(2.12,1.84),(2.75,1.73),(3.40,1.59)]:
    for i in range(3):
        y0=yy+R.uniform(-.012,.012);z0=zz-R.uniform(.008,.04)
        sweep(g,'Tool contact mark',[(.17712,y0,z0),(.17712,y0+R.uniform(-.003,.003),z0-.012)],.00023,'Rust',8,False)
# Correctly proportioned header and size plates, with real fasteners and paper separation.
hw=.57;hh=hw/regions['header']['aspect'];center=(.203,2.69,2.160)
box('ToolMarkings','Header steel backing',center,(.0025,hw+.012,hh+.010),'SheetPaint',.002)
label_new('ToolMarkings',(.2052,2.69,2.160),hw,'header')
for yy in (2.69-hw/2+.008,2.69+hw/2-.008):bolt('ToolMarkings',(.206,yy,2.160),(1,0,0),.0023)
for i in range(5):
    yy=1.77+i*.175;lw=.082;lh=lw/regions['tool'+str(i)]['aspect']
    holder('ToolMarkings',.179,yy,2.015,lw,lh);label_new('ToolMarkings',(.180,yy,2.015),lw,'tool'+str(i))

# Reuse the authored tool geometry, retaining the individual construction and UVs.
with bpy.data.libraries.load(str(SCULPT/'Authored/DungeonWorkshopComponents.blend'),link=False) as (src,dst):dst.collections=['SOURCE_HandTools','SOURCE_BenchDetail']
for col in dst.collections:
    group='HandTools' if col.name.startswith('SOURCE_HandTools') else 'BenchDetail';scene.collection.children.link(col);col.hide_viewport=False;col.hide_render=False
    for ob in list(col.objects):
        if group=='HandTools' and (ob.name.startswith(('Forged engineer hammer centre','Bell hammer face','Rounded peen','Steel handle wedge')) or ob.name.startswith('Hex fastener') or ob.name.startswith('Fastener washer')):
            bpy.data.objects.remove(ob,do_unlink=True);continue
        for i,mat in enumerate(ob.data.materials):
            name=re.sub(r'[._][0-9]{3}$','',mat.name);key=name.removeprefix('WSSculpt_')
            replacement={'Forged':'ToolSteel','Machined':'GroundSteel','RubberGrip':'Grip'}.get(key)
            if ob.name.startswith('Shaped elliptical ash handle') and 'Timber' in name:replacement='WoodGrip'
            if replacement:ob.data.materials[i]=MATS[replacement]
        if ob.name.startswith('Shaped elliptical ash handle'):
            for loop in ob.data.uv_layers.active.data:
                a,b=loop.uv;loop.uv=(b,.32+a*.26)
            for v in ob.data.vertices:
                if v.co.z>1.785:v.co.z=1.785+(v.co.z-1.785)*2.0
        # Ground jaws read differently from the dark forged body.
        if ob.name.startswith('Forged pliers half'):
            ob.data.materials.append(MATS['GroundSteel']);idx=len(ob.data.materials)-1
            zzmin=min(v.co.z for v in ob.data.vertices);zzmax=max(v.co.z for v in ob.data.vertices)
            for face in ob.data.polygons:
                zf=sum(ob.data.vertices[i].co.z for i in face.vertices)/len(face.vertices)
                if zf>zzmin+(zzmax-zzmin)*.73:face.material_index=idx
        PARTS[group].append(ob)
# A continuous forged hammer head with oval handle eye and selectively ground striking face.
f=Frame((.240,3.01,1.798),(1,0,0),(0,1,0))
stations=catmull([(-.077,.017),(-.074,.024),(-.067,.024),(-.058,.020),(-.047,.014),(-.031,.017),(-.021,.020),(.022,.020),(.037,.014),(.051,.013),(.068,.010),(.077,.001)],5)
hammer=lathe('HandTools','Continuous forged hammer head',f,stations,'ToolSteel',80)
bevel(hammer,.0005,3)
poly=[(.009*math.cos(i*math.tau/64),.013*math.sin(i*math.tau/64)) for i in range(64)]
bore(hammer,Frame((.240,3.01,1.798),(1,0,0),(0,1,0)),poly,.09)
hammer.data.materials.append(MATS['GroundSteel'])
for face in hammer.data.polygons:
    if all(hammer.data.vertices[i].co.y<3.01-.070 for i in face.vertices):face.material_index=1
lathe('HandTools','Exposed wood through hammer eye',Frame((.240,3.01,1.813),(1,0,0),(0,0,1)),[(0,.009),(.008,.009),(.010,.0087)],'WoodGrip',48)
box('HandTools','Hammer eye fixing wedge',(.240,3.01,1.824),(.013,.0014,.0018),'GroundSteel',.0003)

# Preserve the shared pipe collars, removing only the old primitive outlet from its source.
with bpy.data.libraries.load(str(ROOM/'Authored/DungeonRooms_Authored.blend'),link=False) as (src,dst):dst.objects=['SM_Room_WS_UtilityDetail']
utility=dst.objects[0];scene.collection.objects.link(utility);utility.data.transform(WORLD.inverted())
bm=bmesh.new();bm.from_mesh(utility.data)
cut=[face for face in bm.faces if all(.14<v.co.x<.29 and 2.49<v.co.y<2.81 and 1.22<v.co.z<1.40 for v in face.verts)]
bmesh.ops.delete(bm,geom=cut,context='FACES');bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(utility.data);bm.free()
utility.data.materials.clear();utility.data.materials.append(MATS['GroundSteel'])
for face in utility.data.polygons:face.material_index=0
utility.name='Retained service pipe straps';PARTS['UtilityDetail'].append(utility)
g='UtilityDetail';body=box(g,'Die cast double socket housing',(.203,2.65,1.31),(.055,.25,.12),'SheetPaint',.008)
cover=box(g,'Moulded insulating cover',(.232,2.65,1.31),(.007,.238,.108),'Bakelite',.006)
for yy in (2.590,2.710):
    ff=Frame((.232,yy,1.310),(0,1,0),(0,0,1));circle=[(.0235*math.cos(i*math.tau/64),.0235*math.sin(i*math.tau/64)) for i in range(64)]
    bore(cover,ff,circle,.025);bore(body,ff,circle,.080)
    lathe(g,'Recessed round socket well',Frame((.236,yy,1.310),(0,1,0),(1,0,0)),[(-.018,.022),(-.018,.024),(.001,.024),(.004,.028),(.006,.027),(.006,.023),(.002,.0215),(-.018,.0215)],'Bakelite',80,cap=False)
    floor=cylinder(g,'Socket recessed insulating floor',(.218,yy,1.310),(.221,yy,1.310),.022,'Bakelite',80)
    for dy in (-.0095,.0095):
        hole=[(.0026*math.cos(i*math.tau/32),.0026*math.sin(i*math.tau/32)) for i in range(32)]
        bore(floor,Frame((.220,yy+dy,1.310),(0,1,0),(0,0,1)),hole,.010)
        cylinder(g,'Deep pin contact shadow',(.211,yy+dy,1.310),(.213,yy+dy,1.310),.0028,'Recess',32)
    for zz in (1.310-.020,1.310+.020):box(g,'Socket earthing spring',(.231,yy,zz),(.012,.006,.0014),'GroundSteel',.0004)
for yy in (2.545,2.755):
    cylinder(g,'Cover screw head',(.236,yy,1.310),(.238,yy,1.310),.0036,'GroundSteel',48)
    sweep(g,'Cover screw slot',[(.2382,yy-.002,1.310),(.2382,yy+.002,1.310)],.0004,'Recess',8,False)
lathe(g,'Conduit entry gland',Frame((.190,2.62,1.370),(1,0,0),(0,0,1)),[(0,.019),(.004,.022),(.012,.021),(.014,.017),(.021,.017)],'GroundSteel',64)
label_new('ToolMarkings',(.2362,2.65,1.350),.060,'socket')

bindings={'Organizer':'DGN_WSSculpt_Organizer','Toolboard':'DGN_Room_WS_Toolboard','ToolMarkings':'DGN_WSTools_ToolMarkings',
    'HandTools':'DGN_Room_WS_HandTools','BenchDetail':'DGN_Room_WS_BenchDetail','UtilityDetail':'DGN_Room_WS_UtilityDetail'}
manifest={'objects':[],'material_aliases':aliases,'source_blend':str(OUT/'DungeonWorkshopSurfaceDetails.blend'),'hide_actors':[],
    'tests_run':False,'screenshots_taken':False,'source_note':'Four user closeups; localized workshop surfaces and assembly detail'}
exports=bpy.data.collections.new('ENGINE_EXPORTS');scene.collection.children.link(exports);deps=bpy.context.evaluated_depsgraph_get()
for group,objects in list(PARTS.items()):
    if group.startswith('_') or not objects:continue
    coll=bpy.data.collections.new('SOURCE_'+group);scene.collection.children.link(coll);copies=[]
    for ob in objects:
        for old in list(ob.users_collection):old.objects.unlink(ob)
        coll.objects.link(ob);ev=ob.evaluated_get(deps);me=bpy.data.meshes.new_from_object(ev,preserve_all_data_layers=True,depsgraph=deps)
        if any(m.type=='REMESH' for m in ob.modifiers):
            uv=me.uv_layers.active or me.uv_layers.new(name='UVMap')
            for face in me.polygons:
                axis=max(range(3),key=lambda a:abs(face.normal[a]));ds=[a for a in range(3) if a!=axis]
                for li in face.loop_indices:
                    p=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(p[ds[0]]/.18,p[ds[1]]/.18)
        copy=bpy.data.objects.new(ob.name+'_export',me);exports.objects.link(copy);copy.matrix_world=ob.matrix_world.copy();copies.append(copy)
    active(copies[0])
    for ob in copies:ob.select_set(True)
    bpy.ops.object.join();ob=copies[0];ob.name='SM_WSFinish_'+group;ob.data.transform(WORLD);ob.data.update()
    tri=ob.modifiers.new('FBX triangulation','TRIANGULATE');tri.keep_custom_normals=True;bpy.ops.object.modifier_apply(modifier=tri.name)
    file=OUT/(ob.name+'.fbx');bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False,bake_anim=False)
    manifest['objects'].append(dict(name=ob.name,actor=bindings[group],replace=True,fbx=str(file),collision=False,cast_shadow=group!='ToolMarkings',materials=[m.name for m in ob.data.materials],triangles=len(ob.data.polygons)))
    coll.hide_render=True;coll.hide_viewport=True
for im in bpy.data.images:
    if im.source=='FILE' and im.filepath and Path(bpy.path.abspath(im.filepath)).exists():im.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'DungeonWorkshopSurfaceDetails.blend'))
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('WORKSHOP_SURFACE_DETAILS_AUTHORED',len(manifest['objects']),'NO_RENDER')
