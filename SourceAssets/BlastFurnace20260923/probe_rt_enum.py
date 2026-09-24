"""Find the render-target format enum this build exposes."""
import unreal as u

print('RTF_LIKE', [n for n in dir(u) if 'RTF' in n.upper() or 'RenderTargetFormat' in n])
print('RL_METHODS', [n for n in dir(u.RenderingLibrary) if not n.startswith('_')])
