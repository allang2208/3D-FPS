"""Export the complete bound body before wardrobe hidden-face removal."""
import json
from pathlib import Path
import unreal as u

WORK = Path('D:/FPS3D/FPSGAME/SourceAssets/KaitlinPlayer20261023')
DEST = '/Game/Characters/KaitlinPlayer20261023/Native/Kaitlin/BodyFull'
SOURCE = '/Game/EditableCharacters/Kaitlin/MHC_Kaitlin.MHC_Kaitlin'
NATIVE = '/Game/Characters/KaitlinPlayer20261023/Native/Kaitlin/Body/SKM_MHC_Kaitlin_BodyMesh.SKM_MHC_Kaitlin_BodyMesh'
subsystem = u.get_editor_subsystem(u.MetaHumanCharacterEditorSubsystem)
character = u.load_asset(SOURCE)
if not subsystem.try_add_object_to_edit(character):
    raise RuntimeError('Cannot open the bound character for full-body export.')
try:
    if u.EditorAssetLibrary.does_asset_exist(DEST + '/MHC_Kaitlin_Body'):
        raise RuntimeError('Full-body authoring output already exists; preserve it.')
    # ExportGeometry reaches Slate notifications unconditionally in UE 5.8.
    # Duplicate the complete editing mesh through AssetTools instead, so the
    # commandlet can save it without opening a Content Browser window.
    editing_bodies = [obj for obj in u.ObjectIterator(u.SkeletalMesh)
                      if obj.get_path_name().startswith('/Engine/Transient')
                      and obj.get_name().startswith('BodyMesh_')]
    if len(editing_bodies) != 1:
        raise RuntimeError('Expected the one initialized editing body: ' + str([obj.get_path_name() for obj in editing_bodies]))
    full_body = u.AssetToolsHelpers.get_asset_tools().duplicate_asset('MHC_Kaitlin_Body', DEST, editing_bodies[0])
    native = u.load_asset(NATIVE)
    if not full_body or not native:
        raise RuntimeError('Native body export did not produce its mesh.')
    # Geometry export deliberately assigns a topology-view material. Use the
    # saved native body skin and runtime skeleton from the completed assembly.
    full_body.set_editor_property('materials', native.get_editor_property('materials'))
    # BlueprintSetter functions are omitted from the Python method table in
    # 5.8, but remain reflected UFunctions callable through UObject.
    full_body.call_method('SetSkeleton', (native.skeleton,))
    full_body.set_editor_property('physics_asset', native.physics_asset)
    full_body.set_editor_property('post_process_anim_blueprint', native.get_editor_property('post_process_anim_blueprint'))
    if not u.EditorAssetLibrary.save_loaded_asset(full_body, False):
        raise RuntimeError('Full-body asset was not saved.')
    receipt = {'status': 'complete_body_saved', 'mesh': full_body.get_path_name(),
               'source_character': SOURCE, 'skeleton': full_body.skeleton.get_path_name(),
               'wardrobe_geometry_removal': False}
    (WORK / 'full_body_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print('KAITLIN_FULL_BODY_SAVED', full_body.get_path_name(), flush=True)
finally:
    subsystem.remove_object_to_edit(character)

# Capture the complete source in this already-running host before releasing it.
import runpy
runpy.run_path('D:/FPS3D/FPSGAME/Tools/KaitlinPlayer/extract_native.py', run_name='__main__')
