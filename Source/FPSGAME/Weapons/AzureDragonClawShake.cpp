#include "AzureDragonClawShake.h"

UAzureDragonClawShake::UAzureDragonClawShake(const FObjectInitializer& ObjectInitializer)
    : Super(ObjectInitializer)
{
    bSingleInstance=true;
    SetRootShakePattern(CreateDefaultSubobject<UAzureDragonClawShakePattern>(TEXT("RakeImpulse")));
}

void UAzureDragonClawShakePattern::GetShakePatternInfoImpl(FCameraShakeInfo& OutInfo) const
{
    OutInfo.Duration=FCameraShakeDuration(.2f);
    OutInfo.BlendIn=.006f; OutInfo.BlendOut=.06f;
}

void UAzureDragonClawShakePattern::UpdateShakePatternImpl(const FCameraShakePatternUpdateParams& Params,
    FCameraShakePatternUpdateResult& OutResult)
{
    Age+=Params.DeltaTime;
    // A hard first beat then a fast decay: reads as weight landing, not as wobble.
    const float Envelope=FMath::Square(FMath::Clamp(1.f-Age/.2f,0.f,1.f));
    OutResult.Rotation=FRotator(-.45f*FMath::Sin(Age*58.f+.6f)*Envelope,.12f*FMath::Sin(Age*37.f)*Envelope,
        .30f*FMath::Sin(Age*44.f)*Envelope);
    OutResult.FOV=-.8f*Envelope*FMath::Clamp(1.f-Age/.08f,0.f,1.f);
}
