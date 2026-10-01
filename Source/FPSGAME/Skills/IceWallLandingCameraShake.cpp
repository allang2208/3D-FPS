#include "IceWallLandingCameraShake.h"

UIceWallLandingCameraShake::UIceWallLandingCameraShake(const FObjectInitializer& ObjectInitializer)
    : Super(ObjectInitializer)
{
    bSingleInstance=true;
    SetRootShakePattern(CreateDefaultSubobject<UIceWallLandingShakePattern>(TEXT("IceWallGroundImpact")));
}

void UIceWallLandingShakePattern::GetShakePatternInfoImpl(FCameraShakeInfo& OutInfo) const
{
    OutInfo.Duration=FCameraShakeDuration(.23f);
    OutInfo.BlendIn=.008f;OutInfo.BlendOut=.075f;
}

void UIceWallLandingShakePattern::UpdateShakePatternImpl(const FCameraShakePatternUpdateParams& Params,
    FCameraShakePatternUpdateResult& OutResult)
{
    Age+=Params.DeltaTime;
    const float Envelope=FMath::Square(FMath::Clamp(1.f-Age/.23f,0.f,1.f));
    OutResult.Location=FVector(.10f*FMath::Sin(Age*73.f),.18f*FMath::Sin(Age*51.f),
        -.85f*FMath::Sin(Age*57.f))*Envelope;
    OutResult.Rotation=FRotator(.32f*FMath::Sin(Age*63.f)*Envelope,0.f,
        .15f*FMath::Sin(Age*47.f)*Envelope);
}
