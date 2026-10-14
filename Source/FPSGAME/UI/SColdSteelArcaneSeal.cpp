#include "SColdSteelArcaneSeal.h"
#include "ColdSteelUIStyle.h"
#include "Rendering/DrawElements.h"

void SColdSteelArcaneSeal::Construct(const FArguments&)
{
    SetVisibility(EVisibility::HitTestInvisible);
}
void SColdSteelArcaneSeal::SetRitualState(bool Enchant,bool Ready)
{
    if(bEnchant==Enchant&&bReady==Ready)return;
    bEnchant=Enchant;bReady=Ready;Invalidate(EInvalidateWidgetReason::Paint);
}
void SColdSteelArcaneSeal::SetPulse(float Progress)
{
    if(Pulse==Progress)return;
    Pulse=Progress;Invalidate(EInvalidateWidgetReason::Paint);
}
int32 SColdSteelArcaneSeal::OnPaint(const FPaintArgs&,const FGeometry& G,const FSlateRect&,FSlateWindowElementList& Out,int32 Layer,const FWidgetStyle& Style,bool)const
{
    const FVector2D Size=G.GetLocalSize(),Center(Size.X*.5,Size.Y*.60);
    const float Radius=FMath::Min(Size.X*.38f,Size.Y*.34f);
    if(Radius<15)return Layer;
    const FLinearColor Tone=(bEnchant?ColdSteelUI::Enchanted:ColdSteelUI::Enhanced)*Style.GetColorAndOpacityTint();
    const FLinearColor Secondary=(bEnchant?ColdSteelUI::Enhanced:ColdSteelUI::Enchanted)*Style.GetColorAndOpacityTint();
    const float Burst=Pulse>=0?FMath::Sin(Pulse*PI):0.f;
    const float Angle=Pulse>=0?Pulse*.32f:0.f;
    auto Point=[&](float R,float A){return FVector2D(Center.X+FMath::Cos(A)*R,Center.Y+FMath::Sin(A)*R*.40f);};
    auto Line=[&](const TArray<FVector2D>& P,float Alpha,float Width=1.f,bool Alternate=false)
    {auto C=Alternate?Secondary:Tone;C.A*=Alpha;FSlateDrawElement::MakeLines(Out,Layer,G.ToPaintGeometry(),P,ESlateDrawEffect::None,C,true,Width);};
    auto Arc=[&](float R,float Start,float Sweep,float Alpha,float Width=1.f,bool Alternate=false)
    {
        TArray<FVector2D> Points;const int32 Steps=64;Points.Reserve(Steps+1);
        for(int32 I=0;I<=Steps;++I)Points.Add(Point(R,Start+Sweep*I/Steps));
        Line(Points,Alpha,Width,Alternate);
    };
    const float Base=bReady?.34f:.17f;
    Arc(Radius,0,2*PI,Base+Burst*.3f);
    Arc(Radius*.88f,Angle,2*PI,Base*.85f,1.f,true);
    Arc(Radius*.64f,-Angle,2*PI,Base*.4f);
    for(int32 I=0;I<24;++I)
    {
        const float A=I*2*PI/24+Angle;
        Line({Point(Radius*.93f,A),Point(Radius*(I%3==0?1.035f:.98f),A)},Base+Burst*.35f,I%3==0?1.5f:1.f,I%3!=0);
    }
    for(int32 I=0;I<6;++I)
    {
        const float A=I*2*PI/6-Angle;
        Line({Point(Radius*.75f,A-.055f),Point(Radius*.82f,A),Point(Radius*.75f,A+.055f),Point(Radius*.69f,A),Point(Radius*.75f,A-.055f)},Base);
    }
    if(Pulse>=0)
    {
        Arc(Radius*(.45f+Pulse*.9f),0,2*PI,(1-Pulse)*.65f,2.f);
        for(int32 I=0;I<12;++I)
        {
            const float A=I*2*PI/12+Pulse*.22f,R=Radius*(.6f+Pulse*.5f);
            const FVector2D P=Point(R,A),Offset(2.5f,0),Vertical(0,2.5f);
            Line({P-Offset,P+Offset},Burst*.8f,1.5f);Line({P-Vertical,P+Vertical},Burst*.8f,1.5f);
        }
    }
    return Layer;
}
