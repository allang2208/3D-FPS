"""Instantiate the official OFL variable serif font for the folio only."""
from pathlib import Path
import json,hashlib,shutil
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1]
OUT=PROJECT/'Content/UI/AlchemyManual/Fonts';OUT.mkdir(parents=True,exist_ok=True)
records=[]
for label,weight in [('Regular',400),('Semibold',600)]:
    font=TTFont(ROOT/'Fonts/NotoSerifSC-Variable.ttf')
    font=instantiateVariableFont(font,{'wght':weight},inplace=True)
    for rec in font['name'].names:
        names={1:'Alchemy Folio Serif',2:label,3:'AlchemyFolioSerif-'+label,4:'Alchemy Folio Serif '+label,6:'AlchemyFolioSerif-'+label,16:'Alchemy Folio Serif',17:label}
        if rec.nameID in names:rec.string=names[rec.nameID].encode(rec.getEncoding())
    path=OUT/('FolioSerif-'+label+'.ttf');font.save(path)
    records.append(dict(file=str(path),weight=weight,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
shutil.copy2(ROOT/'Fonts/OFL.txt',OUT/'OFL.txt')
report=dict(source='https://github.com/google/fonts/tree/main/ofl/notoserifsc',license='SIL OFL 1.1',derived_family='Alchemy Folio Serif',files=records)
(ROOT/'font-receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
(OUT/'provenance.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('Two folio font weights saved.')
