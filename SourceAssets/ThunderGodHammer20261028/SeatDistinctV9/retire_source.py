"""Archive and remove only the two retired adaptations from the editable C6 source."""
import bpy,json,hashlib,shutil,datetime,os
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[2];S=P.parent/'SeatInlaidC6'
ids=('ancient_breaking_seal_seat','storm_drive_seat')
if not json.loads((P/'retirement_assets_receipt.json').read_text(encoding='utf-8'))['complete']:raise RuntimeError('Retire runtime packages first')
archive=R/'trash/thunder-seat-retired-20261031'/('Source-'+datetime.datetime.now().strftime('%H%M%S'));archive.mkdir(parents=True)
receipt=dict(complete=False,files=[],removed_files=[],removed_objects=[],bytes=0,retained=['factory reference','reinforced_block','ribbed_light','laminated_damper','historical receipts and earlier revisions'])
def record():(P/'retirement_source_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
def backup(path):
 path=path.resolve()
 if not path.is_relative_to(S.resolve()):raise RuntimeError('Outside source retirement boundary '+str(path))
 dst=archive/path.relative_to(S.resolve());dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dst)
 raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest()
 if hashlib.sha256(dst.read_bytes()).hexdigest()!=digest:raise RuntimeError('Archive copy failed '+str(path))
 receipt['files'].append(dict(source=str(path),archive=str(dst),bytes=len(raw),sha256=digest));receipt['bytes']+=len(raw);record();return raw
blend=S/'ThorSeats_InlaidC6.blend';original=hashlib.sha256(backup(blend)).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(blend));bpy.context.preferences.filepaths.save_version=0
for id in ids:
 name='SM_ThunderGodHammer_head_mount_'+id;obj=bpy.data.objects.get(name)
 if not obj:raise RuntimeError('Expected adaptation missing '+name)
 mesh=obj.data;bpy.data.objects.remove(obj,do_unlink=True)
 if mesh.users==0:bpy.data.meshes.remove(mesh)
 mat=bpy.data.materials.get('M_ThorSeatC6_'+id)
 if mat and mat.users==0:bpy.data.materials.remove(mat)
 for image in list(bpy.data.images):
  if id in image.name and image.users==0:bpy.data.images.remove(image)
 receipt['removed_objects'].append(name)
pending=S/'ThorSeats_InlaidC6.retirement-pending.blend';bpy.ops.wm.save_as_mainfile(filepath=str(pending))
if hashlib.sha256(blend.read_bytes()).hexdigest()!=original:raise RuntimeError('Concurrent C6 source edit preserved')
os.replace(pending,blend)
for name in ('model_manifest.json','texture_manifest.json'):
 path=S/name;raw=backup(path);data=json.loads(raw.decode('utf-8-sig'));data['parts']=[r for r in data['parts'] if r['id'] not in ids]
 data['retirement_note']='2026-10-31: Thor-specific ancient_breaking_seal_seat and storm_drive_seat removed; original sources archived under trash/thunder-seat-retired-20261031.'
 if path.read_bytes()!=raw:raise RuntimeError('Concurrent '+name)
 path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for name in ('design.py','import_assets.py','publish.py'):
 path=S/name;raw=backup(path);text=raw.decode('utf-8-sig')
 if name=='design.py':text='\n'.join(line for line in text.split('\n') if not any("dict(id='"+id+"'" in line for id in ids))
 elif name=='import_assets.py':text=text.replace('five selected C seats','three retained C seats').replace("len(manifest['parts'])==5","len(manifest['parts'])==3")
 else:text=text.replace("len(receipt['models'])==5 and len(receipt['textures'])==15","len(receipt['models'])==3 and len(receipt['textures'])==9").replace('PUBLISHED_FIVE_INLAID_C6_SEATS','PUBLISHED_THREE_RETAINED_INLAID_C6_SEATS')
 if path.read_bytes()!=raw:raise RuntimeError('Concurrent '+name)
 path.write_text(text,encoding='utf-8')
for id in ids:
 files=[S/'Export'/('SM_ThunderGodHammer_head_mount_'+id+'.fbx'),S/'Data'/(id+'.npz')]
 files += [S/'Textures'/('T_ThorSeatC6_'+id+'_'+kind+'.png') for kind in ('BaseColor','ORM','Normal')]
 for path in files:
  raw=backup(path)
  if path.read_bytes()!=raw:raise RuntimeError('Concurrent source '+str(path))
  path.unlink();receipt['removed_files'].append(str(path));record()
receipt['complete']=True;record();print('THUNDER_TWO_C6_SOURCE_ADAPTATIONS_RETIRED',flush=True)
