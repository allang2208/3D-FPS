#include "FPSPlayerReactionCamera.h"
#include "FPSBodyReactionState.h"
#include "Camera/CameraTypes.h"

void FFPSPlayerReactionCamera::Apply(const FFPSBodyReactionState& State,float Now,float Delta,float Scale,bool bEnabled,FMinimalViewInfo& View)
{
    if(!bEnabled)
    {
        LastHit=State.HitSerial;Stun={};SwayAge=0.f;
        for(auto& Hit:Hits)Hit=FHit();
        return;
    }
    if(State.HitSerial!=LastHit)
    {
        LastHit=State.HitSerial;
        if(Now-State.HitAt<.55f)
        {
            auto& Hit=Hits[NextHit];NextHit=(NextHit+1)%UE_ARRAY_COUNT(Hits);
            Hit.StartedAt=State.HitAt;Hit.Strength=State.HitStrength;
            Hit.Direction=View.Rotation.Quaternion().UnrotateVector(State.HitDirection);
            Hit.Phase=float(State.HitSerial%17)*2.399963f;
        }
    }
    const float Weight=Stun.Step(State.bStunned?1.f:0.f,Delta,State.bStunned?11.f:7.5f);
    if(State.bStunned||Weight>.0001f)SwayAge+=FMath::Max(0.f,Delta);else SwayAge=0.f;
    const float T=SwayAge;
    // Unequal rhythms with slow phase modulation make a drifting, asymmetric
    // balance correction. The envelope preserves continuity when status ends.
    const float A=2.f*PI*.43f*T+.31f*FMath::Sin(2.f*PI*.17f*T);
    const float B=2.f*PI*.67f*T+.42f*FMath::Sin(2.f*PI*.11f*T+.6f);
    FVector Angles(-.7f+1.35f*FMath::Sin(B)+.24f*FMath::Sin(A*1.61f),
        1.8f*FMath::Sin(A+.45f)+.35f*FMath::Sin(B*1.43f),
        3.4f*FMath::Sin(A)+.65f*FMath::Sin(B+.8f));
    FVector Position(.18f*FMath::Sin(B),.55f*FMath::Sin(A+.2f),-.30f+.24f*FMath::Sin(B+.7f));
    Angles*=Weight;Position*=Weight;
    FVector HitAngles=FVector::ZeroVector,HitPosition=FVector::ZeroVector;
    for(const auto& Hit:Hits)
    {
        const float Age=Now-Hit.StartedAt;
        if(Age<0.f||Age>=.55f||Hit.Strength<=0.f)continue;
        const float X=FMath::Clamp(Age/.024f,0.f,1.f);
        const float Entry=X*X*X*(X*(6.f*X-15.f)+10.f);
        const float End=FMath::SmoothStep(.34f,.55f,Age);
        const float Envelope=Entry*FMath::Exp(-8.5f*Age)*(1.f-End)*Hit.Strength;
        const float Kick=FMath::Cos(22.f*Age),Ring=FMath::Sin(53.f*Age+Hit.Phase);
        HitAngles+=FVector((1.75f+.9f*FMath::Abs(Hit.Direction.X))*Kick+.25f*Ring,
            Hit.Direction.Y*1.4f*Kick+.16f*Ring,
            -Hit.Direction.Y*2.2f*Kick+.32f*FMath::Sin(41.f*Age+Hit.Phase))*Envelope;
        HitPosition+=(Hit.Direction*.8f*Kick+FVector(0,.06f*Ring,-.22f*Kick))*Envelope;
    }
    // A short burst can overlap, but cannot accumulate into a large view jump.
    Angles+=HitAngles.GetClampedToMaxSize(4.5f);
    Position+=HitPosition.GetClampedToMaxSize(1.2f);
    const FQuat Base=View.Rotation.Quaternion();
    View.Location+=Base.RotateVector(Position*Scale);
    View.Rotation=(Base*FRotator(Angles.X*Scale,Angles.Y*Scale,Angles.Z*Scale).Quaternion()).Rotator();
}
