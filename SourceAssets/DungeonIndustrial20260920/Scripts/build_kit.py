"""Author Industrial V1 assets in the live editor through the queued bridge.

This builds assets only. No PIE, screenshots, render checks or asset-wide saves.
All output is revision-scoped; the source packs are referenced, never edited.
"""
import json
import math
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/DungeonIndustrial20260920')
OUT = '/Game/Dungeons/IndustrialV1'
MS = u.ModelingService
EAL = u.EditorAssetLibrary
LIB = u.MaterialEditingLibrary
AT = u.AssetToolsHelpers.get_asset_tools()
MATS = {}
RESULT = {'materials': {}, 'meshes': {}, 'stage': 'authoring', 'tests_run': False}


def receipt():
    (ROOT/'Receipts/kit-build.json').write_text(json.dumps(RESULT, indent=2), encoding='utf-8')


def save(asset):
    if not EAL.save_loaded_asset(asset, False):
        raise RuntimeError('Could not save ' + asset.get_path_name())


def ok(r):
    if not r.success:
        raise RuntimeError(r.message)
    return r


def node(m, cls):
    return LIB.create_material_expression(m, cls)


def wire(a, b, pin, out=''):
    if not LIB.connect_material_expressions(a, out, b, pin):
        raise RuntimeError('Material connection: ' + pin)


def output(a, name):
    if not LIB.connect_material_property(a, '', getattr(u.MaterialProperty, 'MP_' + name)):
        raise RuntimeError('Material output: ' + name)


def custom(m, code, inputs, width=3):
    n = node(m, u.MaterialExpressionCustom)
    n.set_editor_property('code', code)
    n.set_editor_property('output_type', getattr(u.CustomMaterialOutputType, 'CMOT_FLOAT' + str(width)))
    pins = []
    for k in inputs:
        pin = u.CustomInput()
        pin.set_editor_property('input_name', k)
        pins.append(pin)
    n.set_editor_property('inputs', pins)
    for k, v in inputs.items():
        wire(v, n, k)
    return n


def scalar(m, name, value):
    n = node(m, u.MaterialExpressionScalarParameter)
    n.set_editor_property('parameter_name', name)
    n.set_editor_property('default_value', value)
    return n


def sample(m, path, uv):
    t = u.load_asset(path)
    if not t:
        raise RuntimeError('Required texture missing: ' + path)
    n = node(m, u.MaterialExpressionTextureSample)
    n.set_editor_property('texture', t)
    compression = str(t.get_editor_property('compression_settings'))
    typ = 'SAMPLERTYPE_NORMAL' if 'NORMALMAP' in compression else (
        'SAMPLERTYPE_MASKS' if 'MASKS' in compression else (
        'SAMPLERTYPE_COLOR' if t.get_editor_property('srgb') else 'SAMPLERTYPE_LINEAR_COLOR'))
    n.set_editor_property('sampler_type', getattr(u.MaterialSamplerType, typ))
    wire(uv, n, 'UVs')
    return n


SURFACE = r'''
float2 uv = abs(N.z) > 0.65 ? P.xy : (abs(N.x) > abs(N.y) ? P.yz : P.xz);
float macro = saturate(G.r * .65 + G.g * .35);
float grain = frac(sin(dot(floor(uv * 2.5), float2(127.1,311.7))) * 43758.5453);
float pits = smoothstep(.94, .995, grain) * .16;
float joint = 0;
float chip = 0;
float3 c = float3(.24,.245,.23);
float rough = .81;
float metal = 0;
if (Kind < .5) {
    c *= lerp(.75,1.18,macro) * (1-pits);
    float board = smoothstep(.985,1,frac(uv.y/100));
    c *= 1-board*.18;
} else if (Kind < 1.5) {
    float2 t = uv/float2(30,15);
    t.x += fmod(floor(t.y),2)*.5;
    float2 f = frac(t);
    float2 e = min(f,1-f)*float2(30,15);
    joint = 1-smoothstep(.16,.33,min(e.x,e.y));
    float variation = frac(sin(dot(floor(t),float2(17.1,91.7)))*43758.5453);
    c = float3(.47,.45,.365) * lerp(.83,1.06,variation) * lerp(.74,1.0,macro);
    c = lerp(c,float3(.085,.09,.073),joint);
    rough = lerp(.34+.22*(1-macro),.89,joint);
} else if (Kind < 2.5) {
    chip = smoothstep(.68,.88,macro);
    c = lerp(float3(.105,.125,.081)*lerp(.65,1.12,G.g),float3(.16,.095,.045),chip);
    rough = lerp(.47,.82,chip);
    metal = lerp(.12,.6,chip);
} else if (Kind < 3.5) {
    c = float3(.07,.079,.078)*lerp(.65,1.2,macro);
    rough = .46+.22*(1-macro);
    metal = .85;
} else if (Kind < 4.5) {
    c = float3(.28,.25,.19)*lerp(.58,1.17,macro)*(1-pits);
    rough = .88;
} else if (Kind < 5.5) {
    c = float3(.13,.14,.13)*lerp(.72,1.17,macro)*(1-pits*.5);
    rough = .77;
} else {
    c = float3(.019,.027,.023)*lerp(.7,1.2,macro);
    rough = .10+.055*macro;
}
float bottom = (1-saturate(P.z/100)) * .18;
c *= 1-bottom;
'''


