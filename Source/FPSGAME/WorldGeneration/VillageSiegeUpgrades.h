#pragma once

#include "CoreMinimal.h"

namespace VillageSiegeUpgrades
{
    enum class EFacility : uint8 { Trebuchet = 0, Ballista = 1, HotOil = 2, LightningSpire = 3, SmartTurret = 4 };
    inline constexpr EFacility Trebuchet = EFacility::Trebuchet;
    inline constexpr EFacility Ballista = EFacility::Ballista;
    inline constexpr EFacility HotOil = EFacility::HotOil;
    inline constexpr EFacility LightningSpire = EFacility::LightningSpire;
    inline constexpr EFacility SmartTurret = EFacility::SmartTurret;
    inline constexpr int32 FacilityCount = 5;
    enum EStat : uint8 { Damage = 0, Reload = 1, Special = 2, Reach = 3 };
    enum EOilStat : uint8 { OilDamage = 0, OilRadius = 1, OilDuration = 2, OilBurnStacks = 3 };
    enum ESpireStat : uint8 { SpireDamage = 0, SpireCooldown = 1, SpireElectrify = 2, SpireReach = 3 };
    enum ETurretStat : uint8
    {
        TurretDamage = 0,    // 火控增幅：0.85 -> 1.60 (+5%/级，15级)
        TurretFeed = 1,      // 伺服供弹：换弹 -3%/级 且 射速 +2%/级（15级）
        TurretOptics = 2,    // 光学锁敌：射程 42m -> 64.5m (+1.5m/级) 且 散布 -3%/级（15级）
        TurretWeakpoint = 3, // 弱点校准：锁头暴击率 10% / 20% / 30%（3级）
        TurretMagExpand = 4, // 弹链扩容：弹匣容量 +25% / +50% / +75%（3级）
        TurretPierce = 5     // 穿甲贯通：额外穿透 +1 / +2 / +3 目标（3级）
    };

    constexpr int32 StatsPerFacility = 4;
    // Keep CoreCount = 16 fixed (4*4 legacy 64-bit Low mask for Trebuchet/Ballista/HotOil/Spire).
    // Indices 16+ live in FRanks.High so existing saves remain 100% compatible.
    constexpr int32 CoreCount = 16;
    constexpr int32 TrebuchetHotOilIdx = 16;
    constexpr int32 SmartTurretBaseIdx = 17;
    constexpr int32 SmartTurretStatCount = 6;
    constexpr int32 Count = SmartTurretBaseIdx + SmartTurretStatCount; // 23 total stats
    constexpr int32 MaxStatsPerFacility = 6;
    inline constexpr const TCHAR* TrebuchetHotOilBlueprintId = TEXT("siege_blueprint_insulated_oil_pack");
    constexpr int32 BitsPerStat = 4;
    constexpr uint64 StatMask = 0xFULL;

    struct FRanks
    {
        uint64 Low = 0;
        uint64 High = 0;
        bool operator==(const FRanks& Other) const { return Low == Other.Low && High == Other.High; }
        bool operator!=(const FRanks& Other) const { return !(*this == Other); }
    };

    constexpr int32 Index(EFacility Facility, int32 Stat)
    {
        if (Facility == SmartTurret) return SmartTurretBaseIdx + Stat;
        if (Facility == Trebuchet && Stat == 4) return TrebuchetHotOilIdx;
        return static_cast<int32>(Facility) * StatsPerFacility + Stat;
    }
    constexpr int32 Index(bool Stone, EStat Stat) { return Index(Stone ? Trebuchet : Ballista, static_cast<int32>(Stat)); }
    constexpr int32 FacilityStatCount(EFacility F) { return F == SmartTurret ? SmartTurretStatCount : (F == Trebuchet ? 5 : 4); }
    constexpr int32 FacilityStatIndex(EFacility F, int32 Slot) { return Index(F, Slot); }
    constexpr bool Valid(int32 Idx) { return Idx >= 0 && Idx < Count; }
    constexpr EFacility FacilityOf(int32 Idx)
    {
        if (Idx >= SmartTurretBaseIdx && Idx < Count) return SmartTurret;
        if (Idx == TrebuchetHotOilIdx) return Trebuchet;
        return static_cast<EFacility>(FMath::Clamp(Idx / StatsPerFacility, 0, 3));
    }
    constexpr int32 StatOf(int32 Idx)
    {
        if (Idx >= SmartTurretBaseIdx && Idx < Count) return Idx - SmartTurretBaseIdx;
        if (Idx == TrebuchetHotOilIdx) return 4;
        return Idx % StatsPerFacility;
    }
    constexpr bool IsUniqueUpgrade(int32 Idx) { return Idx == TrebuchetHotOilIdx; }
    constexpr const TCHAR* RequiredBlueprint(int32 Idx) { return Idx == TrebuchetHotOilIdx ? TrebuchetHotOilBlueprintId : nullptr; }

