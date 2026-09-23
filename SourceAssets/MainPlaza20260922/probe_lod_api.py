"""Read-only: find the real LOD API names available in this engine build."""
import json
import unreal

out = {}
out['EditorStaticMeshLibrary_lod'] = sorted(
    n for n in dir(unreal.EditorStaticMeshLibrary) if 'lod' in n.lower())
out['EditorStaticMeshLibrary_all'] = sorted(n for n in dir(unreal.EditorStaticMeshLibrary)
                                            if not n.startswith('_'))
if hasattr(unreal, 'StaticMeshEditorSubsystem'):
    out['StaticMeshEditorSubsystem_lod'] = sorted(
        n for n in dir(unreal.StaticMeshEditorSubsystem) if 'lod' in n.lower())
    out['subsystem_instance'] = str(unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem))
else:
    out['StaticMeshEditorSubsystem_lod'] = None
out['StaticMesh_lod'] = sorted(n for n in dir(unreal.StaticMesh) if 'lod' in n.lower())
out['has_EditorScriptingStaticMeshLODReductionSettings'] = hasattr(
    unreal, 'EditorScriptingStaticMeshLODReductionSettings')
if hasattr(unreal, 'EditorScriptingStaticMeshLODReductionSettings'):
    out['reduction_fields'] = sorted(
        n for n in dir(unreal.EditorScriptingStaticMeshLODReductionSettings) if not n.startswith('_'))
out['has_StaticMeshReductionSettings'] = hasattr(unreal, 'StaticMeshReductionSettings')
if hasattr(unreal, 'StaticMeshReductionSettings'):
    out['static_reduction_fields'] = sorted(
        n for n in dir(unreal.StaticMeshReductionSettings) if not n.startswith('_'))
print('PROBE2 ' + json.dumps(out, ensure_ascii=False, indent=1))
