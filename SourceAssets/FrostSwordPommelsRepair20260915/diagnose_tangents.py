import bpy,json
from pathlib import Path
P=Path(__file__).parent
for key in ['ballast_hardened','ballast_rune','ballast_magic_orb']:
    bpy.ops.wm.open_mainfile(filepath=str(P/key/'FrostPommel_Editable.blend'))
    mesh=bpy.data.objects['SM_FrostPommel_'+key].data
    mesh.calc_tangents(uvmap=mesh.uv_layers[0].name)
    bad=[]
    for f in mesh.polygons:
        zero=[i for i in f.loop_indices if mesh.loops[i].tangent.length<.0001]
        if zero:
            bad.append({'face':f.index,'material':f.material_index,'area':f.area,'uv':[list(mesh.uv_layers[0].data[i].uv) for i in f.loop_indices]})
    print('TANGENT_SOURCE',key,json.dumps({'zero_faces':len(bad),'examples':bad[:5]}),flush=True)
