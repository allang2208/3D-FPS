"""Separate ground/circulation and vegetation authoring passes for the shared band."""
from pathlib import Path
R=Path(__file__).resolve().parent;p=R/'layout_riverfront.py';s=p.read_text(encoding='utf8')
if 'vegetation_jobs=[]' not in s:
    s=s.replace('all_occupied=[]\nfor zid','all_occupied=[];vegetation_jobs=[];circulation=[]\nfor zid')
    s=s.replace('    lawns=region.difference(paths).difference(unary_union(core))','    paths=paths.difference(unary_union(circulation));circulation.append(paths)\n    lawns=region.difference(paths).difference(unary_union(core))\n    vegetation_jobs.append((zid,region,center,lawns))')
    start=s.index('    plantable=lawns.buffer(-1.5)');end=s.index('\n# Preserve the street',start)
    vegetation=s[start:end]
    s=s[:start]+'''\nall_paths=unary_union(circulation)
for row in old['plants']:
    if row['zone']=='P4':
        m=M[row['mesh']];radius=max(m['max'][0]-m['min'][0],m['max'][1]-m['min'][1])/200*row['scale'];all_occupied.append((row['p'][:2],radius))
for job_index,(zid,region,center,lawns) in enumerate(vegetation_jobs):
    zbase=-106.25;lawns=lawns.difference(all_paths);paths=circulation[job_index]
    zone=next(z for z in out['zones'] if z['id']==zid);zone['lawn_triangles']=surfaces(lawns)
'''+vegetation+s[end:]
    p.write_text(s,encoding='utf8')
print('RIVERFRONT_AUTHOR_SOURCE_UPDATED')
