#pragma once
#include "CoreMinimal.h"

/** Elastic distal flesh. The shoulder and muscular proximal chain never extend. */
namespace BoundCongregateTentacleReach
{
inline constexpr int32 Count=57,Start=14,CoilStart=48,Samples=128;

inline void Deploy(FVector (&Goals)[Count],const float* RestLengths,const FVector& Aim,
    float Stroke,float Wrap,float Radius)
{
    const float Deploy=FMath::SmoothStep(0.f,1.f,Stroke);
    if(Deploy<=0.f)return;
    const FVector Root=Goals[Start],Direction=(Aim-Root).GetSafeNormal();
    const FVector Tangent=(Goals[Start]-Goals[Start-1]).GetSafeNormal();
    FVector Side=FVector::CrossProduct(FVector::UpVector,Direction).GetSafeNormal();
    if(Side.IsNearlyZero())Side=FVector::RightVector;
    float TerminalLength=0.f;
    for(int32 I=CoilStart;I<Count-1;++I)TerminalLength+=RestLengths[I];
    const float Distance=FVector::Distance(Root,Aim);
    const float Lead=FMath::Min(TerminalLength,Distance*.2f);
    const FVector End=Aim-Direction*FMath::Lerp(Lead,Radius,Wrap);
    const FVector C1=Root+Tangent*FMath::Min(90.f,Distance*.15f);
    const FVector C2=End-Direction*FMath::Min(350.f,Distance*.3f);
    FVector Curve[Samples+1];float Arc[Samples+1]={};
    for(int32 I=0;I<=Samples;++I)
    {
        const float U=float(I)/Samples,V=1.f-U;
        // A diminishing transverse wave travels towards the tip while the
        // root drives forward. The final stroke has an exact committed end.
        const float Wave=FMath::Sin(2.f*PI*(U-Stroke)) * FMath::Square(FMath::Sin(PI*U)) *
            (1.f-Stroke)*FMath::Min(130.f,Distance*.12f);
        Curve[I]=Root*(V*V*V)+C1*(3.f*V*V*U)+C2*(3.f*V*U*U)+End*(U*U*U)+Side*Wave;
        if(I)Arc[I]=Arc[I-1]+FVector::Distance(Curve[I-1],Curve[I]);
    }
    float Base=0.f,Flexible=0.f;
    for(int32 I=Start+1;I<=CoilStart;++I)
    {Base+=RestLengths[I-1];Flexible+=RestLengths[I-1]*FMath::SmoothStep(0.f,8.f,float(I-Start));}
    const float Extra=FMath::Max(0.f,Arc[Samples]-Base);
    float Along=0.f;int32 Segment=1;
    for(int32 I=Start+1;I<=CoilStart;++I)
    {
        // Allocate extra travel gradually after the thick root, retaining a
        // dense terminal chain for capture rather than a coarse 30 m coil.
        Along+=RestLengths[I-1]+Extra*RestLengths[I-1]*FMath::SmoothStep(0.f,8.f,float(I-Start))/FMath::Max(.001f,Flexible);
        const float At=Along*Arc[Samples]/FMath::Max(.001f,Base+Extra);
        while(Segment<Samples&&Arc[Segment]<At)++Segment;
        const FVector P=FMath::Lerp(Curve[Segment-1],Curve[Segment],FMath::Clamp(
            (At-Arc[Segment-1])/FMath::Max(.001f,Arc[Segment]-Arc[Segment-1]),0.f,1.f));
        Goals[I]=FMath::Lerp(Goals[I],P,Deploy);
    }
    for(int32 I=CoilStart+1;I<Count;++I)
    {
        const float U=float(I-CoilStart)/(Count-1-CoilStart),Angle=5.2f*U;
        const FVector Straight=Aim-Direction*(Lead*(1.f-U));
        const FVector Coil=Aim+(-Direction*FMath::Cos(Angle)+Side*FMath::Sin(Angle))*Radius+FVector::UpVector*(12.f*U);
        Goals[I]=FMath::Lerp(Goals[I],FMath::Lerp(Straight,Coil,Wrap),Deploy);
    }
}

inline FVector SectionScale(const FTransform& Original,const FVector& RestDirection,float Stretch,int32 Index)
{
    const float Blend=FMath::SmoothStep(float(Start),float(Start+6),float(Index));
    const float Radius=FMath::Lerp(1.f,FMath::Clamp(FMath::Pow(FMath::Max(1.f,Stretch),-.23f),.55f,1.f),Blend);
    FVector Scale(Radius);
    // FBX bone axes are taken from the imported reference frame, never assumed
    // to match Blender's Y axis. Longitudinal displacement comes from stations.
    const FVector Axis=Original.InverseTransformVectorNoScale(RestDirection).GetAbs();
    Scale[Axis.X>Axis.Y?(Axis.X>Axis.Z?0:2):(Axis.Y>Axis.Z?1:2)]=1.f;
    return Original.GetScale3D()*Scale;
}
}
