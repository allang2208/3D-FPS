from pathlib import Path
import bpy,json
ROOT=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authored/FacilityDetailRepair.blend'))
for kind in ('power_IsolatorCabinet','Hall_MaintenancePanel','Hall_ServiceBench'):
    mesh=bpy.data.objects['SM_FDR_'+kind].data;mesh.calc_tangents()
    zero=[i for i,l in enumerate(mesh.loops) if l.tangent.length<1.e-4 or l.bitangent.length<1.e-4]
    cases=[]
    print('ZERO_LOOP_VECTORS',kind,[(i,list(mesh.loops[i].normal),list(mesh.loops[i].tangent),mesh.loops[i].bitangent_sign) for i in zero[:4]],flush=True)
    for p in mesh.polygons:
        if any(i in zero for i in p.loop_indices):
            cases.append(dict(face=p.index,normal=list(p.normal),area=p.area,smooth=p.use_smooth,vertices=[list(mesh.vertices[i].co) for i in p.vertices],uv=[list(mesh.uv_layers.active.data[i].uv) for i in p.loop_indices]))
            if len(cases)>=3:break
    print('SOURCE_TANGENTS',kind,'loops',len(mesh.loops),'zero',len(zero),'examples',json.dumps(cases),flush=True)
