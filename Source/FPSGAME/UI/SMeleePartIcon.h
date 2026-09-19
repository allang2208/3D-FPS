#pragma once
#include "Widgets/SLeafWidget.h"
#include "Rendering/DrawElements.h"
#include "GunsmithUIStyle.h"

/** Vector category symbol; the full sword is shown by the live model preview. */
class SMeleePartIcon : public SLeafWidget
{
public:
    SLATE_BEGIN_ARGS(SMeleePartIcon){} SLATE_ARGUMENT(FString,Part) SLATE_END_ARGS()
    void Construct(const FArguments& Args){Part=Args._Part;SetVisibility(EVisibility::HitTestInvisible);}
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
                (Accent?GunsmithUI::Silver:GunsmithUI::Muted)*Style.GetColorAndOpacityTint(),true,Width*Scale);
        };
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
};
