from pathlib import Path
import json,shutil
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Authored';TEX=OUT/'Textures';TEX.mkdir(parents=True,exist_ok=True)
BASE=ROOT.parent;WOOD=BASE/'AKMIntegration20260910/Redwood/Wood051';SURFACE=BASE/'DungeonWorkshopSurface20260921'
maps={}
for ch,suffix in [('BaseColor','Color'),('Normal','NormalGL'),('Roughness','Roughness')]:
    dest=TEX/('BenchWood_'+ch+'.jpg');shutil.copy2(WOOD/('Wood051_2K-JPG_'+suffix+'.jpg'),dest);maps[ch]=str(dest)
mask=TEX/'MetalImperfection_MaskR_RoughnessG.png';shutil.copy2(SURFACE/'Authored/Textures/MetalImperfection_MaskR_RoughnessG.png',mask)
recipe=json.loads((SURFACE/'Authored/material-manifest.json').read_text())
materials={
 'BenchWood':dict(maps=maps,metallic=0,roughness_scale=.78,roughness_bias=.13,normal_strength=.82,
                   color_tint=[1.40,1.50,1.62],imperfection=str(mask),worktop=True),
 'LampPaint':dict(maps=recipe['SheetPaint']['maps'],metallic=0,roughness_scale=.80,roughness_bias=.08,
                  normal_strength=.32,color_tint=[.76,.88,.83]),
 'CableRubber':dict(maps=recipe['Grip']['maps'],metallic=0,roughness_scale=.78,roughness_bias=.14,
                    normal_strength=.25,color_tint=[.50,.54,.58]),
 'Reflector':dict(color=[.64,.65,.58],metallic=0,roughness=.40),
 'SocketCeramic':dict(color=[.56,.54,.47],metallic=0,roughness=.58),
 'LampBulb':dict(color=[.68,.63,.53],metallic=0,roughness=.40,emission=[1.10,.90,.65]),
 'FreshCut':dict(color=[.27,.20,.125],metallic=0,roughness=.86),
 'IngrainedCut':dict(color=[.024,.018,.011],metallic=0,roughness=.77),
}
endgrain=json.loads((BASE/'DungeonWorkshopTools20260921/Authored/material-manifest.json').read_text())['EndGrain']
materials['EndGrain']=dict(endgrain,color_tint=[.60,.58,.56],normal_strength=.58,roughness_scale=.85,roughness_bias=.10)
(OUT/'material-manifest.json').write_text(json.dumps(materials,indent=2),encoding='utf-8')
print('BENCH_LAMP_MATERIAL_SOURCES_PREPARED',len(materials))
