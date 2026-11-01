from pathlib import Path
exec(compile((Path(__file__).parent/'author_elbow.py').read_text().split('keys={};log=[]')[0],'elbow_setup','exec'))
counts=[{'time':f['time'],'folds':len(rig.inverted(base[i],fm))} for i,f in enumerate(frames)]
(O/'Review/anatomy_native_surface.json').write_text(json.dumps(counts,indent=2))
print('NATIVE_CHAIN_FOLDS',max(v['folds'] for v in counts),counts,flush=True)
