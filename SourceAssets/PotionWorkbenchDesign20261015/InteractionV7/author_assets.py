"""Derive open reagent bodies/caps from accepted sources and author physical controls. No render."""
from pathlib import Path
import bpy,sys,json,math,importlib.util
from mathutils import Vector,Matrix
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[2]
(HERE/'Export').mkdir(exist_ok=True);(HERE/'Authored').mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
rows=[];reagents=[]

def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def export(name,objects,shift=Vector((0,0,0)),uv_helper=None,material_root=''):
    deps=bpy.context.evaluated_depsgraph_get();copies=[]
    for obj in objects:
        if obj.type not in ('MESH','CURVE','FONT'):continue
        mesh=bpy.data.meshes.new_from_object(obj.evaluated_get(deps),preserve_all_data_layers=True,depsgraph=deps)
        dup=bpy.data.objects.new(name+'_part',mesh);bpy.context.scene.collection.objects.link(dup)
        dup.matrix_world=obj.matrix_world.copy()
        if uv_helper and not obj.get('authored_decal'):uv_helper.uv(dup,obj['surface_region'])
        dup.data.transform(Matrix.Translation(shift)@dup.matrix_world);dup.matrix_world=Matrix.Identity(4);copies.append(dup)
    if not copies:raise RuntimeError('Empty export '+name)
    bpy.ops.object.select_all(action='DESELECT')
    for dup in copies:dup.select_set(True)
    bpy.context.view_layer.objects.active=copies[0];bpy.ops.object.join();merged=bpy.context.object;merged.name=name
    bpy.context.scene.unit_settings.scale_length=.01
    bpy.ops.export_scene.fbx(filepath=str(HERE/'Export'/f'{name}.fbx'),use_selection=True,object_types={'MESH'},
        global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',axis_forward='-Y',axis_up='Z',
        bake_space_transform=True,mesh_smooth_type='FACE',use_tspace=True,bake_anim=False,path_mode='STRIP')
    slots={m.name:material_root+'/'+m.name for m in merged.data.materials}
    points=[v.co for v in merged.data.vertices]
    low=[min(p[i] for p in points) for i in range(3)];high=[max(p[i] for p in points) for i in range(3)]
    rows.append(dict(name=name,source=str(HERE/'Export'/f'{name}.fbx'),materials=slots,
        bounds_ue_cm=[[low[0],-high[1],low[2]],[high[0],-low[1],high[2]]],vertices=len(points)))
    return merged

materials=PROJECT/'SourceAssets/AlchemyMaterials20261015'
specs=[('BaseFluid','SM_Alchemy_PureBaseFluid',materials,11.58,('closure','cap top','tamper','tear band')),
       ('RedRoot','SM_Alchemy_RedveinExtract',materials,9.15,('pipette','dropper stem','tamper','tear band')),
       ('BlueFungus','SM_Alchemy_BluemarrowCrystals',materials/'VisualRefineV4',5.55,('jar lid','closure','top printed','tamper','tear band')),
       ('Catalyst','SM_Alchemy_ActiveCatalyst',materials/'VisualRefineV4',5.65,('closure','cap insert','embossed catalyst code'))]
for key,name,folder,mouth_z,cap_words in specs:
    bpy.ops.wm.open_mainfile(filepath=str(folder/'Authored'/f'{name}_Source.blend'),load_ui=False,use_scripts=False)
    H=module(folder/'Scripts/geometry.py','reagent_'+key)
    source=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.get('surface_region')]
    caps=[o for o in source if any(word in o.name.lower() for word in cap_words)]
    body=[o for o in source if o not in caps]
    points=[o.matrix_world@v.co for o in source for v in o.data.vertices]
    lo=Vector([min(p[i] for p in points) for i in range(3)]);hi=Vector([max(p[i] for p in points) for i in range(3)])
    shift=Vector((-(lo.x+hi.x)/2,-(lo.y+hi.y)/2,-lo.z))
    base='/Game/Items/AlchemyMaterials20261015/'+('V4' if 'VisualRefineV4' in str(folder) else 'V3')+'/Materials'
    export('SM_Alchemy'+key+'Open',body,shift,H,base);export('SM_Alchemy'+key+'Cap',caps,shift,H,base)
    reagents.append(dict(key=key,mouth=[0,0,mouth_z-lo.z],height=hi.z-lo.z,cap_parts=[o.name for o in caps]))
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'Authored'/f'{key}_Parts.blend'))

