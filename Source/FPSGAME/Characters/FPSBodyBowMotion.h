#pragma once
#include "FPSPlayerBodyTypes.h"

namespace FPSBodyBowMotion
{
inline FName Clip(const FFPSBodyState& State)
{
    if(State.Family!=TEXT("Bow")||(State.bBowTwoHandConsume&&State.BowStowWeight>=1.f-UE_KINDA_SMALL_NUMBER)
        ||State.Action==EFPSBodyAction::Dead||State.Action==EFPSBodyAction::DoorPush
        ||State.Action==EFPSBodyAction::Traverse||State.Action==EFPSBodyAction::GunBash
        ||State.Motion==EFPSBodyMotion::Vault||State.Motion==EFPSBodyMotion::Mantle)return NAME_None;
    if(State.BowCastTransfer>0.f||State.bBowTwoHandConsume||State.Action==EFPSBodyAction::Cast||State.Action==EFPSBodyAction::Consume)return TEXT("Bow.Sparrow.Carry");
    if(State.BowClip==TEXT("Draw"))return TEXT("Bow.Sparrow.Draw");
    if(State.BowClip==TEXT("Hold"))return TEXT("Bow.Sparrow.Hold");
    if(State.BowClip==TEXT("Release"))return TEXT("Bow.Sparrow.Release");
    if(State.BowClip==TEXT("Ready")||State.BowClip==TEXT("LoadedIdle"))return TEXT("Bow.Sparrow.Ready");
    if(State.BowClip.IsNone()||State.BowClip==TEXT("Idle")||State.BowClip==TEXT("Walk")||State.BowClip==TEXT("Run"))return TEXT("Bow.Sparrow.Carry");
    return NAME_None;
}
inline float Phase(const FFPSBodyState& State)
{return FMath::Clamp(State.BowClipTime/FMath::Max(.001f,State.BowClipLength),0.f,1.f);}
inline bool Loops(FName Key)
{return Key==TEXT("Bow.Sparrow.Carry")||Key==TEXT("Bow.Sparrow.Hold");}
inline const FName WeightCurve(TEXT("SparrowBowWeight"));
inline const FName RightHoldCurve(TEXT("SparrowBowRightHold"));
inline const FName RightGripCurves[]={TEXT("SparrowBowRightX"),TEXT("SparrowBowRightY"),TEXT("SparrowBowRightZ"),
    TEXT("SparrowBowRightQX"),TEXT("SparrowBowRightQY"),TEXT("SparrowBowRightQZ"),TEXT("SparrowBowRightQW")};
inline const FName GripCurves[]={TEXT("SparrowBowGripX"),TEXT("SparrowBowGripY"),TEXT("SparrowBowGripZ"),
    TEXT("SparrowBowGripQX"),TEXT("SparrowBowGripQY"),TEXT("SparrowBowGripQZ"),TEXT("SparrowBowGripQW")};
inline const FName NockCurves[]={TEXT("SparrowBowNockX"),TEXT("SparrowBowNockY"),TEXT("SparrowBowNockZ")};
}
