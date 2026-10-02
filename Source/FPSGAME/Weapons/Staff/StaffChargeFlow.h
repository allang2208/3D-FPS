#pragma once
#include "StaffCastMotion.h"

class UStaffWeaponComponent;

// Gather and release share anatomical cast keys. The primary-smash controls
// retain their separate action bank.
namespace StaffChargeFlow
{
    bool UsesKeys(const FStaffCastPose& Pose);
    FStaffCastPose Raise(const FStaffCastPose& Entry,float Fraction,float& EntryWeight);
    FStaffCastPose Ready(const FStaffCastPose& Entry,float Fraction,float& EntryWeight);
    FStaffCastPose ResolveEntry(const UStaffWeaponComponent& Staff,FStaffCastPose Pose,
        const FStaffCastPose& Entry,float EntryWeight);
    FStaffCastPose ResolveRelease(const UStaffWeaponComponent& Staff,FStaffCastPose Pose);
    FStaffCastPose ResolveRecovery(const UStaffWeaponComponent& Staff,FStaffCastPose Pose,
        const FStaffCastPose& From,const FStaffCastPose& Current,float Fraction);
    FStaffCastPose Settled(const UStaffWeaponComponent& Staff);
}
