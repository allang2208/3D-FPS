from pathlib import Path
exec(compile((Path(__file__).parent/'surface.py').read_text(),'surface','exec'))
c=json.load(gzip.open(O/'quick_melee_patch.json.gz','rt'))['skeleton_base_balanced'];vs=geometry['stock'][0]
for t in (.10,.11666666666666667,.125,.15,.25,.45,.4583333333333333,.4666666666666667,.475,.4833333333,.50,.5166666667):
    row,_=compose(c,t);inv=rest['WPN_root']@row['WPN_root'].inverted();print('GUNPOS',round(t,3),[(n,[round(x*1000,1) for x in (inv@row[n]).translation]) for n in ('hand_r','thumb_01_r','thumb_02_r','thumb_03_r','index_03_r')],flush=True)
print('STOCK_X_RANGE',min(v.x for v in vs)*1000,max(v.x for v in vs)*1000,flush=True)
