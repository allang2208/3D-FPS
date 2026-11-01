"""Build the two M24 lens graphs with a connected OneMinus input."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).resolve().parent;ROOT='/Game/Weapons/M24/Repair20261027'
T='/Game/Weapons/M24/CustomScope20261026/Textures/'
def rebuild(mat,key):
    L=u.MaterialEditingLibrary
    L.delete_all_material_expressions(mat)
    def sample(suffix,kind,y):
        node=L.create_material_expression(mat,u.MaterialExpressionTextureSample,-500,y)
        node.texture=u.load_asset(T+'T_'+key+'_'+suffix)
        node.sampler_type=kind
        return node
    color=sample('BC',u.MaterialSamplerType.SAMPLERTYPE_COLOR,0)
    orm=sample('ORM',u.MaterialSamplerType.SAMPLERTYPE_MASKS,200)
    normal=sample('N',u.MaterialSamplerType.SAMPLERTYPE_NORMAL,400)
    trans=sample('Transmission',u.MaterialSamplerType.SAMPLERTYPE_MASKS,600)
    for node,ch,prop in [(color,'RGB',u.MaterialProperty.MP_BASE_COLOR),
        (orm,'R',u.MaterialProperty.MP_AMBIENT_OCCLUSION),(orm,'G',u.MaterialProperty.MP_ROUGHNESS),
        (orm,'B',u.MaterialProperty.MP_METALLIC),(normal,'RGB',u.MaterialProperty.MP_NORMAL)]:
        assert L.connect_material_property(node,ch,prop)
    inverse=L.create_material_expression(mat,u.MaterialExpressionOneMinus,-250,600)
    # OneMinus exposes its only pin with no name; 'Input' does not resolve.
    assert L.connect_material_expressions(trans,'R',inverse,'')
    coverage=L.create_material_expression(mat,u.MaterialExpressionMultiply,-100,500)
    assert L.connect_material_expressions(inverse,'',coverage,'A')
    assert L.connect_material_expressions(color,'A',coverage,'B')
    minimum=L.create_material_expression(mat,u.MaterialExpressionMax,50,500)
    minimum.set_editor_property('const_b',.06)
    assert L.connect_material_expressions(coverage,'',minimum,'A')
    assert L.connect_material_property(minimum,'',u.MaterialProperty.MP_OPACITY)
    mat.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
    L.recompile_material(mat)
if __name__=='__main__':
    saved=[]
    for key in ('M24_ScopeGlass','M24_TopGlass'):
        mat=u.load_asset(ROOT+'/Materials/M_'+key+'_Static')
        rebuild(mat,key)
        assert u.EditorAssetLibrary.save_loaded_asset(mat,False)
        saved.append(mat.get_path_name())
    (O/'glass_receipt.json').write_text(json.dumps({'saved':saved,'complete':True},indent=2),encoding='utf-8')
    print('M24_LENS_INPUTS_REPAIRED',saved,flush=True)
