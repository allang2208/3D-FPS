"""Split authored moving parts; add an opening folio and practical brewing utensils. No renders."""
import bpy,sys,json,math
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT.parent/'ModelV1'
sys.path.insert(0,str(SOURCE/'Scripts'))
import geometry as g
bpy.ops.wm.open_mainfile(filepath=str(SOURCE/'Authored/PotionWorkbench_Editable.blend'),load_ui=False,use_scripts=False)
scene=bpy.context.scene
for ob in list(scene.objects):
    if ob.type not in ('MESH','FONT','CURVE','EMPTY'):bpy.data.objects.remove(ob,do_unlink=True)
for key,name in {'atlas':'PW_SurfaceAtlas','wood':'PW_wood','endgrain':'PW_endgrain','rune':'PW_RuneInlay','potion':'PW_potion','glass':'PW_glass','amberglass':'PW_amberglass','clearliquid':'PW_clearliquid','redliquid':'PW_redliquid','blueliquid':'PW_blueliquid','label':'PW_PrintedLabels'}.items():
    g.MATS[key]=bpy.data.materials[name]

parts=[]
def export(name,objects,pivot=(0,0,0),lods=False):
    copies=[]
    for source in objects:
        if source.type not in ('MESH','FONT','CURVE'):continue
        ob=source.copy();ob.data=source.data.copy();scene.collection.objects.link(ob)
        ob.parent=None;ob.matrix_world=source.matrix_world.copy();copies.append(ob)
    bpy.ops.object.select_all(action='DESELECT')
    for ob in copies:ob.select_set(True)
    bpy.context.view_layer.objects.active=copies[0]
    bpy.ops.object.convert(target='MESH');bpy.ops.object.join()
    ob=bpy.context.object;ob.name=name
    scene.cursor.location=pivot;bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    ob.location=(0,0,0);bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    mats=[];mapping={}
    for i,mat in enumerate(ob.data.materials):
        if mat not in mats:mats.append(mat)
        mapping[i]=mats.index(mat)
    indices=[mapping[p.material_index] for p in ob.data.polygons]
    ob.data.materials.clear()
    for mat in mats:ob.data.materials.append(mat)
    for p,i in zip(ob.data.polygons,indices):p.material_index=i
    rec={'name':name,'pivot':list(pivot),'materials':[m.name for m in mats],'lods':[]}
    for level,ratio in ((0,1),(1,.52),(2,.22)) if lods else ((0,1),):
        item=ob if level==0 else ob.copy()
        if level:
            item.data=ob.data.copy();scene.collection.objects.link(item)
        g.select(item)
        if level:
            dec=item.modifiers.new('Distance reduction','DECIMATE');dec.ratio=ratio
            dec.delimit={'MATERIAL','SEAM','SHARP'};bpy.ops.object.modifier_apply(modifier=dec.name)
        file=ROOT/'Authored'/f'{name}_LOD{level}.fbx'
        bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH'},apply_unit_scale=True,
            apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE',use_tspace=True,
            add_leaf_bones=False,bake_anim=False,path_mode='STRIP')
        item.data.calc_loop_triangles();rec['lods'].append({'source':str(file),'triangles':len(item.data.loop_triangles)})
        if level:bpy.data.objects.remove(item,do_unlink=True)
    bpy.data.objects.remove(ob,do_unlink=True);parts.append(rec)

original=[o for o in scene.objects if o.type in ('MESH','FONT','CURVE')]
folio=[o for o in original if o.name.startswith(('Closed recipe folio','Folio '))]
pestle=[o for o in original if o.name=='Pestle']
liquid=[o for o in original if o.get('component')=='PotionSurface']
ring=[o for o in original if o.get('component')=='HeaterRing']
excluded=set(folio+pestle+liquid+ring)
extras='--extras' in sys.argv or '--utensils' in sys.argv
if extras:parts=json.loads((ROOT/'runtime_manifest.json').read_text('utf8'))['parts'][:4 if '--utensils' in sys.argv else 10]
else:
    export('SM_AlchemyBody',[o for o in original if o not in excluded],lods=True)
    export('SM_AlchemyFolioClosed',folio,(23,28,94))
    export('SM_AlchemyLiquid',liquid,(225,106,119.2))
    export('SM_AlchemyHeater',ring,(225,106,102.5))

def made(name,fn):
    g.group(name);before=len(g.PARTS);fn()
    if extras and name in [p['name'] for p in parts]:return
    export(name,g.PARTS[before:])