base=HERE.parent/'ModelV1';bpy.ops.wm.open_mainfile(filepath=str(base/'Authored/PotionWorkbench_Editable.blend'),load_ui=False,use_scripts=False)
G=module(base/'Scripts/geometry.py','bench_geometry');G.MATS['atlas']=bpy.data.materials['PW_SurfaceAtlas'];G.PARTS=[]
mortar=[o for o in bpy.context.scene.objects if o.name=='Weighing mortar']
export('SM_AlchemyMortarHover',mortar,Vector((-45,-50,-95)),material_root='/Game/Building/PotionWorkbench20261015/V1/Materials')
for row in rows[-1:]:row['materials']={k:'/Game/Building/PotionWorkbench20261015/V1/Materials/M_'+k for k in row['materials']}

def bench_export(name,parts):
    ob=export(name,parts,material_root='/Game/Building/PotionWorkbench20261015/V1/Materials')
    rows[-1]['materials']={k:'/Game/Building/PotionWorkbench20261015/V1/Materials/M_'+k for k in rows[-1]['materials']}
    return ob

G.group('HeatControl');G.PARTS=[]
G.box('heater control enamel body',(0,0,1.1),(17,15,2.2),'green',.7)
G.box('brass control rim',(0,0,2.3),(16.2,14.2,.25),'brass',.45)
G.box('dark enamel dial plate',(0,0,2.48),(15.7,13.7,.12),'iron',.4)
for i in range(4):
    a=math.radians(-135+90*i)
    G.rod('heat detent '+str(i),(4.6*math.cos(a),4.6*math.sin(a),2.63),(5.5*math.cos(a),5.5*math.sin(a),2.63),.12,'brass',10)
    for k in range(i+1):G.cylinder('heat dot',(6.1*math.cos(a)+(k-i/2)*.4,6.1*math.sin(a),2.65),.13,.05,'brass',sides=12)
bench_export('SM_AlchemyHeatControl',G.PARTS)
G.group('HeatKnob');G.PARTS=[]
G.cylinder('knurled heat knob',(0,0,1.1),2.8,2.2,'rubber',sides=64,edge=.13)
G.cylinder('brass knob cap',(0,0,2.2),2.66,.18,'brass',sides=64,edge=.06)
for i in range(36):
    a=i*math.tau/36;G.rod('knob flute',(2.8*math.cos(a),2.8*math.sin(a),.35),(2.8*math.cos(a),2.8*math.sin(a),1.9),.065,'steel',6)
G.box('pointer',(0,-1.8,2.34),(.24,1.6,.10),'white',.035)
bench_export('SM_AlchemyHeatKnob',G.PARTS)
G.group('ReagentTray');G.PARTS=[]
G.box('preparation tray',(80,46,94.65),(35,36,.44),'brass',.6)
G.box('non slip ceramic inset',(80,46,94.93),(33.5,34.5,.15),'ceramic',.4)
for x,y in ((70,38),(86,38),(79,58)):G.torus('material seat',(x,y,95.01),4.65,.07,'bronze',steps=64,tube=6)
bench_export('SM_AlchemyReagentTray',G.PARTS)
G.group('ImpactRing');G.PARTS=[];G.torus('meniscus ring',(0,0,0),1,.07,'potion',steps=48,tube=6)
G.MATS['potion']=bpy.data.materials.get('PW_potion') or G.MATS['atlas']
bench_export('SM_AlchemyTransferRing',G.PARTS)
G.group('Grain');G.PARTS=[];G.cylinder('falling crystal',(0,0,0),.12,.3,'brass',sides=6,edge=.025)
bench_export('SM_AlchemyTransferGrain',G.PARTS)
bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'Authored/Controls_and_Transfer.blend'))
(HERE/'asset-manifest.json').write_text(json.dumps(dict(meshes=rows,reagents=reagents,rendered=False),ensure_ascii=False,indent=2),encoding='utf-8')
print('ALCHEMY_V7_AUTHORED '+str(len(rows)),flush=True)
