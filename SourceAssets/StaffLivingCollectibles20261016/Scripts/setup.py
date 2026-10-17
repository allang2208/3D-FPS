"""Original living-area collectibles. Create authoring directories and owned helper copy."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
for folder in ('Authored','Export','Textures','Icons','Receipts','UEImportHost/Config'):
    (ROOT/folder).mkdir(parents=True,exist_ok=True)
source=PROJECT/'SourceAssets/IncinerationCollectibles20261015/VisualRefineV2/Scripts'
geometry=(source/'geometry.py').read_text('utf-8-sig')
(ROOT/'Scripts/geometry.py').write_text(geometry,encoding='utf-8')
assets={
 'Perfume':dict(id='search_private_perfume',name='珍藏香水',mesh='SM_Living_Perfume',grid=[1,2],rarity='rare',value=900),
 'Laptop':dict(id='search_business_laptop',name='商务笔记本电脑',mesh='SM_Living_Laptop',grid=[3,2],rarity='epic',value=3600),
 'MusicPlayer':dict(id='search_portable_music_player',name='便携音乐播放器',mesh='SM_Living_MusicPlayer',grid=[1,2],rarity='rare',value=1200),
 'Camera':dict(id='search_compact_camera',name='袖珍数码相机',mesh='SM_Living_CompactCamera',grid=[2,2],rarity='epic',value=2400)}
(ROOT/'design.json').write_text(json.dumps(dict(version=1,assets=assets,
 intent='Non-equipment valuables from private living quarters; no clothing or equipped-item entries.',
 authoring='Precision hard-surface geometry, editable assemblies, original CS brand',
 stage='Model-first production; random-pool proposal is separate from installed loot configuration',
 details={'Laptop':['independent keycaps and legends','milled keyboard recess','real port apertures with contacts','hinges and editable lid pose','speaker perforations','underside feet and screws','anodized shell and polymer deck'],
 'Perfume':['continuous outer and inner glass walls','thick glass heel','separate liquid and meniscus','dip tube','atomizer with bore','collar ribs','faceted cap with socket','metal and paper labels'],
 'MusicPlayer':['laminated display','mechanical buttons','headphone socket and contact rings','USB port and tongue','memory-slot cover','knurled volume wheel','rear fasteners'],
 'Camera':['telescopic lens rings','recessed optical element','lens coatings','grip texture','mode dial and shutter','flash diffuser','rear controls and display','battery compartment and tripod socket']},
 runtime_tested=False),ensure_ascii=False,indent=2),encoding='utf-8')
host={'FileVersion':3,'EngineAssociation':'5.8','Category':'Asset Authoring','Description':'Living collectibles content-only authoring','Plugins':[{'Name':'PythonScriptPlugin','Enabled':True},{'Name':'EditorScriptingUtilities','Enabled':True}]}
(ROOT/'UEImportHost/LivingCollectiblesImport.uproject').write_text(json.dumps(host,indent=2),encoding='utf-8')
(ROOT/'UEImportHost/Config/DefaultEngine.ini').write_text('[/Script/Engine.RendererSettings]\nr.Substrate=True\nr.Substrate.ProjectGBufferFormat=0\n[/Script/WindowsTargetPlatform.WindowsTargetSettings]\nDefaultGraphicsRHI=DefaultGraphicsRHI_DX12\n+D3D12TargetedShaderFormats=PCD3D_SM6\n',encoding='utf-8')
print('LIVING_AUTHORING_READY')
