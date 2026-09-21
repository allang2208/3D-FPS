"""Read back only the five optic meshes and the material outputs requested by user."""
from pathlib import Path
import json,unreal as u
O=Path(__file__).parent
source=(O/'inspect_finish.py').read_text(encoding='utf-8').replace("O/'before.json'","O/'after.json'")
exec(compile(source,str(O/'inspect_finish.py'),'exec'),{'__file__':str(O/'inspect_finish.py')})
before=json.loads((O/'before.json').read_text());after=json.loads((O/'after.json').read_text())
results={};L=u.MaterialEditingLibrary
for key,idx in [('holographic',0),('panoramic_red_dot',2),('prism_scope_2x',2),('lpvo_1_6x',2),('lpvo_ring',0)]:
    slots=after['meshes'][key]['slots'];old=before['meshes'][key]['slots'];target='A762_'+key+'_'+str(idx)
    assert [x['slot'] for x in slots]==[x['slot'] for x in old],key+' slot order changed'
    same=[]
    for s,p in zip(slots,old):
        if s['slot']!=target:
            assert s['material']==p['material'],key+' optical material changed'
            same.append(s['slot'])
    path=next(x['material'] for x in slots if x['slot']==target)
    assert '/OpticFinish06/' in path,key+' material not applied'
    m=after['materials'][path];nodes=m['nodes']
    assert abs(m['parameters']['scalar']['A762CoatingMetallic']-.83)<1e-6
    assert abs(m['parameters']['scalar']['A762CoatingRoughness']-.34)<1e-6
    assert all(abs(a-b)<1e-6 for a,b in zip(m['parameters']['vector']['A762CoatingColor'],[.021,.028,.04,1]))
    for n in nodes.values():
        assert 'MF_PhongToMetalRoughness' not in n.get('material_function',''),key+' legacy conversion remains'
        assert '/AttachmentFinish20260913/M4/' not in n.get('texture',''),key+' M4 coating texture remains'
    for name in ['BASE_COLOR','ROUGHNESS','METALLIC','SPECULAR']:
        blend=nodes[m['outputs'][name]['node']]
        assert blend['class']=='MaterialExpressionLinearInterpolate'
        alpha=nodes[blend['inputs'][2]]
        assert alpha['class']=='MaterialExpressionMultiply',key+' original region/mark mask disconnected'
    if key in ['prism_scope_2x','lpvo_1_6x','lpvo_ring']:
        assert any(n['class']=='MaterialExpressionVertexColor' for n in nodes.values())
    results[key]={'material':path,'optical_slots_unchanged':same,'receiver_pbr_match':True,'legacy_m4_finish_removed':True,'region_mask_retained':True}
(O/'checked.json').write_text(json.dumps({'scope':'saved mesh bindings and material graphs only','results':results,'game_tested':False,'rendered':False},indent=2),encoding='utf-8')
u.log('A762_OPTIC_FINISH06_CHECKED: 5 mesh bindings, receiver PBR, original region masks and optical slots')
