"""Derive a new isolated blade recipe from the completed Hunter pipeline."""
from pathlib import Path
P=Path(__file__).resolve().parent
old=P.parent/'KukriHunterBlade20261027'
text=(old/'author_hunter.py').read_text(encoding='utf-8')
start=text.index('old_normals=')
end=text.index('\nmat,nt,bs,out=',start)
text=text[:start]+"root=.066\noriginal_tip=max(v.co.z for v in mesh.vertices)\nsys.path.insert(0,str(P))\nfrom serrate_mesh import serrate\nserrations=serrate(blade)\nmesh=blade.data\n"+text[end:]
text=text.replace('Hunter','Canine').replace('hunter','canine').replace('HUNTER','CANINE').replace('猎手刀身','犬牙刀身')
text=text.replace("'exposed_length_scale':1.5", "'exposed_length_scale':1.0,'serrations':serrations")
text=text.replace('(max(old_z)-root)*100','(original_tip-root)*100').replace('lengthen(.2629)*100','.2629*100')
text=text.replace('(.115,.125,.132,1),(.155,.165,.175,1)','(.17,.18,.19,1),(.21,.22,.23,1)')
(P/'author_canine.py').write_text(text,encoding='utf-8')
text=(old/'bake_hunter_runes.py').read_text(encoding='utf-8').replace('Hunter','Canine').replace('hunter','canine').replace('z0=.192','z0=.150')
(P/'bake_canine_runes.py').write_text(text,encoding='utf-8')
text=(old/'import_hunter.py').read_text(encoding='utf-8').replace('Hunter','Canine').replace('hunter','canine').replace('HUNTER','CANINE')
text=text.replace('Exposed blade 1.5x; grip interface fixed through 6.6 cm','Factory length; twelve serrations; grip interface fixed through 6.6 cm')
(P/'import_canine.py').write_text(text,encoding='utf-8')
(P/'build-editor.ps1').write_text((old/'build-editor.ps1').read_text(encoding='utf-8'),encoding='utf-8')
