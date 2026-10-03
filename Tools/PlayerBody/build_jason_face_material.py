"""Save an opaque full-face variant for the independent Jason head.

The source MI_Face_Skin_Baked_LOD0 is still masked: MF_skin_bakedInputs
hard-wires T_head_maskDown02 into OpacityMask. It cannot cover the face after
the overlapping body face is removed. Keep all native skin shading inputs,
but explicitly override the blend mode in this player-only material.
"""
import json
import shutil
from pathlib import Path
import unreal as u

PROJECT=Path('D:/FPS3D/FPSGAME')
ROOT=PROJECT/'SourceAssets/JasonFaceRepair20261003'
DEST='/Game/Characters/ModularOutfit20260924/JasonPlayer20261003/MI_Jason_FullFace'
SOURCE='/Game/AsianMale_Jason/Material/MI_Face_Skin_Baked_LOD0'

def build():
    ROOT.mkdir(parents=True,exist_ok=True)
    source=u.load_asset(SOURCE)
    if not source:raise RuntimeError('Missing Jason source skin')
    mat=u.load_asset(DEST)
    if not mat:mat=u.EditorAssetLibrary.duplicate_asset(SOURCE,DEST)
    if not mat:raise RuntimeError('Cannot create full-face skin')
    overrides=mat.get_editor_property('base_property_overrides')
    overrides.set_editor_property('override_blend_mode',True)
    overrides.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE)
    mat.set_editor_property('base_property_overrides',overrides)
    u.MaterialEditingLibrary.update_material_instance(mat)
    if not u.EditorAssetLibrary.save_loaded_asset(mat,False):
        raise RuntimeError('Full-face material was not saved; catalog remains unchanged')
    receipt={'material':mat.get_path_name(),'source':source.get_path_name(),
             'blend_mode':'Opaque','native_skin_inputs_preserved':True,
             'reason':'Source masked skin clips facial surface via T_head_maskDown02.'}
    (ROOT/'face_material_saved.json').write_text(json.dumps(receipt,indent=2))
    body_receipt=PROJECT/'SourceAssets/JasonPlayer20261003/body_saved.json'
    backup=ROOT/'body_saved_before.json'
    if body_receipt.exists():
        if not backup.exists():shutil.copy2(body_receipt,backup)
        data=json.loads(body_receipt.read_text())
        data['head_face_material']=mat.get_path_name()
        body_receipt.write_text(json.dumps(data,indent=2))
    print('JASON_FULL_FACE_MATERIAL_SAVED '+json.dumps(receipt),flush=True)
    return mat

if __name__=='__main__':
    mat=build()
    catalog=PROJECT/'Content/ColdSteelData/player_body.json'
    backup=ROOT/'player_body_before.json'
    if not backup.exists():shutil.copy2(catalog,backup)
    config=json.loads(catalog.read_text(encoding='utf-8-sig'))
    config['heads']['jason']['materials']['lambert1']=mat.get_path_name()
    catalog.write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('JASON_FULL_FACE_CATALOG_PUBLISHED '+mat.get_path_name(),flush=True)
