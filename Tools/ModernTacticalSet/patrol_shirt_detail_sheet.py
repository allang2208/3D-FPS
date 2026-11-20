"""Lay out the sewn shoulder, wrist and tucked hem at readable detail scale."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

REVIEW = Path(__file__).resolve().parents[2]/"SourceAssets/ModernTacticalSet20261113/PatrolShirtR2/Review"


def main():
    sheet = Image.new("RGB",(1548,568),(242,240,235))
    draw = ImageDraw.Draw(sheet)
    heading = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc",24)
    small = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc",17)
    for idx,(source,title,caption) in enumerate((
            ("raglan-elbow","肩袖与肘部","插肩接缝、上臂口袋、肘部补强"),
            ("cuff-glove","袖口与手套","翻折袖袢与手套腕口"),
            ("tucked-waist","衣摆与战术裤","扎腰衣摆与裤腰上缘"))):
        x = 12+512*idx
        draw.rounded_rectangle((x,12,x+500,555),radius=5,fill=(251,250,247))
        draw.text((x+18,24),title,font=heading,fill=(53,48,39))
        draw.text((x+18,65),caption,font=small,fill=(96,86,73))
        view = Image.open(REVIEW/(source+".png")).convert("RGBA").resize((500,464),Image.Resampling.LANCZOS)
        sheet.paste(view,(x,91),view)
    sheet.save(REVIEW/"equipped-details.jpg",quality=94,optimize=True)


if __name__=="__main__":
    main()
