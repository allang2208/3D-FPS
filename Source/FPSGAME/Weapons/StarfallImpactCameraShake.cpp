#include "StarfallImpactCameraShake.h"

UStarfallImpactCameraShake::UStarfallImpactCameraShake(const FObjectInitializer& Initializer)
    : Super(Initializer)
{
    bSingleInstance=true;
    SetRootShakePattern(CreateDefaultSubobject<UStarfallImpactShakePattern>(TEXT("StarfallContact")));
}

void UStarfallImpactShakePattern::GetShakePatternInfoImpl(FCameraShakeInfo& Info) const
{
    Info.Duration=FCameraShakeDuration(.26f);
    Info.BlendIn=.005f;
    Info.BlendOut=.09f;
}

void UStarfallImpactShakePattern::UpdateShakePatternImpl(const FCameraShakePatternUpdateParams& Params,
    FCameraShakePatternUpdateResult& Result)
{
    Age+=Params.DeltaTime;
    const float Envelope=FMath::Square(FMath::Clamp(1.f-Age/.26f,0.f,1.f));
    // One compact push with a softer return, no controller/input modification.
    const float Push=FMath::Sin(FMath::Min(Age/.10f,1.f)*PI);
    Result.Location=FVector(-.95f*Push,.10f*FMath::Sin(Age*83.f),-.28f*FMath::Sin(Age*51.f))*Envelope;
    Result.Rotation=FRotator(.24f*FMath::Sin(Age*47.f)*Envelope,0.f,.08f*FMath::Sin(Age*71.f)*Envelope);
}
