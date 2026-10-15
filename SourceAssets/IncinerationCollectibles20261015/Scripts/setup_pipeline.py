"""Create this batch's authoring tools from the established local collectible pipeline."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parents[1]
PREVIOUS=PROJECT/'SourceAssets/PowerCollectibles20261014'
for folder in ('Authored','Export','Textures','Icons','Receipts','Before','UEImportHost/Config'):
    (ROOT/folder).mkdir(parents=True,exist_ok=True)
for name in ('geometry.py','author_models.py','import_assets.py','import_staged.ps1','install_staged.py'):
    text=(PREVIOUS/'Scripts'/name).read_text('utf-8-sig')
    text=text.replace('PowerCollectibles20261014','IncinerationCollectibles20261015').replace('PowerCollectiblesImport','IncinerationCollectiblesImport')
    text=text.replace('PowerCollectibles.Owner','IncinerationCollectibles.Owner').replace('POWER_TOOL','INCINERATION_TOOL').replace('POWER_MODEL','INCINERATION_MODEL')
    if name=='import_assets.py':
        text=text.replace('Import three detailed freight tool models and PBR assets; no map, inventory or play changes.', 'Save six incineration collectible models and shared PBR assets in the content-only host.')
        text=text.replace("ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)\nif ed and ed.get_game_world():raise RuntimeError('Preserve active gameplay')", "# Content-only commandlet host; do not call interactive PIE APIs here.")
        text=text.replace("'T_FT_'+key", "'T_IC_'+key")
    (ROOT/'Scripts'/name).write_text(text,encoding='utf-8-sig' if name.endswith('.ps1') else 'utf-8')
text=(PREVIOUS/'Scripts/render_icons.py').read_text('utf-8')
text=text.replace("OUT=ROOT/'Icons';ICONS=PROJECT/'Content/ColdSteelData/Icons/PowerCollectibles20261014'", "OUT=ROOT/'Icons';ICONS=ROOT/'Icons'")
text=text.replace("OUT=ROOT/'Icons';ICONS=ROOT/'Icons'", "OUT=ROOT/'IconLayoutV2';ICONS=OUT")
text=text.replace("def record():(ROOT/'presentation.json')", "def record():(ROOT/'icon-layout-v2.json')")
text=text.replace("bpy.context.view_layer.update();lo,hi,points=bounds(objects)", "bpy.context.view_layer.update();lo,hi,_=bounds(objects)\n    points=[o.matrix_world@v.co for o in objects for v in o.data.vertices]")
text=text.replace("GRIDS={'FuseSet':(1,1),'PowerModule':(2,1),'StorageCell':(1,2)}", "GRIDS={k:tuple(v['grid']) for k,v in SPEC['assets'].items()}")
text=text.replace("VIEWS={'FuseSet':[((6,-9,14),'icon')],'PowerModule':[((8,-13,15),'icon')],'StorageCell':[((7,-13,7),'icon')]}", "VIEWS={k:[((7,-11,11),'icon')] for k in SPEC['assets']}")
text=text.replace("key=='StorageCell'", "key=='IndustrialFilter'")
text=text.replace("str(path.relative_to(PROJECT/'Content/ColdSteelData')).replace('\\\\','/')", "'Icons/IncinerationCollectibles20261015/'+path.name")
text=text.replace('POWER_PRESENTATION','INCINERATION_PRESENTATION')
text=text.replace('User-requested views and actual transparent inventory art', 'Production inventory icons only')
(ROOT/'Scripts/render_icons.py').write_text(text,encoding='utf-8')
(ROOT/'build_native.ps1').write_text((PREVIOUS/'build_native.ps1').read_text('utf-8-sig'),encoding='utf-8-sig')
host=json.loads((PREVIOUS/'UEImportHost/PowerCollectiblesImport.uproject').read_text('utf-8-sig'))
host['Description']='Content-only incineration collectible authoring host'
(ROOT/'UEImportHost/IncinerationCollectiblesImport.uproject').write_text(json.dumps(host,indent=2),encoding='utf-8')
(ROOT/'UEImportHost/Config/DefaultEngine.ini').write_text('[/Script/Engine.RendererSettings]\nr.Substrate=True\nr.Substrate.ProjectGBufferFormat=0\n\n[/Script/WindowsTargetPlatform.WindowsTargetSettings]\nDefaultGraphicsRHI=DefaultGraphicsRHI_DX12\n+D3D12TargetedShaderFormats=PCD3D_SM6\n',encoding='utf-8')
print('INCINERATION_PIPELINE_PREPARED')
