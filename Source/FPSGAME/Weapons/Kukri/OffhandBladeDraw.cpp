#include "OffhandBladeDraw.h"
#include "OffhandDrawWrist.h"
#include "HatchetPairRhythm.h"
#include "HatchetDrawRhythm.h"
#include "KukriDrawRhythm.h"
#include "KukriOffhandDraw.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"

namespace OffhandBladeDraw
{
float Length(bool Axe){return ((Axe?UE_ARRAY_COUNT(OffhandDrawWrist::Hatchet):UE_ARRAY_COUNT(OffhandDrawWrist::Kukri))-1)/60.f;}
FTransform InHand(bool Axe,float Time){return Axe?HatchetPairRhythm::SampleLeftHatchet(Time):KukriOffhandDraw::Sample(Time);}
FTransform FlightDelta(bool Axe,float Time){return InHand(Axe,Time).GetRelativeTransform(KukriOffhandDraw::Grip());}
FVector WristOffset(bool Axe,float Time)
{
    const float (*Curve)[3]=Axe?OffhandDrawWrist::Hatchet:OffhandDrawWrist::Kukri;
    const int32 End=(Axe?UE_ARRAY_COUNT(OffhandDrawWrist::Hatchet):UE_ARRAY_COUNT(OffhandDrawWrist::Kukri))-1;
    const float X=FMath::Clamp(Time*60.f,0.f,float(End));
    const int32 I=FMath::Min(int32(X),End-1);
    return FMath::Lerp(FVector(Curve[I][0],Curve[I][1],Curve[I][2]),
        FVector(Curve[I+1][0],Curve[I+1][1],Curve[I+1][2]),X-I);
}
float OpenHand(bool Axe,float Time)
{
    const float T=Time-(Axe?HatchetPairRhythm::LeftDelay:KukriDualEquipBlade::LeftDelay);
    const float Toss=Axe?HatchetDrawRhythm::TossAt:KukriDrawRhythm::TossAt;
    const float Catch=Axe?HatchetDrawRhythm::CatchAt:KukriDrawRhythm::CatchAt;
    return FMath::SmoothStep(Toss-.055f,Toss+.025f,T)*(1.f-FMath::SmoothStep(Catch-.065f,Catch+.015f,T));
}
void Camera(bool Axe,float Time,FRotator& Rotation,float& Fov)
{
    const float T=FMath::Max(0.f,Time-(Axe?HatchetPairRhythm::LeftDelay:KukriDualEquipBlade::LeftDelay));
    (Axe?HatchetDrawRhythm::Camera:KukriDrawRhythm::Camera)(T,Rotation,Fov);
    Rotation.Yaw=-Rotation.Yaw;Rotation.Roll=-Rotation.Roll;
}
void PlayCues(UObject* Owner,bool Axe,float Before,float Now,USoundBase* Toss,USoundBase* Catch)
{
    const float Delay=Axe?HatchetPairRhythm::LeftDelay:KukriDualEquipBlade::LeftDelay;
    const float Release=Delay+(Axe?HatchetDrawRhythm::TossAt:KukriDrawRhythm::TossAt);
    const float Land=Delay+(Axe?HatchetDrawRhythm::CatchAt:KukriDrawRhythm::CatchAt);
    if(Toss&&Before<Release&&Now>=Release)UGameplayStatics::PlaySound2D(Owner,Toss,
        (Axe?HatchetDrawRhythm::TossVolume:KukriDrawRhythm::TossVolume)*KukriDrawRhythm::OffhandVolume,
        (Axe?HatchetDrawRhythm::TossPitch:KukriDrawRhythm::TossPitch)*KukriDrawRhythm::OffhandPitch);
    if(Catch&&Before<Land&&Now>=Land)UGameplayStatics::PlaySound2D(Owner,Catch,
        (Axe?HatchetDrawRhythm::CatchVolume:KukriDrawRhythm::CatchVolume)*KukriDrawRhythm::OffhandVolume,
        (Axe?HatchetDrawRhythm::CatchPitch:KukriDrawRhythm::CatchPitch)*KukriDrawRhythm::OffhandPitch);
}
}
