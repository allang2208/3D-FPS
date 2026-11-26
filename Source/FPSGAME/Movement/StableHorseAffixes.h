#pragma once

#include "CoreMinimal.h"
#include "Math/RandomStream.h"

enum class EStableHorseAffix : uint8
{
    VeryStrong,      // 非常强壮: 生命上限 +10%
    Strong,          // 强壮: 生命上限 +5%
    Frail,           // 瘦弱: 生命上限 -5%
    VeryFrail,       // 非常瘦弱: 生命上限 -10%
    FleetFooted,     // 健步如飞: 奔跑/疾驰速度 +10%
    Swift,           // 迅捷: 奔跑/疾驰速度 +5%
    Lame,            // 跛脚: 奔跑/疾驰速度 -5%
    Crippled,        // 残疾: 奔跑/疾驰速度 -10%
    BigHeart,        // 大心脏: 体力恢复速度 +20%
    HeartCondition,  // 心脏病: 体力恢复速度 -20%
    Nimble,          // 灵巧: 转向速度 +20%
    Clumsy,          // 笨拙: 转向速度 -20%
    Industrious,     // 勤劳: 马匹背包 +2 排
    Lazy,            // 懒惰: 马匹背包 -2 排
    BattleHardened,  // 身经百战: 基础移速 +5%，疾驰 +10%，出战自然回血 +1%/秒
    AllRounder,      // 多面手: 所有六维属性 +10%（随等级成长同步乘算）
    PackMule,        // 搬运工: 马匹背包 +4 排
    Warhorse,        // 战马: 在场时玩家物理伤害 +10%，玩家生命恢复速度 +30%
    SpiritSteed,     // 灵驹: 在场时玩家魔法伤害 +10%，玩家魔法恢复速度 +30%
    Tireless,        // 生生不息: 基础体力上限 +20%，体力恢复速度 +50%
    Count
};

enum class EStableHorseAffixTier : uint8
{
    Special,
    PositiveMajor,
    Positive,
    Negative,
    NegativeMajor
};

struct FStableHorseAffixDef
{
    EStableHorseAffix Type;
    const TCHAR* Id;          // Icon filename stem under Content/ColdSteelData/Icons/HorseAffixes/<Id>.png
    const TCHAR* Name;
    const TCHAR* ShortEffect;
    const TCHAR* Description;
    EStableHorseAffixTier Tier;
    int32 PriceDelta;
};

struct FStableHorseAffixBonuses
{
    float HealthMultiplier = 1.f;
    float StaminaMultiplier = 1.f;
    float BaseMoveMultiplier = 1.f;
    float CanterSpeedMultiplier = 1.f;
    float StaminaRecoveryMultiplier = 1.f;
    float TurnMultiplier = 1.f;
    float StatAllMultiplier = 1.f;
    float NaturalRegenPerSecondPct = 0.f;
    int32 BagRowDelta = 0;
    float PlayerPhysicalDamageBonus = 0.f;
    float PlayerHealthRegenBonus = 0.f;
    float PlayerMagicDamageBonus = 0.f;
    float PlayerManaRegenBonus = 0.f;
    int32 PriceDelta = 0;

    static constexpr int32 BaseBagRows = 2;
    int32 BagRows() const { return FMath::Max(0, BaseBagRows + BagRowDelta); }
    int32 BagCells() const { return BagRows() * 18; }
};

namespace StableHorseAffixes
{
    inline constexpr int32 TotalCount = int32(EStableHorseAffix::Count);
    inline constexpr const TCHAR* MountBagContainerPrefix = TEXT("mount.");

