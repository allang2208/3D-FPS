#pragma once
#include "CoreMinimal.h"

struct FColdSteelItem;

// Gameplay-only attachment: the original trigger mesh and animation stay in use.
namespace FullAutoTrigger
{
inline constexpr const TCHAR* Part = TEXT("legendary_full_auto_trigger");
inline constexpr const TCHAR* ModeKey = TEXT("pistol_fire_mode");
bool Supports(const FString& Definition);
bool Installed(const FString& Definition, const TMap<FString,FString>& Parts);
bool Automatic(const FColdSteelItem& Item, bool bInstalled);
FString Hint(bool bAutomatic, int32 HandIndex);
}