def rz(name,p,profile,*args,**kwargs):
    return g.lathe(name,p,[(height,radius) for radius,height in profile],*args,**kwargs)
def pestle_new():
    rz('Polished brass pestle',(0,0,0),[(0,-6),(.8,-5.9),(1.2,-4),(.8,-2),(.68,7),(.95,8),(0,8.5)],'brass',48)
made('SM_AlchemyPestle',pestle_new)
def stirrer():
    g.rod('Stirring shaft',(0,0,-22),(0,0,8),.52,'brass',32)
    rz('Oval paddle',(0,0,-22),[(0,-2),(2.6,-1.5),(3,0),(2.7,1.8),(0,2.1)],'brass',48)
    for z in (3,4,5,6):g.torus('Handle grip',(0,0,z),.58,.14,'wood',steps=32,tube=8)
made('SM_AlchemyStirrer',stirrer)
def dose():
    rz('Measuring vial',(0,0,-5),[(0,0),(2.7,0),(2.9,.4),(2.9,9),(1.5,11),(1.5,14),(1.1,14),(1.1,11),(2.55,8.8),(2.55,.6),(0,.6)],'glass',64)
    g.ring('Brass neck band',(0,0,7),1.7,1.5,.6,'brass',sides=48)
    for z in range(-2,5,2):g.torus('Volume mark',(0,0,z),2.92,.035,'brass',steps=48,tube=6)
made('SM_AlchemyDose',dose)
def book():
    g.box('Leather spine',(0,0,.4),(2.1,22,.8),'leather',.2)
    for sign in (-1,1):
        g.box('Open leather cover',(sign*8.5,0,.3),(16.9,22.3,.6),'leather',.2)
        g.box('Bound page block',(sign*8.5,0,1.1),(16.2,21.5,1),'pages',.15)
        for y in (-10,10):g.rod('Gilt cover edge',(sign*.7,y,.65),(sign*16.5,y,.65),.06,'brass',12)
        for z in (.8,1,1.2,1.4):g.rod('Page layers',(sign*16.65,-10.4,z),(sign*16.65,10.4,z),.025,'pages',8)
    g.box('Ribbon bookmark',(2,-10.8,1.7),(.65,6,.07),'redliquid',.02)
made('SM_AlchemyBook',book)
def page():
    g.box('Turning leaf',(-7.6,0,0),(15.2,20.5,.06),'pages',.015)
made('SM_AlchemyPage',page)
def sandglass():
    for z in (0,15):g.cylinder('Hourglass cap',(0,0,z),3.5,.7,'brass',sides=48)
    for a in (0,120,240):
        x,y=3*math.cos(math.radians(a)),3*math.sin(math.radians(a));g.rod('Hourglass rail',(x,y,0),(x,y,15),.18,'brass',16)
    rz('Hourglass vessel',(0,0,.4),[(0,0),(2.9,0),(2.7,3),(.25,7),(2.7,11),(2.9,14),(0,14)],'glass',48)
made('SM_AlchemyHourglass',sandglass)
def ladle():
    g.rod('Ladle long handle',(0,0,-19),(0,0,8),.52,'brass',32)
    rz('Ladle bowl',(0,0,-22),[(0,0),(2,0),(3.8,1.5),(4.2,3.6),(3.8,3.6),(3.3,1.7),(1.6,.4),(0,.4)],'brass',64)
    for z in (3,4,5,6):g.torus('Ladle grip',(0,0,z),.59,.14,'wood',steps=32,tube=8)
made('SM_AlchemyLadle',ladle)
made('SM_AlchemyStream',lambda:g.cylinder('Pouring stream',(0,0,.5),.22,1,'potion',sides=16,edge=0))
made('SM_AlchemySand',lambda:rz('Fine golden sand',(0,0,0),[(0,0),(2.5,0),(2,2),(.05,6),(0,6)],'pages',48))
made('SM_AlchemyDoseFill',lambda:g.cylinder('Vial liquid',(0,0,-1.8),2.48,5.2,'potion',sides=48,edge=.05))
# Keep the editable authoring scene, with runtime pieces in their own collections.
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authored/PotionWorkbench_Runtime.blend'))
(ROOT/'runtime_manifest.json').write_text(json.dumps({'parts':parts,'units':'cm','source':'ModelV1/Authored/PotionWorkbench_Editable.blend','rendered':False},indent=2),'utf8')
print('ALCHEMY_RUNTIME_EXPORTED',len(parts),flush=True)
