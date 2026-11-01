from pathlib import Path
exec(compile((Path(__file__).parent/'setup.py').read_text(),'setup','exec'))
for family in ('base','mag10'):
    normal,nentry=entry_for(family,'reload');empty,eentry=entry_for(family,'reload_empty')
    data=[]
    for f in (50,52,54,55,56,60,62,65,70,77,94,105,110):
        a=local_pose(normal,nentry,min(f,60)/30)[0];b=local_pose(empty,eentry,f/30)[0];d=a['WPN_root']@b['WPN_root'].inverted()
        data.append({'frame':f,'cm':{n:(a[n].translation-(d@b[n]).translation).length*100 for n in ('clavicle_l','upperarm_l','lowerarm_l','hand_l')}})
    print('SUPPORT_DIFF',family,json.dumps(data),flush=True)
