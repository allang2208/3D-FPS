from pathlib import Path
from PIL import Image, ImageFilter, ImageOps

here = Path(__file__).resolve().parent
frame = Image.open(here.parents[1] / "KukriRefinement20261027/StandardEmptyFrame.png").convert("RGBA")
part = Image.open(here / "GripIcon.png").convert("RGBA")
part = part.crop(part.getchannel("A").getbbox())
part.thumbnail((round(frame.width * .56), round(frame.height * .56)), Image.Resampling.LANCZOS)
alpha = part.getchannel("A")
part = ImageOps.grayscale(part).convert("RGBA")
part.putalpha(alpha)
x, y = (frame.width - part.width) // 2, (frame.height - part.height) // 2
shadow = Image.new("RGBA", frame.size)
shadow.paste((0, 0, 0, 160), (x + 3, y + 8, x + 3 + part.width, y + 8 + part.height), alpha)
frame = Image.alpha_composite(frame, shadow.filter(ImageFilter.GaussianBlur(6)))
frame.alpha_composite(part, (x, y))
frame.resize((1024, 1024), Image.Resampling.LANCZOS).save(here / "ue_zhanmadao_grip_pojun_longhaft.png")
