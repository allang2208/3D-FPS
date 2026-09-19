"""Reuse the validated M4 chain/twist baking workflow with a dedicated handstop fit."""
from pathlib import Path
O=Path(__file__).parent
source=(O/'ReferenceWorkflow/build_animation.py').read_text(encoding='utf-8')
source=source.replace('A_M4_Foregrip_','A_M4_Prism_').replace('FOREGRIP_','PRISM_')
source=source.replace('M4_Foregrip_Fitted.blend','M4_Prism_Fitted.blend').replace("'FG_'","'PH_'")
source=source.replace("if f<end/2:opening=smooth(f/4);retreat=smooth((f-4)/5)\n    else:opening=1-smooth((f-(end-6))/6);retreat=1-smooth((f-(end-16))/10)", "if f<end/2:u=max(0,min(1,f/9))\n    else:u=1-max(0,min(1,(f-(end-12))/12))\n    retreat=smooth(u);opening=smooth((u-fit['release_open_delay'])/(1-fit['release_open_delay']))")
source=source.replace("H.translation+=grip.to_3x3().col[1].normalized()*(.11*retreat)","H.translation+=grip.to_3x3()@Vector(fit['release_vector'])*retreat")
source=source.replace("grip.to_3x3().col[1].normalized()*(.08*math.sin(math.pi*w))","(grip.to_3x3()@Vector((fit['release_vector'][0]*.8,fit['release_vector'][1]*.8,-.14 if clip=='reload_empty' else -.10)))*math.sin(math.pi*w)")
exec(compile(source,str(O/'build_generated.py'),'exec'))