def surface(name, kind):
    path = OUT + '/Materials/M_' + name
    # A resumed authoring run uses already saved assets; it does not rewrite them.
    m = u.load_asset(path)
    if not m or EAL.get_metadata_tag(m, 'DungeonIndustrialV1') != 'complete':
        if not m:
            m = AT.create_asset('M_'+name, OUT+'/Materials', u.Material, u.MaterialFactoryNew())
        else:
            LIB.delete_all_material_expressions(m)
        m.set_editor_property('tangent_space_normal', False)
        p = node(m, u.MaterialExpressionWorldPosition)
        normal = node(m, u.MaterialExpressionVertexNormalWS)
        uv = custom(m, 'return (abs(N.z)>.65 ? P.xy : (abs(N.x)>abs(N.y) ? P.yz : P.xz))/240;', {'P':p,'N':normal}, 2)
        grain = sample(m, '/Game/UnrealNormandy/Textures/T_GrungeNoise_01A_Masks', uv)
        k = scalar(m, 'SurfaceKind', kind)
        inputs = {'P':p, 'N':normal, 'G':grain, 'Kind':k}
        output(custom(m, SURFACE+'return c;', inputs), 'BASE_COLOR')
        output(custom(m, SURFACE+'return rough;', inputs, 1), 'ROUGHNESS')
        output(custom(m, SURFACE+'return metal;', inputs, 1), 'METALLIC')
        detailuv = custom(m, 'return (abs(N.z)>.65 ? P.xy : (abs(N.x)>abs(N.y) ? P.yz : P.xz))/65;', {'P':p,'N':normal}, 2)
        detail = sample(m, '/Game/UnrealNormandy/Textures/T_StoneSurface_DetailNormal_00A', detailuv)
        strength = scalar(m, 'SurfaceRelief', .10 if kind in (1,2,3,6) else .26)
        normals = r'''
float3 T = abs(N.z)>.65 ? float3(1,0,0) : (abs(N.x)>abs(N.y) ? float3(0,1,0) : float3(1,0,0));
float3 B = normalize(cross(N,T));
return normalize(N + (D.x*T+D.y*B)*S);
'''
        output(custom(m, normals, {'N':normal,'D':detail,'S':strength}), 'NORMAL')
        LIB.layout_material_expressions(m)
        LIB.recompile_material(m)
        EAL.set_metadata_tag(m, 'DungeonIndustrialV1', 'complete')
        save(m)
    MATS[name] = path
    RESULT['materials'][name] = path


def emissive(name, color, strength):
    path = OUT+'/Materials/M_'+name
    m = u.load_asset(path)
    if not m:
        m = AT.create_asset('M_'+name, OUT+'/Materials', u.Material, u.MaterialFactoryNew())
        c = node(m, u.MaterialExpressionConstant3Vector)
        c.set_editor_property('constant', u.LinearColor(*color,1))
        output(c,'BASE_COLOR')
        output(custom(m, 'return C*Strength;', {'C':c,'Strength':scalar(m,'Emission',strength)}), 'EMISSIVE_COLOR')
        output(scalar(m,'Roughness',.45),'ROUGHNESS')
        LIB.recompile_material(m)
        save(m)
    MATS[name] = path
    RESULT['materials'][name] = path


def tr(loc=(0,0,0), rot=(0,0,0), scale=(1,1,1)):
    return u.Transform(location=u.Vector(*loc), rotation=u.Rotator(roll=rot[0],pitch=rot[1],yaw=rot[2]), scale=u.Vector(*scale))


def box(h, loc, size, material=0, rot=(0,0,0)):
    ok(MS.append_box(h,tr(loc,rot),*size,origin='Center',material_id=material))


def cyl(h, loc, radius, length, material=0, rot=(0,0,0), steps=24):
    ok(MS.append_cylinder(h,tr(loc,rot),radius,length,radial_steps=steps,origin='Center',material_id=material))


def torus(h, loc, radius, tube, material=0, rot=(0,0,0)):
    ok(MS.append_torus(h,tr(loc,rot),radius,tube,major_steps=32,minor_steps=8,origin='Center',material_id=material))


