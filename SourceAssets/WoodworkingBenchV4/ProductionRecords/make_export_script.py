from pathlib import Path
W=Path(__file__).resolve().parent
s=(W.parent/'woodworking_v2_import_20261007/export_game.py').read_text()
s=s[:s.index('select([table,props]);')]
s=s.replace('WoodworkingBenchV2','WoodworkingBenchV4').replace('==442','==423').replace("copied=[];table=None;material_copies={}","copied=[];tables=[];glass=[];table=None;material_copies={}")
s=s.replace("    if original.name=='Retained_Table':table=o\n    else:","""    blade_flag=mesh.attributes.new('WW_Blade','INT','FACE')
    for value in blade_flag.data:value.value=int(original.name=='Driven circular blade')
    if original.name.startswith('Retained_Table'):
        tables.append(o)
        for i,m in enumerate(mesh.materials):
            if m is None:mesh.materials[i]=bpy.data.materials['WSBench_BenchWood']
    elif any(m and m.name=='Clear saw hood' for m in mesh.materials):glass.append(o)
    else:""")
s=s.replace("    blade_flag=", "    for i,m in enumerate(mesh.materials):\n        if m is None:mesh.materials[i]=next(x for x in mesh.materials if x is not None)\n    blade_flag=")
s=s.replace('assert table\n# Keep',"assert len(tables)==2 and len(glass)==3\n# Keep")
start=s.index("uv=next((u for u in table.data.uv_layers")
end=s.index('\ndef select(objects)',start)
s=s[:start]+"for table in tables:\n"+''.join('    '+l+'\n' for l in s[start:end].splitlines())+s[end:]
s=s.replace("select(copied);", "select(tables);bpy.ops.object.join();table=bpy.context.object\nselect(copied);")
s=s.replace("clone=m.copy();clone.name=", "clone=m.copy();clone.name=")
# Normalize the newer-file Principled weight, which Blender 5.1 reads as zero.
s=s.replace("nodes=clone.node_tree.nodes;links=clone.node_tree.links", "nodes=clone.node_tree.nodes;links=clone.node_tree.links\n                for bsdf in nodes:\n                    if bsdf.type=='BSDF_PRINCIPLED' and 'Weight' in bsdf.inputs:bsdf.inputs['Weight'].default_value=1.0")
s=s.replace("for m in table.data.materials:\n    p=", "for m in dict.fromkeys(table.data.materials):\n    p=")
s=s.replace("R=Path(","R=Path(",1)
s += (W/'export_geometry_tail.py').read_text()
(W/'export_game.py').write_text(s,encoding='utf-8')
print('EXPORT_SCRIPT_READY')
