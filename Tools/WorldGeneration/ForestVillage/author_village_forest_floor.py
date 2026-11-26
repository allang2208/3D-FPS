"""Bind the baked Forest Floor pattern only to the village material permutation."""
import json
import sys
from pathlib import Path

import unreal as u

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import author_trail_cover_materials as art

LIB,ED=art.lib,art.ed
ROOT=HERE.parents[2]
NAME='T_VillageForestFloorPatches'
FOLDER=art.ref+'/VillageLoess'
SCAN='/Game/ForestPathStudy/VillageRegion/ForestFloor/T_ForestFloor_'
TAG='Village Forest Floor deposits'
OUTPUTS=(('BaseColor',''),('Normal','OutNormal'),('Roughness','OutRough'),('AmbientOcclusion','OutAO'))


def import_mask(folder):
    task=u.AssetImportTask()
    task.filename=str(folder/(NAME+'.png'))
    task.destination_name=NAME
    task.destination_path=FOLDER
    task.automated=task.replace_existing=True
    art.tools.import_asset_tasks([task])
    tex=next((o for o in task.get_objects() if isinstance(o,u.Texture2D) and o.get_name()==NAME),None)
    if not tex:raise RuntimeError('Could not import '+task.filename)
    tex.srgb=False
    tex.compression_settings=u.TextureCompressionSettings.TC_BC7
    tex.compression_no_alpha=False
    tex.address_x=tex.address_y=u.TextureAddress.TA_CLAMP
    tex.set_editor_property('never_stream',False)
    tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE)
    art.save(tex)
    return tex


def bind(master,mask):
    switch=ED.get_material_property_input_node(master,u.MaterialProperty.MP_MATERIAL_ATTRIBUTES)
    if not isinstance(switch,u.MaterialExpressionStaticSwitchParameter) or str(switch.get_editor_property('parameter_name'))!='Use original village mud roads':
        raise RuntimeError('Village road output switch missing on '+master.get_path_name())
    town=art.inputs(master,switch)['True']
    nodes=ED.get_material_expressions(master)
    existing=next((n for n in nodes if n.get_editor_property('desc')==TAG),None)
    code=HERE.joinpath('village_forest_floor.ush').read_text(encoding='utf8')
    if existing:
        # The existing loess builder may refresh its own textures on a later bake.
        # The accents stay downstream of the original mud, gravel and loess.
        existing.set_editor_property('code',code)
        art.inputs(master,existing)['Patch'].set_editor_property('texture',mask)
        return
    old=art.inputs(master,town)
    pins={}
    if not all(isinstance(old[prop],u.MaterialExpressionLinearInterpolate) for prop,_ in OUTPUTS):
        raise RuntimeError('Unexpected source channels on the town material')
    loess=next(n for n in nodes if n.get_editor_property('desc')=='R32 village loess')
    inputs=art.inputs(master,loess)
    for name in ('P','V','Eye','Wet'):
        pins[name]=(inputs[name],'')
    pose=next(n for n in nodes if isinstance(n,u.MaterialExpressionVectorParameter) and str(n.get_editor_property('parameter_name'))=='VillageRoadPose')
    pins.update(Pose=(pose,''),SinYaw=(pose,'A'),Patch=(art.object_node(master,mask,'LINEAR_COLOR'),''))
    span=art.node(master,u.MaterialExpressionConstant2Vector)
    layout=json.loads((ROOT/'SourceAssets/TemperateHillsVillage/layout.json').read_text(encoding='utf8'))
    ex,ey=layout['surface_extent_m']
    span.set_editor_property('r',2*ex*100.)
    span.set_editor_property('g',2*ey*100.)
    pins['Span']=(span,'')
    for name,suffix,kind in [('FloorC','Color','COLOR'),('FloorN','Normal','NORMAL'),('FloorARH','ARH','MASKS')]:
        texture=art.asset(SCAN+suffix)
        if not texture:raise RuntimeError(SCAN+suffix)
        pins[name]=(art.object_node(master,texture,kind),'')
    shader=art.custom(master,code,pins,TAG,[('OutNormal',3),('OutRough',1),('OutAO',1),('Coverage',1)])
    for prop,outpin in OUTPUTS:
        mix=art.node(master,u.MaterialExpressionLinearInterpolate)
        art.wire(old[prop],'',mix,'A')
        art.wire(shader,outpin,mix,'B')
        art.wire(shader,'Coverage',mix,'Alpha')
        art.wire(mix,'',town,prop)


def install():
    instance=art.asset(art.ref+'/MI_ForestVillageMudRoad')
    if not ED.get_material_instance_static_switch_parameter_value(instance,'Use original village mud roads'):
        raise RuntimeError('The loaded town surface does not use the village permutation')
    mask=import_mask(art.src)
    master=instance.get_base_material()
    bind(master,mask)
    art.compile_mat(master)
    return [mask.get_path_name(),master.get_path_name()]

