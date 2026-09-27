#pragma once
#include "CoreMinimal.h"
#include "Rendering/DrawElements.h"
#include "Framework/Application/SlateApplication.h"
#include "Rendering/SlateRenderer.h"
#include "Styling/CoreStyle.h"

// The optic housing and engraved reticles are screen-space presentation only.
// Coordinates never feed back into the camera, recoil or the projectile path.
namespace ScopeOpticDrawing
{
constexpr int32 Segments=192;
inline const TArray<FVector2f>& Circle()
{
    static const TArray<FVector2f> Points=[]
    {
        TArray<FVector2f> Result;Result.Reserve(Segments+1);
        for(int32 I=0;I<=Segments;++I)
        {
            const float A=2.f*PI*I/Segments;
            Result.Emplace(FMath::Cos(A),FMath::Sin(A));
        }
        return Result;
    }();
    return Points;
}

inline float ApertureRadius(const FVector2f& Size,float Alpha,bool Handgun=false)
{
    // Matches the peripheral material. Settled diameter remains 85% of the
    // short viewport axis at every zoom; entry only converges through 3.5%.
    return FMath::Min(Size.X,Size.Y)*(Handgun?.33f:.425f)*FMath::Lerp(.965f,1.f,FMath::SmoothStep(0.f,1.f,Alpha));
}

inline void PaintHandgunReticle(FSlateWindowElementList& Out,int32 Layer,const FGeometry& G,
    const FVector2f& Center,float R,float Alpha)
{
    // Fixed-power duplex: no range ladder, illumination or uncalibrated marks.
    const float Pixel=1.f/FMath::Max(.1f,G.GetAccumulatedLayoutTransform().GetScale());
    const FLinearColor Ink(.012f,.014f,.015f,Alpha),Backing(.7f,.72f,.72f,.2f*Alpha);
    for(const FVector2D Axis:{FVector2D(1,0),FVector2D(0,1)})
    {
        const auto Line=[&](float A,float B,float Width)
        {
            const TArray<FVector2D> P={FVector2D(Center)+Axis*(R*A),FVector2D(Center)+Axis*(R*B)};
            FSlateDrawElement::MakeLines(Out,Layer,G.ToPaintGeometry(),P,ESlateDrawEffect::None,Backing,true,Width+Pixel*.8f);
            FSlateDrawElement::MakeLines(Out,Layer+1,G.ToPaintGeometry(),P,ESlateDrawEffect::None,Ink,true,Width);
        };
        Line(-.23f,.23f,Pixel*.95f);
        Line(-.97f,-.23f,Pixel*2.5f);Line(.23f,.97f,Pixel*2.5f);
    }
}

inline void PaintHousing(FSlateWindowElementList& Out,int32 Layer,const FGeometry& G,
    const FVector2f& Center,float R,float S,float Alpha,bool PSO,const FVector2f& Eye)
{
    TArray<FSlateVertex> Verts;TArray<SlateIndex> Indices;
    Verts.Reserve(11*(Segments+1));Indices.Reserve(9*Segments*6);
    const auto AddRing=[&](float Radius,const FLinearColor& Color,float Light)
    {
        for(const auto& U:Circle())
        {
            const float Highlight=FMath::Pow(FMath::Max(0.f,FVector2f::DotProduct(U,FVector2f(-.6f,-.8f))),5.f);
            FLinearColor Tint=Color;Tint.R+=Light*Highlight;Tint.G+=Light*Highlight;Tint.B+=Light*Highlight;
            Tint.A*=Alpha;
            Verts.Add(FSlateVertex::Make<ESlateVertexRounding::Disabled>(G.GetAccumulatedRenderTransform(),
                Center+U*Radius,FVector2f(.5f,.5f),Tint.ToFColor(true)));
        }
    };
    const auto Join=[&](int32 A,int32 B)
    {
        for(int32 I=0;I<Segments;++I)
            Indices.Append({SlateIndex(A+I),SlateIndex(B+I),SlateIndex(A+I+1),
                SlateIndex(A+I+1),SlateIndex(B+I),SlateIndex(B+I+1)});
    };
    // Matte bore, lens seat, a narrow machined lip, then the rubber eyepiece.
    AddRing(R-.6f*S,FLinearColor(0,0,0,0),0.f);
    AddRing(R+1.1f*S,FLinearColor(.008f,.010f,.011f,.88f),0.f);
    AddRing(R+3.1f*S,PSO?FLinearColor(.022f,.023f,.018f,1):FLinearColor(.018f,.023f,.027f,1),.018f);
    AddRing(R+4.3f*S,PSO?FLinearColor(.09f,.087f,.07f,1):FLinearColor(.078f,.087f,.095f,1),.055f);
    AddRing(R+6.2f*S,FLinearColor(.016f,.019f,.021f,1),.009f);
    AddRing(R+(PSO?13.f:10.f)*S,FLinearColor(.004f,.005f,.005f,1),0.f);
    AddRing(FVector2f(G.GetLocalSize()).Size(),FLinearColor::Black,0.f);
    for(int32 Band=0;Band<6;++Band)Join(Band*(Segments+1),(Band+1)*(Segments+1));

    // A shallow directional crescent makes eye alignment legible without
    // drifting the reticle or filling the centre with black scope shadow.
    const int32 Shadow=Verts.Num();
    for(int32 Ring=0;Ring<2;++Ring)for(const auto& U:Circle())
    {
        const float Misalignment=FMath::Max(0.f,FVector2f::DotProduct(U,Eye));
        const float Depth=(PSO?.022f:.014f)+Misalignment*.9f+(1.f-Alpha)*.025f;
        const float Radius=Ring==0?R*(1.f-Depth):R;
        const float Opacity=Ring==0?0.f:FMath::Min(.38f,(PSO?.22f:.16f)+Misalignment*4.f)*Alpha;
        Verts.Add(FSlateVertex::Make<ESlateVertexRounding::Disabled>(G.GetAccumulatedRenderTransform(),
            Center+U*Radius,FVector2f(.5f,.5f),FLinearColor(.005f,.007f,.008f,Opacity).ToFColor(true)));
    }
    Join(Shadow,Shadow+Segments+1);

    // Weak grazing coating reflections; no dirt, opaque glass tint or central wash.
    const int32 Coating=Verts.Num();
    const FLinearColor CoatingColor=PSO?FLinearColor(.38f,.31f,.15f):FLinearColor(.14f,.32f,.37f);
    for(int32 Ring=0;Ring<2;++Ring)for(const auto& U:Circle())
    {
        const float Arc=FMath::Pow(FMath::Max(0.f,FVector2f::DotProduct(U,FVector2f(.8f,.6f))),6.f);
        const float Radius=R*(Ring==0?.945f:.998f);
        const float Opacity=Ring==0?0.f:Arc*(PSO?.055f:.04f)*Alpha;
        Verts.Add(FSlateVertex::Make<ESlateVertexRounding::Disabled>(G.GetAccumulatedRenderTransform(),
            Center+U*Radius,FVector2f(.5f,.5f),FLinearColor(CoatingColor.R,CoatingColor.G,CoatingColor.B,Opacity).ToFColor(true)));
    }
    Join(Coating,Coating+Segments+1);
    const auto Resource=FSlateApplication::Get().GetRenderer()->GetResourceHandle(*FCoreStyle::Get().GetBrush(TEXT("WhiteBrush")));
    FSlateDrawElement::MakeCustomVerts(Out,Layer,Resource,Verts,Indices,nullptr,0,0);
}

struct FEngraving
{
    TArray<FVector2D> Points;
    float Width=1.f;
    bool Illuminated=false;
};

inline const TArray<FEngraving>& Reticle(bool PSO)
{
    static const TArray<FEngraving> LPVO=[]
    {
        TArray<FEngraving> P;
        P.Add({{{-174,0},{-86,0}},2.2f});P.Add({{{86,0},{174,0}},2.2f});
        P.Add({{{-86,0},{-22,0}},.95f});P.Add({{{22,0},{86,0}},.95f});
        P.Add({{{0,-63},{0,-21}},.9f});P.Add({{{0,21},{0,112}},.95f});
        P.Add({{{0,112},{0,168}},2.2f});
        for(int32 I=0;I<4;++I)
        {
            const double Y=39.+I*21.,W=4.+I*2.;
            P.Add({{{-W,Y},{W,Y}},.9f});
        }
        // Open illuminated centre ring leaves a clear point of aim.
        for(int32 Side=0;Side<2;++Side)
        {
            FEngraving Arc;Arc.Width=1.05f;Arc.Illuminated=true;
            for(int32 I=0;I<=24;++I)
            {
                const double A=FMath::DegreesToRadians(-68.+I*(136./24.)+Side*180.);
                Arc.Points.Emplace(FMath::Cos(A)*10.,FMath::Sin(A)*10.);
            }
            P.Add(MoveTemp(Arc));
        }
        return P;
    }();
    static const TArray<FEngraving> PSOReticle=[]
    {
        TArray<FEngraving> P;
        P.Add({{{-15,11},{0,0},{15,11}},1.1f,true});
        for(double Y:{38.,64.,90.})P.Add({{{-10,Y+8},{0,Y},{10,Y+8}},.95f});
        P.Add({{{-178,0},{-41,0}},.95f});P.Add({{{41,0},{178,0}},.95f});
        for(int32 I=0;I<5;++I)
        {
            const double X=54.+I*25.,H=I%2==0?6.:3.5;
            P.Add({{{-X,-H},{-X,H}},.9f});P.Add({{{X,-H},{X,H}},.9f});
        }
        P.Add({{{-170,150},{-50,150}},.95f});
        FEngraving Curve;Curve.Width=.95f;
        // Continuous authored curve. No uncalibrated range numbers are implied.
        for(int32 I=0;I<=48;++I)
        {
            const double T=double(I)/48.,U=1.-T;
            Curve.Points.Add(FVector2D(-170,85)*(U*U*U)+FVector2D(-142,115)*(3.*U*U*T)
                +FVector2D(-91,133)*(3.*U*T*T)+FVector2D(-50,139)*(T*T*T));
        }
        for(int32 I:{0,12,24,36,48})
        {
            const auto A=Curve.Points[I];P.Add({{A,A-FVector2D(0,4)},.85f});
        }
        P.Add(MoveTemp(Curve));
        return P;
    }();
    return PSO?PSOReticle:LPVO;
}

inline void PaintReticle(FSlateWindowElementList& Out,int32 Layer,const FGeometry& G,
    const FVector2f& Center,float S,float Alpha,bool PSO,float Illumination)
{
    const float Pixel=1.f/FMath::Max(.1f,G.GetAccumulatedLayoutTransform().GetScale());
    const FLinearColor Ink(.014f,.016f,.014f,Alpha);
    const FLinearColor Backing(.65f,.67f,.62f,.18f*Alpha);
    const FLinearColor Light=PSO?FLinearColor(.80f,.12f,.025f,Alpha*Illumination)
        :FLinearColor(1.f,.035f,.012f,Alpha*Illumination);
    TArray<FVector2D> Points;Points.Reserve(49);
    for(const auto& Mark:Reticle(PSO))
    {
        Points.Reset();for(const auto& P:Mark.Points)Points.Add(FVector2D(Center)+P*S);
        const float Width=FMath::Max(Mark.Width*S,.85f*Pixel);
        FSlateDrawElement::MakeLines(Out,Layer,G.ToPaintGeometry(),Points,ESlateDrawEffect::None,Backing,true,Width+Pixel*.9f);
        FSlateDrawElement::MakeLines(Out,Layer+1,G.ToPaintGeometry(),Points,ESlateDrawEffect::None,Ink,true,Width);
        if(Mark.Illuminated&&Illumination>0.f)
            FSlateDrawElement::MakeLines(Out,Layer+2,G.ToPaintGeometry(),Points,ESlateDrawEffect::None,Light,true,Width);
    }
    if(!PSO)
    {
        // Round dot, analytically sized in screen pixels, not the old square box.
        const float Radius=FMath::Max(1.1f*S,.8f*Pixel);
        TArray<FSlateVertex> Verts;TArray<SlateIndex> Indices;
        Verts.Add(FSlateVertex::Make<ESlateVertexRounding::Disabled>(G.GetAccumulatedRenderTransform(),Center,FVector2f(.5f,.5f),
            FMath::Lerp(Ink,FLinearColor(Light.R,Light.G,Light.B,Alpha),Illumination).ToFColor(true)));
        for(int32 I=0;I<=24;++I)
        {
            const auto U=Circle()[I*8];
            Verts.Add(FSlateVertex::Make<ESlateVertexRounding::Disabled>(G.GetAccumulatedRenderTransform(),Center+U*(Radius+Pixel*.6f),
                FVector2f(.5f,.5f),FLinearColor(Light.R,Light.G,Light.B,0).ToFColor(true)));
            if(I<24)Indices.Append({SlateIndex(0),SlateIndex(I+1),SlateIndex(I+2)});
        }
        const auto Resource=FSlateApplication::Get().GetRenderer()->GetResourceHandle(*FCoreStyle::Get().GetBrush(TEXT("WhiteBrush")));
        FSlateDrawElement::MakeCustomVerts(Out,Layer+2,Resource,Verts,Indices,nullptr,0,0);
    }
}
}
