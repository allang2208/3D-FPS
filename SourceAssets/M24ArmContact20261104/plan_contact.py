from pathlib import Path
__file__=str(Path(__file__).parent/'common.py')
exec(compile(Path(__file__).read_text(),'contact setup','exec'))
out={}
for family in ('base','mag10'):
    row,loc=compose(entry(family,'reload'),18/30);pts=skin_corrected(row)
    vs,fs=weapon(row,family)['magazine'];ids=np.unique(np.array(fs).ravel());verts=vs[ids]
    fw=(row['WPN_FrontSight'].translation-row['WPN_RearSight'].translation).normalized()
    ev,evec=np.linalg.eigh(np.cov(verts.T));thin=Vector(evec[:,0]);up=thin.cross(fw).normalized()
    if up.dot((row['WPN_root']@rest['WPN_root'].inverted()).to_quaternion()@Vector((0,0,1)))<0:up=-up
    thin=fw.cross(up).normalized();B=Matrix((fw,thin,up));center=Vector(verts.mean(0))
    palm=Vector(pts[anchors[family]['old']['palm']].mean(0))
    H=row['hand_l'].translation;F=(row['middle_01_l'].translation-H).normalized()
    W=(row['index_01_l'].translation-row['pinky_01_l'].translation).normalized();N=F.cross(W).normalized()
    out[family]={'bounds':[(B@(Vector(v)-center)*1000)[:] for v in [verts.min(0),verts.max(0)]],
       'actual_bounds':np.array([list(B@(Vector(v)-center)*1000) for v in verts]).min(0).tolist()+np.array([list(B@(Vector(v)-center)*1000) for v in verts]).max(0).tolist(),
       'hand':list(B@(H-center)*1000),'palm':list(B@(palm-center)*1000),'palmF':list(B@F),'palmN':list(B@N),
       'finger_mid':{d:list(B@(row[d+'_02_l'].translation-center)*1000) for d in FINGERS}}
(TASKOUT/'contact_layout.json').write_text(json.dumps(out,indent=2));print('LAYOUT',json.dumps(out),flush=True)
