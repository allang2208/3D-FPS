from pathlib import Path
import bpy,json,math,random
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Authored';OLD=ROOT.parent/'DungeonWorkshopTools20260921';DETAIL=ROOT.parent/'DungeonWorkshopDetail20260921'
OUT.mkdir(parents=True,exist_ok=True);R=random.Random(21934)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
MATS={};aliases={}
oldassets=json.loads((OLD/'Receipts/asset-import.json').read_text());detailassets=json.loads((DETAIL/'Receipts/asset-import.json').read_text())
with bpy.data.libraries.load(str(OLD/'Authored/DungeonWorkshopTools.blend'),link=False) as (src,dst):
    dst.materials=['WSTools_'+k for k in ('Timber','EndGrain','Canvas','Enamel','Lens','TaskLens','OilFilm','ToolLabels')]+['WSDetail_RackPaint']
for m in dst.materials:
    if not m:raise RuntimeError('Required previous material unavailable')
    key=m.name.removeprefix('WSTools_').removeprefix('WSDetail_');MATS[key]=m;aliases[m.name]=(detailassets if key=='RackPaint' else oldassets)['materials'][key]
recipes=json.loads((OUT/'material-manifest.json').read_text())
for key,r in recipes.items():
    m=bpy.data.materials.new('WSSculpt_'+key);m.use_nodes=True;p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    p.inputs['Metallic'].default_value=r['metallic'];p.inputs['Roughness'].default_value=r.get('roughness',.5)
    if 'color' in r:p.inputs['Base Color'].default_value=(*r['color'],1)
    for ch,path in r.get('maps',{}).items():
        n=m.node_tree.nodes.new('ShaderNodeTexImage');n.image=bpy.data.images.load(path,check_existing=True)
        if ch!='BaseColor':n.image.colorspace_settings.name='Non-Color'
        if ch=='Normal':
            normal=m.node_tree.nodes.new('ShaderNodeNormalMap');m.node_tree.links.new(n.outputs['Color'],normal.inputs['Color']);m.node_tree.links.new(normal.outputs['Normal'],p.inputs['Normal'])
        else:m.node_tree.links.new(n.outputs['Color'],p.inputs['Base Color' if ch=='BaseColor' else 'Roughness'])
    MATS[key]=m
for script in ('modeling.py','components.py','luminaires.py','workbench.py'):exec(compile((ROOT/'Scripts'/script).read_text(),script,'exec'),globals())
build_bench();print('SCULPT_STAGE bench',flush=True)
build_vise();print('SCULPT_STAGE vise',flush=True)
# Wall tools retain the accepted display positions, with new continuous forged bodies.
for i,L in enumerate((.20,.225,.245,.27,.30)):
    yy=1.77+i*.175;bottom=1.91-L;f=Frame((.235,yy,bottom),(0,1,0),(0,0,1));wrench('HandTools',f,L)
    zz=bottom+.210*(L/.24)
    sweep('HandTools','Bent wire peg hook',[(.175,yy,zz),(.228,yy,zz),(.258,yy,zz),(.261,yy,zz+.012)],.0026,'Machined',20)
    label('ToolMarkings',(.199,yy,2.015),(0,1,0),(0,0,1),.105,.048,i+1)
for yy,what in [(2.75,pliers),(3.01,hammer)]:
    what('HandTools',Frame((.240,yy,1.55),(0,1,0),(0,0,1)))
    zz=1.742 if what==pliers else 1.776
    for dy in (-.021,.021):sweep('HandTools','Twin support peg',[(.177,yy+dy,zz),(.252,yy+dy,zz),(.264,yy+dy,zz+.014)],.0028,'Machined',20)
for i,yy in enumerate((3.24,3.40,3.55)):
    driver('HandTools',Frame((.238,yy,1.52),(0,1,0),(0,0,1)),.22+i*.025,i%2==0)
    ring('HandTools','Driver rack hoop',Frame((.237,yy,1.586),(1,0,0),(0,1,0)),.018,.0023,'Machined',40)
    cylinder('HandTools','Hoop mounting stalk',(.177,yy,1.586),(.217,yy,1.586),.003,'Machined',24)
label('ToolMarkings',(.200,2.67,2.165),(0,1,0),(0,0,1),.67,.071,0)
for yy in (1.64,3.74):
    for zz in (1.185,2.185):bolt('HandTools',(.198,yy,zz),(1,0,0),.0055)
