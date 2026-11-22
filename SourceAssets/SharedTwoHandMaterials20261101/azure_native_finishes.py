"""Restore V2 native finishes to a rune-sword parent or its whirlwind counterpart."""
from pathlib import Path
import runpy
import unreal as u


def apply(material, sources):
    fields = [node for node in u.MaterialEditingLibrary.get_material_expressions(material)
              if isinstance(node, u.MaterialExpressionCustom)
              and str(node.get_editor_property('desc')).startswith('BladeFinish20261031V1 ')]
    if len(fields) != 4:
        raise ValueError('Expected four native finish branches on ' + material.get_path_name())
    applied = []
    for folder, revision, tag in [
        ('MeteoricIronRefinement20261101', 'MeteoricIron20261101V2', 'MeteoricIronRefinementRevision'),
        ('TimeSandPolish20261101', 'TimeSandPolish20261101V2', 'TimeSandPolishRevision'),
    ]:
        if all(revision in str(node.get_editor_property('code')) for node in fields):
            continue
        edit = runpy.run_path(str(Path(sources) / folder / 'finish_graph.py'))['apply']
        if folder == 'MeteoricIronRefinement20261101':
            texture = u.load_asset('/Game/Weapons/AzureRunesword20260913/MeteoricIronRefinement20261101/T_MeteoricCrystalFieldV2')
            if not texture:
                raise ValueError('Missing native meteor field texture')
            edit(material, texture)
        else:
            edit(material)
        u.EditorAssetLibrary.set_metadata_tag(material, tag, revision)
        applied.append(revision)
    return applied
