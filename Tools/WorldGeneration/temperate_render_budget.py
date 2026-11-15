"""Author near-camera coverage on owned low foliage; keep far fades and wind."""
import hashlib
import json
import shutil
from pathlib import Path
import unreal as u

PROJECT = Path('D:/FPS3D/FPSGAME')
TASK = PROJECT/'SourceAssets/HillsEcologyUpgrade20261114'
BASE = '/Game/WorldGeneration/TemperateHills'
DEST = BASE+'/EcologyUpgrade/Materials'
TAG = 'HillsCameraCoverage20261114'
LIB = u.MaterialEditingLibrary
EAL = u.EditorAssetLibrary
REPORT = {'saved': [], 'low_foliage': [], 'tested': False}

def load(path):
    obj = u.load_asset(path)
    if obj is None: raise RuntimeError('Missing asset: '+path)
    return obj

def backup(obj):
    package = obj.get_path_name().split('.')[0]
    if not package.startswith(BASE+'/'): raise RuntimeError('Outside hills ownership: '+package)
    for ext in ('.uasset', '.uexp', '.ubulk', '.umap'):
        relative = package.removeprefix('/Game/')+ext
        src, dst = PROJECT/'Content'/relative, TASK/'Before/Content'/relative
        if src.exists() and not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

def save(obj):
    if not EAL.save_loaded_asset(obj, False): raise RuntimeError('Save failed: '+obj.get_path_name())
    REPORT['saved'].append(obj.get_path_name())

def node(mat, cls):
    n = LIB.create_material_expression(mat, cls)
    n.set_editor_property('desc', TAG)
    return n

def wire(a, b, pin='', output=''):
    if not LIB.connect_material_expressions(a, output, b, pin): raise RuntimeError('Material input: '+pin)

