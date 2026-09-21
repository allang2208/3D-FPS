from pathlib import Path
import json
import unreal as u
p=Path(__file__).parent
m=u.load_asset('/Game/Skills/Whirlwind20260920/M_WhirlwindFocus')
if not m: raise RuntimeError('Whirlwind focus material missing')
rows=[]
for e in u.MaterialEditingLibrary.get_material_expressions(m):
 row={'name':e.get_name(),'class':e.get_class().get_name()}
 if isinstance(e,u.MaterialExpressionCustom):
  row['code']=e.get_editor_property('code')
  row['description']=e.get_editor_property('description')
 rows.append(row)
(p/'material-before.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(rows,ensure_ascii=False))
