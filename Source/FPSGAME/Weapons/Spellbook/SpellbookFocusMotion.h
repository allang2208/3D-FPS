#pragma once
#include "CoreMinimal.h"

namespace SpellbookFocusMotion
{
inline constexpr float Detach=.18f, Gather=.65f, OpenStart=.84f, OpenDuration=.35f;
inline constexpr float HoverArrive=.80f, Ready=OpenStart+OpenDuration;
inline constexpr float PageCycle=16.f, Close=.34f, PalmPrepare=.18f, Drop=.24f;
inline constexpr float ContactHold=.10f, Grip=.36f, Settle=1.30f, HeldReturn=.42f;
inline constexpr float DropStart=Close+PalmPrepare, Contact=DropStart+Drop;
inline constexpr float GripStart=Contact+ContactHold, GripEnd=GripStart+Grip;
inline constexpr float ReturnLength=GripEnd+Settle;
inline constexpr float GripContact=Contact/ReturnLength;
inline float Ease(float From,float To,float Value)
{
    const float T=FMath::Clamp((Value-From)/FMath::Max(.001f,To-From),0.f,1.f);
    return T*T*T*(T*(T*6.f-15.f)+10.f);
}
inline float IdleHandoff(float Age)
{
    return Ease(ReturnLength-.12f,ReturnLength,Age);
}
inline FTransform ReadingFrame()
{
    // Restore the original readable page orientation and placement. This is
    // the stable reading endpoint, independent of the side-on carry grip.
    const float Tilt=FMath::DegreesToRadians(25.f);
    const FQuat Rotation=FRotationMatrix::MakeFromXY(FVector(0,-1,0),
        FVector(FMath::Cos(Tilt),0,FMath::Sin(Tilt))).ToQuat();
    return FTransform(Rotation,FVector(44.f,-19.f,-14.f));
}
inline FTransform ReturnBook(const FTransform& From,const FTransform& Catch,float Age)
{
    // Once gripped, the book follows the authored hand directly. A second
    // camera-space blend here would make it lag and slide through the fingers.
    if(Age>=GripEnd)return Catch;
    // Keep the spine axis and position fixed. Raising the back half by 90 degrees
    // while the front's open angle closes makes both halves meet above the spine.
    // This is the closing hinge motion, not a turn of the closed book afterward.
    FTransform Closed=From;
    // Closing shares the original reading basis. Capture From at the toggle
    // so a partial opening also enters the landing frame continuously.
    const FQuat SpineDown=ReadingFrame().GetRotation()*FQuat(FVector::YAxisVector,-.5f*PI);
    Closed.SetRotation(FQuat::Slerp(From.GetRotation(),SpineDown,Ease(0.f,Close,Age)).GetNormalized());
    if(Age<=DropStart)return Closed;
    const float Fall=FMath::Clamp((Age-DropStart)/Drop,0.f,1.f);
    FTransform Result=Closed;
    FVector Location=From.GetLocation();
    Location.Z=FMath::Lerp(From.GetLocation().Z,Catch.GetLocation().Z,Fall*Fall);
    Result.SetLocation(Location);
    // Resolve the tiny hover offset during the final finger closure, before
    // the wrist starts rolling. Preserve the accepted drop and contact path.
    FTransform Attached;
    Attached.Blend(Result,Catch,Ease(GripEnd-.08f,GripEnd,Age));
    return Attached;
}
inline FTransform Hover(float Age)
{
    FTransform Result=ReadingFrame();
    const float Fade=FMath::SmoothStep(Ready,Ready+.6f,Age);
    Result.AddToTranslation(FVector(.35f*FMath::Sin(Age*1.1f),0,.55f*FMath::Sin(Age*1.5f))*Fade);
    return Result;
}
inline FTransform OpenBook(const FTransform& From,float Age,float ReleasedAt)
{
    // One eased transition from the original gather/release to the original
    // reading frame. Finish it before the covers open; no extra held-arm flip
    // and no further book-root rotation during opening or reading.
    const float Rise=Ease(ReleasedAt,FMath::Max(ReleasedAt+.01f,HoverArrive),Age);
    FTransform Result;
    Result.Blend(From,Hover(Age),Rise);
    Result.SetScale3D(From.GetScale3D());
    return Result;
}
}
