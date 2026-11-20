"""Make review sheets from the registered product rendering, without warping the mesh image."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[2]/"SourceAssets/ModernTacticalSet20261113/ExfilReferenceR4"
REVIEW=ROOT/"Review"
BG=(32,37,40)


def flat(image):
    image=image.convert("RGBA")
    board=Image.new("RGBA",image.size,BG+(255,));board.alpha_composite(image)
    return board.convert("RGB")


def make_sheet(name,panels,columns,tile):
    width,height=tile;gap=12;label_h=46
    rows=(len(panels)+columns-1)//columns
    board=Image.new("RGB",(gap+(width+gap)*columns,gap+(height+label_h+gap)*rows),(28,32,35))
    draw=ImageDraw.Draw(board);font=ImageFont.truetype("C:/Windows/Fonts/msyh.ttc",22)
    for i,(image,label) in enumerate(panels):
        x=(i%columns)*(width+gap)+gap;y=(i//columns)*(height+label_h+gap)+gap
        board.paste(flat(image).resize((width,height),Image.Resampling.LANCZOS),(x,y+label_h))
        draw.text((x+4,y+3),label,font=font,fill="#e9edf0")
    board.save(REVIEW/name,quality=95,optimize=True)


def main():
    ref=Image.open(ROOT/"Reference/user-angle-crop.png")
    current=Image.open(REVIEW/"product-render.png")
    panels=[(ref,"用户参考图"),(current,"游戏模型 · 参考视角")]
    make_sheet("reference-comparison.jpg",panels,2,(530,round(530*ref.height/ref.width)))
    old=Image.open(REVIEW/"previous-crown.png")
    crown=[]
    for im,label in [(ref,"用户参考图"),(old,"调整前 · 冠顶"),(current,"调整后 · 冠顶")]:
        # The previous and current renders use the same registered camera and lighting.
        factor=im.width/ref.width
        crop=im.crop(tuple(round(v*factor) for v in (0,0,354,130)))
        crown.append((crop,label))
    make_sheet("crown-comparison.jpg",crown,3,(440,round(440*130/354)))
    more=[(Image.open(REVIEW/f"view-{name}.png"),label) for name,label in
          (("front","正面"),("side","侧面"),("rear","后侧"),("liner","内衬"))]
    make_sheet("model-views.jpg",more,2,(480,480))


if __name__=="__main__":
    main()
