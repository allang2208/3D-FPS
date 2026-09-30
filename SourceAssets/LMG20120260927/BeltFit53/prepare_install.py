"""Create this revision's native import/save entry points from the proven buffer route."""
from pathlib import Path
O=Path(__file__).parent
s=(O.parent/'BeltRebuild52/install.py').read_text().replace('BeltRebuild52','BeltFit53').replace('BELT52','BELT53').replace('_B52_','_B53_').replace("O/'source.json'","O/'source_compat.json'")
s=s.replace(" exec(compile((O/'materials.py').read_text(),str(O/'materials.py'),'exec'),{'__file__':str(O/'materials.py'),'__name__':'__main__'})\n",'')
s=s.replace("materials=json.loads((O/'materials.json').read_text())","materials=json.loads((O.parent/'BeltRebuild52/materials.json').read_text())")
s=s.replace(" expected={'LMG201_Belt_%02d'%i for i in range(9)}|{'New_LMG201_Belt_%02d'%i for i in range(9) if i!=6}"," with gzip.open(O/'mesh_buffers.json.gz','rt') as f:expected={r['bone'] for r in json.load(f)}")
s=s.replace('two receiver cells; no cloth atlas','articulated links and continuous pouch tail').replace('receiver run, nine-cell feed pool','receiver run and fourteen-cell circulation')
(O/'install.py').write_text(s)
(O/'prepare.py').write_text("from pathlib import Path\nimport sys\nsys.path.insert(0,str(Path(__file__).parent))\nimport install\ninstall.prepare()\n")
(O/'publish.py').write_text("from pathlib import Path\nimport sys\nsys.path.insert(0,str(Path(__file__).parent))\nimport install\ninstall.publish()\n")
ps=(O.parent/'BeltRebuild52/run_publish.ps1').read_text(encoding='utf-8-sig')
for step in ['prepare','publish','install_motion','read_saved']:
 (O/('run_'+step+'.ps1')).write_text(ps.replace('publish.py',step+'.py').replace('publish.log',step+'.log').replace('publish_console.log',step+'_console.log').replace('Belt52','Belt53'),encoding='utf-8-sig')
(O/'run_build.ps1').write_text((O.parent/'BeltRebuild52/run_build.ps1').read_text(encoding='utf-8-sig'),encoding='utf-8-sig')
(O/'read_saved.py').write_text((O.parent/'BeltRebuild52/read_saved.py').read_text().replace('BELT52','BELT53'))