def mesh(name, material_names, build, bevel=0, collision=True):
    path = OUT+'/Meshes/SM_'+name
    if not EAL.does_asset_exist(path):
        h = ok(MS.create_mesh()).handle
        try:
            build(h)
            if bevel:
                ok(MS.bevel_polygroups(h,bevel,1))
            ok(MS.recompute_normals(h,55))
            ok(MS.project_uv(h,'Box',tr(scale=(200,200,200))))
            ok(MS.save_mesh_to_static_mesh(h,path,False,False,False,True))
            ok(MS.set_asset_materials(path,','.join(MATS[n] for n in material_names)))
            asset = u.load_asset(path)
            if collision:
                body = asset.get_editor_property('body_setup')
                body.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
                save(asset)
        finally:
            MS.release_mesh(h)
    RESULT['meshes'][name] = path
    receipt()


def wall(h, tile=True, door=False):
    if door:
        for x in (-150,150):
            box(h,(x,0,200),(100,20,400),0)
            if tile:
                box(h,(x,-10.8,85),(98,1.6,150),1)
                box(h,(x,10.8,85),(98,1.6,150),1)
        box(h,(0,0,340),(200,20,120),0)
        # Jamb trim is outside the 200 cm clear opening.
        for x in (-105,105):
            box(h,(x,0,140),(10,28,280),2)
        box(h,(0,0,285),(220,28,10),2)
    else:
        box(h,(0,0,200),(400,20,400),0)
        if tile:
            for y in (-10.8,10.8):
                box(h,(0,y,85),(399,1.6,150),1)
        for x in (-140,140):
            for z in (210,330):
                for y in (-10.15,10.15):
                    cyl(h,(x,y,z),1.3,.4,2,rot=(90,0,0),steps=12)
    if not door:
        for y in (-12,12):
            box(h,(0,y,10),(400,4,20),2)
            if tile:
                box(h,(0,y,162),(400,3,4),2)


def pipe(h):
    cyl(h,(200,0,0),18,400,0,rot=(0,90,0))
    for x in (12,388):
        cyl(h,(x,0,0),25,6,1,rot=(0,90,0))
        for n in range(8):
            a=n*math.tau/8
            cyl(h,(x,21*math.cos(a),21*math.sin(a)),2,9,1,rot=(0,90,0),steps=6)
    for x in (100,300):
        cyl(h,(x,0,0),20,5,1,rot=(0,90,0))
        box(h,(x,25,0),(10,40,7),1)


def pump(h):
    box(h,(0,0,12),(460,220,24),0)
    for x in (-140,80):
        box(h,(x,0,36),(100,125,24),2)
    # Motor, cooling rings, volute, flanged pressure delivery.
    cyl(h,(-105,0,91),48,180,1,rot=(0,90,0))
    for x in range(-180,-30,15):
        cyl(h,(x,0,91),51,3,2,rot=(0,90,0))
    cyl(h,(60,0,96),66,78,1,rot=(0,90,0))
    torus(h,(20,0,96),44,14,1,rot=(0,90,0))
    cyl(h,(95,0,145),22,125,1)
    cyl(h,(95,0,211),31,8,2)
    box(h,(-100,0,147),(70,62,32),1)
    for x in (-205,205):
        for y in (-88,88):
            cyl(h,(x,y,27),4,8,2,steps=6)


def valve(h):
    cyl(h,(0,0,0),22,48,0,rot=(0,90,0))
    cyl(h,(0,-35,0),6,60,1,rot=(90,0,0))
    torus(h,(0,-67,0),26,3,1,rot=(90,0,0))
    for a in (0,60,120):
        box(h,(0,-67,0),(48,4,4),1,rot=(0,a,0))


def luminaire(h):
    box(h,(0,0,0),(120,28,9),0)
    box(h,(0,0,-6),(106,20,4),1)
    for x in (-48,-24,0,24,48):
        box(h,(x,0,-9),(1.6,24,3),0)
    for x in (-46,46):
        box(h,(x,0,12),(4,8,18),0)


def stairs(h):
    for i in range(10):
        box(h,(17.5+i*35,0,10+i*20),(35,200,20),0)
        # Riser closes the tread from below; exact static triangle collision.
        box(h,(i*35+2,0,i*20),(4,200,20),0)
    for side in (-99,99):
        # Stringer follows the same rise/run, with feet connected to floor.
        box(h,(175,side,82),(403,6,14),1,rot=(0,29.745,0))
        box(h,(175,side,214),(403,5,5),1,rot=(0,29.745,0))
        for i in (0,3,6,9):
            box(h,(17.5+i*35,side,75+i*20),(5,5,110),1)


