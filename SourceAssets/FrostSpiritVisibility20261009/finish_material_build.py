"""Finish compilation of the saved revision, then persist that material only."""
from pathlib import Path
from datetime import datetime
import hashlib,json
import unreal as u
P=Path(__file__).resolve().parent
ASSET='/Game/Weapons/FrostSpiritBurst20260922/M_SilverRuneSurface_FrostSpirit'
m=u.load_asset(ASSET)
E=u.MaterialEditingLibrary
if not m:raise RuntimeError('Installed material missing')
shader=next(n for n in E.get_material_expressions(m) if isinstance(n,u.MaterialExpressionCustom) and 'RuneTexture' in n.get_editor_property('code'))
if shader.get_editor_property('code')!=(P/'spirit_visible.hlsl').read_text(encoding='utf-8'):
    raise RuntimeError('The authored visibility revision is not the installed material')
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('Preserve active PIE; material is saved and shader build must wait')
    if m.get_outermost().get_path_name() in {x.get_path_name() for x in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:
        raise RuntimeError('Preserve unsaved spirit material edits')
errors=list(E.recompile_material(m))
if errors:raise RuntimeError(str(errors))
stats=E.get_statistics(m)
instructions=stats.get_editor_property('num_pixel_shader_instructions')
if instructions<=0:raise RuntimeError('No compiled pixel shader; read the build log')
if not u.EditorLoadingAndSavingUtils.save_packages([m.get_outermost()],False):raise RuntimeError('Save failed')
receipt=json.loads((P/'install_receipt.json').read_text(encoding='utf-8'))
receipt.update(shader_compilation_finished=True,material_build_time=datetime.now().isoformat(),
               pixel_shader_instructions=instructions,
               saved_file_sha256=hashlib.sha256((P.parents[1]/'Content/Weapons/FrostSpiritBurst20260922/M_SilverRuneSurface_FrostSpirit.uasset').read_bytes()).hexdigest())
(P/'install_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
print('FROST_SPIRIT_MATERIAL_BUILD_FINISHED')
