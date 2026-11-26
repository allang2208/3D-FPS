"""Refresh final textile fields without rerunning garment mesh production."""
import ast
from pathlib import Path
source=Path('D:/FPS3D/FPSGAME/Tools/ModernTacticalSet/combat2_save.py')
tree=ast.parse(source.read_text(encoding='utf-8'))
prefix=[]
for node in tree.body:
    if isinstance(node,ast.Expr) and isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Name) and node.value.func.id=='material':
        prefix.append(node)
        break
    prefix.append(node)
exec(compile(ast.Module(body=prefix,type_ignores=[]),str(source),'exec'))
print('TS01_COMBAT2_FINAL_TEXTILES_SAVED',flush=True)
