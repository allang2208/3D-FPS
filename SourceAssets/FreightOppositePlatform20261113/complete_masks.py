"""Finish only the wall-foot deposits and the defined walking strip using the existing registered masks."""
from pathlib import Path
import runpy
R=Path(__file__).resolve().parent
src=(R/'bake_surfaces.py').read_text('utf8').split("if __name__=='__main__':")[0]
# A little more dust at the protected wall edge; a narrower, lower-roughness wear strip through the aisle.
src=src.replace("23.+12*large+17*(.55+.45*mid)","34.+15*large+20*(.55+.45*mid)")
src=src.replace("(.53*skirt+.27*corner)","(.73*skirt+.35*corner)").replace("0,.78)","0,.84)")
src=src.replace("(117.+10*large+9*mid)","(105.+10*large+9*mid)").replace("wear=.44*lane","wear=.53*lane")
src=src.replace("(.41+.07*mid)*wear","(.36+.08*mid)*wear")
src=src.replace("*(.30+.08*mid+.05*fine)","*(.45+.11*mid+.06*fine)")
src=src.replace("O=R/'Textures'","O=R/'CompletionTextures'")
env={'__file__':str(R/'bake_surfaces.py')}
exec(compile(src,'completion_mask_recipe','exec'),env)
env['floor']();env['skirt']('Return',-3036,-1558);env['skirt']('Pipe',6174,7820)
