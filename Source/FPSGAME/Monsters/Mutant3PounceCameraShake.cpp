#include "Mutant3PounceCameraShake.h"

UMutant3PounceCameraShake::UMutant3PounceCameraShake(const FObjectInitializer& ObjectInitializer)
    : Super(ObjectInitializer)
{
    bSingleInstance=true;
    SetRootShakePattern(CreateDefaultSubobject<UMutant3PounceShakePattern>(TEXT("LandingImpulse")));
}

void UMutant3PounceShakePattern::GetShakePatternInfoImpl(FCameraShakeInfo& OutInfo) const
{
    OutInfo.Duration=FCameraShakeDuration(.18f);
    OutInfo.BlendIn=.008f; OutInfo.BlendOut=.055f;
}

void UMutant3PounceShakePattern::UpdateShakePatternImpl(const FCameraShakePatternUpdateParams& Params,
    FCameraShakePatternUpdateResult& OutResult)
{
    Age+=Params.DeltaTime;
    const float Envelope=FMath::Square(FMath::Clamp(1.f-Age/.18f,0.f,1.f));
    OutResult.Rotation=FRotator(.32f*FMath::Sin(Age*65.f)*Envelope, 0.f,
        .16f*FMath::Sin(Age*48.f)*Envelope);
    // A separate short grading pulse composes with the player's existing red
    // damage fade; it never takes ownership of CameraManager's fade state.
    if (Age<.08f)
    {
        OutResult.PostProcessSettings.bOverride_ColorGain=true;
        OutResult.PostProcessSettings.ColorGain=FVector4(1.8f,1.8f,1.8f,1.f);
        OutResult.PostProcessSettings.bOverride_ColorSaturation=true;
        OutResult.PostProcessSettings.ColorSaturation=FVector4(.55f,.55f,.55f,1.f);
        OutResult.PostProcessBlendWeight=.18f*FMath::Sin(PI*Age/.08f);
    }
}
