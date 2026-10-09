import json,subprocess
from pathlib import Path
O=Path(__file__).parent
scope={'__file__':str(O/'export_equipment_sources.py')}
exec(compile((O/'export_equipment_sources.py').read_text(encoding='utf-8-sig').split('seen=set()')[0],str(O/'export_equipment_sources.py'),'exec'),scope)
c=scope['C'];scope['read'](c['items']['ue_field_gloves']['skin_meshes']['M4'],'skin_ue_field_gloves',True)
subprocess.run([r'C:/Users/allan/AppData/Local/Programs/Python/Python311/python.exe',str(O/'author_fingerless_skin.py')],check=True)
scope={'__file__':str(O/'import_equipment_family.py')}
code=(O/'import_equipment_family.py').read_text(encoding='utf-8-sig').split('# Merge at the end')[0].replace("equipment_manifest.json","equipment_skin_manifest.json")
exec(compile(code,str(O/'import_equipment_family.py'),'exec'),scope)
P=O.parents[1];cp=P/'Content/ColdSteelData/modular_outfits.json';c=json.loads(cp.read_text(encoding='utf-8-sig'));record=json.loads((O/'EquipmentSaved/Super90_skin_ue_field_gloves.json').read_text());receipt=json.loads((O/'import_receipt.json').read_text())
c['items']['ue_field_gloves']['skin_meshes']['Super90']=record['mesh'];c['profiles'][receipt['mesh']].pop('separate_gloves',None)
cp.write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
p=O/'equipment_delivery.json';d=json.loads(p.read_text());d['fingerless_skin_companion']=record['mesh'];d['saved_derivatives']=56;p.write_text(json.dumps(d,indent=2))
print('SUPER90_FINGERLESS_SKIN_SAVED',flush=True)
