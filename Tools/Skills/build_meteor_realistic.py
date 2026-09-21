"""Use the installed Rural Australia rock and its complete PBR material for meteor.

Run one stage per MCP batch: material, mesh. No scene edits or preview/test run.
"""
import json,re,sys
from pathlib import Path
import unreal as u

ROOT=Path(u.Paths.project_dir()).resolve()
OUT=ROOT/'SourceAssets/MeteorRealistic20260921'
DEST='/Game/Skills/FireMagic20260921/RealisticV3'
ROCK='/Game/RuralAustralia/StaticMeshes/Rocks/Rock_M_02'
sys.path.insert(0,str(ROOT/'Tools/Skills'))
from build_fireball_impact_realistic import custom,scalar
LIB=u.MaterialEditingLibrary

def save(asset):
    if not u.EditorAssetLibrary.save_loaded_asset(asset,False):raise RuntimeError('Cannot save '+asset.get_path_name())

def own(source,name):
    path=DEST+'/'+name
    dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if path in dirty:raise RuntimeError('Preserve unsaved target edits: '+path)
    a=u.load_asset(path) if u.EditorAssetLibrary.does_asset_exist(path) else u.EditorAssetLibrary.duplicate_asset(source,path)
    if not a:raise RuntimeError(source)
    return a

def link(a,out,b,inp):
    if not LIB.connect_material_expressions(a,out,b,inp):raise RuntimeError('Cannot connect '+out+' -> '+inp)

def material():
    parent=own('/Game/RuralAustralia/Presets/M_Nature_01','M_MeteorNaturalRock')
    # Keep the pack's detail normals, roughness, UVs and material functions intact.
    # Only tint the final BaseColor; no procedural tessellation, lava cells or glow.
    if not u.EditorAssetLibrary.get_metadata_tag(parent,'MeteorRealistic.Charred'):
        source=next(e for e in LIB.get_material_expressions(parent) if e.get_name()=='MaterialExpressionMaterialFunctionCall_4')
        unpack=LIB.create_material_expression(parent,u.MaterialExpressionBreakMaterialAttributes)
        pack=LIB.create_material_expression(parent,u.MaterialExpressionMakeMaterialAttributes)
        link(source,'Result',unpack,str(LIB.get_material_expression_input_names(unpack)[0]))
        normalize=lambda s:re.sub('[^a-z0-9]','',str(s).lower())
        outputs={normalize(n):str(n) for n in LIB.get_material_expression_output_names(unpack)}
        inputs={normalize(n):str(n) for n in LIB.get_material_expression_input_names(pack)}
        for key,inp in inputs.items():
            if key in outputs:link(unpack,outputs[key],pack,inp)
        char=custom(parent,'float gray=dot(Color,float3(.2126,.7152,.0722));return lerp(gray.xxx,Color,.42)*Char;',
                    {'Color':(unpack,outputs['basecolor']),'Char':(scalar(parent,'CrustBrightness',.52),'')},u.CustomMaterialOutputType.CMOT_FLOAT3)
        link(char,'',pack,inputs['basecolor'])
        if not LIB.connect_material_property(pack,'',u.MaterialProperty.MP_MATERIAL_ATTRIBUTES):raise RuntimeError('Material output')
        u.EditorAssetLibrary.set_metadata_tag(parent,'MeteorRealistic.Charred','RuralAustralia Rock_M_02 PBR; final BaseColor only')
    errors=LIB.recompile_material(parent)
    if errors:raise RuntimeError(str(errors))
    save(parent)
    mi=own(ROCK+'/MI_Rock_M_02','MI_MeteorNaturalRock')
    LIB.set_material_instance_parent(mi,parent)
    LIB.set_material_instance_scalar_parameter_value(mi,'CrustBrightness',.52)
    # Texture frequency follows the 80 cm rock; the scan's authored UVs stay intact.
    LIB.set_material_instance_scalar_parameter_value(mi,'Detail Texture Tiling - U',18.)
    LIB.set_material_instance_scalar_parameter_value(mi,'Detail Texture Tiling - V',18.)
    for switch in ['Overlay Enabled','World Projected Masked Texture Enabled','Rock Stains Enabled','Wind']:
        LIB.set_material_instance_static_switch_parameter_value(mi,switch,False)
    LIB.update_material_instance(mi);save(mi)
    return [parent.get_path_name(),mi.get_path_name()]

def mesh():
    model=u.ModelingService
    def done(result):
        if not result.get_editor_property('success'):raise RuntimeError(result.get_editor_property('message'))
        return result
    source=u.load_asset(ROCK+'/SM_Rock_M_02')
    result=done(model.load_mesh_from_static_mesh(source.get_path_name(),0));handle=result.get_editor_property('handle')
    extent=source.get_bounds().box_extent
    scale=76./max(extent.x*2,extent.y*2,extent.z*2)
    try:
        done(model.recenter_mesh(handle,'Bounds'))
        done(model.scale_mesh(handle,u.Vector(scale,scale,scale),u.Vector()))
        done(model.save_mesh_to_static_mesh(handle,DEST+'/SM_MeteorNaturalRock',True,False,False,True))
    finally:model.release_mesh(handle)
    asset=u.load_asset(DEST+'/SM_MeteorNaturalRock')
    mat=u.load_asset(DEST+'/MI_MeteorNaturalRock')
    if not mat:raise RuntimeError('Run material stage first')
    for i in range(len(asset.get_editor_property('static_materials'))):asset.set_material(i,mat)
    save(asset)
    return [asset.get_path_name()]

def run(stage):
    OUT.mkdir(parents=True,exist_ok=True);u.EditorAssetLibrary.make_directory(DEST)
    assets={'material':material,'mesh':mesh}[stage]()
    record={'stage':stage,'saved':assets,'source':ROCK,'tested':False}
    (OUT/(stage+'-authored.json')).write_text(json.dumps(record,indent=2),encoding='utf8')
    print(record)