def patch_parent(mat):
    if any(n.get_editor_property('desc') == TAG for n in LIB.get_material_expressions(mat)): return
    backup(mat)
    attributes = mat.get_editor_property('use_material_attributes')
    prop = u.MaterialProperty.MP_MATERIAL_ATTRIBUTES if attributes else u.MaterialProperty.MP_OPACITY_MASK
    original = LIB.get_material_property_input_node(mat, prop)
    output = LIB.get_material_property_input_node_output_name(mat, prop) if original else ''
    # Preserve an opaque material as opaque. This wrapper is for masked leaves.
    if mat.get_editor_property('blend_mode') != u.BlendMode.BLEND_MASKED: return
    position = node(mat, u.MaterialExpressionWorldPosition)
    position.set_editor_property('world_position_shader_offset', u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    camera = node(mat, u.MaterialExpressionCameraPositionWS)
    inputs = {'P': position, 'C': camera}
    for key, value in [('NearStartCm',40.0), ('NearEndCm',65.0), ('NearFadeEnabled',0.0)]:
        p = node(mat, u.MaterialExpressionScalarParameter)
        p.set_editor_property('parameter_name', 'Hills'+key)
        p.set_editor_property('default_value', value)
        inputs[key] = p
    fade = node(mat, u.MaterialExpressionCustom)
    fade.set_editor_property('output_type', u.CustomMaterialOutputType.CMOT_FLOAT1)
    fade.set_editor_property('code', 'return lerp(1.0,smoothstep(NearStartCm,max(NearStartCm+1.0,NearEndCm),distance(P,C)),saturate(NearFadeEnabled));')
    pins=[]
    for name in inputs:
        p=u.CustomInput();p.set_editor_property('input_name',name);pins.append(p)
    fade.set_editor_property('inputs',pins)
    for name, value in inputs.items(): wire(value, fade, name)
    dither=node(mat,u.MaterialExpressionMaterialFunctionCall)
    dither.set_editor_property('material_function',load('/Engine/Functions/Engine_MaterialFunctions02/Utility/DitherTemporalAA'))
    wire(fade,dither,LIB.get_material_expression_input_names(dither)[0])
    # A view-local coverage effect must not punch a moving hole in sun shadows.
    shadow=node(mat,u.MaterialExpressionShadowReplace)
    wire(dither,shadow,'Default')
    one=node(mat,u.MaterialExpressionConstant);one.set_editor_property('r',1.0)
    wire(one,shadow,'Shadow')
    multiply=node(mat,u.MaterialExpressionMultiply)
    wire(shadow,multiply,'B')
    if attributes:
        if original is None: raise RuntimeError('Missing foliage attributes: '+mat.get_path_name())
        get=node(mat,u.MaterialExpressionGetMaterialAttributes)
        idx=u.TemperateForestAuthoringLibrary.add_visibility_mask_pin(get)
        if idx<0: raise RuntimeError('Missing attribute reader')
        wire(original,get,LIB.get_material_expression_input_names(get)[0],output)
        wire(get,multiply,'A',LIB.get_material_expression_output_names(get)[idx])
        put=node(mat,u.MaterialExpressionSetMaterialAttributes)
        idx=u.TemperateForestAuthoringLibrary.add_visibility_mask_pin(put)
        if idx<0: raise RuntimeError('Missing attribute writer')
        names=LIB.get_material_expression_input_names(put)
        wire(original,put,names[0],output);wire(multiply,put,names[idx])
        result=put
    else:
        wire(original or one,multiply,'A',output)
        result=multiply
    if not LIB.connect_material_property(result,'',prop): raise RuntimeError('Cannot bind leaf coverage')
    LIB.recompile_material(mat);save(mat)

def leaf_instance(material):
    parent=material
    while isinstance(parent,u.MaterialInstanceConstant): parent=parent.get_editor_property('parent')
    if not isinstance(parent,u.Material) or parent.get_editor_property('blend_mode')!=u.BlendMode.BLEND_MASKED:
        return material
    def inherit(source):
        if isinstance(source,u.Material):
            if source.get_path_name().startswith(BASE+'/'):
                result=source
            else:
                key='M_Leaf_'+hashlib.sha1(source.get_path_name().encode()).hexdigest()[:12]
                dest=DEST+'/'+key
                result=load(dest) if EAL.does_asset_exist(dest) else EAL.duplicate_asset(source.get_path_name(),dest)
            patch_parent(result)
            return result
        original=source.get_editor_property('parent')
        new_parent=inherit(original)
        if new_parent==original:return source
        dest=DEST+'/MI_Inherit_'+hashlib.sha1(source.get_path_name().encode()).hexdigest()[:12]
        clone=load(dest) if EAL.does_asset_exist(dest) else EAL.duplicate_asset(source.get_path_name(),dest)
        LIB.set_material_instance_parent(clone,new_parent);LIB.update_material_instance(clone);save(clone)
        return clone
    if material.get_path_name().startswith(DEST+'/MI_Leaf_'):
        mi=material
        inherited=inherit(mi.get_editor_property('parent'))
    else:
        inherited=inherit(material)
        name='MI_Leaf_'+hashlib.sha1(material.get_path_name().encode()).hexdigest()[:12]
        dest=DEST+'/'+name
        mi=load(dest) if EAL.does_asset_exist(dest) else u.AssetToolsHelpers.get_asset_tools().create_asset(name,DEST,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    backup(mi)
    if mi.get_editor_property('parent')!=inherited: LIB.set_material_instance_parent(mi,inherited)
    LIB.set_material_instance_scalar_parameter_value(mi,'HillsNearFadeEnabled',1.0)
    LIB.update_material_instance(mi);save(mi)
    return mi

def apply_palette(assets):
    EAL.make_directory(DEST)
    paths=set()
    for key in ('grass','grass_accents','rainforest_grass','rainforest_carpet_grass','forest_ferns',
                'river_ground_cover','river_bank_grasses','river_reeds','river_understory','rainforest_herbs','meadow_flowers'):
        for ref in assets.get_editor_property(key): paths.add(ref.get_path_name())
    for family in assets.get_editor_property('clearing_flowers'):
        for ref in family.get_editor_property('variants'): paths.add(ref.get_path_name())
    replacements={}
    for path in sorted(paths):
        mesh=load(path)
        if not path.startswith(BASE+'/'): continue
        backup(mesh)
        prop='materials' if isinstance(mesh,u.SkeletalMesh) else 'static_materials'
        slots=list(mesh.get_editor_property(prop))
        for slot in slots:
            mat=slot.get_editor_property('material_interface')
            if mat is None: continue
            key=mat.get_path_name()
            if key not in replacements: replacements[key]=leaf_instance(mat)
            slot.set_editor_property('material_interface',replacements[key])
        mesh.set_editor_property(prop,slots);save(mesh)
        REPORT['low_foliage'].append(path)
    graph=load(BASE+'/PCG_HillsGrass');backup(graph)
    for n in graph.get_editor_property('nodes'):
        s=n.get_settings()
        if not isinstance(s,u.PCGStaticMeshSpawnerSettings): continue
        selector=s.get_editor_property('mesh_selector_parameters')
        d=selector.get_editor_property('template_descriptor');d.set_editor_property('cast_shadow',False)
        selector.set_editor_property('template_descriptor',d)
    save(graph)

def main():
    apply_palette(load(BASE+'/DA_TemperateHillsStreaming'))
    TASK.mkdir(parents=True,exist_ok=True)
    (TASK/'near-foliage-saved.json').write_text(json.dumps(REPORT,indent=2),encoding='utf-8')
    u.log('HILLS_NEAR_FOLIAGE_SAVED '+str(len(REPORT['saved'])))

if __name__=='__main__':main()
