"""Import the original ceramic fracture PBR; retain existing glaze and mortar."""
import json
from pathlib import Path
from datetime import datetime
import unreal as u
ROOT=Path(__file__).resolve().parents[1];BASE='/Game/Dungeons/AtmosphereV2/TileFracture'
MAN=json.loads((ROOT/'Authored/material-manifest.json').read_text())
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
if not u.get_editor_subsystem(u.UnrealEditorSubsystem) or Path(u.Paths.project_dir()).resolve()!=ROOT.parents[1].resolve():
    raise RuntimeError('Requires FPSGAME editor')
if any(p.get_path_name().startswith(BASE+'/') for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('Preserve unsaved ceramic-revision assets')
(ROOT/'Receipts').mkdir(exist_ok=True)
receipt=dict(saved=[],tests_run=False,stage='authoring')
def save(obj):
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Save failed '+obj.get_path_name())
    receipt['saved'].append(obj.get_path_name())
    (ROOT/'Receipts/materials.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
textures={}
for channel,filename in MAN['channels'].items():
    name='T_CeramicFracture_'+channel;task=u.AssetImportTask()
    task.filename=filename;task.destination_path=BASE+'/Textures';task.destination_name=name
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
    A.import_asset_tasks([task]);tex=u.load_asset(BASE+'/Textures/'+name)
    if not tex:raise RuntimeError('Import failed '+name)
    tex.set_editor_property('srgb',channel=='BaseColor')
    if channel=='Normal':
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP)
        tex.set_editor_property('flip_green_channel',True)
    elif channel=='Roughness':tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
    save(tex);textures[channel]=tex
path=BASE+'/Materials/M_CeramicFractureCore';mat=u.load_asset(path)
if not mat:mat=A.create_asset('M_CeramicFractureCore',BASE+'/Materials',u.Material,u.MaterialFactoryNew())
mat.modify();L.delete_all_material_expressions(mat)
mat.set_editor_property('used_with_instanced_static_meshes',True)
mat.set_editor_property('used_with_nanite',True)
for channel,prop in [('BaseColor','BASE_COLOR'),('Normal','NORMAL'),('Roughness','ROUGHNESS')]:
    n=L.create_material_expression(mat,u.MaterialExpressionTextureSample)
    n.set_editor_property('texture',textures[channel])
    n.set_editor_property('sampler_type',{'BaseColor':u.MaterialSamplerType.SAMPLERTYPE_COLOR,
        'Normal':u.MaterialSamplerType.SAMPLERTYPE_NORMAL,'Roughness':u.MaterialSamplerType.SAMPLERTYPE_MASKS}[channel])
    if not L.connect_material_property(n,'R' if channel=='Roughness' else '',getattr(u.MaterialProperty,'MP_'+prop)):
        raise RuntimeError('Material connection failed '+prop)
n=L.create_material_expression(mat,u.MaterialExpressionConstant);n.set_editor_property('r',.23)
L.connect_material_property(n,'',u.MaterialProperty.MP_SPECULAR)
L.layout_material_expressions(mat);L.recompile_material(mat);save(mat)
receipt.update(stage='materials_saved',saved_at=datetime.now().isoformat(),material=path)
(ROOT/'Receipts/materials.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('CERAMIC_FRACTURE_MATERIAL_SAVED '+json.dumps(receipt))
