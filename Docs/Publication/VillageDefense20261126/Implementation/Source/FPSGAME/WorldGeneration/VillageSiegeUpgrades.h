#pragma once

#include "CoreMinimal.h"

namespace VillageSiegeUpgrades
{
    enum EStat : uint8 { Damage, Reload, Special, Reach };
    constexpr int32 MaxRank = 3;
    constexpr int32 Count = 8;
    constexpr int32 Index(bool Stone, EStat Stat) { return (Stone ? 0 : 4) + Stat; }
    constexpr bool Valid(int32 Index) { return Index >= 0 && Index < Count; }
    constexpr int32 Rank(uint16 Ranks,int32 Index) { return Valid(Index) ? (Ranks >> (2 * Index)) & 3 : 0; }
    constexpr int32 Price(int32 Rank) { return Rank >= 0 && Rank < MaxRank ? 200 << Rank : 0; }
    constexpr double Value(bool Stone,EStat Stat,int32 Rank)
    {
        switch (Stat)
        {
        case Damage: return (Stone ? 300. : 180.) * (1. + .20 * Rank);
        case Reload: return (Stone ? 10. : 3.27) * (1. - .10 * Rank);
        case Special: return Stone ? 500. + 75. * Rank : .10 * Rank;
        case Reach: return (Stone ? 8100. : 5600.) * (1. + .10 * Rank);
        }
        return 0.;
    }
    inline double Installed(uint16 Ranks,bool Stone,EStat Stat)
    {
        return Value(Stone,Stat,Rank(Ranks,Index(Stone,Stat)));
    }
}
