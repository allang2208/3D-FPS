"""Author an isolated blue derivative of the installed weapon-fire system."""
from pathlib import Path
import json,sys
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME');OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'Tools/Skills'))
from build_fireball_assets import LIB,ref,setdata
SOURCE='/Game/Skills/FlameArmor20261016/TorchV2'
DEST='/Game/Weapons/FrostCrystalSword20260915/StarMarrowCharge20261103'
saved=[]

def owned(source,name):
    path=DEST+'/'+name
    if path in {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:
        raise RuntimeError('Preserve dirty asset: '+path)
    asset=u.load_asset(path) if u.EditorAssetLibrary.does_asset_exist(path) else u.EditorAssetLibrary.duplicate_asset(source,path)
    if not asset:raise RuntimeError('Cannot create '+path)
    return asset

def save(asset):
    if isinstance(asset,u.Material):
        errors=LIB.recompile_material(asset)
        if errors:raise RuntimeError(str(errors))
    if isinstance(asset,u.NiagaraSystem) and not u.RainAssetEditor.compile_rain(asset,True):
        raise RuntimeError('Niagara compile failed')
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):
        raise RuntimeError('Save failed: '+asset.get_path_name())
    saved.append(asset.get_path_name())

def blue(mat):
    # Keep native flame density, erosion, particle alpha and exposure compensation.
    # Remap the final emitted RGB, so orange texture/particle tint cannot leak through.
    prop=u.MaterialProperty.MP_EMISSIVE_COLOR
    node=next((n for n in LIB.get_material_expressions(mat) if n.get_editor_property('desc')=='StarMarrow blue flame'),None)
    if node is None:
        source=LIB.get_material_property_input_node(mat,prop)
        pin=str(LIB.get_material_property_input_node_output_name(mat,prop))
        if source is None:raise RuntimeError('No flame emission: '+mat.get_path_name())
        node=LIB.create_material_expression(mat,u.MaterialExpressionCustom)
        node.set_editor_property('desc','StarMarrow blue flame')
        node.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
        inp=u.CustomInput();inp.set_editor_property('input_name','Fire');node.set_editor_property('inputs',[inp])
        if not LIB.connect_material_expressions(source,pin,node,'Fire'):raise RuntimeError('Cannot connect flame')
        LIB.connect_material_property(node,'',prop)
    node.set_editor_property('code','float heat=max(Fire.r,max(Fire.g,Fire.b)); float core=saturate(min(Fire.g,Fire.b)/max(heat,0.001)); return heat*lerp(float3(0.035,0.29,1.0),float3(0.32,0.82,1.0),core)*0.85;')
    mat.set_editor_property('disable_depth_test',False)
    u.EditorAssetLibrary.set_metadata_tag(mat,'StarMarrow.Revision','ChargeBlueFlame20261103')
    save(mat)

def run():
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor.get_game_world():raise RuntimeError('End PIE before saving charge assets')
    u.EditorAssetLibrary.make_directory(DEST)
    core=owned(SOURCE+'/FireballV3/M_FA_FireballCoreV3','M_StarMarrowBlueCore');blue(core)
    parent=owned(SOURCE+'/FireballV3/M_FA_FireballErosionV3','M_StarMarrowBlueFlame');blue(parent)
    ember=owned(SOURCE+'/M_FA_Ember','M_StarMarrowBlueEmber');blue(ember)
    flame=owned(SOURCE+'/FireballV3/MI_FA_FireballFlameV3','MI_StarMarrowBlueFlame')
    LIB.set_material_instance_parent(flame,parent);LIB.update_material_instance(flame);save(flame)
    system=owned(SOURCE+'/NS_FlameArmorWeaponV2','NS_StarMarrowCharge')
    for name,mat in [('WeaponFireballCore',core),('WeaponFireballTongues',flame),('WeaponFireballCurls',flame),('MotionFireballFlame',flame),('WeaponEmbers',ember)]:
        setdata('SetRendererData',u.NiagaraExt_RendererData,ref(system,name,renderer=0),{'Material':mat.get_path_name()})
    u.EditorAssetLibrary.set_metadata_tag(system,'StarMarrow.Revision','ChargeBlueFlame20261103')
    save(system)
    (OUT/'flames-receipt.json').write_text(json.dumps({'saved_assets':saved,'gameplay_tested':False,'rendered':False},indent=2),encoding='utf8')
    print('STAR_MARROW_BLUE_FLAMES_SAVED',saved)

if __name__=='__main__':
    run()
    # Keep the irregular distribution and distinct curl material on rebuild.
    sys.path.insert(0,str(OUT/'VariationV2'))
    from install_variation import run as install_variation
    install_variation()
    sys.path.insert(0,str(OUT/'DenseFlowV3'))
    from install_dense_flow import run as install_dense_flow
    install_dense_flow()
