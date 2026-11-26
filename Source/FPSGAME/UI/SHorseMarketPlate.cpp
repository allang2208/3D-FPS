#include "SHorseMarketPlate.h"
#include "ColdSteelUIStyle.h"

#include "Framework/Application/SlateApplication.h"
#include "Rendering/DrawElementTypes.h"
#include "Rendering/SlateRenderer.h"
#include "Styling/CoreStyle.h"

void SHorseMarketPlate::Construct(const FArguments& Args)
{
    Sharp=Args._Sharp;
    Soft=Args._Soft;
    PreferredHeight=Args._PreferredHeight;
    CornerRadius=Args._CornerRadius;
    bShowScrim=Args._ShowScrim;
    bCornerBrackets=Args._CornerBrackets;
    PortraitFocus=Args._PortraitFocus;
    SetVisibility(EVisibility::HitTestInvisible);
}

void SHorseMarketPlate::SetReveal(float Value)
{
    if(FMath::IsNearlyEqual(Reveal,Value,.001f))return;
    Reveal=Value;
    Invalidate(EInvalidateWidgetReason::Paint);
}

void SHorseMarketPlate::SetSelected(bool Value)
{
    if(bSelected==Value)return;
    bSelected=Value;
    Invalidate(EInvalidateWidgetReason::Paint);
}

void SHorseMarketPlate::SetMuted(bool Value)
{
    if(bMuted==Value)return;
    bMuted=Value;
    Invalidate(EInvalidateWidgetReason::Paint);
}