    inline const FStableHorseAffixDef& Definition(EStableHorseAffix Type)
    {
        static const FStableHorseAffixDef Table[TotalCount] = {
            { EStableHorseAffix::VeryStrong,     TEXT("very_strong"),     TEXT("非常强壮"), TEXT("生命 +10%"),      TEXT("体格雄健，生命上限 +10%"),                                      EStableHorseAffixTier::PositiveMajor,  260 },
            { EStableHorseAffix::Strong,         TEXT("strong"),          TEXT("强壮"),     TEXT("生命 +5%"),       TEXT("筋骨结实，生命上限 +5%"),                                       EStableHorseAffixTier::Positive,       130 },
            { EStableHorseAffix::Frail,          TEXT("frail"),           TEXT("瘦弱"),     TEXT("生命 -5%"),       TEXT("体格偏弱，生命上限 -5%"),                                       EStableHorseAffixTier::Negative,      -120 },
            { EStableHorseAffix::VeryFrail,      TEXT("very_frail"),      TEXT("非常瘦弱"), TEXT("生命 -10%"),      TEXT("气血亏虚，生命上限 -10%"),                                      EStableHorseAffixTier::NegativeMajor, -240 },
            { EStableHorseAffix::FleetFooted,    TEXT("fleet_footed"),    TEXT("健步如飞"), TEXT("奔跑 +10%"),      TEXT("四蹄生风，奔跑与疾驰速度 +10%"),                                EStableHorseAffixTier::PositiveMajor,  360 },
            { EStableHorseAffix::Swift,          TEXT("swift"),           TEXT("迅捷"),     TEXT("奔跑 +5%"),       TEXT("步履轻快，奔跑与疾驰速度 +5%"),                                 EStableHorseAffixTier::Positive,       180 },
            { EStableHorseAffix::Lame,           TEXT("lame"),            TEXT("跛脚"),     TEXT("奔跑 -5%"),       TEXT("腿脚偶有滞涩，奔跑与疾驰速度 -5%"),                             EStableHorseAffixTier::Negative,      -170 },
            { EStableHorseAffix::Crippled,       TEXT("crippled"),        TEXT("残疾"),     TEXT("奔跑 -10%"),      TEXT("旧伤缠身，奔跑与疾驰速度 -10%"),                                EStableHorseAffixTier::NegativeMajor, -340 },
            { EStableHorseAffix::BigHeart,       TEXT("big_heart"),       TEXT("大心脏"),   TEXT("回体 +20%"),      TEXT("心肺澎湃，体力恢复速度 +20%"),                                  EStableHorseAffixTier::Positive,       190 },
            { EStableHorseAffix::HeartCondition, TEXT("heart_condition"), TEXT("心脏病"),   TEXT("回体 -20%"),      TEXT("心脉孱弱，体力恢复速度 -20%"),                                  EStableHorseAffixTier::Negative,      -180 },
            { EStableHorseAffix::Nimble,         TEXT("nimble"),          TEXT("灵巧"),     TEXT("转向 +20%"),      TEXT("身姿敏捷，转向速度 +20%"),                                      EStableHorseAffixTier::Positive,       150 },
            { EStableHorseAffix::Clumsy,         TEXT("clumsy"),          TEXT("笨拙"),     TEXT("转向 -20%"),      TEXT("转身迟缓，转向速度 -20%"),                                      EStableHorseAffixTier::Negative,      -140 },
            { EStableHorseAffix::Industrious,    TEXT("industrious"),     TEXT("勤劳"),     TEXT("背包 +2排"),     TEXT("擅长负重，马匹背包容量 +2 排（+36 格）"),                       EStableHorseAffixTier::Positive,       220 },
            { EStableHorseAffix::Lazy,           TEXT("lazy"),            TEXT("懒惰"),     TEXT("背包 -2排"),     TEXT("抗拒负重，马匹背包容量 -2 排（若未叠加搬运工则无背包空间）"),   EStableHorseAffixTier::Negative,      -200 },
            { EStableHorseAffix::BattleHardened, TEXT("battle_hardened"), TEXT("身经百战"), TEXT("移速+5%/疾驰+10%/回血1%"), TEXT("沙场老将：基础移速 +5%，疾驰速度额外 +10%，出战在场每秒自然恢复 1% 生命值"), EStableHorseAffixTier::Special, 720 },
            { EStableHorseAffix::AllRounder,     TEXT("all_rounder"),     TEXT("多面手"),   TEXT("全属性 +10%"),    TEXT("天资均衡：全部六维属性 +10%，并随等级成长同步乘算生效"),       EStableHorseAffixTier::Special,        780 },
            { EStableHorseAffix::PackMule,       TEXT("pack_mule"),       TEXT("搬运工"),   TEXT("背包 +4排"),     TEXT("行商良伴：马匹背包容量额外 +4 排（+72 格），可与普通背包词条叠加"), EStableHorseAffixTier::Special, 640 },
            { EStableHorseAffix::Warhorse,       TEXT("warhorse"),        TEXT("战马"),     TEXT("主人物伤+10%/回血+30%"), TEXT("铁血战骑：在场存活时，主人物理伤害 +10%，生命值恢复速度 +30%"), EStableHorseAffixTier::Special, 860 },
            { EStableHorseAffix::SpiritSteed,    TEXT("spirit_steed"),    TEXT("灵驹"),     TEXT("主人魔伤+10%/回魔+30%"), TEXT("灵脉相通：在场存活时，主人魔法伤害 +10%，魔法恢复速度 +30%"),   EStableHorseAffixTier::Special, 860 },
            { EStableHorseAffix::Tireless,       TEXT("tireless"),        TEXT("生生不息"), TEXT("体力+20%/回体+50%"), TEXT("精力无穷：基础体力上限 +20%，体力恢复速度 +50%，可与普通体力词条叠加"), EStableHorseAffixTier::Special, 680 },
        };
        const int32 Idx = FMath::Clamp(int32(Type), 0, TotalCount - 1);
        return Table[Idx];
    }

