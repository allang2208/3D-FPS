import bpy,runpy,json,hashlib
from pathlib import Path
O=Path(__file__).parent;B=O.parent/'AKMAttachments20260911';configure=runpy.run_path(str(B/'preview_visibility.py'))['configure_preview'];report={}
files=[B/'AKM_Attachments_Editable.blend']+list(B.glob('prism/*.blend'))+list(B.glob('angled/*.blend'))+list(O.glob('base/*.blend'))+list(O.glob('prism/*.blend'))+list(O.glob('angled/*.blend'))
for path in files:
 bpy.ops.wm.open_mainfile(filepath=str(path));drum='drum_reload' in path.stem;variant=path.parent.name if path.parent.name in ['prism','angled'] else 'base'
 n=sum(len(o.data.polygons) for o in bpy.context.scene.objects if o.name in ['AKM_Soviet_Native','AKM_FactoryMagazine_Preview'])
 magazine=configure(drum,variant)
 assert n==sum(len(bpy.data.objects[n].data.polygons) for n in ['AKM_Soviet_Native','AKM_FactoryMagazine_Preview'])
 assert not any(p.material_index==1 for p in bpy.data.objects['AKM_Soviet_Native'].data.polygons)
 assert magazine.hide_render==drum and magazine.hide_get()==drum
 bpy.ops.wm.save_as_mainfile(filepath=str(path));report[str(path.relative_to(O.parent))]={'drum':drum,'factory_hidden':magazine.hide_render,'factory_faces':len(magazine.data.polygons)}
(O/'preview_visibility_validation.json').write_text(json.dumps(report,indent=2));print('AKM_PREVIEW_VISIBILITY_PASS',len(files))
