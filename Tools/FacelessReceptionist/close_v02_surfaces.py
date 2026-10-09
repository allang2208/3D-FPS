from pathlib import Path
p=Path(r'D:\FPS3D\FPSGAME\Tools\FacelessReceptionist\author_character_v02.py')
s=p.read_text(encoding='utf-8')
s=s.replace("o.data.materials.clear();o.data.materials.append(mat)\n bm=bmesh.new();bm.from_mesh(o.data)","""o.data.materials.clear();o.data.materials.append(mat)
 # The generated unitard and exposed arms have separate surface seams.
 # Union their volume before cutting the garment, keeping the source untouched.
 active(o)
 rem=o.modifiers.new('ContinuousFabricVolume','REMESH');rem.mode='VOXEL';rem.voxel_size=.005;rem.use_smooth_shade=True;apply(o,rem)
 bm=bmesh.new();bm.from_mesh(o.data)""")
s=s.replace("dec.ratio=.48 if kind=='jacket' else .35","dec.ratio=.33 if kind=='jacket' else .25")
s=s.replace("region=[p for p in points if abs(p.z-z)<.018 and abs(p.x)<.275]","""max_x=float(np.interp(z,[.475,.9,1.01,1.13],[.24,.24,.225,.182]))
 region=[p for p in points if abs(p.z-z)<.018 and abs(p.x)<max_x]""")
s=s.replace("else anatomical_weights(v.co) for v in o.data.vertices]","else body_sample(v.co) for v in o.data.vertices]")
s=s.replace("shell(o,.003)\n# Lapels", "shell(o,.003);kinds[o.name]='skirt'\n# Lapels")
s=s.replace("sm=o.modifiers.new('LeatherSurface','SMOOTH')","dec=o.modifiers.new('ShoeSurfaceTopology','DECIMATE');dec.ratio=.23;apply(o,dec)\n sm=o.modifiers.new('LeatherSurface','SMOOTH')")
s=s.replace("sub=o.modifiers.new('UpperFinish','SUBSURF');sub.levels=1;apply(o,sub)","""sub=o.modifiers.new('UpperFinish','SUBSURF');sub.levels=1;apply(o,sub)
 for v in o.data.vertices:
  v.co.x=sign*.134+(v.co.x-sign*.134)*1.08
  v.co.y=-.005+(v.co.y+.005)*1.045
  v.co.z=-.008+(v.co.z+.008)*1.05""")
p.write_text(s,encoding='utf-8')
