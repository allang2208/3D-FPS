from pathlib import Path
R=Path(__file__).resolve().parent
steps=["surfaces()"]+[f"foliage('{k}')" for k in ('TreeA','TreeB','Shrub','GroundA','GroundB','Grass','Flower')]+['water()']+[f'meshes({i},{i+3})' for i in range(0,23,3)]+[f"assembly('{k}')" for k in ('P1','P2','P3','P4','P5','P6')]+['finish()']
for i,step in enumerate(steps):
    (R/f'batch_{i:02}.py').write_text("import runpy\nfrom pathlib import Path\nr=runpy.run_path(str(Path(__file__).resolve().parent/'build_assets.py'))\nexec("+repr(step)+",r)\nprint('URBAN_BATCH_DONE',"+str(i)+",flush=True)\n",encoding='utf8')
print('PRODUCTION_BATCHES',len(steps))
