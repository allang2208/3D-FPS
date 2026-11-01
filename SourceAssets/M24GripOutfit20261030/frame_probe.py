from pathlib import Path
exec(compile((Path(__file__).parent/'setup.py').read_text(),'setup','exec'))
old=pose('idle',0,layer=False)[0];new=pose('idle',0)[0]
rotation=C.to_3x3()@old['WPN_root'].to_3x3()@new['WPN_root'].to_3x3().inverted();target=C@old['hand_r'].translation
newC=rotation.to_4x4();newC.translation=target-rotation@new['hand_r'].translation
print('CURRENT_FRAME',json.dumps({'C_old':[list(v) for v in C],'C_new':[list(v) for v in newC],'hand_raw':list(old['hand_r'].translation),'hand_layer':list(new['hand_r'].translation)}),flush=True)
C=newC
path=next(p for p in roles if p.endswith('A_M24_inspect'));clip=roles[path]
for family in ('base','mag10'):
    entry=next(x for x in ue['profiles'][family] if x['base']==path)
    for t in (0.,.5,1.,1.5,2.,2.5,3.):
        row,_=local_pose(clip,entry,t);view(row,O/'Diagnosis'/('correct_frame_'+family+'_'+str(t)+'.png'))
