"""Freeze the active nun boot, native weights and hem material graphs for authoring."""
from pathlib import Path
import hashlib
code=Path('D:/FPS3D/FPSGAME/Tools/ChapelNun/capture_sources.py').read_text(encoding='utf-8-sig')
exec(compile(code.split('head=capture(')[0],'<nun capture helpers>','exec'))
R=P/'SourceAssets/ChapelNun20261115/BootFinishR8'
(R/'Inputs').mkdir(parents=True,exist_ok=True)
asset=capture('boots','/Game/Characters/ChapelNun20261115/RefinementR4/Meshes/SK_Nun_Boots')
ml=u.MaterialEditingLibrary
materials=[]
for slot in asset.materials:
    mat=slot.material_interface
    entry={'slot':str(slot.material_slot_name),'asset':mat.get_path_name(),'textures':[]}
    if isinstance(mat,u.Material):
        for node in ml.get_material_expressions(mat):
            if isinstance(node,u.MaterialExpressionTextureSample):
                tex=node.get_editor_property('texture')
                if tex:entry['textures'].append({'asset':tex.get_path_name(),'srgb':tex.get_editor_property('srgb'),'flip_green':tex.get_editor_property('flip_green_channel')})
    materials.append(entry)
disk=P/'Content/Characters/ChapelNun20261115/RefinementR4/Meshes/SK_Nun_Boots.uasset'
meta={'asset':asset.get_path_name(),'asset_sha256':hashlib.sha256(disk.read_bytes()).hexdigest(),'materials':materials,'lod_count':u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem).get_lod_count(asset),'runtime_tested':False}
(R/'Inputs/recipe.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
print('NUN_BOOT_R8_INPUTS_SAVED',flush=True)
