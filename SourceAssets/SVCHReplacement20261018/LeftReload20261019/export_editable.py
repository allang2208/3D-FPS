"""Save an editable action source with the installed native V9, without reimport."""
from pathlib import Path
O=Path(__file__).parent;P=O.parents[2]
source=P/'SourceAssets/SVCHRefinement20261018/R9ReloadGrip/export_editable.py'
code=source.read_text().replace('profile_reload_grip.json','profile_left_reload.json').replace('SVCH_R9_','SVCH_LeftReload_')
code=code.replace("O.parent / 'R8Surface/SVCH_R8Surface.blend'","O.parent / 'RealSights20261019/SVCH_RealFoldingSights_Editable.blend'")
code=code.replace('world.append(world[parent] @ local[j] if parent >= 0 else local[j])', '''if parent < 0:
                world.append(local[j])
            else:
                pp,pq,ps=world[parent].decompose()
                lp,lq,ls=local[j].decompose()
                world.append(Matrix.LocRotScale(world[parent] @ lp,pq @ lq,Vector(tuple(a*b for a,b in zip(ps,ls)))))''')
exec(compile(code,str(source),'exec'),globals())
