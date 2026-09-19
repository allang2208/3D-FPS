from pathlib import Path
P=Path(__file__).parent
source=(P.parent/'import_assets.py').read_text(encoding='utf-8')
# Preserve the rebuilt area-weighted normals in the actual UE mesh.
source=source.replace('t=unreal.AssetImportTask()', 'o.static_mesh_import_data.normal_import_method=unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS\nt=unreal.AssetImportTask()')
exec(compile(source,str(P/'import_generated.py'),'exec'))