def arch(h):
    # Solid ancient portal framing an unobstructed 260 cm wide central recess.
    for side in (-1,1):
        for row in range(6):
            box(h,(side*169,0,row*38+19),(76,92,37),0)
    for i in range(13):
        a = (i+.5)*math.pi/13
        x,z = 169*math.cos(a),228+169*math.sin(a)
        box(h,(x,0,z),(40,92,76),0,rot=(0,math.degrees(a)-90,0))


def plinth(h):
    box(h,(0,0,12),(240,220,24),0)
    box(h,(0,0,33),(210,190,18),0)
    box(h,(0,0,68),(175,155,52),0)
    box(h,(0,0,97),(205,185,12),0)


def cabinet(h):
    box(h,(0,0,80),(95,42,160),0)
    box(h,(0,-22,90),(88,3,126),0)
    for x in (-24,0,24):
        box(h,(x,-24,133),(14,2,20),1)
    box(h,(30,-26,80),(4,6,16),1)
    for z in range(32,66,5):
        box(h,(-10,-24,z),(40,2,1.5),1)


def grate(h):
    for y in (-16,16):
        box(h,(200,y,0),(400,3,4),0)
    for x in range(4,399,8):
        box(h,(x,0,0),(3,30,3),0)


def rubble(h):
    import random
    rng = random.Random(20920)
    for i in range(20):
        x,y = rng.uniform(-100,100),rng.uniform(-55,55)
        z = rng.uniform(8,22)
        box(h,(x,y,z),(rng.uniform(12,48),rng.uniform(10,30),z*1.5),0,
            rot=(rng.uniform(-18,18),rng.uniform(-25,25),rng.uniform(-180,180)))
    for y in (-25,10,40):
        cyl(h,(0,y,20),1.3,170,1,rot=(0,80,y))


for name, kind in [('Concrete',0),('AgedCeramic',1),('OliveSteel',2),('DarkSteel',3),
                   ('AncientStone',4),('FloorConcrete',5),('WetConcrete',6)]:
    surface(name,kind)
emissive('CoolTube',(.72,.82,.88),3.2)
emissive('WarmTube',(1,.52,.16),3)
emissive('AnomalySeam',(.025,.32,.28),2.0)

mesh('Wall_Tiled_400',['Concrete','AgedCeramic','DarkSteel'],lambda h:wall(h),.35)
mesh('Wall_Concrete_400',['Concrete','AgedCeramic','DarkSteel'],lambda h:wall(h,False),.35)
mesh('DoorWall_200x280',['Concrete','AgedCeramic','DarkSteel'],lambda h:wall(h,True,True),.35)
mesh('Floor_400',['FloorConcrete'],lambda h:box(h,(0,0,-10),(400,400,20)))
mesh('Ceiling_400',['Concrete'],lambda h:box(h,(0,0,10),(400,400,20)))
mesh('CornerPier',['Concrete'],lambda h:box(h,(0,0,200),(32,32,400)),.6)
mesh('Pipe_Flanged_400',['OliveSteel','DarkSteel'],pipe)
mesh('ValveWheel',['OliveSteel','DarkSteel'],valve)
mesh('PumpIsland',['Concrete','OliveSteel','DarkSteel'],pump,.6)
mesh('CeilingLamp_Cool',['DarkSteel','CoolTube'],luminaire,.25,False)
mesh('CeilingLamp_Warm',['DarkSteel','WarmTube'],luminaire,.25,False)
mesh('StairFlight_Rise200',['DarkSteel','OliveSteel'],stairs,.18)
mesh('StairLanding',['DarkSteel'],lambda h:box(h,(70,0,-10),(140,200,20)))
mesh('AncientArch',['AncientStone'],arch,1.8)
mesh('EventPlinth',['AncientStone'],plinth,1.2)
mesh('ElectricalCabinet',['OliveSteel','DarkSteel'],cabinet,.4)
mesh('DrainGrate_400',['DarkSteel'],grate,.12,False)
mesh('BreachRubble',['Concrete','DarkSteel'],rubble,.6)
def backing(h):
    for row in range(5):
        for col in range(5):
            x=(col-2)*105+(12 if row%2 else -12)
            box(h,(x,0,34+row*65),(103,65,63),0,rot=(0,0,(col-row)%3-1))
mesh('BreachBacking',['AncientStone'],backing,1.5)
mesh('AnomalySeam',['AnomalySeam'],lambda h:box(h,(0,0,0),(1,4,155)),0,False)
# Thin non-colliding wet patch; the surface material keeps it locally reflective.
def wet_patch(h):
    ok(MS.append_cylinder(h,tr(scale=(1.65,.72,1)),85,.06,radial_steps=29,origin='Center',material_id=0))
mesh('WetPatch',['WetConcrete'],wet_patch,0,False)
RESULT['stage'] = 'assets_saved'
receipt()
print('DUNGEON_KIT_SAVED ' + json.dumps(RESULT))
