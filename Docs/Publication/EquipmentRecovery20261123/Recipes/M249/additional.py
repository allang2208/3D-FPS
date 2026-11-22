from shared import *
a=read(W/'inventory.json');add={}
def collect(v,stage):
 if not isinstance(v,dict):return
 for k,value in v.items():
  key=k.replace('\\','/')
  if key.startswith('/Game/') and own(key):key=game(key)
  if key in a and 'expected' not in a[key] and isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value,re.I):
   add[key]=dict(expected=value.lower(),version=stage)
  elif isinstance(value,dict):collect(value,stage)
for z in sorted((p for p in S.iterdir() if re.search(r'\d+$',p.name)),key=lambda p:int(re.search(r'\d+$',p.name)[0])):
 for f in sorted(z.glob('*hash*.json'))+list(z.glob('*receipt.json'))+list(z.glob('saved.json')):
  collect(read(f),str(f.relative_to(S)))
for key,row in add.items():
 row['current']=a[key]['current']
write('additional-checkpoints.json',add)
print('extra',len(add),'matched',sum(v['expected']==v['current'] for v in add.values()))
print([(k.split('/')[-1],v['version']) for k,v in add.items() if v['expected']!=v['current']][:28])
