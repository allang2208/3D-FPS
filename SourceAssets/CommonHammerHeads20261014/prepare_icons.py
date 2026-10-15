"""Reuse the existing actual-mesh icon studio and frame for shared hammer heads."""
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[1]
source=(ROOT/'SourceAssets/SteelWarhammer20261014/ModulesV1/author_icons.py').read_text(encoding='utf-8')
source=source.replace('ROOT=P.parents[2]','ROOT=P.parents[1]').replace('Warhammer_Modular_Editable.blend','CommonHammerHeads_Editable.blend')
source=source.replace("surface=modules[0].data.materials[0]\nbs=", "surface=modules[0].data.materials[0]\nbs=")
start=source.index('surface=modules[0].data.materials[0]');end=source.index('\ndef metal(',start)
source=source[:start]+'''for surface in {m for obj in modules for m in obj.data.materials}:
    bs=next(n for n in surface.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    link=next((link for link in surface.node_tree.links if link.to_socket==bs.inputs['Base Color']),None)
    if link:
        gray=surface.node_tree.nodes.new('ShaderNodeRGBToBW');surface.node_tree.links.new(link.from_socket,gray.inputs[0]);surface.node_tree.links.new(gray.outputs[0],bs.inputs['Base Color'])
''' + source[end:]
source=source.replace("row['slot']","row['id']").replace("r['slot']","r['id']")
source=source.replace("('ue_steel_warhammer_category_'+row['id'],'ue_steel_warhammer_'+row['id']+'_false')","('hammer_heads_'+row['id'],)")
source=source.replace('Warhammer_PartIcons_Editable.blend','CommonHammerHeads_Icons_Editable.blend')
(P/'author_icons.py').write_text(source,encoding='utf-8')
