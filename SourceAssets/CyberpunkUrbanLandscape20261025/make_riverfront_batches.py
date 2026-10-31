from pathlib import Path
R=Path(__file__).resolve().parent
prefix="from pathlib import Path\nimport runpy\nR=Path(__file__).resolve().parent\nr=runpy.run_path(str(R/'build_assets.py'))\n"
steps=[]
for z in ('P1','P2','P3','P5','P6'):steps.append("i=next(i for i,row in enumerate(r['G']['meshes']) if row['key']=="+repr(z+'_Ground')+")\nr['meshes'](i,i+1)\n")
for z in ('P1','P2','P3','P4','P5','P6'):steps.append("r['assembly']("+repr(z)+")\n")
steps.append("r['finish']()\n")
for i,step in enumerate(steps):(R/f'riverfront_batch_{i:02}.py').write_text(prefix+step+f"print('RIVERFRONT_BATCH_SAVED',{i},flush=True)\n",encoding='utf8')
print('RIVERFRONT_BATCHES_PREPARED',len(steps))
