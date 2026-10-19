finish=json.loads((O/'finish.json').read_text())
for part,f in finish.items():
 if part not in mats:continue
 bs=mats[part].node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*f['color'],1);bs.inputs['Roughness'].default_value=f['roughness']
