"""Put M_Kukri back on SM_Kukri's material slot and save only that package (2026-10-22 fix).

The slot had fallen back to /Engine/EngineMaterials/WorldGridMaterial (the white checker the user saw as "white
mosaic"): import_kukri.py's slot loop edited copies of the static_materials array and never assigned anything.
M_Kukri and the three textures were intact.  Runs as a commandlet with the editor closed
(-run=pythonscript -script=<this file>) or inside a live editor via Tools/AssetPipeline/mcp_call_codex.ps1
-PythonScript.  Touches nothing else; never runs PIE or tests."""
import unreal as u

MESH = '/Game/Weapons/Kukri20261020/SM_Kukri'
MAT = '/Game/Weapons/Kukri20261020/Materials/M_Kukri'
dirty = {str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if MESH in dirty:
    raise RuntimeError('Preserving unsaved edits: ' + MESH)
mesh = u.load_asset(MESH)
mat = u.load_asset(MAT)
if not mesh or not mat:
    raise RuntimeError('SM_Kukri or M_Kukri missing')
before = [mesh.get_material(i).get_path_name() if mesh.get_material(i) else None
          for i in range(len(mesh.get_editor_property('static_materials')))]
for i in range(len(before)):
    mesh.set_material(i, mat)
after = [mesh.get_material(i).get_path_name() if mesh.get_material(i) else None for i in range(len(before))]
if any(a != mat.get_path_name() for a in after):
    raise RuntimeError('Kukri material slot not assigned: %s' % after)
if not u.EditorLoadingAndSavingUtils.save_packages([mesh.get_outermost()], False):
    raise RuntimeError('Kukri save failed: ' + MESH)
u.log('KUKRI_MATERIAL_REPAIRED before=%s after=%s' % (before, after))
