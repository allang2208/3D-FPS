#pragma once
#include "SpellbookFocusMotion.h"
#include "SpellbookBookOrientation.h"

// V2: rapid page sweep -> close above the waiting palm -> vertical drop ->
// contact -> the unchanged normal return clock. Fingers close after contact.
namespace SpellbookFocusInterruptMotion
{
inline constexpr float RapidEnd=.30f,CollapseStart=RapidEnd,CollapseEnd=.49f;
inline constexpr float DropStart=.51f,Catch=.75f,GoldOut=.07f,DropHeight=14.f;
inline constexpr float CatchSource=1.28f;
// V3: give the moving pages a head start before raising the receiving hand.
inline constexpr float BookClearanceStart=.14f,HandApproachStart=RapidEnd;
inline constexpr float ThumbClearanceDegrees=14.f,ThumbClearanceEndSource=.95f;
inline FQuat ClearThumb(const FQuat& Rotation,float Weight)
{
    // Thumb_01 is parented to hand_l. Rotate about the actual book spine in
    // that parent space, away from the cover; preserve the native bone length.
    static const FVector Spine=SpellbookBookOrientation::InHand().GetRotation().RotateVector(FVector::YAxisVector);
    return (FQuat(Spine,FMath::DegreesToRadians(ThumbClearanceDegrees)*Weight)*Rotation).GetNormalized();
}
inline float NormalReturnStart(float Source)
{
    float Low=0.f,High=SpellbookFocusMotion::OpenLength;
    for(int32 I=0;I<20;++I)
    {
        const float Middle=(Low+High)*.5f;
        if(SpellbookFocusMotion::SourceTime(Middle)<Source)Low=Middle;else High=Middle;
    }
    return (Low+High)*.5f;
}
}
