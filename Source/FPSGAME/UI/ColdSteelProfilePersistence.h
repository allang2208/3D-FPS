#pragma once

#include "ColdSteelInventoryTypes.h"

class UColdSteelProfileSave;

// Shared by profile loading and checked transactions; definitions have one owner.
namespace ColdSteelProfilePersistence
{
    bool RemoveRetiredItems(FColdSteelProfile& Profile);
    UColdSteelProfileSave* ReadCheckedProfile(const FString& Slot);
}
