from pathlib import Path
exec(compile((Path(__file__).parent/'setup.py').read_text(),'setup','exec'))
folder=O/'Diagnosis';folder.mkdir(exist_ok=True);out={}
for family,suffix in (('base',''),('mag10','_mag10')):
    out[family]={};normal,nentry=entry_for(family,'reload'+suffix);empty,eentry=entry_for(family,'reload_empty'+suffix)
    anchor=row_at(family,'reload'+suffix,normal['keys']-1)['WPN_root']
    for role,clip in [('reload'+suffix,normal),('reload_empty'+suffix,empty)]:
        data=[]
        for frame in (0,8,14,16,18,20,21,22,24,25.25,27,29,30,38,40,44,50,54,55,60,65,70,75,80,85,90,95,100,105,110):
            if frame>clip['keys']-1:continue
            row=row_at(family,role,frame);wpn=row['WPN_root'];mag=wpn.inverted()@row['WPN_Magazine'];hand=wpn.inverted()@row['hand_l'];ref=row_at(family,'reload'+suffix,min(frame,normal['keys']-1))['WPN_root']
            data.append({'frame':frame,'weapon_camera_cm':list(C@wpn.translation),'normal_difference_cm':(wpn.translation-ref.translation).length*100,'normal_rotation_degrees':math.degrees(2*math.acos(min(1,abs(wpn.to_quaternion().dot(ref.to_quaternion()))))),'mag_relative_cm':list(mag.translation*100),'hand_relative_cm':list(hand.translation*100)})
        out[family][role]={'keys':clip['keys'],'rows':data}
    if family=='base':
        for role in ('reload','reload_empty'):
            for frame in (18,21,24,54,70,85):
                clip,_=entry_for(family,role)
                if frame>clip['keys']-1:continue
                view(row_at(family,role,frame),folder/(role+'_'+str(frame)+'.png'))
(O/'diagnosis.json').write_text(json.dumps(out,indent=2));print('M24_RELOAD_DIAGNOSIS',json.dumps({k:{r:{'keys':v['keys'],'max_gun_difference_cm':max(x['normal_difference_cm'] for x in v['rows']),'max_gun_rotation_difference':max(x['normal_rotation_degrees'] for x in v['rows'])} for r,v in data.items()} for k,data in out.items()}),flush=True)
