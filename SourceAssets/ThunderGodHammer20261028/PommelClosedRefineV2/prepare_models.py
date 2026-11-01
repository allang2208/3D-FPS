from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parent
for kind,key in [('LeiXi','lei_xi'),('ZhenTing','zhen_ting')]:
 D=P/kind;D.mkdir(exist_ok=True)
 old=R/(kind+'PommelV1')
 text=(old/'author_geometry.py').read_text(encoding='utf-8')
 prefix=text[:text.index('# Close the real cut face')]
 prefix=prefix.replace("P.parent/'ModulesV1", "P.parent.parent/'ModulesV1").replace("P.parent/'Textures'", "P.parent.parent/'Textures'")
 # Rebuild source faces before bevel; never recalculate normals on separate open patches.
 a=prefix.index('def make(');b=prefix.index('\ndef tube(',a)
 prefix=prefix[:a]+(P/'mesh_helpers.py').read_text(encoding='utf-8')+prefix[b:]
 prefix=prefix.replace("(.20,.22,.25)","(.42,.49,.60)").replace("(1.55,1.47,1.29)","(1.15,1.10,.99)").replace("(.70,.47,.26)","(1.0,.60,.29)")
 (D/'author_geometry.py').write_text(prefix+f"\nKIND='{kind}';KEY='{key}'\n"+(P/'collar_refine.py').read_text(encoding='utf-8')+'\n'+(P/'closed_body.py').read_text(encoding='utf-8')+'\n'+(P/'ornaments.py').read_text(encoding='utf-8')+'\n'+(P/'export_model.py').read_text(encoding='utf-8'),encoding='utf-8')
 # Author the same subdued, low-pass forged surface for both parts.
 tx=(R/'ZhenTingPommelV1/author_textures.py').read_text(encoding='utf-8').replace('ZhenTing',kind).replace('ZHENTING',kind.upper())
 tx=tx.replace('N=2048','N=4096').replace("shade=np.clip(.40+.015*coarse+.001*grain,.1,.8)","linear=np.clip(.40+.012*coarse+.001*grain,.1,.8)\nshade=1.055*np.power(linear,1/2.4)-.055")
 tx=tx.replace('gy,gx=np.gradient(height)',"height=np.asarray(Image.fromarray(height).filter(ImageFilter.GaussianBlur(1.2)),np.float32)\ngy,gx=np.gradient(height)")
 # Pillow Gaussian blur on float images is not supported: encode a bounded height first.
 tx=tx.replace("Image.fromarray(height).filter(ImageFilter.GaussianBlur(1.2))","Image.fromarray(np.uint8(np.clip(height*10+.5,0,1)*255)).filter(ImageFilter.GaussianBlur(1.2))").replace('np.float32)\ngy,gx=np.gradient(height)','np.float32)/2550\ngy,gx=np.gradient(height)')
 if kind=='LeiXi':
  leixi=(R/'LeiXiPommelV1/author_textures.py').read_text(encoding='utf-8');a=leixi.index('# Diamond UV');b=leixi.index("(P/'texture_manifest.json')",a)
  tx=tx[:tx.index('# Thin real geometry')]+leixi[a:b]+tx[tx.index("(P/'texture_manifest.json')"):]
 (D/'author_textures.py').write_text(tx,encoding='utf-8')
 icon=(old/'render_icon_source.py').read_text(encoding='utf-8').replace(kind+'PommelV1_Editable.blend',kind+'PommelV2_Editable.blend').replace('pommel_'+key+"'",'pommel_'+key+"_v2'")
 (D/'render_icon_source.py').write_text(icon,encoding='utf-8')
print('POMMEL_V2_SOURCES_PREPARED')
