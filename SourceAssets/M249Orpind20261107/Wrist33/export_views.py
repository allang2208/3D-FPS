import pickle,sys
from pose import *
d=pickle.load(open(r/'current.pkl','rb'));label=sys.argv[1] if len(sys.argv)>1 else 'before'
cache=pickle.load(open(r/'candidate.pkl','rb')) if label=='candidate' else None
views={}
for family in d['profiles']:
    for role,at in [('idle',0),('reload',1.13),('reload_empty',.9)]:
        if role!='idle' and family!='base':continue
        path=next(p for p in d['clips'] if p.endswith('A_M249_'+role));c=d['clips'][path];t=np.array(c['times'])
        w=cache[(family,path)] if cache else compose(layer(np.array(c['frames']),path,d['profiles'][family],d['names'],t),d['parents'])
        views[family+'_'+role]=w[np.argmin(abs(t-at))]
pickle.dump(views,open(r/(label+'_views.pkl'),'wb'))
