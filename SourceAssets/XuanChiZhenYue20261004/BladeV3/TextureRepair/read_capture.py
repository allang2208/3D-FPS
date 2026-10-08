import json
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent
rows=[]
for c in u.ObjectIterator(u.SceneCaptureComponent2D):
    r={'path':c.get_path_name(),'source':str(c.capture_source),'components':[]}
    for x in u.ObjectIterator(u.StaticMeshComponent):
        if x.static_mesh and 'XuanChi' in x.static_mesh.get_path_name():
            r['components'].append({'path':x.get_path_name(),'mesh':x.static_mesh.get_path_name() if x.static_mesh else None,'materials':[x.get_material(i).get_path_name() if x.get_material(i) else None for i in range(x.get_num_materials())]})
    if c.get_path_name().startswith('/Engine/Transient'):
        for key in ['post_process_settings','show_flag_settings','post_process_blend_weight']:r[key]=str(c.get_editor_property(key))
        if c.texture_target:
            r['target']=c.texture_target.get_path_name()
            u.RenderingLibrary.export_render_target(c,c.texture_target,str(P),'live_'+c.get_name())
            r['export']=c.get_name()
    rows.append(r)
(P/'live_captures.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print(json.dumps(rows,default=str))