    constexpr int32 MaxRank(int32 Idx)
    {
        if (!Valid(Idx)) return 0;
        if (Idx == TrebuchetHotOilIdx) return 1;
        const EFacility F = FacilityOf(Idx);
        const int32 S = StatOf(Idx);
        if (F == SmartTurret) return (S <= TurretOptics) ? 15 : 3;
        if (F == HotOil) return (S == OilDamage || S == OilRadius) ? 15 : 3;
        if (F == LightningSpire) return (S == SpireElectrify) ? 3 : 15;
        return (S == Damage || S == Reload || S == Reach) ? 15 : 3;
    }

    constexpr int32 FacilityMaxTotal(EFacility F)
    {
        int32 Sum = 0;
        const int32 N = FacilityStatCount(F);
        for (int32 S = 0; S < N; ++S) Sum += MaxRank(FacilityStatIndex(F, S));
        return Sum;
    }

    constexpr int32 Rank(uint64 Ranks, int32 Idx)
    {
        if (Idx < 0 || Idx >= CoreCount) return 0;
        const int32 Raw = static_cast<int32>((Ranks >> (BitsPerStat * Idx)) & StatMask);
        const int32 Cap = MaxRank(Idx);
        return Raw < Cap ? Raw : Cap;
    }

    constexpr int32 Rank(FRanks Ranks, int32 Idx)
    {
        if (!Valid(Idx)) return 0;
        if (Idx < CoreCount) return Rank(Ranks.Low, Idx);
        const int32 Local = Idx - CoreCount;
        const int32 Raw = static_cast<int32>((Ranks.High >> (BitsPerStat * Local)) & StatMask);
        const int32 Cap = MaxRank(Idx);
        return Raw < Cap ? Raw : Cap;
    }

    constexpr uint64 SetRank(uint64 Ranks, int32 Idx, int32 NewRank)
    {
        if (Idx < 0 || Idx >= CoreCount) return Ranks;
        const int32 Cap = MaxRank(Idx);
        const int32 Clamped = NewRank < 0 ? 0 : (NewRank > Cap ? Cap : NewRank);
        const int32 Shift = BitsPerStat * Idx;
        return (Ranks & ~(StatMask << Shift)) | (static_cast<uint64>(Clamped) << Shift);
    }

    constexpr FRanks SetRank(FRanks Ranks, int32 Idx, int32 NewRank)
    {
        if (!Valid(Idx)) return Ranks;
        if (Idx < CoreCount)
        {
            Ranks.Low = SetRank(Ranks.Low, Idx, NewRank);
            return Ranks;
        }
        const int32 Cap = MaxRank(Idx);
        const int32 Clamped = NewRank < 0 ? 0 : (NewRank > Cap ? Cap : NewRank);
        const int32 Shift = BitsPerStat * (Idx - CoreCount);
        Ranks.High = (Ranks.High & ~(StatMask << Shift)) | (static_cast<uint64>(Clamped) << Shift);
        return Ranks;
    }

    constexpr FRanks MergeRanks(FRanks A, FRanks B)
    {
        FRanks Out{};
        for (int32 Idx = 0; Idx < Count; ++Idx)
        {
            const int32 R1 = Rank(A, Idx);
            const int32 R2 = Rank(B, Idx);
            Out = SetRank(Out, Idx, R1 > R2 ? R1 : R2);
        }
        return Out;
    }

    constexpr bool HasTrebuchetHotOil(FRanks Ranks) { return Rank(Ranks, TrebuchetHotOilIdx) > 0; }

    constexpr uint64 MigrateLegacyRanks(uint16 Legacy)
    {
        uint64 Out = 0;
        for (int32 Idx = 0; Idx < 8; ++Idx)
        {
            const int32 Old = (Legacy >> (2 * Idx)) & 3;
            Out = SetRank(Out, Idx, Old);
        }
        return Out;
    }

    constexpr int32 Price(int32 Idx, int32 CurrentRank)
    {
        if (!Valid(Idx)) return 0;
        const int32 Cap = MaxRank(Idx);
        if (CurrentRank < 0 || CurrentRank >= Cap) return 0;
        if (Idx == TrebuchetHotOilIdx) return 1200;
        if (Cap <= 3)
        {
            constexpr int32 Tiers3[3] = { 200, 400, 800 };
            return Tiers3[CurrentRank];
        }
        constexpr int32 Tiers15[15] = {
            100, 140, 180, 230, 290, 360, 440, 530,
            640, 760, 900, 1060, 1240, 1440, 1680
        };
        return Tiers15[CurrentRank];
    }

