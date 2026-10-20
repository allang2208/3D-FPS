import json, io, sys
sys.stdout.reconfigure(encoding='utf-8')
p=r"D:\FPS3D\FPSGAME\Content\ColdSteelData\items.json"
d=json.load(open(p,encoding='utf-8'))
out=r"D:\FPS3D\FPSGAME\SourceAssets\SVCHSketchfab20261017\items_probe.json"
json.dump({"svd":d.get("ue_svd"),"m870":d.get("ue_m870"),"svd_ammo":d.get("ammo_pkm_762x54r"),"m870_ammo":d.get("ammo_12g")},open(out,"w",encoding="utf-8"),ensure_ascii=False,indent=2)
print("written")
