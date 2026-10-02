#include "DoorPushCameraShake.h"

UDoorPushCameraShake::UDoorPushCameraShake(const FObjectInitializer& ObjectInitializer)
    : Super(ObjectInitializer)
{
    bSingleInstance=true;
    SetRootShakePattern(CreateDefaultSubobject<UDoorPushContactShakePattern>(TEXT("DoorPushContactImpulse")));
}

void UDoorPushContactShakePattern::GetShakePatternInfoImpl(FCameraShakeInfo& OutInfo) const
{
    OutInfo.Duration=FCameraShakeDuration(DurationSeconds);
    OutInfo.BlendIn=.004f;OutInfo.BlendOut=.035f;
}

void UDoorPushContactShakePattern::UpdateShakePatternImpl(const FCameraShakePatternUpdateParams& Params,
    FCameraShakePatternUpdateResult& OutResult)
{
    Age+=Params.DeltaTime;
    // The first peak lands immediately after contact, followed by two smaller
    // opposite/return pulses. Each segment settles to its authored endpoint.
    constexpr float Times[]={0.f,.018f,.055f,.10f,DurationSeconds};
    constexpr float Values[]={0.f,1.f,-.24f,.075f,0.f};
    float Pulse=0.f;
    for(int32 Segment=0;Segment<4;++Segment)
    {
        if(Age>Times[Segment+1])continue;
        const float Alpha=FMath::Clamp((Age-Times[Segment])/(Times[Segment+1]-Times[Segment]),0.f,1.f);
        const float Smooth=Alpha*Alpha*(3.f-2.f*Alpha);
        Pulse=FMath::Lerp(Values[Segment],Values[Segment+1],Smooth);
        break;
    }
    OutResult.Location=FVector(-1.28f*Pulse,0.f,-.4f*Pulse);
    OutResult.Rotation=FRotator(-1.12f*Pulse,0.f,.32f*Pulse);
}
