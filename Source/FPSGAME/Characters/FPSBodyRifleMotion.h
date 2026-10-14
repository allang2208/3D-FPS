#pragma once
#include "FPSPlayerBodyTypes.h"

namespace FPSBodyRifleMotion
{
// These rifle wrists are sampled relative to the native hold, then placed on
// the world torso. Camera-space contacts remain reserved for other executors.
inline bool UsesHoldSpace(const FFPSBodyState& State)
{
    if(State.Family!=TEXT("Rifle")||State.bDual||State.Contacts.Channel==TEXT("Bipod"))return false;
    return State.Action==EFPSBodyAction::Reload||State.Action==EFPSBodyAction::ReloadEmpty
        ||State.Action==EFPSBodyAction::Inspect||State.Action==EFPSBodyAction::Equip;
}
}
