"""Apply a tabletop-local wear map only to the round table's oiled oak slot."""
from pathlib import Path
import json
import unreal as u


here = Path(__file__).resolve().parent
src = here.parents[3] / 'SourceAssets/HillsVillageTavern/Furniture/T_TavernTableWear.png'
folder = '/Game/WorldGeneration/VillageTavern/Furniture'
assets = u.EditorAssetLibrary
graph = u.MaterialEditingLibrary
task = u.AssetImportTask()
task.filename, task.destination_path, task.destination_name = str(src),folder,src.stem
task.automated, task.replace_existing = True,True
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
if not task.get_objects():
    raise RuntimeError('Cannot import table wear mask')
tex = assets.load_asset(folder+'/'+src.stem)
tex.set_editor_property('srgb',False)
tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
tex.set_editor_property('address_x',u.TextureAddress.TA_CLAMP)
tex.set_editor_property('address_y',u.TextureAddress.TA_CLAMP)

mat_path = folder+'/M_TavernDiningOak'
if not assets.does_asset_exist(mat_path):
    mat = assets.duplicate_asset(folder+'/M_TavernOiledOak',mat_path)
    if not mat:
        raise RuntimeError('Cannot duplicate the existing table finish')
    def node(kind, x, y):
        return graph.create_material_expression(mat,getattr(u,'MaterialExpression'+kind),x,y)
    def wire(source, channel, target, pin):
        if not graph.connect_material_expressions(source,channel,target,pin):
            raise RuntimeError('Cannot wire '+pin)
    def output(source, prop):
        if not graph.connect_material_property(source,'',prop):
            raise RuntimeError('Cannot wire '+str(prop))
    base = u.MaterialProperty.MP_BASE_COLOR
    rough = u.MaterialProperty.MP_ROUGHNESS
    old_base = graph.get_material_property_input_node(mat,base)
    old_rough = graph.get_material_property_input_node(mat,rough)

    local = node('PreSkinnedPosition',-1250,650)
    interp = node('VertexInterpolator',-1030,650)
    wire(local,'',interp,'')
    xy = node('ComponentMask',-820,650)
    for channel in ('r','g','b','a'):
        xy.set_editor_property(channel,channel in ('r','g'))
    wire(interp,'',xy,'')
    scale = node('Multiply',-610,650)
    scale.set_editor_property('const_b',1./120.)
    wire(xy,'',scale,'A')
    uv = node('Add',-410,650)
    uv.set_editor_property('const_b',.5)
    wire(scale,'',uv,'A')
    wear = node('TextureSample',-170,590)
    wear.set_editor_property('texture',tex)
    wear.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    wire(uv,'',wear,'')

    # Top is at 76 cm. The eased edge fades the marks down to clean side and bottom faces.
    z = node('ComponentMask',-820,870)
    for channel in ('r','g','b','a'):
        z.set_editor_property(channel,channel=='b')
    wire(interp,'',z,'')
    gate = node('SmoothStep',-550,870)
    gate.set_editor_property('const_min',75.25)
    gate.set_editor_property('const_max',75.9)
    wire(z,'',gate,'Value')
    aged = node('Multiply',90,430)
    wire(old_base,'',aged,'A')
    wire(wear,'R',aged,'B')
    colour = node('LinearInterpolate',320,360)
    wire(old_base,'',colour,'A')
    wire(aged,'',colour,'B')
    wire(gate,'',colour,'Alpha')
    output(colour,base)
    bias = node('Subtract',80,720)
    bias.set_editor_property('const_b',.5)
    wire(wear,'G',bias,'A')
    strength = node('Multiply',290,750)
    wire(bias,'',strength,'A')
    wire(gate,'',strength,'B')
    finish = node('Add',480,670)
    wire(old_rough,'',finish,'A')
    wire(strength,'',finish,'B')
    output(finish,rough)
    graph.recompile_material(mat)
else:
    mat = assets.load_asset(mat_path)

table = assets.load_asset(folder+'/SM_TavernTable')
slot = next(i for i,s in enumerate(table.static_materials) if str(s.material_slot_name)=='OiledOak')
table.set_material(slot,mat)
saved = []
for obj in (tex,mat,table):
    if not assets.save_loaded_asset(obj,False):
        raise RuntimeError('Cannot save '+obj.get_path_name())
    saved.append(folder+'/'+obj.get_name())
host = Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
(host/'saved.json').write_text(json.dumps(saved),encoding='utf8')
u.log('TAVERN_DINING_FINISH_SAVED')
