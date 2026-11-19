"""Complete the three close-up material graphs for the desktop skeletal shader path."""
from pathlib import Path
import json
import unreal as u
root='/Game/Characters/VillageBlacksmithNPC20261118/'
api=u.MaterialEditingLibrary
properties=u.MaterialProperty
out=Path(__file__).resolve().parents[3]/'SourceAssets/VillageBlacksmithNPC20261118/FinishR2/Review'
def connect(a,channel,b,pin=''):
    if not api.connect_material_expressions(a,channel,b,pin):raise ValueError('Cannot connect '+str(a)+' to '+str(b)+': '+pin)
def output(a,pin):
    if not api.connect_material_property(a,'',pin):raise ValueError(str(pin))
def vertex_position(mat):
    existing=next((x for x in u.ObjectIterator(u.MaterialExpressionVertexInterpolator) if x.get_outer()==mat),None)
    if existing:return existing
    pre=api.create_material_expression(mat,u.MaterialExpressionPreSkinnedPosition)
    vertex=api.create_material_expression(mat,u.MaterialExpressionVertexInterpolator)
    connect(pre,'',vertex)
    return vertex
def skin_scatter(mat):
    bc=api.get_material_property_input_node(mat,properties.MP_BASE_COLOR)
    # Derive the scattering colour from the pigmented surface. Bright constant scatter makes dark hair and irises look like clay.
    tint=api.create_material_expression(mat,u.MaterialExpressionConstant3Vector)
    tint.set_editor_property('constant',u.LinearColor(.15,.085,.055,1))
    mul=api.create_material_expression(mat,u.MaterialExpressionMultiply)
    connect(bc,'RGB' if isinstance(bc,u.MaterialExpressionTextureSample) else '',mul,'A')
    connect(tint,'',mul,'B')
    output(mul,properties.MP_SUBSURFACE_COLOR)
results=[]
for tail in ['BodyOutfit/Materials/M_Smith_Apron','HeadParts/M_Smith_NativeNeck','HeadFinishR2/M_Smith_MeshyFace_R2']:
    mat=u.load_asset(root+tail)
    if not mat:raise ValueError(tail)
    if 'Apron' in tail or 'Neck' in tail:
        v=vertex_position(mat)
        masks=[x for x in u.ObjectIterator(u.MaterialExpressionComponentMask) if x.get_outer()==mat]
        matches=len(masks)
        if matches!= (2 if 'Apron' in tail else 1):raise ValueError(f'{tail} geometry masks: {matches}')
        for mask in masks:
            use_z=bool(mask.get_editor_property('b')) or 'Neck' in tail
            for axis in 'rgba':mask.set_editor_property(axis,axis==('b' if use_z else 'r'))
            connect(v,'',mask)
    if 'Apron' not in tail:skin_scatter(mat)
    api.recompile_material(mat)
    if not u.EditorAssetLibrary.save_loaded_asset(mat,False):raise ValueError(tail)
    results.append(tail)
(out/'studio_materials_saved.json').write_text(json.dumps(results,indent=2))