wrench('BenchDetail',flat((1.12,3.58,.945),-.30),.21)
driver('BenchDetail',flat((1.48,3.49,.954),.32),.245,False)
pliers('BenchDetail',flat((.60,3.27,.950),-.28))
ratchet('BenchDetail',flat((1.83,3.55,.954),.08))
# Socket rack with individual hollow broached heads.
box('BenchDetail','Socket rail',(1.59,3.97,.946),(.41,.043,.012),'RubberGrip',.004)
for i in range(7):socket('BenchDetail',flat((1.42+i*.057,3.97,.953)),.014+i*.0015,.032+i*.002)
# Vernier caliper with forged fixed jaw, open measuring throat and milled carriage.
f=flat((.57,1.78,.943),-.24)
profile('BenchDetail','Caliper fixed beam and measuring jaw',rounded([(-.009,0),(.009,0),(.009,.223),(-.009,.223),(-.009,.029),(-.036,.060),(-.042,.062),(-.038,.032),(-.017,.010)],.002,5),f,.004,'Machined',.0005)
profile('BenchDetail','Caliper sliding jaw',rounded([(-.010,.097),(.014,.097),(.015,.130),(-.009,.130),(-.036,.166),(-.041,.167),(-.038,.137),(-.010,.115)],.002,5),f.offset(z=.0035),.004,'Machined',.0005)
box('BenchDetail','Vernier scale carriage',(0,0,0),(.030,.032,.009),'Forged',.002,frame=f.offset(y=.112,z=.004))
cylinder('BenchDetail','Caliper thumb wheel',f.p(.016,.109,.006),f.p(.016,.119,.006),.009,'Machined',48)
for i in range(23):
    y=.018+i*.008
    sweep('BenchDetail','Engraved caliper graduation',[f.p(-.006,y,.0021),f.p(.003 if i%5==0 else -.001,y,.0021)],.00015,'RubberGrip',6,False)
# Deep-drawn oval parts tray with rounded bottom corners and rolled rim.
f=flat((1.68,3.74,.948));N=96;vs=[];fs=[]
for zz,s in [(0,.90),(.003,.96),(.018,1),(.024,1),(.024,.968),(.018,.965),(.005,.90)]:
    for i in range(N):
        a=i*math.tau/N;vs.append(f.p(.142*s*math.copysign(abs(math.cos(a))**.38,math.cos(a)),.115*s*math.copysign(abs(math.sin(a))**.38,math.sin(a)),zz))
for j in range(6):
    for i in range(N):a=j*N+i;b=j*N+(i+1)%N;fs.append((a,b,b+N,a+N))
fs.extend([tuple(reversed(range(N))),tuple(6*N+i for i in range(N))]);part('BenchDetail','Deep-drawn magnetic parts tray',vs,fs,'Machined',True)
for xx in (1.60,1.76):
    for yy in (3.68,3.80):cylinder('BenchDetail','Tray rubber magnet foot',(xx,yy,.939),(xx,yy,.949),.015,'RubberGrip',32)
for i in range(12):
    xx=1.68+R.uniform(-.10,.10);yy=3.74+R.uniform(-.075,.075)
    if i%2:ring('BenchDetail','Loose steel washer',flat((xx,yy,.955)),.006,.0015,'Machined',32)
    else:bolt('BenchDetail',(xx,yy,.953),(0,0,1),.004)
# Oil can with formed shoulder, screw cap and long brass-like steel spout.
for xx,yy,h,index in [(1.11,3.97,.17,8),(1.24,3.97,.21,9)]:
    f=Frame((xx,yy,.940),(1,0,0),(0,0,1))
    lathe('BenchDetail','Spun oil can' if index==8 else 'Moulded cleaning bottle',f,[(0,.030),(.002,.038),(.008,.041),(h*.66,.041),(h*.74,.038),(h*.80,.029),(h*.86,.019),(h*.93,.018)],'Enamel' if index==8 else 'RedGrip',80)
    lathe('BenchDetail','Knurled bottle cap',f,[(h*.88,.020),(h*.98,.020),(h,.017)],'RubberGrip',72,.06)
    label('BenchDetail',(xx,yy-.0415,.94+h*.42),(1,0,0),(0,0,1),.058,.063,index)
    if index==8:sweep('BenchDetail','Tapered oil spout',[(xx,yy,.94+h),(xx+.015,yy,1.00+h),(xx+.062,yy,1.027+h)],lambda t:.004*(1-.45*t),'Machined',32)
print('SCULPT_STAGE tools',flush=True)
# Compact parts organizer below the tool row, taken from the concept's service-storage vocabulary.
g='Organizer';x=.235;y=3.32;z=1.324;w=.73;h=.266;depth=.126
box(g,'Organizer folded backing',(x-.050,y,z),(.003,w,h),'RackPaint',.001)
for yy in (y-w/2,y+w/2):box(g,'Organizer return side',(x,yy,z),(depth,.003,h),'RackPaint',.001)
for zz in (z-h/2,z+h/2):box(g,'Organizer top and bottom return',(x,y,zz),(depth,w,.003),'RackPaint',.001)
for row in range(3):
    for col in range(4):
        yy=y-w/2+.092+col*.182;zz=z-h/2+.045+row*.088;opening=.020 if (row,col)==(1,2) else 0
        box(g,'Pressed drawer front',(x+depth/2+opening,yy,zz),(.006,.172,.077),'RackPaint',.003)
        box(g,'Drawer bottom',(x+opening,yy,zz-.035),(depth-.003,.167,.003),'RackPaint',.001)
        sweep(g,'Folded drawer finger pull',[(x+.067+opening,yy-.026,zz+.003),(x+.078+opening,yy-.026,zz-.006),(x+.078+opening,yy+.026,zz-.006),(x+.067+opening,yy+.026,zz+.003)],.003,'Machined',16)
        label('ToolMarkings',(x+.066+opening,yy,zz+.021),(0,1,0),(0,0,1),.073,.019,10 if row%2 else 11)
