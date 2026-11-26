"""Run only the already-requested calf defect measurement, without rerender."""
import ast
from pathlib import Path
file=Path('D:/FPS3D/FPSGAME/Tools/ModernTacticalSet/combat2_lower_review.py')
tree=ast.parse(file.read_text(encoding='utf-8'));nodes=[]
for node in tree.body:
    if isinstance(node,ast.Expr) and isinstance(node.value,ast.Call) and ast.unparse(node.value.func)=='bpy.ops.wm.open_mainfile':break
    nodes.append(node)
exec(compile(ast.Module(body=nodes,type_ignores=[]),str(file),'exec'))
