"""Reuse the validated M4 chain/twist baking workflow with a dedicated handstop fit."""
from pathlib import Path
O=Path(__file__).parent
source=(O/'ReferenceWorkflow/build_animation.py').read_text(encoding='utf-8')
source=source.replace('A_M4_Foregrip_','A_M4_Vertical_').replace('FOREGRIP_','VERTICAL_')
source=source.replace('M4_Foregrip_Fitted.blend','M4_Vertical_Fitted.blend').replace("'FG_'","'VG_'")
source=source.replace("if f<end/2:opening=smooth(f/4);retreat=smooth((f-4)/5)\n    else:opening=1-smooth((f-(end-6))/6);retreat=1-smooth((f-(end-16))/10)", "if f<end/2:u=max(0,min(1,f/9))\n    else:u=1-max(0,min(1,(f-(end-12))/12))\n    retreat=smooth(u);opening=smooth(u*fit.get('release_open_speed',1))")
source=source.replace("H.translation+=grip.to_3x3().col[1].normalized()*(.11*retreat)","H.translation+=grip.to_3x3()@Vector(fit['release_vector'])*retreat")
source=source.replace("grip.to_3x3().col[1].normalized()*(.08*math.sin(math.pi*w))","(grip.to_3x3()@Vector((fit['release_vector'][0]*.8,fit['release_vector'][1]*.8,-.14 if clip=='reload_empty' else -.10)))*math.sin(math.pi*w)")
source=source.replace("local=Matrix(fit['grip_matrix']).inverted()@ob.matrix_basis.copy();","local=Matrix(fit['grip_matrix']).inverted()@ob.matrix_basis.copy();")
source=source.replace("or n=='pinky_01_l'","or '_01_' in n")
source=source.replace("report=json.loads", "release=json.loads((O/'release_profile.json').read_text()) if (O/'release_profile.json').exists() else []\nreport=json.loads")
start=source.index('     if opening and not n.startswith')
end=source.index('     p[n]=',start)
source=source[:start]+"""     if 'reload' in clip and release:
      t=max(0,min(1,f/9)) if f<end/2 else 1-max(0,min(1,(f-(end-12))/12));index=min(len(release)-2,int(t*(len(release)-1)));lo,hi=release[index],release[index+1]
      blend=max(0,min(1,(t-lo['u'])/(hi['u']-lo['u'])))
      digitbasis=Quaternion(lo['basis'][n]).slerp(Quaternion(hi['basis'][n]),blend).to_matrix().to_4x4()
"""+source[end:]
source=source.replace("   A=old[un].translation.copy();target=H.translation;", "   support_offset=Vector((.12,.20,-.08))*w\n   p['clavicle_l'].translation+=support_offset\n   A=old[un].translation+support_offset;target=H.translation;")
source=source.replace('lerp(natural.normalized(),.8*w)','lerp(natural.normalized(),w)')
exec(compile(source,str(O/'build_generated.py'),'exec'))