int32 SHorseMarketPlate::OnPaint(const FPaintArgs&, const FGeometry& G, const FSlateRect&,
    FSlateWindowElementList& Out, int32 Layer, const FWidgetStyle& Style, bool Enabled) const
{
    if(!Sharp || !Sharp->GetResourceObject())return Layer;
    const FVector2f Size(G.GetLocalSize());
    if(Size.X<2.f || Size.Y<2.f)return Layer;

    const float Radius=FMath::Clamp(CornerRadius,0.f,FMath::Min(Size.X,Size.Y)*.25f);
    const float Aspect=Size.X/Size.Y;
    const FVector2f BrushDim(FMath::Max(1.f,float(Sharp->ImageSize.X)),FMath::Max(1.f,float(Sharp->ImageSize.Y)));
    const float TileAspect=BrushDim.X/BrushDim.Y;
    const FVector2f SampleSpan(FMath::Min(1.f,Aspect/TileAspect),FMath::Min(1.f,TileAspect/Aspect));
    const FBox2f Region=Sharp->GetUVRegion();
    const FBox2f UVBox=(Region.bIsValid && Region.GetSize().X>0.f && Region.GetSize().Y>0.f)
        ? Region : FBox2f(FVector2f::ZeroVector,FVector2f(1.f,1.f));

    // Rounded top corners, crisp flush bottom edge matching ColdSteel architectural glass framing.
    TArray<float,TInlineAllocator<48>> Stops={0.f,Size.X};
    if(Radius>.5f)
    {
        for(int32 I=1;I<=8;++I)
        {
            const float Theta=(HALF_PI/8.f)*I;
            const float Edge=Radius*(1.f-FMath::Cos(Theta));
            Stops.Add(Edge);
            Stops.Add(Size.X-Edge);
        }
    }
    Stops.Sort();
    auto Arc=[](float R,float Offset)
    {
        return FMath::Sqrt(FMath::Max(0.f,R*R-Offset*Offset));
    };

    TArray<float,TInlineAllocator<48>> Xs,Tops;
    Xs.Reserve(Stops.Num());
    Tops.Reserve(Stops.Num());
    for(const float X:Stops)
    {
        if(!Xs.IsEmpty() && FMath::IsNearlyEqual(X,Xs.Last(),.01f))continue;
        const float FromEdge=FMath::Min(X,Size.X-X);
        Xs.Add(X);
        Tops.Add(FromEdge>=Radius?0.f:Radius-Arc(Radius,Radius-FromEdge));
    }

    const int32 Slices=Xs.Num()-1;
    TArray<FSlateVertex> Vertices;
    TArray<SlateIndex> Indices;
    Vertices.Reserve((Slices+1)*4);
    Indices.Reserve(Slices*18);

    const float Zoom=1.f+.06f*FMath::Clamp(Reveal,0.f,1.f);
    const FVector2f Span=SampleSpan/Zoom;
    FLinearColor BaseTint=Style.GetColorAndOpacityTint();
    if(bMuted) BaseTint*=FLinearColor(.52f,.52f,.55f,1.f);
    else BaseTint*=FMath::Lerp(FLinearColor(.96f,.96f,.98f,1.f),FLinearColor(1.04f,1.03f,1.01f,1.f),Reveal);
    const FColor Ink=BaseTint.ToFColor(true);
    const FColor Clear(Ink.R,Ink.G,Ink.B,0);

    for(int32 I=0;I<=Slices;++I)
    {
        const float X=Xs[I];
        const float Top=Tops[I];
        const float Ys[]={Top,FMath::Min(Size.Y,Top+1.f),FMath::Max(Top+1.f,Size.Y-1.f),Size.Y};
        for(int32 J=0;J<4;++J)
        {
            const FVector2f XY(X,Ys[J]);
            const FVector2f TileUV=(XY/Size)*Span+(FVector2f(1.f,1.f)-Span)*PortraitFocus;
            Vertices.Add(FSlateVertex::Make<ESlateVertexRounding::Disabled>(G.GetAccumulatedRenderTransform(),
                XY,UVBox.Min+TileUV*UVBox.GetSize(),J==0?Clear:Ink));
        }
        if(!I)continue;
        for(int32 J=0;J<3;++J)
        {
            const SlateIndex A=SlateIndex((I-1)*4+J);
            Indices.Append({A,SlateIndex(A+4),SlateIndex(A+1),SlateIndex(A+1),SlateIndex(A+4),SlateIndex(A+5)});
        }
    }

    auto Renderer=FSlateApplication::Get().GetRenderer();
    const ESlateDrawEffect Effect=Enabled?ESlateDrawEffect::None:ESlateDrawEffect::DisabledEffect;
    FSlateDrawElement::MakeCustomVerts(Out,Layer,Renderer->GetResourceHandle(*Sharp,Size,G.Scale),
        Vertices,Indices,nullptr,0,0,Effect);

    int32 TopLayer=Layer;
    if(bShowScrim)
    {
        // Multi-stop vertical dark studio scrim (subtle top shade for pills, rich bottom shade for nameplate).
        const float Bands[]={0.f,.36f,.64f,1.f};
        const float Alphas[]={.38f,.02f,.22f,.92f};
        TArray<FSlateVertex> ScrimVerts;
        TArray<SlateIndex> ScrimIdx;
        ScrimVerts.Reserve((Slices+1)*4);
        ScrimIdx.Reserve(Slices*18);
        const float AlphaScale=Style.GetColorAndOpacityTint().A;
        for(int32 I=0;I<=Slices;++I)
        {
            const float X=Xs[I];
            const float Top=Tops[I];
            for(int32 B=0;B<4;++B)
            {
                const float Y=FMath::Lerp(Top,Size.Y,Bands[B]);
                const FColor C(14,14,16,uint8(FMath::Clamp(Alphas[B]*AlphaScale,0.f,1.f)*255.f));
                ScrimVerts.Add(FSlateVertex::Make<ESlateVertexRounding::Disabled>(G.GetAccumulatedRenderTransform(),
                    FVector2f(X,Y),FVector2f(.5f,.5f),C));
            }
            if(!I)continue;
            for(int32 B=0;B<3;++B)
            {
                const SlateIndex A=SlateIndex((I-1)*4+B);
                ScrimIdx.Append({A,SlateIndex(A+4),SlateIndex(A+1),SlateIndex(A+1),SlateIndex(A+4),SlateIndex(A+5)});
            }
        }
        const auto WhiteRes=Renderer->GetResourceHandle(*FCoreStyle::Get().GetBrush(TEXT("WhiteBrush")));
        FSlateDrawElement::MakeCustomVerts(Out,Layer+1,WhiteRes,ScrimVerts,ScrimIdx,nullptr,0,0,Effect);
        TopLayer=Layer+1;
    }

    // Crisp 1px architectural separator along the bottom edge (neutral border at rest, brass sheen on hover/select).
    const FLinearColor RuleColor=FMath::Lerp(
        ColdSteelUI::Border,
        bSelected?ColdSteelUI::HUDGold:ColdSteelUI::HUDGoldDim,
        bSelected?1.f:FMath::Clamp(Reveal,0.f,1.f));
    const TArray<FVector2f> BottomLine={FVector2f(0.f,Size.Y-.5f),FVector2f(Size.X,Size.Y-.5f)};
    FSlateDrawElement::MakeLines(Out,TopLayer+1,G.ToPaintGeometry(),BottomLine,Effect,
        Style.GetColorAndOpacityTint()*RuleColor,true,1.f);
    TopLayer+=1;

    // Machined 4-corner L-brackets on selected/deployed cards or hero banners.
    if(bCornerBrackets || bSelected)
    {
        const float Arm=FMath::Min(11.f,FMath::Min(Size.X,Size.Y)*.14f);
        const float Pad=2.5f;
        const FLinearColor BracketColor=Style.GetColorAndOpacityTint()*ColdSteelUI::HUDGold;
        auto DrawCorner=[&](FVector2f A,FVector2f B,FVector2f C)
        {
            FSlateDrawElement::MakeLines(Out,TopLayer+1,G.ToPaintGeometry(),TArray<FVector2f>{A,B,C},Effect,BracketColor,true,1.5f);
        };
        DrawCorner({Pad,Pad+Arm},{Pad,Pad},{Pad+Arm,Pad});
        DrawCorner({Size.X-Pad-Arm,Pad},{Size.X-Pad,Pad},{Size.X-Pad,Pad+Arm});
        DrawCorner({Pad,Size.Y-Pad-Arm},{Pad,Size.Y-Pad},{Pad+Arm,Size.Y-Pad});
        DrawCorner({Size.X-Pad-Arm,Size.Y-Pad},{Size.X-Pad,Size.Y-Pad},{Size.X-Pad,Size.Y-Pad-Arm});
        TopLayer+=1;
    }

    return TopLayer;
}
