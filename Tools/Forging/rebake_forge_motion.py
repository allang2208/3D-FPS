"""Update the editable arm motion only; no tool exports, imports, renders or tests."""
import json
import sys
from pathlib import Path
import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from forge_arm_pose import bake_motion

path = ROOT / 'SourceAssets/ForgeInteraction20260927/ForgeTools_V7_Grasp.blend'
bpy.ops.wm.open_mainfile(filepath=str(path))
native = json.loads((ROOT / 'SourceAssets/ModularOutfit20260925/BarePalmV7/M4_original.json').read_text())
data = json.loads((ROOT / 'Content/ColdSteelData/forge-grip.json').read_text())
reference = {}
for name, bone in native['bones'].items():
    transform = Matrix([Vector(axis).normalized() for axis in bone['axes']]).transposed().to_4x4()
    transform.translation = Vector(bone['position']) / 100
    reference[name] = transform
bake_motion(bpy.context.scene, bpy.data.objects['V7_M4_NativeForge'],
            bpy.data.objects['SM_ForgeHammer'], bpy.data.objects['SM_ForgeTongs'], reference, data)
bpy.ops.wm.save_as_mainfile(filepath=str(path))
print('FORGE_MOTION_SAVED', str(path), flush=True)