    inline uint32 AffixSeed(const FGuid& Id)
    {
        uint32 Domain = 0x41464658u; // 'AFFX' — independent from 'NAME'/'BASE'/'GROW'/coat
        for (uint32 Word : { Id.A, Id.B, Id.C, Id.D })
        {
            Domain ^= Word;
            Domain ^= Domain >> 16; Domain *= 0x7feb352du;
            Domain ^= Domain >> 15; Domain *= 0x846ca68bu;
            Domain ^= Domain >> 16;
        }
        return Domain;
    }

    using FAffixList = TArray<EStableHorseAffix, TInlineAllocator<4>>;

    inline FAffixList Roll(const FGuid& Id)
    {
        FAffixList Result;
        if (!Id.IsValid()) return Result;

        FRandomStream Rng(int32(AffixSeed(Id)));
        // 1~4 affixes per horse (weighted: 1=26%, 2=36%, 3=26%, 4=12%)
        const int32 CountRoll = Rng.RandRange(0, 99);
        const int32 Count = CountRoll < 26 ? 1 : (CountRoll < 62 ? 2 : (CountRoll < 88 ? 3 : 4));

        // At most 1 special affix (~25% chance)
        const bool bHasSpecial = Rng.RandRange(0, 99) < 25;
        if (bHasSpecial)
        {
            static constexpr EStableHorseAffix Specials[] = {
                EStableHorseAffix::BattleHardened,
                EStableHorseAffix::AllRounder,
                EStableHorseAffix::PackMule,
                EStableHorseAffix::Warhorse,
                EStableHorseAffix::SpiritSteed,
                EStableHorseAffix::Tireless,
            };
            Result.Add(Specials[Rng.RandRange(0, UE_ARRAY_COUNT(Specials) - 1)]);
        }

        // Fill remaining slots from distinct normal dimensions (mutually exclusive within each dimension).
        // Special affixes (PackMule / Tireless) may freely coexist with normal Bag / StaminaRecovery affixes.
        int32 Dimensions[5] = { 0, 1, 2, 3, 4 }; // 0=HP, 1=Speed, 2=StamRec, 3=Turn, 4=Bag
        for (int32 I = 4; I > 0; --I)
        {
            const int32 SwapIdx = Rng.RandRange(0, I);
            Swap(Dimensions[I], Dimensions[SwapIdx]);
        }

        const int32 NormalSlots = FMath::Min(5, Count - Result.Num());
        for (int32 I = 0; I < NormalSlots; ++I)
        {
            const int32 Dim = Dimensions[I];
            const int32 Pick = Rng.RandRange(0, 99);
            switch (Dim)
            {
                case 0: // HP
                    Result.Add(Pick < 18 ? EStableHorseAffix::VeryStrong
                             : Pick < 50 ? EStableHorseAffix::Strong
                             : Pick < 82 ? EStableHorseAffix::Frail
                                         : EStableHorseAffix::VeryFrail);
                    break;
                case 1: // Speed
                    Result.Add(Pick < 18 ? EStableHorseAffix::FleetFooted
                             : Pick < 50 ? EStableHorseAffix::Swift
                             : Pick < 82 ? EStableHorseAffix::Lame
                                         : EStableHorseAffix::Crippled);
                    break;
                case 2: // Stamina Recovery
                    Result.Add(Pick < 50 ? EStableHorseAffix::BigHeart : EStableHorseAffix::HeartCondition);
                    break;
                case 3: // Turn
                    Result.Add(Pick < 50 ? EStableHorseAffix::Nimble : EStableHorseAffix::Clumsy);
                    break;
                case 4: // Bag
                    Result.Add(Pick < 50 ? EStableHorseAffix::Industrious : EStableHorseAffix::Lazy);
                    break;
                default: break;
            }
        }

        // Sort: Special -> PositiveMajor -> Positive -> Negative -> NegativeMajor
        Result.StableSort([](EStableHorseAffix A, EStableHorseAffix B)
        {
            const uint8 TA = uint8(Definition(A).Tier);
            const uint8 TB = uint8(Definition(B).Tier);
            return TA != TB ? TA < TB : uint8(A) < uint8(B);
        });
        return Result;
    }

