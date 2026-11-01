from pathlib import Path
exec(compile((Path(__file__).parent/'audit.py').read_text().split("\nif __name__=='__main__':")[0],'audit','exec'))
X,row=source_pose('skeleton_base','idle',0.)
for variant in ('balanced','phantom','stable'):render(X,'idle_'+variant+'_back',variant=variant,view='back')
trigger=bpy.data.objects['M24_trigger'];tv=[v.co[:] for v in trigger.data.vertices];tf=[list(p.vertices) for p in trigger.data.polygons];tree=BVHTree.FromPolygons(tv,tf)
ids=np.flatnonzero(W[:,indices['index_03_r']]>.5)
distance=[tree.find_nearest(Vector(X[i]))[3]*1000 for i in ids]
(O/'trigger_contact.json').write_text(json.dumps({'index_distal_vertices':len(ids),'index_distal_min_gap_mm':min(distance),'index_distal_median_gap_mm':float(np.median(distance))},indent=2))
print('TRIGGER_GAP',min(distance),float(np.median(distance)),flush=True)
