"""Create the six-material production workspace from established local tooling."""
from pathlib import Path
import json, shutil
ROOT=Path(__file__).resolve().parents[1]; PROJECT=ROOT.parents[1]
for name in ('Textures','Authored','Export','Icons','Receipts','Before','UEImportHost/Config'):
    (ROOT/name).mkdir(parents=True,exist_ok=True)
previous=PROJECT/'SourceAssets/PowerCollectibles20261014/Scripts'
shutil.copy2(previous/'geometry.py',ROOT/'Scripts/geometry.py')
render=(previous/'render_icons.py').read_text('utf8')
render=render.replace('PowerCollectibles20261014','AlchemyMaterials20261015').replace("GRIDS={'FuseSet':(1,1),'PowerModule':(2,1),'StorageCell':(1,2)}","GRIDS={k:tuple(v['grid']) for k,v in SPEC['assets'].items()}")
render=render.replace("VIEWS={'FuseSet':[((6,-9,14),'icon')],'PowerModule':[((8,-13,15),'icon')],'StorageCell':[((7,-13,7),'icon')]}","VIEWS={k:[((4,-14,7) if v['grid']==[1,2] else (5,-13,11),'icon')] for k,v in SPEC['assets'].items()}")
render=render.replace("forward=(0,0,1) if key=='StorageCell' else (-1,0,0)","forward=(0,0,1) if gh>gw else (-1,0,0)")
render=render.replace("scene.cycles.max_bounces=8","scene.cycles.max_bounces=16;scene.cycles.transmission_bounces=12;scene.cycles.transparent_max_bounces=16")
render=render.replace('ONLY_ICON=None',"ONLY_ICON=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else None")
render=render.replace('direction=VIEWS[key][0][0]',"direction=(5,-13,11) if key=='Stabilizer' else VIEWS[key][0][0]")
render=render.replace('forward=(0,0,1) if gh>gw else (-1,0,0)',"forward=(1,0,0) if key=='Stabilizer' else (0,0,1) if gh>gw else (-1,0,0)")
(ROOT/'Scripts/render_icons.py').write_text(render,'utf8')
host={'FileVersion':3,'EngineAssociation':'5.8','Category':'Asset Authoring','Description':'Six alchemy ingredients content-only production host','Plugins':[{'Name':x,'Enabled':True} for x in ('PythonScriptPlugin','EditorScriptingUtilities')]}
(ROOT/'UEImportHost/AlchemyMaterialsImport.uproject').write_text(json.dumps(host,indent=2),'utf8')
(ROOT/'UEImportHost/Config/DefaultEngine.ini').write_text('[/Script/Engine.RendererSettings]\nr.Substrate=True\nr.Substrate.ProjectGBufferFormat=0\n\n[/Script/WindowsTargetPlatform.WindowsTargetSettings]\nDefaultGraphicsRHI=DefaultGraphicsRHI_DX12\n+D3D12TargetedShaderFormats=PCD3D_SM6\n','utf8')
ps=(previous/'import_staged.ps1').read_text('utf-8-sig').replace('PowerCollectiblesImport.uproject','AlchemyMaterialsImport.uproject')
ps=ps.replace("'-nosound'","'-nosound' '-LiveCoding=false'")
(ROOT/'Scripts/import_staged.ps1').write_text(ps,'utf-8-sig')
install=(previous/'install_staged.py').read_text('utf8').replace('PowerCollectibles20261014','AlchemyMaterials20261015')
install=install.replace('AlchemyMaterials20261015/V1','AlchemyMaterials20261015/V3')
(ROOT/'Scripts/install_staged.py').write_text(install,'utf8')
build=(previous.parent/'build_native.ps1').read_text('utf-8-sig')
(ROOT/'build_native.ps1').write_text(build,'utf-8-sig')
print('ALCHEMY_WORKSPACE_READY')
