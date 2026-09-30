#pragma once
#include "Widgets/SLeafWidget.h"
#include "Rendering/DrawElements.h"
#include "GunsmithUIStyle.h"

/** Vector category symbol; the full sword is shown by the live model preview. */
class SMeleePartIcon : public SLeafWidget
{
public:
    SLATE_BEGIN_ARGS(SMeleePartIcon){} SLATE_ARGUMENT(FString,Part)
    /** 采集工具四栏（握把／握柄／改件／主部件）用工具自己的矢量符号，不借剑类图形。 */
    SLATE_ARGUMENT(bool,bTool)
    /** 主部件按工具类型分别画斧头或镐头。 */
    SLATE_ARGUMENT(FString,Definition)
    /** 禁用档位卡把图标整体压暗；不传＝原色。 */
    SLATE_ARGUMENT(FLinearColor,ColorAndOpacity)
    SLATE_END_ARGS()
    void Construct(const FArguments& Args){Part=Args._Part;bTool=Args._bTool;Definition=Args._Definition;
        ColorAndOpacity=Args._ColorAndOpacity;SetVisibility(EVisibility::HitTestInvisible);}
    virtual FVector2D ComputeDesiredSize(float)const override{return FVector2D(48,48);}
    virtual int32 OnPaint(const FPaintArgs&,const FGeometry& Geometry,const FSlateRect&,FSlateWindowElementList& Elements,
        int32 Layer,const FWidgetStyle& Style,bool)const override
    {
        const FVector2D Size=Geometry.GetLocalSize();const float Scale=FMath::Min(Size.X,Size.Y)/48.f;
        const FVector2D Offset=(Size-FVector2D(48,48)*Scale)*.5f;
        auto Line=[&](std::initializer_list<FVector2D> Points,float Width=1.5f,bool Accent=true)
        {
            TArray<FVector2D> Path;for(const auto& Point:Points)Path.Add(Offset+Point*Scale);
            FSlateDrawElement::MakeLines(Elements,Layer,Geometry.ToPaintGeometry(),Path,ESlateDrawEffect::None,
                (Accent?GunsmithUI::Silver:GunsmithUI::Muted)*Style.GetColorAndOpacityTint()*ColorAndOpacity,true,Width*Scale);
        };
        if(bTool)
        {
            if(Part==TEXT("head"))
            {
                // 主部件：柄杆 + 斧头或镐头，按工具定义分开画。
                Line({{21,10},{27,10},{27,44},{21,44},{21,10}},1.f,false);
                if(Definition==TEXT("tool_pickaxe"))
                {
                    Line({{6,16},{42,16},{42,21},{6,21},{6,16}},2.f);
                    Line({{6,21},{12,31},{17,21}},2.f);
                    Line({{31,21},{36,31},{42,21}},2.f);
                    Line({{18,12},{30,12}},1.f,false);
                }
                else
                {
                    Line({{27,11},{38,15},{40,23},{35,29},{27,25},{27,11}},2.f);
                    Line({{38,15},{40,23},{35,29}},2.5f);
                    Line({{19,13},{29,13}},1.f,false);
                }
            }
            else if(Part==TEXT("shaft"))
            {
                // 握柄：整根柄杆、上箍与柄尾铁套。
                Line({{22,4},{26,4},{27,40},{21,40},{22,4}},2.f);
                Line({{18,10},{30,10},{30,14},{18,14},{18,10}},1.f,false);
                Line({{19,34},{29,34},{29,41},{19,41},{19,34}},1.f,false);
                Line({{24,17},{24,31}},1.f,false);
            }
            else if(Part==TEXT("enhance"))
            {
                // 强化：底部砧座＋向上五道层叠档位刻痕（最高档最长），与工具三栏同风格。
                Line({{9,38},{39,38},{39,43},{9,43},{9,38}},2.f);
                Line({{14,33},{34,33},{34,38},{14,38},{14,33}},1.f,false);
                for(int32 I=0;I<5;++I)
                {
                    const double Width=9.+I*2.5;
                    Line({{24-Width*.5,32.-I*5.5},{24+Width*.5,32.-I*5.5}},2.f);
                }
            }
            else if(Part==TEXT("fitting"))
            {
                // 改件：柄颈加装件——头部孔眼、钢楔与两颗铆钉。
                Line({{17,6},{31,6},{31,17},{17,17},{17,6}},1.f,false);
                Line({{24,8},{29,15},{19,15},{24,8}},2.f);
                Line({{21,17},{27,17},{27,40},{21,40},{21,17}},1.f,false);
                Line({{19,22},{29,22}},2.f);Line({{19,29},{29,29}},2.f);
            }
            else
            {
                // 握把：双手接触区的缠裹与加宽握面。
                Line({{20,6},{28,6},{27,42},{21,42},{20,6}},1.f,false);
                for(int32 Y=15;Y<32;Y+=6)Line({{20.,double(Y)},{28.,double(Y-5)}},2.f);
                Line({{15,32},{33,32},{33,39},{15,39},{15,32}},2.f);
                Line({{19,42},{29,42}},1.f,false);
            }
            return Layer;
        }
        if(Part==TEXT("blade_1")||Part==TEXT("blade_2"))
        {
            Line({{24,4},{31,13},{29,35},{19,35},{17,13},{24,4}});
            if(Part==TEXT("blade_1")){Line({{24,9},{28,14},{27,31}},2.f);Line({{16,39},{32,39}},1.f,false);}
            else{Line({{24,12},{24,31}},2.f);Line({{21,16},{21,29}},1.f,false);Line({{27,16},{27,29}},1.f,false);}
        }
        else if(Part==TEXT("guard"))
        {
            Line({{21,7},{27,7},{27,39},{21,39},{21,7}},1.f,false);
            Line({{5,21},{12,18},{20,21},{28,21},{36,18},{43,21},{40,28},{30,26},{18,26},{8,28},{5,21}},2.f);
        }
        else if(Part==TEXT("pommel"))
        {
            Line({{20,5},{28,5},{28,18},{20,18},{20,5}},1.f,false);
            Line({{24,17},{35,24},{35,35},{24,43},{13,35},{13,24},{24,17}},2.f);
            Line({{24,22},{30,26},{30,32},{24,37},{18,32},{18,26},{24,22}},1.f,false);
        }
        else
        {
            Line({{17,8},{31,8},{29,39},{19,39},{17,8}},2.f);
            Line({{14,6},{34,6}});Line({{17,42},{31,42}});
            for(int32 Y=13;Y<37;Y+=6)Line({{19.,double(Y)},{29.,double(Y-3)}},1.f,false);
        }
        return Layer;
    }
private:
    FString Part;
    bool bTool=false;
    FString Definition;
    FLinearColor ColorAndOpacity=FLinearColor::White;
};
