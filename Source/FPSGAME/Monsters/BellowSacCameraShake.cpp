#include "BellowSacCameraShake.h"
UBellowSacCameraShake::UBellowSacCameraShake(const FObjectInitializer& Initializer) : Super(Initializer)
{
    bSingleInstance=true;
    SetRootShakePattern(CreateDefaultSubobject<UBellowSacShakePattern>(TEXT("SacPressureImpulse")));
}
void UBellowSacShakePattern::GetShakePatternInfoImpl(FCameraShakeInfo& Info) const
{ Info.Duration=FCameraShakeDuration(.22f); Info.BlendIn=.006f; Info.BlendOut=.07f; }
void UBellowSacShakePattern::UpdateShakePatternImpl(const FCameraShakePatternUpdateParams& Params, FCameraShakePatternUpdateResult& Result)
{
    Age+=Params.DeltaTime;
    const float Envelope=FMath::Square(FMath::Clamp(1.f-Age/.22f,0.f,1.f));
    Result.Rotation=FRotator(.65f*FMath::Sin(Age*63.f), .09f*FMath::Sin(Age*43.f), .25f*FMath::Sin(Age*51.f))*Envelope;
    Result.Location=FVector(-.9f*FMath::Sin(Age*51.f),0,.25f*FMath::Sin(Age*73.f))*Envelope;
}
