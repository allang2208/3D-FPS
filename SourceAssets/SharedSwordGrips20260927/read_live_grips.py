"""Read only the affected live sword components while diagnosing a reported failure."""
import unreal as u,json
from pathlib import Path
P=Path(__file__).resolve().parent
rows=[]
for c in u.ObjectIterator(u.StaticMeshComponent):
 tags=[str(t) for t in c.component_tags]
 if not any(t=='SwordSlot=grip' or t.startswith('FrostSwordVisual=') for t in tags):continue
 parent=c.get_attach_parent()
 mesh=c.get_editor_property('static_mesh')
 rows.append({'component':c.get_path_name(),'mesh':mesh.get_path_name() if mesh else None,'tags':tags,
  'parent_tags':[str(t) for t in parent.component_tags] if parent else [],'visible':c.is_visible()})
(P/'live_grips_before_cache_fix.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(rows,ensure_ascii=False))
