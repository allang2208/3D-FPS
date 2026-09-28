"""Incrementally save cloud body/detail changes; preserve weather and lighting."""
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
import unreal as u

ROOT=Path(__file__).parent
PROJECT=ROOT.parents[2]
PATH='/Game/Props/GodSpaceLayout20260927/Materials/M_GodSpaceCloudSea_Cumulus'
L=u.MaterialEditingLibrary

def apply():
    dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if PATH in dirty:raise RuntimeError('Preserve unsaved cloud master edits')
    mat=u.load_asset(PATH)
    if not mat:raise RuntimeError('Existing cumulus cloud material missing')
    src=PROJECT/'Content'/(PATH.removeprefix('/Game/')+'.uasset')
    dst=PROJECT/'trash/godspace-cloud-lobes-20260928'/datetime.now().strftime('%H%M%S-%f')/src.name
    dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
    codes={
        'Weather footprint, rounded height profile and conservative empty-space skip':'CloudSeaCumulusCoverage.hlsl',
        'Cloud lobes and bounded edge erosion with distance-conditional sampling':'CloudSeaCumulusDensity.hlsl'}
    expressions=list(L.get_material_expressions(mat))
    # Resolve owned nodes before changing the asset, leaving all external nodes
    # (including the shared lightning integration) intact.
    targets={}
    for expression in expressions:
        if isinstance(expression,u.MaterialExpressionCustom):
            desc=expression.get_editor_property('desc')
            if desc not in codes:desc=expression.get_editor_property('description')
            if desc in codes:targets[desc]=expression
    if set(targets)!=set(codes):raise RuntimeError('Cumulus custom nodes differ from authored graph')
    for desc,expression in targets.items():expression.set_editor_property('code',(ROOT/codes[desc]).read_text(encoding='utf8'))
    for expression in expressions:
        if isinstance(expression,u.MaterialExpressionVolumetricAdvancedMaterialOutput):
            expression.set_editor_property('const_multi_scattering_contribution',.65)
            expression.set_editor_property('const_multi_scattering_occlusion',.40)
    mat.set_editor_property('used_with_volumetric_cloud',True)
    errors=list(L.recompile_material(mat))
    if errors:raise RuntimeError('Cloud lobe material compile failed: '+str(errors))
    u.SystemLibrary.execute_console_command(None,'Editor.AsyncAssetCompilationFinishAll')
    if not u.EditorAssetLibrary.save_loaded_asset(mat,False):raise RuntimeError('Cloud lobe save failed')
    report={'saved':mat.get_path_name(),'compile_errors':errors,'backup':str(dst),
        'backup_sha256':hashlib.sha256(dst.read_bytes()).hexdigest(),'runtime_tested':False,
        'shape_period_m':[1700,2300,850],'detail_period_m':[520,730,410],
        'max_texture_samples_primary_near':3,'max_texture_samples_primary_far':2,
        'additional_layers':0,'sample_count_changed':False,'coverage_measured':False,
        'lights_changed':False,'usage_volumetric_cloud':True}
    (ROOT/'Receipts/cloud-lobes-saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print('GODSPACE_CLOUD_LOBES_SAVED '+json.dumps(report))
    return report

if __name__=='__main__':apply()
