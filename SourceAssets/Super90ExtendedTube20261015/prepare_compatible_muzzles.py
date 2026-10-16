"""Prepare low-profile exterior variants for the extended tube combination."""
from pathlib import Path
O=Path(__file__).parent
jobs=[('Choke','Super90Choke20261015','ShotgunChoke_Box01','Super90_ChokeTubeFit',.029),
      ('Suppressor','Super90Suppressor20261015','ShotgunSuppressor01','Super90_SuppressorTubeFit',.035)]
for kind,source,old,new,width in jobs:
    target=O/'CompatibleMuzzles'/kind;target.mkdir(parents=True,exist_ok=True)
    text=(O.parent/source/'author_model.py').read_text(encoding='utf-8')
    marker='model_collection = collection' if kind=='Choke' else "model_collection=collection"
    text=text[:text.index(marker)].replace(old,new)
    text=text.replace("shutil.copy2(SOURCE_IMAGE, REFERENCE / 'user_shape_reference.png')",'')
    text=text.replace('z = -.034','z = 0.0').replace('z = -.050','z = 0.0')
    text=text.replace("target, -.015)","target, -.022)").replace("target, .015)","target, .022)")
    text=text.replace("shader = material.node_tree.nodes.get('Principled BSDF')", """nodes=material.node_tree.nodes;nodes.clear()
    shader=nodes.new('ShaderNodeBsdfPrincipled');out=nodes.new('ShaderNodeOutputMaterial')
    material.node_tree.links.new(shader.outputs[0],out.inputs['Surface'])""")
    if kind=='Suppressor':
        text=text.replace('side*.0288','side*.0348').replace('(-.015,-.024,-.033)','(.005,0,-.005)')
    text+=f'''
PARAMS.update(half_width={width},half_height=.012,vertical_center=0.0,top_corner_radius=.006,bottom_corner_radius=.006)
model_collection=collection('ExtendedTubeCompatible')
parts=author_parts(128,model_collection){'+side_details(model_collection)' if kind=='Suppressor' else ''}
lods={{'LOD0':export_mesh(parts,'LOD0')}}
for level,count in [('LOD1',64),('LOD2',32)]:
    c=collection(level);low=author_parts(count,c){'+side_details(c)' if kind=='Suppressor' else ''}
    lods[level]=export_mesh(low,level)
    for obj in low:bpy.data.objects.remove(obj,do_unlink=True)
    bpy.data.collections.remove(c)
select(parts)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'{new}_Editable.blend'))
(ROOT/'authoring_receipt.json').write_text(json.dumps({{'lods':lods,'parameters':PARAMS,
'materials':[n for n,c,r,m in MATERIAL_RECIPES],'runtime_tested':False}},indent=2),encoding='utf-8')
print('{new.upper()}_AUTHORED',flush=True)
'''
    (target/'author_model.py').write_text(text,encoding='utf-8')
