#pragma once
#include "CoreMinimal.h"

struct FColdSteelProfile;

namespace ColdSteelCurrency
{
    // Same exact-integer ceiling as the profile's other economic quantities.
    inline constexpr int64 MaxSouls = 9007199254740991ll;
    inline constexpr const TCHAR* Definition = TEXT("souls");
    inline bool IsCurrency(const FString& Id) { return Id==Definition || Id==TEXT("gold"); }
    FPSGAME_API bool Credit(FColdSteelProfile& Profile,int64 Amount);
    FPSGAME_API bool Debit(FColdSteelProfile& Profile,int64 Amount);
    FPSGAME_API bool MergeServerCredits(FColdSteelProfile& Local,const FColdSteelProfile& Server);
    FPSGAME_API bool Normalize(FColdSteelProfile& Profile,bool& Changed,FString& Reason);
}
