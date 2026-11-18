"""Perimeter-owned copies of chapel stone with a short, irregular soil contact edge."""
import runpy
from pathlib import Path
import unreal as u

L=u.MaterialEditingLibrary
E=u.EditorAssetLibrary
TAG='VillagePerimeterRoot20261117'
SOURCE_TAG='HillsLocalRVT20261114'
ROOT=Path(__file__).resolve().parents[3]
ground=runpy.run_path(str(ROOT/'Tools/WorldGeneration/temperate_ground_cache.py'))
receiver=ground['receiver']
# Reuse the established RVT graph builder, but publish only perimeter-owned copies.
# The COLOR/HEIGHT RVT references retain their original village surface caches.
receiver.__globals__['BASE']='/Game/WorldGeneration/TemperateHills/VillagePerimeter/Materials'
BLEND='''float d=P.z-H;
float rag=sin(P.x*.173+sin(P.y*.119)*1.7)*1.6;
float edge=6.0+rag;
float soil=.32+.10*sin(P.x*.113+P.y*.157);
return soil*(1.0-smoothstep(.5,edge,d))*smoothstep(-12.0,-2.0,d);'''


def contact_material(source,cache):
    obj=receiver(source,cache)
    if isinstance(obj,u.MaterialInstanceConstant):
        finish_graph(obj.get_editor_property('parent'))
    else:
        finish_graph(obj)
    return obj


def finish_graph(obj):
    if isinstance(obj,u.MaterialInstanceConstant):
        finish_graph(obj.get_editor_property('parent'));return
    nodes=list(L.get_material_expressions(obj))
    if any(n.get_editor_property('desc')==TAG for n in nodes):return
    for n in nodes:
        if isinstance(n,u.MaterialExpressionCustom) and n.get_editor_property('desc')==SOURCE_TAG and 'float d=P.z-H;' in n.get_editor_property('code'):
            n.set_editor_property('code',BLEND)
        if isinstance(n,u.MaterialExpressionLinearInterpolate) and n.get_editor_property('desc')==SOURCE_TAG:
            inputs=dict(zip(map(str,L.get_material_expression_input_names(n)),L.get_inputs_for_material_expression(obj,n)))
            if isinstance(inputs.get('B'),u.MaterialExpressionTransform) and isinstance(inputs.get('Alpha'),u.MaterialExpressionVirtualTextureFeatureSwitch):
                reduced=L.create_material_expression(obj,u.MaterialExpressionMultiply)
                reduced.set_editor_property('desc',TAG);reduced.set_editor_property('const_b',.25)
                if not L.connect_material_expressions(inputs['Alpha'],'',reduced,'A') or not L.connect_material_expressions(reduced,'',n,'Alpha'):
                    raise RuntimeError('Perimeter soil normal wiring failed')
    L.recompile_material(obj)
    E.set_metadata_tag(obj,'VillagePerimeterOwner','HillsVillagePerimeter20261117')
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Perimeter contact material save failed')
