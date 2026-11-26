"""Author the mesh-compatible Sensei road surface in the isolated publishing host."""
from pathlib import Path
import os
import runpy
import unreal as u

ed = u.MaterialEditingLibrary
lib = u.EditorAssetLibrary
out = '/Game/WorldGeneration/TemperateHills/EastRiverRoad'
fab = Path(os.environ['EAST_ROAD_FAB'])
study = '/Game/ForestPathStudy/Materials'
grass = '/Game/PN_GrassLibrary/Textures/LandscapeTextures/ground_I_'
lib.make_directory(out)

def load(path):
    obj = u.load_asset(path)
    if not obj:
        raise RuntimeError(path)
    return obj

def duplicate(src, name):
    path = out + '/' + name
    return load(path) if lib.does_asset_exist(path) else lib.duplicate_asset(src, path)

def save(obj):
    if not lib.save_loaded_asset(obj, False):
        raise RuntimeError(obj.get_path_name())

def scan_texture(group, suffix):
    name = 'T_' + group + '_' + suffix
    path = out + '/' + name
    if not lib.does_asset_exist(path):
        task = u.AssetImportTask()
        task.filename = str(next((fab / group).glob('*_2K_' + suffix + '.*')))
        task.destination_path, task.destination_name = out, name
        task.automated, task.save = True, False
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    texture = load(path)
    texture.set_editor_property('srgb', False)
    texture.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_MASKS)
    save(texture)
    return texture

base = duplicate('/Game/Landscape/Materials/M_Landscape_Height', 'M_EastRoad_Sensei')
nodes = {n.get_name(): n for n in ed.get_material_expressions(base)}

def expr(cls, x, y):
    return ed.create_material_expression(base, cls, x, y)

def wire(a, pin, b, target):
    if not ed.connect_material_expressions(a, pin, b, target):
        raise RuntimeError(f'{a.get_name()}.{pin} to {b.get_name()}.{target}')

# Keep the author's texture projection, near/far sampling, macro colour and normal chain.
# Streamed terrain provides its paint weights through UV4 instead of Landscape weightmaps.
paint = expr(u.MaterialExpressionTextureCoordinate, -3000, 2300)
paint.set_editor_property('coordinate_index', 4)
def painted(channel, reroute, y):
    mask = expr(u.MaterialExpressionComponentMask, -2750, y)
    for prop in ('r','g','b','a'):
        mask.set_editor_property(prop, prop == channel)
    wire(paint, '', mask, '')
    detail = expr(u.MaterialExpressionCustom, -2300, y)
    detail.set_editor_property('description', 'Feather scanned relief at painted edge')
    detail.set_editor_property('output_type', u.CustomMaterialOutputType.CMOT_FLOAT1)
    detail.set_editor_property('code', 'return saturate(W + (saturate(H)-0.5)*0.72*4.0*W*(1.0-W));')
    inputs = []
    for name in ('W','H'):
        item = u.CustomInput()
        item.set_editor_property('input_name', name)
        inputs.append(item)
    detail.set_editor_property('inputs', inputs)
    wire(mask, '', detail, 'W')
    wire(nodes[reroute], '', detail, 'H')
    return detail

layers = nodes['MaterialExpressionLandscapeLayerBlend_0']
pins = ed.get_inputs_for_material_expression(base, layers)
# Vendor layer blend inputs are Auto, then attribute/height pairs A through E.
def blend(a, b, weight, y):
    obj = expr(u.MaterialExpressionBlendMaterialAttributes, -1800, y)
    wire(a,'',obj,'A')
    wire(b,'',obj,'B')
    wire(weight,'',obj,'Alpha')
    return obj
# A = moss (the approved forest instance), B = current hills grass, C = roots/dirt.
verge = blend(pins[3], pins[1], painted('g',pins[2].get_name(),2300), 2350)
road = blend(verge, pins[5], painted('r',pins[6].get_name(),2540), 2550)
wire(road,'',nodes['MaterialExpressionBreakMaterialAttributes_0'],'Attr' if 'Attr' in ed.get_material_expression_input_names(nodes['MaterialExpressionBreakMaterialAttributes_0']) else ed.get_material_expression_input_names(nodes['MaterialExpressionBreakMaterialAttributes_0'])[0])
# Macro normal/colour already feed the master's final MakeMaterialAttributes.
# Bypass landscape-only grass and displacement outputs for the streamed triangle mesh.
result = nodes['MaterialExpressionMakeMaterialAttributes_0']
depth = expr(u.MaterialExpressionCustom, -900, 2800)
depth.set_editor_property('description','Sub-centimetre road relief within 12 metres')
depth.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT1)
depth.set_editor_property('code','float h=lerp(lerp(G,M,saturate(W.y)),D,saturate(W.x)); return (1-saturate(h))*0.8*(1-smoothstep(350,1200,Z));')
args=[]
for name in ['G','M','D','W','Z']:
    arg=u.CustomInput()
    arg.set_editor_property('input_name',name)
    args.append(arg)
depth.set_editor_property('inputs',args)
for name,node in [('G',pins[4]),('M',pins[2]),('D',pins[6]),('W',paint),('Z',expr(u.MaterialExpressionPixelDepth,-1500,3000))]:
    wire(node,'',depth,name)
pdo=next(pin for pin in ed.get_material_expression_input_names(result) if str(pin).replace(' ','').lower()=='pixeldepthoffset')
wire(depth,'',result,pdo)
base.set_editor_property('use_material_attributes', True)
if not ed.connect_material_property(result, '', u.MaterialProperty.MP_MATERIAL_ATTRIBUTES):
    raise RuntimeError('Sensei final material attributes')
wild_grass='/Game/ForestPathStudy/VillageRegion/WildGrass/MF_HillsWildGrass'
if lib.does_asset_exist(wild_grass):
    recipe=Path(__file__).resolve().parents[1]/'ForestVillage'/'author_wild_grass.py'
    runpy.run_path(str(recipe))['mesh_surface'](base,load(wild_grass),verge,depth)
ed.recompile_material(base)
save(base)
mi = duplicate(study + '/MI_ForestPathForest', 'MI_EastRiverRoad')
ed.set_material_instance_parent(mi, base)
def tex(param,obj):
    # UE 5.8's setter always returns false, including after a successful write.
    ed.set_material_instance_texture_parameter_value(mi,param,obj)
for group,layer,relief in [('NordicMoss','A','Bump'),('NordicForestGroundRootsCoarse','C','Displacement')]:
    for key,suffix in [('Color','BaseColor'),('Normal','Normal')]:
        tex(key+' '+layer,load(study+'/T_'+group+'_'+suffix))
    tex('Roughness '+layer,scan_texture(group,'Roughness'))
    tex('Height '+layer,scan_texture(group,relief))
    tex('Ambient Occlusion '+layer,scan_texture(group,'AO'))
for key,suffix in [('Color','albedo'),('Normal','normal'),('Height','height'),('Ambient Occlusion','ao')]:
    tex(key+' B',load(grass+suffix))
for key,val in {'Size A':0.5,'Size B':0.18,'Size C':0.33,'Normal Strength A':0.65,'Normal Strength B':0.72,'Normal Strength C':0.9}.items():
    ed.set_material_instance_scalar_parameter_value(mi,key,val)
for layer in 'ABC':
    for key,val in [('Mask?',False),('Use Ambient Occlusion?',True)]:
        ed.set_material_instance_static_switch_parameter_value(mi,key+' '+layer,val)
ed.update_material_instance(mi)
save(mi)
