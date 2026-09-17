#include "LPVOScopeWidget.h"
#include "../FPSGAMECharacter.h"
#include "GameFramework/PlayerController.h"
#include "Rendering/DrawElements.h"
#include "Styling/CoreStyle.h"
#include "Framework/Application/SlateApplication.h"
#include "Rendering/SlateRenderer.h"
#include "HAL/IConsoleManager.h"

namespace
{
// Optic-layer firing presentation. The owner's weapon model is hidden behind the
// scope overlay, so the world-space muzzle flash only leaves a sliver inside the
// narrow magnified frustum. These knobs drive a screen-space flash drawn inside
// the aperture instead. Presentation only: it never writes ControlRotation, the
// shot direction or the trace, stays clear of the reticle and can be disabled
// with `fps.Scope.FlashAlpha 0`.
static TAutoConsoleVariable<float> ScopeFlashAlpha(TEXT("fps.Scope.FlashAlpha"),.55f,
    TEXT("Peak opacity of the in-optic muzzle flash; 0 disables it."));
static TAutoConsoleVariable<float> ScopeFlashHoldMs(TEXT("fps.Scope.FlashHoldMs"),70.f,
    TEXT("In-optic muzzle flash lifetime in milliseconds."));
static TAutoConsoleVariable<float> ScopeFlashRadius(TEXT("fps.Scope.FlashRadius"),.42f,
    TEXT("Flash radius as a fraction of the aperture radius."));
static TAutoConsoleVariable<float> ScopeFlashOffsetX(TEXT("fps.Scope.FlashOffsetX"),.16f,
    TEXT("Flash centre offset toward the ejection side, in aperture radii."));
static TAutoConsoleVariable<float> ScopeFlashOffsetY(TEXT("fps.Scope.FlashOffsetY"),.85f,
    TEXT("Flash centre offset below the reticle, in aperture radii."));
static TAutoConsoleVariable<float> ScopeFlashBurstMs(TEXT("fps.Scope.FlashBurstMs"),18.f,
    TEXT("Near-white core burst window at shot onset, in milliseconds."));
static TAutoConsoleVariable<float> ScopeEmberAlpha(TEXT("fps.Scope.EmberAlpha"),.12f,
    TEXT("Peak opacity of the low-orange afterglow; 0 disables it."));
static TAutoConsoleVariable<float> ScopeEmberHoldMs(TEXT("fps.Scope.EmberHoldMs"),180.f,
    TEXT("Afterglow lifetime in milliseconds after the shot."));
static TAutoConsoleVariable<float> ScopeAmbientAlpha(TEXT("fps.Scope.AmbientAlpha"),.12f,
    TEXT("Peak opacity of the whole-aperture ambient wash; 0 disables it."));
static TAutoConsoleVariable<float> ScopeAmbientHoldMs(TEXT("fps.Scope.AmbientHoldMs"),50.f,
    TEXT("Ambient wash lifetime in milliseconds (a few frames)."));
static TAutoConsoleVariable<float> ScopeSideFlashChance(TEXT("fps.Scope.SideFlashChance"),.15f,
    TEXT("Fraction of shots whose flash lights the left/right rim instead."));
static TAutoConsoleVariable<float> ScopeEdgeBloomAlpha(TEXT("fps.Scope.EdgeBloomAlpha"),.38f,
    TEXT("Aperture rim bloom while firing; 0 disables it."));
static TAutoConsoleVariable<float> ScopeLensDirtAlpha(TEXT("fps.Scope.LensDirtAlpha"),.10f,
    TEXT("Baseline lens dirt opacity inside the aperture; 0 disables it."));
static TAutoConsoleVariable<float> ScopeSmokeAlpha(TEXT("fps.Scope.SmokeAlpha"),.16f,
    TEXT("Peak opacity of the post-shot heat wisp; 0 disables it."));
static TAutoConsoleVariable<float> ScopeSmokeHoldMs(TEXT("fps.Scope.SmokeHoldMs"),220.f,
    TEXT("Heat wisp lifetime in milliseconds after the shot."));

// Every lens element below shares the white brush and one custom-vertex batch, so
// Slate keeps the whole optic layer in a handful of draw calls.
struct FScopeFx
{
    float Flash = 0.f;
    float Burst = 0.f;
    float Ember = 0.f;
    float Ambient = 0.f;
    float Wisp = 0.f;
    float WispT = 0.f;
    float Seed = 0.f;
};

void AppendSoftDisc(TArray<FSlateVertex>& Verts,TArray<SlateIndex>& Indices,const FGeometry& G,
    const FVector2f& C,float R,const FLinearColor& Inner,const FLinearColor& Outer,
    float CoreScale=.55f,int32 Segments=20)
{
    const int32 Base=Verts.Num();
    Verts.Add(FSlateVertex::Make<ESlateVertexRounding::Disabled>(G.GetAccumulatedRenderTransform(),
        C,FVector2f(.5f,.5f),Inner.ToFColor(true)));
    for(int32 Ring=0;Ring<2;++Ring)
    {
        const float Radius=Ring==0?R*CoreScale:R;
        const FLinearColor Color=Ring==0?Inner:Outer;
        for(int32 I=0;I<=Segments;++I)
        {
            const float Angle=2.f*PI*I/Segments;
            Verts.Add(FSlateVertex::Make<ESlateVertexRounding::Disabled>(G.GetAccumulatedRenderTransform(),
                C+FVector2f(FMath::Cos(Angle),FMath::Sin(Angle))*Radius,FVector2f(.5f,.5f),Color.ToFColor(true)));
        }
    }
    const int32 RingA=Base+1,RingB=RingA+Segments+1;
    for(int32 I=0;I<Segments;++I)
        Indices.Append({SlateIndex(Base),SlateIndex(RingA+I),SlateIndex(RingA+I+1)});
    for(int32 I=0;I<Segments;++I)
        Indices.Append({SlateIndex(RingA+I),SlateIndex(RingB+I),SlateIndex(RingA+I+1),
            SlateIndex(RingA+I+1),SlateIndex(RingB+I),SlateIndex(RingB+I+1)});
}

void AppendLensRim(TArray<FSlateVertex>& Verts,TArray<SlateIndex>& Indices,const FGeometry& G,
    const FVector2f& C,float R0,float R1,const FLinearColor& Inner,const FLinearColor& Outer,int32 Segments=96)
{
    const int32 Base=Verts.Num();
    for(int32 Ring=0;Ring<2;++Ring)
    {
        const float Radius=Ring==0?R0:R1;
        const FLinearColor Color=Ring==0?Inner:Outer;
        for(int32 I=0;I<=Segments;++I)
        {
            const float Angle=2.f*PI*I/Segments;
            Verts.Add(FSlateVertex::Make<ESlateVertexRounding::Disabled>(G.GetAccumulatedRenderTransform(),
                C+FVector2f(FMath::Cos(Angle),FMath::Sin(Angle))*Radius,FVector2f(.5f,.5f),Color.ToFColor(true)));
        }
    }
    const int32 A=Base,B=Base+Segments+1;
    for(int32 I=0;I<Segments;++I)
        Indices.Append({SlateIndex(A+I),SlateIndex(B+I),SlateIndex(A+I+1),
            SlateIndex(A+I+1),SlateIndex(B+I),SlateIndex(B+I+1)});
}

void FlushVerts(FSlateWindowElementList& Out,int32 Layer,TArray<FSlateVertex>& Verts,TArray<SlateIndex>& Indices)
{
    if(Indices.IsEmpty())return;
    const auto Resource=FSlateApplication::Get().GetRenderer()->GetResourceHandle(*FCoreStyle::Get().GetBrush(TEXT("WhiteBrush")));
    FSlateDrawElement::MakeCustomVerts(Out,Layer,Resource,Verts,Indices,nullptr,0,0);
}

// Fixed lens specks: dust on the glass, briefly lit by the muzzle flash. Positions
// are aperture-radius units; real glass dirt is never uniform, and the flash is
// what makes it read.
void PaintLensDirt(FSlateWindowElementList& Out,int32 Layer,const FGeometry& G,
    const FVector2f& Center,float R,const FScopeFx& Fx)
{
    const float Peak=ScopeLensDirtAlpha.GetValueOnGameThread();
    if(Peak<=0.f)return;
    static const float Speck[][3]={
        {-.42f,-.55f,.11f},{.36f,-.30f,.08f},{.55f,.22f,.13f},{-.58f,.18f,.09f},
        {.12f,.62f,.14f},{-.22f,.42f,.07f},{.46f,-.58f,.06f}};
    const float Lit=FMath::Clamp(Peak+Fx.Flash*.30f,0.f,.45f);
    TArray<FSlateVertex> Verts;TArray<SlateIndex> Indices;
    for(const auto& S:Speck)
        AppendSoftDisc(Verts,Indices,G,Center+FVector2f(S[0]*R,S[1]*R),S[2]*R,
            FLinearColor(.62f,.57f,.50f,Lit),FLinearColor(.62f,.57f,.50f,0.f),.5f,20);
    FlushVerts(Out,Layer,Verts,Indices);
}

// Aperture rim bloom: the flash lighting the inside of the tube, one frame thick.
void PaintEdgeBloom(FSlateWindowElementList& Out,int32 Layer,const FGeometry& G,
    const FVector2f& Center,float R,float S,const FScopeFx& Fx)
{
    const float Peak=ScopeEdgeBloomAlpha.GetValueOnGameThread();
    if(Peak<=0.f||Fx.Flash<=0.f)return;
    TArray<FSlateVertex> Verts;TArray<SlateIndex> Indices;
    AppendLensRim(Verts,Indices,G,Center,R-S*1.5f,R+S*3.f,
        FLinearColor(1.f,.86f,.62f,Peak*Fx.Flash),FLinearColor(1.f,.52f,.16f,0.f),128);
    FlushVerts(Out,Layer,Verts,Indices);
}

// Post-shot heat wisp: two soft ribbons drifting up through the lower aperture.
// Position is a pure function of the shot age, so the widget stays stateless.
void PaintHeatWisp(FSlateWindowElementList& Out,int32 Layer,const FGeometry& G,
    const FVector2f& Center,float R,const FScopeFx& Fx)
{
    if(Fx.Wisp<=0.f)return;
    TArray<FSlateVertex> Verts;TArray<SlateIndex> Indices;
    for(int32 Ribbon=0;Ribbon<2;++Ribbon)
    {
        const float Rnd=FMath::Frac(Fx.Seed*(1.7f+Ribbon*.9f)+Ribbon*.37f);
        const float Rise=FMath::Lerp(.34f,-.30f,Fx.WispT);
        const float Drift=FMath::Lerp(-.22f,.34f,Fx.WispT)*FMath::Lerp(.6f,1.4f,Rnd);
        const FVector2f At=Center+FVector2f(Drift*R,Rise*R);
        const float Rx=R*FMath::Lerp(.16f,.26f,Rnd),Ry=R*FMath::Lerp(.07f,.11f,Rnd);
        for(int32 Puff=0;Puff<3;++Puff)
        {
            const float Side=(Puff-1)*Rx*1.1f;
            const float Weight=Puff==1?1.f:.55f;
            AppendSoftDisc(Verts,Indices,G,At+FVector2f(Side,Ry*.25f),
                FMath::Lerp(Rx*.7f,Rx,Puff==1?1.f:.7f),
                FLinearColor(.72f,.70f,.68f,Fx.Wisp*Weight*(Ribbon?.5f:1.f)),
                FLinearColor(.72f,.70f,.68f,0.f),.30f,24);
        }
    }
    FlushVerts(Out,Layer,Verts,Indices);
}

constexpr float FlashInner=.30f;   // inner radius of the flash blob, in blob radii

// Position, size and orientation for one shot's flash, all derived from the per-shot
// seed: position jitter, a size roll and a small chance of lighting a side rim instead.
struct FFlashShape{FVector2f Origin;float Radius=0.f;float Lean=0.f;bool bSide=false;float SideSign=1.f;};

FFlashShape MakeFlashShape(const FVector2f& Center,float ApertureR,float Seed)
{
    const float OffsetX=FMath::Clamp(ScopeFlashOffsetX.GetValueOnGameThread(),-.8f,.8f)
        +(FMath::Frac(Seed*7.13f+.31f)*2.f-1.f)*.10f;
    const float OffsetY=FMath::Clamp(ScopeFlashOffsetY.GetValueOnGameThread(),-.8f,.8f)
        +(FMath::Frac(Seed*3.71f+.17f)*2.f-1.f)*.08f;
    const float RScale=FMath::Lerp(.85f,1.15f,FMath::Frac(Seed*5.29f+.53f));
    const float Base=FMath::Clamp(ScopeFlashRadius.GetValueOnGameThread(),.05f,.6f)*ApertureR*RScale;
    FFlashShape S;
    S.Lean=FMath::Lerp(-.40f,.40f,Seed);
    S.bSide=FMath::Frac(Seed*11.37f+.29f)<FMath::Clamp(ScopeSideFlashChance.GetValueOnGameThread(),0.f,1.f);
    if(S.bSide)
    {
        S.SideSign=FMath::Frac(Seed*13.77f+.11f)<.5f?-1.f:1.f;
        S.Origin=Center+FVector2f(S.SideSign*.90f*ApertureR,.06f*ApertureR);
        S.Radius=Base*.75f;
    }
    else
    {
        S.Origin=Center+FVector2f(OffsetX*ApertureR,OffsetY*ApertureR);
        // Crosshair guard: the blob's inner edge stays just below the centre line.
        S.Radius=FMath::Min(Base,FMath::Max(.02f*ApertureR,(OffsetY-.06f)*ApertureR/(FlashInner*1.15f)));
    }
    return S;
}

// Whole-aperture ambient wash: the flash lighting the scene for a few frames. At high
// magnification this brief brightening, not the blob itself, is what reads as "fired".
void PaintAmbientWash(FSlateWindowElementList& Out,int32 Layer,const FGeometry& G,
    const FVector2f& Center,float R,float Strength)
{
    if(Strength<=0.f)return;
    const FLinearColor Warm(1.f,.76f,.47f);
    constexpr int32 Segments=48;
    TArray<FSlateVertex> Verts;TArray<SlateIndex> Indices;
    const int32 Base=Verts.Num();
    Verts.Add(FSlateVertex::Make<ESlateVertexRounding::Disabled>(G.GetAccumulatedRenderTransform(),
        Center,FVector2f(.5f,.5f),FLinearColor(Warm.R,Warm.G,Warm.B,Strength*.55f).ToFColor(true)));
    for(int32 I=0;I<=Segments;++I)
    {
        const float Angle=2.f*PI*I/Segments;
        // Light floods in from the muzzle below the sight line: the lower rim leads.
        const float Weight=.35f+.65f*(.5f+.5f*FMath::Sin(Angle));
        Verts.Add(FSlateVertex::Make<ESlateVertexRounding::Disabled>(G.GetAccumulatedRenderTransform(),
            Center+FVector2f(FMath::Cos(Angle),FMath::Sin(Angle))*R,FVector2f(.5f,.5f),
            FLinearColor(Warm.R,Warm.G,Warm.B,Strength*.35f*Weight).ToFColor(true)));
        if(I<Segments)Indices.Append({SlateIndex(Base),SlateIndex(Base+1+I),SlateIndex(Base+2+I)});
    }
    FlushVerts(Out,Layer,Verts,Indices);
}

// Low-orange afterglow at the flash's position, outliving the main blob.
void PaintEmber(FSlateWindowElementList& Out,int32 Layer,const FGeometry& G,
    const FVector2f& Center,float ApertureR,float Strength,float Seed)
{
    if(Strength<=0.f)return;
    const FFlashShape S=MakeFlashShape(Center,ApertureR,Seed);
    TArray<FSlateVertex> Verts;TArray<SlateIndex> Indices;
    AppendSoftDisc(Verts,Indices,G,S.Origin,S.Radius*.62f,
        FLinearColor(1.f,.34f,.12f,Strength),FLinearColor(1.f,.22f,.08f,0.f),.5f,24);
    FlushVerts(Out,Layer,Verts,Indices);
}

void PaintOpticFlash(FSlateWindowElementList& Out,int32 Layer,const FGeometry& G,
    const FVector2f& Center,float ApertureR,float Alpha,float Burst,float Seed)
{
    if(Alpha<=0.f)return;
    const FFlashShape S=MakeFlashShape(Center,ApertureR,Seed);
    const float Gain=FMath::Lerp(.85f,1.15f,FMath::Frac(Seed*9.41f+.77f));
    // Side shots lie along the rim: rotate the lobe's long axis by a quarter turn.
    const float Lean=S.Lean+(S.bSide?PI*.5f:0.f);
    const float Cos=FMath::Cos(Lean),Sin=FMath::Sin(Lean);
    const FVector2f Along(-Sin,Cos);   // mostly downwards (or sideways), leaning with the shot
    const FVector2f Across(-Cos,-Sin);
    const float BurstAmt=FMath::Clamp(Burst,0.f,1.f);
    constexpr int32 Bands=8,Segments=72;
    TArray<FSlateVertex> Verts;TArray<SlateIndex> Indices;
    Verts.Reserve((Bands+1)*(Segments+1));
    for(int32 Band=0;Band<=Bands;++Band)
    {
        const float T=static_cast<float>(Band)/Bands;
        FLinearColor Core=FMath::Lerp(FLinearColor(1.f,.95f,.86f),FLinearColor(1.f,.42f,.10f),T);
        // The opening burst whitens the core for a frame or two before the colour settles.
        Core=FMath::Lerp(Core,FLinearColor(1.f,.98f,.95f),BurstAmt*(1.f-T)*.8f);
        const float BandAlpha=FMath::Min(1.f,Alpha*(1.f-T)*(1.f-T)*Gain*(1.f+BurstAmt*.8f*(1.f-T)));
        for(int32 I=0;I<=Segments;++I)
        {
            const float Angle=2.f*PI*I/Segments;
            const float Local=FMath::Lerp(FlashInner,1.f,T)*S.Radius;
            FVector2f P=S.Origin+Along*(Local*1.15f*FMath::Cos(Angle))+Across*(Local*.80f*FMath::Sin(Angle));
            // The tube rim clips the blob: Slate verts are not cut by the painted mask,
            // so anything outside the aperture is pinned back onto the rim circle.
            const FVector2f D=P-Center;const float Dist=D.Size();
            if(Dist>ApertureR&&Dist>UE_KINDA_SMALL_NUMBER)P=Center+(D/Dist)*ApertureR;
            Verts.Add(FSlateVertex::Make<ESlateVertexRounding::Disabled>(G.GetAccumulatedRenderTransform(),P,
                FVector2f(.5f,.5f),FLinearColor(Core.R,Core.G,Core.B,BandAlpha).ToFColor(true)));
            if(Band<Bands&&I<Segments){const int32 A=Band*(Segments+1)+I,B=A+Segments+1;
                Indices.Append({SlateIndex(A),SlateIndex(B),SlateIndex(A+1),SlateIndex(A+1),SlateIndex(B),SlateIndex(B+1)});}
        }
    }
    const auto Resource=FSlateApplication::Get().GetRenderer()->GetResourceHandle(*FCoreStyle::Get().GetBrush(TEXT("WhiteBrush")));
    FSlateDrawElement::MakeCustomVerts(Out,Layer,Resource,Verts,Indices,nullptr,0,0);
}

void PaintLPVOScope(FSlateWindowElementList& Out,int32 Layer,const FGeometry& G,float Alpha,const FScopeFx& Fx)
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
    // Lens stack, all above the aperture mask and below the reticle: dust, ambient
    // wash, flash, afterglow, rim bloom, then the post-shot heat wisp. The crosshair
    // is always last.
    PaintLensDirt(Out,Layer,G,Center,R,Fx);
    PaintAmbientWash(Out,Layer,G,Center,R,Fx.Ambient);
    if(Fx.Flash>0.f)PaintOpticFlash(Out,Layer,G,Center,R,Fx.Flash,Fx.Burst,Fx.Seed);
    PaintEmber(Out,Layer,G,Center,R,Fx.Ember,Fx.Seed);
    PaintEdgeBloom(Out,Layer,G,Center,R,S,Fx);
    PaintHeatWisp(Out,Layer,G,Center,R,Fx);
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
    if(Alpha>0.f)
    {
        // Facts only: the shot clock and its per-shot seed. Nothing here feeds back
        // into ControlRotation, the shot direction or the trace.
        FScopeFx Fx;
        if(Character)
        {
            Fx.Seed=Character->GetLastShotSeed();
            const float Age=Character->GetLastShotAgeSeconds();
            if(const float Peak=ScopeFlashAlpha.GetValueOnGameThread();Peak>0.f)
            {
                if(Age<FMath::Max(.01f,ScopeFlashHoldMs.GetValueOnGameThread()*.001f))
                {
                    // Sharp attack, smooth release; the sight picture is never blocked long.
                    const float T=Age/FMath::Max(.01f,ScopeFlashHoldMs.GetValueOnGameThread()*.001f);
                    Fx.Flash=Peak*Alpha*(1.f-T)*(1.f-T);
                }
                // Near-white opening burst, then a low-orange ember outliving the flash.
                const float BurstS=FMath::Max(.005f,ScopeFlashBurstMs.GetValueOnGameThread()*.001f);
                if(Age<BurstS)Fx.Burst=1.f-Age/BurstS;
                if(const float Ember=ScopeEmberAlpha.GetValueOnGameThread();Ember>0.f)
                {
                    const float Hold=FMath::Max(.02f,ScopeEmberHoldMs.GetValueOnGameThread()*.001f);
                    if(Age<Hold)Fx.Ember=Ember*Alpha*(1.f-Age/Hold)*(1.f-Age/Hold)
                        *FMath::Min(1.f,Age/(Hold*.3f));
                }
            }
            if(const float Ambient=ScopeAmbientAlpha.GetValueOnGameThread();Ambient>0.f)
            {
                // The whole sight picture lights up for a few frames; a per-shot gain
                // roll keeps repeat fire from pulsing at one fixed strength.
                const float Hold=FMath::Max(.01f,ScopeAmbientHoldMs.GetValueOnGameThread()*.001f);
                if(Age<Hold)Fx.Ambient=Ambient*Alpha*(1.f-Age/Hold)*(1.f-Age/Hold)
                    *FMath::Lerp(.8f,1.2f,FMath::Frac(Fx.Seed*2.31f+.47f));
            }
            if(const float Smoke=ScopeSmokeAlpha.GetValueOnGameThread();
                Smoke>0.f&&Age<FMath::Max(.02f,ScopeSmokeHoldMs.GetValueOnGameThread()*.001f))
            {
                // The wisp outlives the flash; the skewed envelope peaks well after the shot.
                const float T=Age/FMath::Max(.02f,ScopeSmokeHoldMs.GetValueOnGameThread()*.001f);
                Fx.Wisp=Smoke*Alpha*FMath::Sin(PI*FMath::Pow(T,1.4f));
                Fx.WispT=T;
            }
        }
        PaintLPVOScope(Elements,Result,Geometry,Alpha,Fx);
    }
    return Result+2;
}
