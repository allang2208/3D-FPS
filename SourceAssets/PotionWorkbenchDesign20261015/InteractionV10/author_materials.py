"""Readable dispensing liquid and vessel contents. Isolated host, no runtime test."""
from pathlib import Path
import json
import unreal as u
ROOT=Path(__file__).resolve().parent
if Path(u.Paths.project_dir()).resolve()!=(ROOT/'UEImportHost').resolve(): raise RuntimeError('Wrong import host')
DEST='/Game/Building/PotionWorkbench20261015/InteractionV10'
A=u.AssetToolsHelpers.get_asset_tools(); E=u.EditorAssetLibrary; M=u.MaterialEditingLibrary
report={'stage':'authoring','packages':[],'runtime_tested':False}
def node(mat,kind,**props):
    n=M.create_material_expression(mat,kind)
    for k,v in props.items(): n.set_editor_property(k,v)
    return n
def wire(a,b,pin):
    if not M.connect_material_expressions(a,'',b,pin): raise RuntimeError('Cannot connect '+pin)
def prop(n,p):
    if not M.connect_material_property(n,'',p): raise RuntimeError('Cannot connect material property')
for name,flow in [('M_AlchemyBottlingFlow',True),('M_AlchemyVesselLiquid',False)]:
    path=DEST+'/'+name
    if E.does_asset_exist(path):
        mat=u.load_asset(path)
        if E.get_metadata_tag(mat,'Alchemy.Owner')!='InteractionV10': raise RuntimeError('Unowned '+path)
        M.delete_all_material_expressions(mat)
    else: mat=A.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
    mat.set_editor_property('used_with_instanced_static_meshes',True)
    if flow:
        mat.set_editor_property('used_with_spline_meshes',True)
        mat.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
        mat.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
    # Vessel fill writes depth, which removes glass/contents translucency-sort
    # ambiguity. The existing bottle glass remains transparent and unchanged.
    color=node(mat,u.MaterialExpressionVectorParameter,parameter_name='PotionColor',default_value=u.LinearColor(.16,.42,.22,1))
    prop(color,u.MaterialProperty.MP_BASE_COLOR)
    prop(node(mat,u.MaterialExpressionConstant,r=.12 if flow else .18),u.MaterialProperty.MP_ROUGHNESS)
    prop(node(mat,u.MaterialExpressionConstant,r=.65),u.MaterialProperty.MP_SPECULAR)
    glow=node(mat,u.MaterialExpressionMultiply,const_b=.14 if flow else .08); wire(color,glow,'A')
    prop(glow,u.MaterialProperty.MP_EMISSIVE_COLOR)
    if flow:
        rim=node(mat,u.MaterialExpressionFresnel,exponent=3.0,base_reflect_fraction=.08)
        edge=node(mat,u.MaterialExpressionMultiply,const_b=.18); wire(rim,edge,'A')
        opacity=node(mat,u.MaterialExpressionAdd,const_b=.7); wire(edge,opacity,'A')
        prop(opacity,u.MaterialProperty.MP_OPACITY)
    M.recompile_material(mat)
    E.set_metadata_tag(mat,'Alchemy.Owner','InteractionV10')
    if not E.save_loaded_asset(mat,False): raise RuntimeError('Save failed '+path)
    report['packages'].append(mat.get_path_name())
    (ROOT/'import-receipt.json').write_text(json.dumps(report,indent=2),'utf8')
report['stage']='assets_saved'
(ROOT/'import-receipt.json').write_text(json.dumps(report,indent=2),'utf8')
u.log('ALCHEMY_INTERACTION_V10_ASSETS_SAVED')