    inline FStableHorseAffixBonuses Bonuses(const FGuid& Id)
    {
        FStableHorseAffixBonuses B;
        if (!Id.IsValid()) return B;
        float HealthPct = 0.f;
        float StaminaPct = 0.f;
        float RunSpeedPct = 0.f;
        float StaminaRecPct = 0.f;
        float TurnPct = 0.f;
        for (EStableHorseAffix Affix : Roll(Id))
        {
            B.PriceDelta += Definition(Affix).PriceDelta;
            switch (Affix)
            {
                case EStableHorseAffix::VeryStrong:     HealthPct += 0.10f; break;
                case EStableHorseAffix::Strong:         HealthPct += 0.05f; break;
                case EStableHorseAffix::Frail:          HealthPct -= 0.05f; break;
                case EStableHorseAffix::VeryFrail:      HealthPct -= 0.10f; break;
                case EStableHorseAffix::FleetFooted:    RunSpeedPct += 0.10f; break;
                case EStableHorseAffix::Swift:          RunSpeedPct += 0.05f; break;
                case EStableHorseAffix::Lame:           RunSpeedPct -= 0.05f; break;
                case EStableHorseAffix::Crippled:       RunSpeedPct -= 0.10f; break;
                case EStableHorseAffix::BigHeart:       StaminaRecPct += 0.20f; break;
                case EStableHorseAffix::HeartCondition: StaminaRecPct -= 0.20f; break;
                case EStableHorseAffix::Nimble:         TurnPct += 0.20f; break;
                case EStableHorseAffix::Clumsy:         TurnPct -= 0.20f; break;
                case EStableHorseAffix::Industrious:    B.BagRowDelta += 2; break;
                case EStableHorseAffix::Lazy:           B.BagRowDelta -= 2; break;
                case EStableHorseAffix::BattleHardened:
                    B.BaseMoveMultiplier += 0.05f;
                    RunSpeedPct += 0.10f;
                    B.NaturalRegenPerSecondPct += 0.01f;
                    break;
                case EStableHorseAffix::AllRounder:
                    B.StatAllMultiplier = 1.10f;
                    break;
                case EStableHorseAffix::PackMule:
                    B.BagRowDelta += 4;
                    break;
                case EStableHorseAffix::Warhorse:
                    B.PlayerPhysicalDamageBonus += 0.10f;
                    B.PlayerHealthRegenBonus += 0.30f;
                    break;
                case EStableHorseAffix::SpiritSteed:
                    B.PlayerMagicDamageBonus += 0.10f;
                    B.PlayerManaRegenBonus += 0.30f;
                    break;
                case EStableHorseAffix::Tireless:
                    StaminaPct += 0.20f;
                    StaminaRecPct += 0.50f;
                    break;
                default: break;
            }
        }
        B.HealthMultiplier = FMath::Max(0.25f, 1.f + HealthPct);
        B.StaminaMultiplier = FMath::Max(0.25f, 1.f + StaminaPct);
        B.CanterSpeedMultiplier = FMath::Max(0.25f, 1.f + RunSpeedPct);
        B.StaminaRecoveryMultiplier = FMath::Max(0.20f, 1.f + StaminaRecPct);
        B.TurnMultiplier = FMath::Max(0.20f, 1.f + TurnPct);
        return B;
    }

    inline bool HasAffix(const FGuid& Id, EStableHorseAffix Target)
    {
        return Roll(Id).Contains(Target);
    }

    inline FString BagContainerKey(const FGuid& HorseId)
    {
        return HorseId.IsValid() ? (FString(MountBagContainerPrefix) + HorseId.ToString(EGuidFormats::Digits)) : FString();
    }

    inline bool TryParseBagContainer(const FString& Container, FGuid& OutHorseId)
    {
        if (!Container.StartsWith(MountBagContainerPrefix)) return false;
        const FString Suffix = Container.Mid(FCString::Strlen(MountBagContainerPrefix));
        return FGuid::ParseExact(Suffix, EGuidFormats::Digits, OutHorseId) && OutHorseId.IsValid();
    }

    inline bool IsBagContainer(const FString& Container)
    {
        FGuid Parsed;
        return TryParseBagContainer(Container, Parsed);
    }

    inline int32 BagRowsForHorse(const FGuid& HorseId)
    {
        return Bonuses(HorseId).BagRows();
    }

    inline int32 BagCellsForHorse(const FGuid& HorseId)
    {
        return Bonuses(HorseId).BagCells();
    }
}
