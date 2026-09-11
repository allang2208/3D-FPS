#include "LPVOScopeWidget.h"
#include "../FPSGAMECharacter.h"
#include "GameFramework/PlayerController.h"
#include "Rendering/DrawElements.h"
#include "Styling/CoreStyle.h"
#include "Framework/Application/SlateApplication.h"
#include "Rendering/SlateRenderer.h"

namespace
{
void PaintLPVOScope(FSlateWindowElementList& Out,int32 Layer,const FGeometry& G,float Alpha)
{
    const FVector2f Size(G.GetLocalSize()),Center=Size*.5f;
    const float S=FMath::Min(Size.X,Size.Y)/900.f,R=FMath::Min(Size.X,Size.Y)*.425f;
    // A clear image fills 85% of the short screen axis at every magnification.
    // Only the outer few pixels carry the optical edge; no long physical bore.
    const float Radii[]={R,R+3*S,R+5*S,R+7*S,R+10*S,Size.Size()};
    const FLinearColor Colors[]={FLinearColor(0,0,0,0),FLinearColor(.015f,.018f,.022f,.8f),FLinearColor(.08f,.09f,.10f,1),FLinearColor(.028f,.032f,.038f,1),FLinearColor::Black,FLinearColor::Black};
    constexpr int32 Segments=256;
    TArray<FSlateVertex> Verts;TArray<SlateIndex> Indices;
    for(int32 Band=0;Band<6;++Band)for(int32 I=0;I<=Segments;++I){
        const float Angle=2*PI*I/Segments;FLinearColor Tint=Colors[Band];Tint.A*=Alpha;
        const FVector2f P=Center+FVector2f(FMath::Cos(Angle),FMath::Sin(Angle))*Radii[Band];
        Verts.Add(FSlateVertex::Make<ESlateVertexRounding::Disabled>(G.GetAccumulatedRenderTransform(),P,FVector2f(.5f,.5f),Tint.ToFColor(true)));
        if(Band<5&&I<Segments){const int32 A=Band*(Segments+1)+I,B=A+Segments+1;
            Indices.Append({SlateIndex(A),SlateIndex(B),SlateIndex(A+1),SlateIndex(A+1),SlateIndex(B),SlateIndex(B+1)});}
    }
    const auto Resource=FSlateApplication::Get().GetRenderer()->GetResourceHandle(*FCoreStyle::Get().GetBrush(TEXT("WhiteBrush")));
    FSlateDrawElement::MakeCustomVerts(Out,Layer,Resource,Verts,Indices,nullptr,0,0);
    const FLinearColor Red(1,.045f,.025f,Alpha);
    for(const FVector2D Axis:{FVector2D(1,0),FVector2D(-1,0),FVector2D(0,1),FVector2D(0,-1)}){
        TArray<FVector2D> Points={FVector2D(Center)+Axis*12*S,FVector2D(Center)+Axis*42*S};
        FSlateDrawElement::MakeLines(Out,Layer+1,G.ToPaintGeometry(),Points,ESlateDrawEffect::None,Red,true,1.2f*S);
    }
    FSlateDrawElement::MakeBox(Out,Layer+1,G.ToPaintGeometry(FVector2D(3*S,3*S),FSlateLayoutTransform(FVector2D(Center)-FVector2D(1.5*S,1.5*S))),FCoreStyle::Get().GetBrush(TEXT("WhiteBrush")),ESlateDrawEffect::None,Red);
}
}

int32 ULPVOScopeWidget::NativePaint(const FPaintArgs& Args,const FGeometry& Geometry,
    const FSlateRect& Clip,FSlateWindowElementList& Elements,int32 Layer,const FWidgetStyle& Style,bool Enabled) const
{
    const int32 Result=Super::NativePaint(Args,Geometry,Clip,Elements,Layer,Style,Enabled);
    const auto* PC=GetOwningPlayer();
    const auto* Character=PC?Cast<AFPSGAMECharacter>(PC->GetPawn()):nullptr;
    const float Alpha=Character&&!PC->bShowMouseCursor?Character->GetScopePresentationAlpha():0.f;
    if(Alpha>0.f)PaintLPVOScope(Elements,Result,Geometry,Alpha);
    return Result+2;
}
