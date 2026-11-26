"""Export the source height of the existing generic stone for the Blender displacement bake."""
from pathlib import Path
import unreal as u

source = u.load_asset('/Game/UnrealNormandy/Textures/T_StoneSurface_02A_Height')
target = Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir())) / 'SourceAssets/TemperateHillsOldChapel/Concept01/Surfaces/Footing'
target.mkdir(parents=True, exist_ok=True)
task = u.AssetExportTask()
task.object = source
task.filename = str(target / 'StoneSurface02A_Height.png')
task.automated = True
task.prompt = False
task.replace_identical = True
task.exporter = u.TextureExporterPNG()
if not u.Exporter.run_asset_export_task(task):
    raise RuntimeError('Could not export StoneSurface 02A height')
