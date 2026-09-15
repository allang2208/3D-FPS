#include "FPSDodgeRootMotionSource.h"

FRootMotionSource_FPSDodge::FRootMotionSource_FPSDodge()
{
    Settings.UnSetFlag(ERootMotionSourceSettingsFlags::DisablePartialEndTick);
    Settings.SetFlag(ERootMotionSourceSettingsFlags::IgnoreZAccumulate);
}

FRootMotionSource* FRootMotionSource_FPSDodge::Clone() const { return new FRootMotionSource_FPSDodge(*this); }
UScriptStruct* FRootMotionSource_FPSDodge::GetScriptStruct() const { return StaticStruct(); }

void FRootMotionSource_FPSDodge::PrepareRootMotion(float SimulationTime, float MovementTickTime,
    const ACharacter&, const UCharacterMovementComponent&)
{
    RootMotionParams.Clear();
    if (Duration > UE_SMALL_NUMBER && MovementTickTime > UE_SMALL_NUMBER)
    {
        const float A=FMath::Clamp(GetTime()/Duration,0.f,1.f);
        const float B=FMath::Clamp((GetTime()+SimulationTime)/Duration,0.f,1.f);
        // p(t)=2t-t^2: start quickly, brake to rest. Integrate the interval so
        // different frame lengths do not change the requested total distance.
        const float Fraction=(B-A)*(2.f-A-B);
        RootMotionParams.Set(FTransform(Force*(Duration*Fraction/MovementTickTime)));
    }
    SetTime(GetTime()+SimulationTime);
}
