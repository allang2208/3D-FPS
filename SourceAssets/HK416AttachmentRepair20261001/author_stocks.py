"""Re-author only the four HK416 stock seats, without changing animation assets."""
from pathlib import Path
recipe=Path(__file__).parent.parent/'HK416CommonAttachments20260930/author_models.py'
scope={'__file__':str(recipe),'__name__':'hk416_stock_repair'}
exec(compile(recipe.read_text().split("keys=['tactical_vertical'")[0],str(recipe),'exec'),scope)
exec('''
O=S/'HK416AttachmentRepair20261001';(O/'Meshes').mkdir(exist_ok=True)
for key in stock_interfaces.STOCK_FRONT:
 o=load(key)
 collar,fit=stock_interfaces.fit_stock(key,o,R,A,H/'HK416_Gameplay_Editable.blend',metal)
 bindings={s['slot']:s['material'] for s in sources[key]['slots']};bindings[metal.name]=None
 export(key,[o,collar],bindings)
 report['parts'][key]['interface']=fit
(O/'stock_models.json').write_text(json.dumps(report,indent=2))
print('HK416_FOUR_STOCK_SEATS_AUTHORED',flush=True)
''',scope)
