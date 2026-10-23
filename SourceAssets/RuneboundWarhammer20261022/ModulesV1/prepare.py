"""Freeze the standard split/icon authors with this hammer's measured mounting planes."""
from pathlib import Path
P=Path(__file__).resolve().parent
ROOT=P.parents[2]
source=(ROOT/'SourceAssets/SteelWarhammer20261014/ModulesV1/author_modules.py').read_text(encoding='utf-8-sig')
source=source.replace("SOURCE=P.parent/'SprintDragV1/RigSource/SteelWarhammer_Editable.blend'", "SOURCE=P.parent/'RuneboundWarhammer_Editable.blend'")
source=source.replace("original=bpy.data.objects['SM_SteelWarhammer'];rig=original.parent\nsource=original.data.copy();source.transform(rig.data.bones['WPN_root'].matrix_local.inverted());source.update()", "original=bpy.data.objects['SM_RuneboundWarhammer']\nsource=original.data.copy();source.update()")
source=source.replace("'shaft':(2,.820),'neck':(2,.865),'left':(0,-.040),'right':(0,.040)", "'shaft':(2,.780),'neck':(2,.842),'left':(0,-.0354452141),'right':(0,.0345547859)")
source=source.replace("'hammer_heads':(0,0,.925),'neck':(0,0,.865)", "'hammer_heads':(0,0,.916),'neck':(0,0,.842)")
source=source.replace("'shaft':(0,0,.820)", "'shaft':(0,0,.780)")
source=source.replace("'SM_Warhammer_'", "'SM_RuneboundWarhammer_'")
source=source.replace('Warhammer_Modular_Editable.blend', 'RuneboundWarhammer_Modular_Editable.blend')
source=source.replace("'interface':'warhammer_factory_v1'", "'interface':'runebound_warhammer_modular_v1'")
(P/'author_factory.py').write_text(source,encoding='utf-8')
icons=(ROOT/'SourceAssets/SteelWarhammer20261014/ModulesV1/author_icons.py').read_text(encoding='utf-8-sig')
icons=icons.replace('Warhammer_Modular_Editable.blend','RuneboundWarhammer_Modular_Editable.blend')
icons=icons.replace('ue_steel_warhammer','ue_runebound_warhammer')
icons=icons.replace('Warhammer_PartIcons_Editable.blend','RuneboundWarhammer_PartIcons_Editable.blend')
icons=icons.replace('for row,obj in zip(rows,modules):\n', '''for row,obj in zip(rows,modules):
    final_icon=P.parent/'FactoryFramedIconsV2/Masters'/(row['slot']+'.png')
    if final_icon.is_file():
        shutil.copy2(final_icon,O/(row['slot']+'.png'))
        dest=ROOT/'Content/ColdSteelData/AttachmentIcons20260913';dest.mkdir(exist_ok=True)
        for key in ('ue_runebound_warhammer_category_'+row['slot'],'ue_runebound_warhammer_'+row['slot']+'_false'):
            shutil.copy2(final_icon,dest/(key+'.png'))
        continue
''')
icons=icons.replace("'style':'grayscale PBR; square bevel steel frame, four rivets, circular silver rim','size':[1024,1024]",
    "'style':'FactoryFramedIconsV2 generated masters for visible factory parts; legacy render for fixed modules','canonical_masters':'../FactoryFramedIconsV2/Masters'")
(P/'author_icons.py').write_text(icons,encoding='utf-8')
print('Factory split and inventory icon authors prepared')
