#pragma once
#include "FPSPlayerBodyTypes.h"

// Cosmetic library selection. Executors retain stamina, hitstop and hit timing.
namespace FPSBodyHandAttackMotion
{
inline FName Clip(const FFPSBodyState& S)
{
    if(S.Motion==EFPSBodyMotion::Vault||S.Motion==EFPSBodyMotion::Mantle)return NAME_None;
    if(S.Family==TEXT("Staff"))
    {
        if(S.Action==EFPSBodyAction::Strike)return TEXT("Staff.FullBody.Strike");
        if(S.Action==EFPSBodyAction::GunBash&&S.ActionVariant==TEXT("StaffPunch"))return TEXT("Unarmed.FullBody.PunchLeft");
    }
    if(S.Family==TEXT("Unarmed")&&S.Action==EFPSBodyAction::GunBash)
    {
        if(S.ActionVariant==TEXT("PunchLeft"))return TEXT("Unarmed.FullBody.PunchLeft");
        if(S.ActionVariant==TEXT("PunchRight"))return TEXT("Unarmed.FullBody.PunchRight");
    }
    return NAME_None;
}
inline uint8 PreserveHands(const FFPSBodyState& S)
{
    if(S.Family!=TEXT("Staff"))return 0;
    // A left jab must retain the right-hand staff. During a staff strike the
    // optional left pistol retains its own aim, recoil, equip and reload pose.
    return S.Action==EFPSBodyAction::GunBash?1:S.bOffhandPistol?2:0;
}
}
