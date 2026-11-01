"""Adapt the existing production pipeline; replace the body with the approved Zhen Ting design."""
from pathlib import Path
P=Path(__file__).resolve().parent;S=P.parent/'LeiXiPommelV1'
def rename(s):
 return s.replace('LeiXi','ZhenTing').replace('lei_xi','zhen_ting').replace('LEIXI','ZHENTING').replace('Lei Xi','Zhen Ting').replace('StormCore','ThunderGroove')
s=rename((S/'author_geometry.py').read_text(encoding='utf-8'))
a=s.index('profile=[');b=s.index('\ndef radius',a)
s=s[:a]+'''profile=[(-.0750,.0200),(-.0740,.0213),(-.0715,.0213),(-.0700,.0235),(-.0660,.0275),(-.0400,.0275),(-.0394,.0275),(-.0386,.0267),(-.0356,.0238),(-.0348,.0242),(-.0338,.0240),(-.0313,.0206),(-.0305,.0210),(-.0295,.0207),(-.0275,.0170),(-.0262,.0150),(-.02435,.0153)]'''+s[b:]
a=s.index('# Continuous octagonal shell:');b=s.index('# Recalculate only new geometry normals.',a)
s=s[:a]+(P/'body_geometry.py').read_text(encoding='utf-8')+'\n'+s[b:]
s=s.replace("uv=me.uv_layers.new(name=src.uv_layers[0].name)","bm=bmesh.new();bm.from_mesh(me);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-8);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free();me.update()\n uv=me.uv_layers.new(name=src.uv_layers[0].name)")
s=s.replace("'SM_ThunderGodHammer_pommel_zhen_ting'","'SM_ThunderGodHammer_pommel_zhen_ting'")
s=s.replace('Precision solid shell; four recessed diamond windows; woven inlays and stepped terminal diamond','Preserved native collar; integral three-step shoulder; four recessed triple-chevron panels; flat woven silver inlays; wide terminal thunder seal')
(P/'author_geometry.py').write_text(s,encoding='utf-8')
tex=rename((S/'author_textures.py').read_text(encoding='utf-8'))
tex=tex.replace('.08*coarse+.006*grain+.012*', '.018*coarse+.0015*grain+.003*').replace('.40+.045*coarse+.004*grain','.40+.015*coarse+.001*grain').replace('.44+coarse*.17+grain*.012','.44+coarse*.05+grain*.003')
a=tex.index('# Diamond UV');b=tex.index("(P/'texture_manifest.json')",a)
tex=tex[:a]+'''# Thin real geometry carries these blue-white groove maps, never a large glass window.
M=1024;yy,xx=np.mgrid[0:M,0:M].astype(np.float32)
filament=.82+.18*np.sin(xx*.025+np.sin(yy*.017))**2
save('CoreEmission',np.stack((filament*.38,filament*.76,filament),2))
save('CoreBaseColor',np.stack((filament*.025,filament*.06,filament*.11),2))
'''+tex[b:]
tex=tex.replace('authored seeded microrelief and branch paths; structural relief is real geometry','authored seeded microrelief; structural chevrons, braids, panel reveals and seams are real geometry')
(P/'author_textures.py').write_text(tex,encoding='utf-8')
(P/'render_icon_source.py').write_text(rename((S/'render_icon_source.py').read_text(encoding='utf-8')),encoding='utf-8')
s=rename((S/'import_all.py').read_text(encoding='utf-8'))
s=s.replace("return (3.0 + Active * 9.0) * (0.88 + 0.12 * sin(T * 7.0));","return 2.5 * (0.94 + 0.06 * sin(T * 3.0));")
a=s.index('def option(data):');b=s.index('publish(R/',a)
s=s[:a]+'''def option(data):
 column=next(c for c in data['columns'] if c['key']=='pommel');column['options']=[o for o in column['options'] if o['id']!='zhen_ting_pommel']
 column['options'].append({'id':'zhen_ting_pommel','name':'震霆配重','tier':'special','weapons':['ue_thunder_god_hammer'],
  'description':'雷神之锤专属。三阶锻肩汇聚重击雷能，三重折雷纹沿前方引出连续落雷。',
  'appearance':'原厂编纹接颈 · 三阶锻肩 · 三重折雷纹 · 底部雷印',
  'stats':{'heavy_charge_speed_bonus':.30},
  'effects':[{'text':'重击蓄力速度+30%','benefit':1}],
  'special_effects':['震霆连落｜满蓄力重击保留原有落雷，沿释放方向额外落下3道雷击；半径3米，中心间距6米，从原落点向前6、12、18米展开，遇墙或断崖停止。',
  '贯雷协同｜搭配贯雷锤座，最大投掷距离+50%；在落地位置沿投出方向追加3道落雷，抛物线预览同步延长。',
  '疾雷协同｜搭配疾雷锤座，保留指定位置的正常落雷，从该位置沿释放方向追加3道同款魔法落雷。',
  '雷击判定｜普通重击和贯雷追加雷只造成原雷击的魔法伤害；疾雷追加雷沿用疾雷重击魔法伤害。每道雷击叠加2层感电并眩晕1.5秒。普通攻击、冲刺攻击和召回不触发连落。']})
def module(data):
 data['slots']['pommel']['zhen_ting_pommel']={'mesh':mesh.get_path_name(),'location_cm':manifest['location_cm'],'appearance':'原厂接颈 · 三阶锻肩 · 三重折雷纹 · 底部雷印','interface':'thunder_god_hammer_modular_v1','model_revision':'ZhenTingPommelV1'}
'''+s[b:]
(P/'import_all.py').write_text(s,encoding='utf-8')
print('ZHENTING_PRODUCTION_SOURCES_READY')
