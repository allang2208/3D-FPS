#pragma once
#include "CoreMinimal.h"
#include "../Monsters/MonsterCoreStats.h"

// Internal catalog tables and formatting; definitions remain owned by the page.
namespace ColdSteelCodexPrivate
{
extern const TCHAR* WeaponCategoryKeys[];
extern const TCHAR* WeaponCategoryLabels[];
extern const int32 WeaponCategoryCount;
extern const EMonsterRank MonsterCategoryRanks[5];
extern const TCHAR* MonsterCategoryLabels[5];
extern const int32 MonsterCategoryCount;
extern const TCHAR* StatusCategoryKinds[3];
extern const TCHAR* StatusCategoryLabels[3];
extern const int32 StatusCategoryCount;
struct FStatusGroupDef { const TCHAR* Key; const TCHAR* Label; const TCHAR* Note; };
extern const FStatusGroupDef StatusGroups[5];
extern const int32 StatusGroupCount;
extern const TCHAR* TributeRarityKeys[6];
extern const TCHAR* TributeRarityLabels[6];
inline constexpr int32 TributeRarityCount = UE_ARRAY_COUNT(TributeRarityKeys);
extern const TCHAR* EnchantCategorySlots[3];
extern const TCHAR* EnchantCategoryLabels[3];
extern const int32 EnchantCategoryCount;
FString EnchantRestrictionText(const FString& Key);
bool MatchesTributeRarity(const FString& Rarity);
FString Dash();
FString FormatNumber(double Value, int32 Decimals = 0);
FString RankLabel(EMonsterRank Rank);
}
