#include "ColdSteelOathCue.h"
#include "ColdSteelUIStyle.h"
#include "../Weapons/RuneSwordComponent.h"
#include "Rendering/DrawElements.h"
#include "Framework/Application/SlateApplication.h"
#include "Fonts/FontMeasure.h"

int32 ColdSteelOathCue::Paint(const URuneSwordComponent* Sword,const FGeometry& G,FSlateWindowElementList& E,int32 Layer)
{
    if(!Sword)return Layer;
    const float Remaining=Sword->OathWindowRemaining(),Flash=Sword->OathReleaseFlash();
    if(Remaining<=0.f&&Flash<=0.f)return Layer;
    const float Scale=G.GetLocalSize().Y/1080.f;
    const FVector2D Center=G.GetLocalSize()*.5;
    const float Age=.35f-Remaining;
    const float Pulse=Age<.06f?FMath::Sin(PI*Age/.06f):0.f;
    const float Radius=43.2f*Scale*(1.f+.15f*Pulse);
    const FLinearColor Gold(1.f,.72f,.24f,Remaining>0.f?1.f:Flash);
    const auto Stroke=[&](const TArray<FVector2D>& P,float Width)
    {
        FSlateDrawElement::MakeLines(E,Layer+1,G.ToPaintGeometry(),P,ESlateDrawEffect::None,FLinearColor(0,0,0,Gold.A*.9f),true,(Width+3.f)*Scale);
        FSlateDrawElement::MakeLines(E,Layer+2,G.ToPaintGeometry(),P,ESlateDrawEffect::None,Gold,true,Width*Scale);
        FSlateDrawElement::MakeLines(E,Layer+3,G.ToPaintGeometry(),P,ESlateDrawEffect::None,FLinearColor(1.f,.96f,.8f,Gold.A),true,.8f*Scale);
    };
    if(Remaining>0.f)
    {
        for(int32 I=0;I<4;++I)
        {
            const float Angle=PI*(.25f+.5f*I);const FVector2D Out(FMath::Cos(Angle),FMath::Sin(Angle)),Tangent(-Out.Y,Out.X);
            const FVector2D P=Center+Out*Radius;
            Stroke({P+Tangent*8.f*Scale+Out*5.f*Scale,P,P-Tangent*8.f*Scale+Out*5.f*Scale},2.6f);
        }
        const float Fraction=Remaining/.35f;
        for(int32 I=0;I<24;++I)
        {
            const float Start=float(I)/24.f;if(Start>=Fraction)break;
            TArray<FVector2D> Points;
            for(int32 J=0;J<4;++J)
            {
                const float T=FMath::Lerp(Start,FMath::Min((I+.78f)/24.f,Fraction),float(J)/3.f);
                const float A=-PI*.5f+2.f*PI*T;
                Points.Add(Center+FVector2D(FMath::Cos(A),FMath::Sin(A))*(Radius+7.f*Scale));
            }
            Stroke(Points,2.3f);
        }
    }
    const FString Text=Remaining>0.f?TEXT("裁决就绪"):TEXT("裁决");
    const auto Font=ColdSteelUI::TextFont(17.f*Scale);
    const FVector2D Size=FSlateApplication::Get().GetRenderer()->GetFontMeasureService()->Measure(Text,Font);
    const FVector2D Position=Center+FVector2D(-Size.X*.5f,Radius+18.f*Scale);
    FSlateDrawElement::MakeText(E,Layer+3,G.ToPaintGeometry(Size,FSlateLayoutTransform(Position+FVector2D(1,1))),Text,Font,ESlateDrawEffect::None,FLinearColor(0,0,0,Gold.A));
    FSlateDrawElement::MakeText(E,Layer+4,G.ToPaintGeometry(Size,FSlateLayoutTransform(Position)),Text,Font,ESlateDrawEffect::None,Gold);
    return Layer+4;
}
