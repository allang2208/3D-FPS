from pathlib import Path
O=Path(__file__).parent; author=O.parent/'Super90Speedloader20261007/author_speedloader.py'
s={'__file__':str(author)}
exec(compile(author.read_text().split('def local_rows(')[0],str(author),'exec'),s)
bpy=s['bpy'];name='WPN_SOCKET_Magazine'
print('NATIVE_HELPER',name,'parent',s['parents'][name],flush=True)
for ob in bpy.data.objects:
    if ob.type!='MESH':continue
    vg=ob.vertex_groups.get(name)
    if vg:
        weights=[(v.index,g.weight) for v in ob.data.vertices for g in v.groups if g.group==vg.index and g.weight>0]
        print('WEIGHTED',ob.name,len(weights),flush=True)
print('AUTHOR_INPUT_READ',flush=True)