build_task_lamp();build_ceiling_lights();print('SCULPT_STAGE lighting',flush=True)
build_cloth();print('SCULPT_STAGE cloth_settled',flush=True)
# Retain only localized oil stain surfaces from the accepted earlier working surface.
with bpy.data.libraries.load(str(OLD/'Authored/DungeonWorkshopTools.blend'),link=False) as (src,dst):dst.objects=['SM_WSTools_BenchWear']
stains=dst.objects[0];scene.collection.objects.link(stains)
import bmesh
bm=bmesh.new();bm.from_mesh(stains.data);oil={i for i,m in enumerate(stains.data.materials) if 'OilFilm' in m.name}
bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index not in oil],context='FACES');bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(stains.data);bm.free()
stains.data.materials.clear();stains.data.materials.append(MATS['OilFilm'])
for face in stains.data.polygons:face.material_index=0
WORLD=Matrix((( -1,0,0,10),(0,-1,0,0),(0,0,1,0),(0,0,0,1)))
stains.data.transform(WORLD.inverted());stains.name='Local oil residues retained from accepted surface';PARTS['BenchWear'].append(stains)
bindings={'BenchFrame':'DGN_Room_WS_Workbench','BenchTop':'DGN_WSTools_BenchTop','BenchDetail':'DGN_Room_WS_BenchDetail',
 'HandTools':'DGN_Room_WS_HandTools','TaskLamp':'DGN_Room_WS_TaskLight','CeilingFixtures':'DGN_WSTools_CeilingFixtures',
 'Rag':'DGN_Room_WS_Cloth','ToolMarkings':'DGN_WSTools_ToolMarkings','BenchWear':'DGN_Room_WS_LocalWear'}
manifest=dict(objects=[],material_aliases=aliases,source_blend=str(OUT/'DungeonWorkshopComponents.blend'),
    hide_actors=['DGN_WSTools_TaskCable','DGN_WSTools_ToolWear'],tests_run=False,screenshots_taken=False,
    reference='Docs/Gameplay/Previews/DungeonRoomConcepts_20260921/01_workshop_concept.png',
    construction='Independent manufactured component profiles and modifiers; cloth gravity drape; no global mesh subdivision pass')
# Preserve independently editable components; export evaluated copies grouped for UE.
exports=bpy.data.collections.new('ENGINE_EXPORTS');scene.collection.children.link(exports)
deps=bpy.context.evaluated_depsgraph_get()
for group,objects in list(PARTS.items()):
    if group.startswith('_') or not objects:continue
    coll=bpy.data.collections.new('SOURCE_'+group);scene.collection.children.link(coll);copies=[]
    for ob in objects:
        for oldcoll in list(ob.users_collection):oldcoll.objects.unlink(ob)
        coll.objects.link(ob)
        ev=ob.evaluated_get(deps);me=bpy.data.meshes.new_from_object(ev,preserve_all_data_layers=True,depsgraph=deps)
        if any(mod.type=='REMESH' for mod in ob.modifiers):
            # Remeshing creates new topology. Give the cast body its own post-remesh UVs.
            uv=me.uv_layers.active or me.uv_layers.new(name='UVMap')
            for face in me.polygons:
                axis=max(range(3),key=lambda a:abs(face.normal[a]));dims=[a for a in range(3) if a!=axis]
                for li in face.loop_indices:
                    p=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(p[dims[0]]/.18,p[dims[1]]/.18)
        copy=bpy.data.objects.new(ob.name+'_export',me);exports.objects.link(copy);copy.matrix_world=ob.matrix_world.copy();copies.append(copy)
    active(copies[0])
    for ob in copies:ob.select_set(True)
    bpy.ops.object.join();ob=copies[0];ob.name='SM_WSSculpt_'+group
    ob.data.transform(WORLD);ob.data.update()
    tri=ob.modifiers.new('Final export triangulation','TRIANGULATE');tri.keep_custom_normals=True;bpy.ops.object.modifier_apply(modifier=tri.name)
    file=OUT/(ob.name+'.fbx');bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False,bake_anim=False)
    manifest['objects'].append(dict(name=ob.name,actor=bindings.get(group,'DGN_WSSculpt_'+group),replace=group in bindings,fbx=str(file),
        collision=group in ('BenchFrame','BenchTop'),cast_shadow=group not in ('ToolMarkings','BenchWear'),materials=[m.name for m in ob.data.materials],triangles=len(ob.data.polygons),components=len(objects)))
    print('SCULPT_EXPORTED',group,len(ob.data.polygons),flush=True)
    # Component source and engine assembly are separate visible collections, never double drawn.
    coll.hide_render=True;coll.hide_viewport=True
for im in bpy.data.images:
    if im.source=='FILE' and im.filepath and Path(bpy.path.abspath(im.filepath)).exists():im.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'DungeonWorkshopComponents.blend'))
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('WORKSHOP_COMPONENTS_AUTHORED',len(manifest['objects']),'NO_RENDER',flush=True)
