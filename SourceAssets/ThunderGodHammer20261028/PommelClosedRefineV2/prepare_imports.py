from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parent
for kind,key in [('LeiXi','lei_xi'),('ZhenTing','zhen_ting')]:
 s=(R/(kind+'PommelV1')/'import_all.py').read_text(encoding='utf-8')
 s=s.replace('R=P.parents[2]','R=P.parents[3]').replace('/'+kind+'PommelV1\'', '/PommelClosedRefineV2/'+kind+"'")
 s=s.replace("(.20,.22,.25)","(.42,.49,.60)").replace("(1.55,1.47,1.29)","(1.15,1.10,.99)").replace("(.70,.47,.26)","(1.0,.60,.29)")
 s=s.replace("'max_texture_size',2048","'max_texture_size',4096")
 s=s.replace("mesh=imp(P/'Export'/(manifest['mesh']+'.fbx'),manifest['mesh'],D+'/Meshes',opt)","mesh=u.load_asset(D+'/Meshes/'+manifest['mesh']) or imp(P/'Export'/(manifest['mesh']+'.fbx'),manifest['mesh'],D+'/Meshes',opt)")
 s=s[:s.index('def publish(path,edit):')]+"receipt['complete']=True;receipt['mesh']=mesh.get_path_name();receipt['icon']=icon.get_path_name();record()\nprint('"+kind+"_V2_ASSETS_SAVED')\n"
 (P/kind/'import_assets.py').write_text(s,encoding='utf-8')
print('POMMEL_V2_IMPORT_SOURCES_READY')