    constexpr double TurretDamageMultiplier(int32 CurrentRank) { return 0.85 + 0.05 * CurrentRank; }
    constexpr double TurretReloadScale(int32 CurrentRank) { return 1.0 - 0.03 * CurrentRank; }
    constexpr double TurretFireRateScale(int32 CurrentRank) { return 1.0 + 0.02 * CurrentRank; }
    constexpr double TurretRangeCm(int32 CurrentRank) { return 4200.0 + 150.0 * CurrentRank; }
    constexpr double TurretSpreadScale(int32 CurrentRank) { return 1.0 - 0.03 * CurrentRank; }
    constexpr double TurretWeakpointChance(int32 CurrentRank) { return 0.10 * CurrentRank; }
    constexpr double TurretMagExpandBonus(int32 CurrentRank) { return 0.25 * CurrentRank; }
    inline int32 TurretExpandedCapacity(int32 BaseCapacity, int32 CurrentRank)
    {
        if (BaseCapacity <= 0) return 0;
        if (CurrentRank <= 0) return BaseCapacity;
        return FMath::Max(BaseCapacity + 1, FMath::CeilToInt(static_cast<double>(BaseCapacity) * (1.0 + TurretMagExpandBonus(CurrentRank))));
    }
    constexpr int32 TurretBonusPierce(int32 CurrentRank) { return CurrentRank < 0 ? 0 : (CurrentRank > 3 ? 3 : CurrentRank); }

    constexpr double Value(EFacility Facility, int32 Stat, int32 CurrentRank)
    {
        if (Facility == SmartTurret)
        {
            switch (Stat)
            {
            case TurretDamage:    return TurretDamageMultiplier(CurrentRank);
            case TurretFeed:      return TurretReloadScale(CurrentRank);
            case TurretOptics:    return TurretRangeCm(CurrentRank);
            case TurretWeakpoint: return TurretWeakpointChance(CurrentRank);
            case TurretMagExpand: return TurretMagExpandBonus(CurrentRank);
            case TurretPierce:    return static_cast<double>(TurretBonusPierce(CurrentRank));
            default: return 0.;
            }
        }
        if (Facility == HotOil)
        {
            switch (Stat)
            {
            case OilDamage:     return 10. * (1. + .10 * CurrentRank);
            case OilRadius:     return 275. + 15. * CurrentRank;
            case OilDuration:   return 10. + 2. * CurrentRank;
            case OilBurnStacks: return 1. + 1. * CurrentRank;
            default: return 0.;
            }
        }
        if (Facility == LightningSpire)
        {
            switch (Stat)
            {
            case SpireDamage:    return 90. * (1. + .10 * CurrentRank);
            case SpireCooldown:  return 5.20 * (1. - .03 * CurrentRank);
            case SpireElectrify: return 1. + 1. * CurrentRank;
            case SpireReach:     return 5200. * (1. + .03 * CurrentRank);
            default: return 0.;
            }
        }
        const bool Stone = (Facility == Trebuchet);
        switch (Stat)
        {
        case Damage:  return (Stone ? 220. : 320.) * (1. + .10 * CurrentRank);
        case Reload:  return (Stone ? 12.00 : 2.60) * (1. - .03 * CurrentRank);
        case Special: return Stone ? 500. + 75. * CurrentRank : .15 * CurrentRank;
        case Reach:   return (Stone ? 8100. : 5600.) * (1. + .03 * CurrentRank);
        case 4:       return Stone && CurrentRank > 0 ? 1. : 0.;
        default: return 0.;
        }
    }

    constexpr double Value(bool Stone, EStat Stat, int32 CurrentRank)
    {
        return Value(Stone ? Trebuchet : Ballista, static_cast<int32>(Stat), CurrentRank);
    }

    inline double Installed(uint64 Ranks, EFacility Facility, int32 Stat)
    {
        return Value(Facility, Stat, Rank(Ranks, Index(Facility, Stat)));
    }

    inline double Installed(FRanks Ranks, EFacility Facility, int32 Stat)
    {
        return Value(Facility, Stat, Rank(Ranks, FacilityStatIndex(Facility, Stat)));
    }

    inline double Installed(uint64 Ranks, bool Stone, EStat Stat)
    {
        return Installed(Ranks, Stone ? Trebuchet : Ballista, static_cast<int32>(Stat));
    }
}
