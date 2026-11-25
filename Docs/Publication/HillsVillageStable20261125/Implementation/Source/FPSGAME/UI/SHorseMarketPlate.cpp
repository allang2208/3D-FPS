#include "SHorseMarketPlate.h"
#include "ColdSteelUIStyle.h"

#include "Framework/Application/SlateApplication.h"
#include "Rendering/DrawElementTypes.h"
#include "Rendering/SlateRenderer.h"

void SHorseMarketPlate::Construct(const FArguments& Args)
{
    Sharp=Args._Sharp;
    Soft=Args._Soft;
    SetVisibility(EVisibility::HitTestInvisible);
}

void SHorseMarketPlate::SetReveal(float Value)
{
    Reveal=Value;
    Invalidate(EInvalidateWidgetReason::Paint);
}

int32 SHorseMarketPlate::OnPaint(const FPaintArgs&, const FGeometry& G, const FSlateRect&,
    FSlateWindowElementList& Out, int32 Layer, const FWidgetStyle& Style, bool Enabled) const
{
    if(!Sharp || !Sharp->GetResourceObject())return Layer;
    const FVector2f Size(G.GetLocalSize());
    if(Size.X<2.f || Size.Y<2.f)return Layer;

    const float Radius=FMath::Min(22.f,Size.X*.12f);
    const float Shoulder=FMath::Min(29.f,Size.Y*.22f);
    const float Turn=Shoulder*.5f;
    const float Join=Size.X-FMath::Min(90.f,Size.X*.28f);
    const float Aspect=Size.X/Size.Y, TileAspect=384.f/184.f;
    const FVector2f SampleSpan(FMath::Min(1.f,Aspect/TileAspect),FMath::Min(1.f,TileAspect/Aspect));
    const FBox2f Region=Sharp->GetUVRegion();
    // Concentrate vertices around the tangent points so the scallop stays smooth at large drawer widths.
    TArray<float,TInlineAllocator<64>> Stops={0.f,Size.X,Join};
    for(int32 I=0;I<=12;++I)
    {
        const float Theta=(HALF_PI/12.f)*I;
        const float Edge=Radius*(1.f-FMath::Cos(Theta));
        Stops.Add(Edge);
        Stops.Add(Size.X-Edge);
        Stops.Add(Join+Turn*FMath::Sin(Theta));
        Stops.Add(Join+Turn*(2.f-FMath::Cos(Theta)));
    }
    Stops.Sort();
    // Use precisely the same edge for the image cutout and the gold inlay.
    auto Arc=[](float RadiusValue,float Offset)
    {
        return FMath::Sqrt(FMath::Max(0.f,RadiusValue*RadiusValue-Offset*Offset));
    };
    TArray<FVector2f> BottomEdge;
    TArray<float,TInlineAllocator<64>> TopEdge;
    BottomEdge.Reserve(Stops.Num());
    for(const float X:Stops)
    {
        if(!BottomEdge.IsEmpty() && FMath::IsNearlyEqual(X,BottomEdge.Last().X,.01f))continue;
        const float FromEdge=FMath::Min(X,Size.X-X);
        TopEdge.Add(FromEdge>=Radius?0.f:Radius-Arc(Radius,Radius-FromEdge));
        const float D=X-Join;
        float Bottom=Size.Y-Shoulder;
        if(D>=Shoulder)Bottom=Size.Y;
        else if(D>Turn)Bottom+=Turn+Arc(Turn,Shoulder-D);
        else if(D>0.f)Bottom+=Turn-Arc(Turn,D);
        BottomEdge.Emplace(X,Bottom);
    }
    const int32 Slices=BottomEdge.Num()-1;
    TArray<FSlateVertex> Vertices;
    TArray<SlateIndex> Indices;
    Vertices.Reserve((Slices+1)*4);
    Indices.Reserve(Slices*18);
    auto Draw=[&](const FSlateBrush& Brush,float Opacity,int32 DrawLayer)
    {
        Vertices.Reset();
        Indices.Reset();
        FLinearColor Tint=Style.GetColorAndOpacityTint();
        Tint.A*=Opacity;
        const FColor Ink=Tint.ToFColor(true);
        const FColor Clear(Ink.R,Ink.G,Ink.B,0);
        for(int32 I=0;I<=Slices;++I)
        {
            const float X=BottomEdge[I].X;
            const float Top=TopEdge[I];
            const float Bottom=BottomEdge[I].Y;
            // Reserve one antialiased pixel at each edge; texture coordinates stay inside this horse's tile.
            const float Ys[]={Top,Top+1.f,Bottom-1.f,Bottom};
            for(int32 J=0;J<4;++J)
            {
                const FVector2f XY(X,Ys[J]);
                const FVector2f Span=SampleSpan/(1.f+.10f*Reveal);
                const FVector2f TileUV=XY/Size*Span+(FVector2f(1.f,1.f)-Span)*FVector2f(.45f,.08f);
                Vertices.Add(FSlateVertex::Make<ESlateVertexRounding::Disabled>(G.GetAccumulatedRenderTransform(),
                    XY,Region.Min+TileUV*Region.GetSize(),J==0 || J==3?Clear:Ink));
            }
            if(!I)continue;
            for(int32 J=0;J<3;++J)
            {
                const SlateIndex A=(I-1)*4+J;
                Indices.Append({A,SlateIndex(A+4),SlateIndex(A+1),SlateIndex(A+1),SlateIndex(A+4),SlateIndex(A+5)});
            }
        }
        auto Renderer=FSlateApplication::Get().GetRenderer();
        FSlateDrawElement::MakeCustomVerts(Out,DrawLayer,Renderer->GetResourceHandle(Brush,Size,G.Scale),
            Vertices,Indices,nullptr,0,0,Enabled?ESlateDrawEffect::None:ESlateDrawEffect::DisabledEffect);
    };
    const bool HasSoft=Soft && Soft->GetResourceObject();
    if(HasSoft && Reveal<1.f)Draw(*Soft,1.f,Layer);
    if(!HasSoft || Reveal>0.f)Draw(*Sharp,HasSoft?Reveal:1.f,Layer+1);
    FSlateDrawElement::MakeLines(Out,Layer+2,G.ToPaintGeometry(),MoveTemp(BottomEdge),
        Enabled?ESlateDrawEffect::None:ESlateDrawEffect::DisabledEffect,
        Style.GetColorAndOpacityTint()*ColdSteelUI::HUDGold,true,1.5f);
    return Layer+2;
}
