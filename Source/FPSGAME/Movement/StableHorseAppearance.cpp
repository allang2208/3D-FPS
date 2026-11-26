#include "StableHorseAppearance.h"
#include "Components/PrimitiveComponent.h"
#include "Math/RandomStream.h"

namespace
{
uint32 Mix(uint32 V)
{
    V^=V>>16;V*=0x7feb352du;V^=V>>15;V*=0x846ca68bu;
    return V^(V>>16);
}
FLinearColor Pigment(const FColor& Colour,float Shade)
{
    FLinearColor C=FLinearColor::FromSRGBColor(Colour)*Shade;
    C.A=1.f;return C;
}
FVector4f Channels(const FLinearColor& C){return FVector4f(C.R,C.G,C.B,1.f);}
constexpr const TCHAR* CoatNames[]={TEXT("黑"),TEXT("白"),TEXT("灰"),TEXT("棕")};
}

FStableHorseAppearance FStableHorseAppearance::FromId(const FGuid& Id)
{
    const uint32 Seed=Mix(Mix(Mix(Mix(Id.A^0x52483330u)^Id.B)^Id.C)^Id.D);
    FRandomStream CoatRng(int32(Mix(Seed^0x11u))),ManeRng(int32(Mix(Seed^0x22u))),TailRng(int32(Mix(Seed^0x33u)));
    FStableHorseAppearance A;
    const FColor Coats[]={FColor(52,47,44),FColor(209,205,192),FColor(143,145,143),FColor(122,77,51)};
    A.Coat=CoatRng.RandRange(0,3);
    A.Patch=(A.Coat+CoatRng.RandRange(1,3))%4;
    A.CoatColour=Pigment(Coats[A.Coat],CoatRng.FRandRange(.83f,1.15f));
    A.PatchColour=Pigment(Coats[A.Patch],CoatRng.FRandRange(.87f,1.12f));
    // Preserve the R30 quarters and draw order. Each patterned quarter keeps ten
    // of its 25 percentage points, so surviving markings keep their original layout.
    const int32 PatternRoll=CoatRng.RandRange(0,99);
    constexpr int32 Quarter=25,PointsPerPattern=10;
    A.Pattern=(PatternRoll%Quarter<PointsPerPattern)?PatternRoll/Quarter:0;
    constexpr float Frequency[]={.01f,.0075f,.021f,.062f};
    constexpr float Threshold[]={1.25f,.50f,.61f,.65f};
    constexpr float Softness[]={.025f,.022f,.032f,.09f};
    const float ShiftU=CoatRng.FRand(),ShiftV=CoatRng.FRand();
    const float Scale=Frequency[A.Pattern]*CoatRng.FRandRange(.78f,1.23f);
    const float Level=Threshold[A.Pattern]+CoatRng.FRandRange(-.045f,.045f);
    A.Projection=FVector4f(ShiftU,ShiftV,Scale,Level);A.Feather=Softness[A.Pattern];
    const FColor Hair[]={FColor(45,40,37),FColor(144,139,127),FColor(83,83,80),FColor(63,45,36)};
    const bool Pale=ManeRng.FRand()<.26f && A.Coat!=0;
    A.HairColour=Pigment(Pale?FColor(158,141,112):Hair[A.Coat],ManeRng.FRandRange(.76f,1.13f));
    A.Mane=EMane(ManeRng.RandRange(0,2));A.ManeCoverage=ManeRng.FRandRange(.65f,.99f);
    A.ManeLength=ManeRng.FRandRange(.83f,1.f);
    A.Tail=ETail(TailRng.RandRange(0,2));
    const int32 T=int32(A.Tail);
    constexpr float Length[]={.77f,.96f,1.01f};
    constexpr float Width[]={.81f,1.12f,.97f};
    A.TailLength=Length[T]*TailRng.FRandRange(.94f,1.04f);
    A.TailWidth=Width[T]*TailRng.FRandRange(.93f,1.06f);
    const float Side=TailRng.RandRange(0,1)?1.f:-1.f;
    A.TailSweepCm=Side*TailRng.FRandRange(T==2?4.f:0.f,T==2?7.f:1.6f);
    A.TailCoverage=TailRng.FRandRange(.59f,.99f);
    return A;
}

void FStableHorseAppearance::ApplyPigment(UPrimitiveComponent& Body,UPrimitiveComponent& Fibres) const
{
    // CPD 0 is the existing recall/retreat fade. The graphs share the remaining slots.
    const FVector4f Coverage(ManeCoverage,TailCoverage,Feather,ManeLength);
    Body.SetCustomPrimitiveDataVector4f(4,Channels(CoatColour));
    Body.SetCustomPrimitiveDataVector4f(8,Channels(PatchColour));
    Body.SetCustomPrimitiveDataVector4f(12,Projection);
    Body.SetCustomPrimitiveDataVector4f(16,Channels(HairColour));
    Body.SetCustomPrimitiveDataVector4f(20,Coverage);
    Fibres.SetCustomPrimitiveDataVector4f(16,Channels(HairColour));
    Fibres.SetCustomPrimitiveDataVector4f(20,Coverage);
}

FString FStableHorseAppearance::CoatDescription() const
{
    const TCHAR* Patterns[]={TEXT("纯色"),TEXT("大片花"),TEXT("碎花"),TEXT("细斑")};
    FString Name=CoatNames[Coat];
    if(Pattern)Name+=FString(TEXT("／"))+CoatNames[Patch];
    return Name+Patterns[Pattern];
}

FString FStableHorseAppearance::HairDescription() const
{
    const TCHAR* Manes[]={TEXT("短鬃"),TEXT("偏梳鬃"),TEXT("长披鬃")};
    const TCHAR* Tails[]={TEXT("短收尾"),TEXT("蓬散尾"),TEXT("侧拂尾")};
    return FString::Printf(TEXT("%s · %s"),Manes[int32(Mane)],Tails[int32(Tail)]);
}

FString FStableHorseAppearance::Describe() const
{
    return CoatDescription()+TEXT("   ")+HairDescription();
}
