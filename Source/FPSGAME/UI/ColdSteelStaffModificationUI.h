#pragma once

#include "../Weapons/Staff/StaffCatalog.h"

/** 仅定义改造台的名称、单位与收益方向；数值来自实际装配的 _craftEffects。 */
namespace ColdSteelStaffUI
{
    struct FEffectField
    {
        const TCHAR* Key;
        const TCHAR* Label;
        double Scale;
        int32 Digits;
        const TCHAR* Unit;
        bool bLowerBetter;
        bool bAlwaysInOverview;
        bool bTriggerPeriod = false;
    };

    inline const FEffectField Fields[] = {
        {TEXT("magicDamagePercent"),TEXT("法术伤害加成"),100,1,TEXT("%"),false,true},
        {TEXT("magicCritPercent"),TEXT("法术暴击率加成"),100,1,TEXT("%"),false,true},
        {TEXT("magicMpCostPercent"),TEXT("法术耗蓝增减"),100,1,TEXT("%"),true,true},
        {TEXT("magicRangePercent"),TEXT("法术距离加成"),100,1,TEXT("%"),false,true},
        {TEXT("magicCooldownPercent"),TEXT("法术冷却缩减"),100,1,TEXT("%"),false,true},
        {TEXT("castSpeedPercent"),TEXT("施法速度加成"),100,1,TEXT("%"),false,true},
        {TEXT("fireDamagePercent"),TEXT("火系伤害加成"),100,1,TEXT("%"),false,true},
        {TEXT("iceDamagePercent"),TEXT("冰系伤害加成"),100,1,TEXT("%"),false,true},
        {TEXT("electricDamagePercent"),TEXT("电系伤害加成"),100,1,TEXT("%"),false,true},
        {TEXT("lightHealPercent"),TEXT("光系治疗加成"),100,1,TEXT("%"),false,true},
        {TEXT("iceSpikeCountDelta"),TEXT("冰锥数量加成"),1,0,TEXT(" 枚"),false,false},
        {TEXT("fireballExplosionRadiusPercent"),TEXT("火球爆炸范围加成"),100,1,TEXT("%"),false,false},
        {TEXT("lightningChainTargetsDelta"),TEXT("闪电传导目标加成"),1,0,TEXT(" 个"),false,false},
        {TEXT("holyLightHoTStacks"),TEXT("圣光续疗层数"),1,0,TEXT(" 层"),false,false},
        {TEXT("holyLightHoTSeconds"),TEXT("圣光续疗持续时间"),1,2,TEXT(" s"),false,false},
        {TEXT("chainSpellDamagePercent"),TEXT("链式强化伤害（每层）"),100,1,TEXT("%"),false,false},
        {TEXT("chainSpellMpCostPercent"),TEXT("链式强化耗蓝（每层）"),100,1,TEXT("%"),true,false},
        {TEXT("castHasteStacks"),TEXT("施法后自身加速层数"),1,0,TEXT(" 层"),false,false},
        {TEXT("castHasteDuration"),TEXT("施法后自身加速时间"),.001,2,TEXT(" s"),false,false},
        {TEXT("iceChillSlowPercent"),TEXT("寒冷减速（每层）"),100,1,TEXT("%"),false,false},
        {TEXT("iceChillDuration"),TEXT("寒冷持续时间"),.001,2,TEXT(" s"),false,false},
        {TEXT("electricStunExtendMs"),TEXT("附加／延长眩晕时间"),.001,2,TEXT(" s"),false,false},
        {TEXT("lightHasteStacks"),TEXT("光系治疗目标加速层数"),1,0,TEXT(" 层"),false,false},
        {TEXT("lightHasteDuration"),TEXT("光系治疗目标加速时间"),.001,2,TEXT(" s"),false,false},
        {TEXT("fireBurnDamageMul"),TEXT("灼伤每跳魔法伤害倍率"),1,2,TEXT("×"),false,false},
        {TEXT("fireBurnTickMs"),TEXT("灼伤跳伤间隔"),.001,2,TEXT(" s"),true,false,true},
        {TEXT("fireBurnDuration"),TEXT("灼伤持续时间"),.001,2,TEXT(" s"),false,false}
    };

    inline bool LowerBetter(const FEffectField& Field, double Before, double After)
    {
        // 原厂没有灼伤时 0 表示未触发，不是比 0.5 秒更快的跳伤。
        return Field.bTriggerPeriod && (Before <= 0 || After <= 0) ? false : Field.bLowerBetter;
    }

    inline TSharedPtr<FJsonObject> Part(const FString& Slot, const FString& Id)
    {
        const auto Catalog = ColdSteelStaff::Catalog();
        if (!Catalog || Id.IsEmpty() || Id == TEXT("false")) return nullptr;
        for (const auto& Value : Catalog->GetArrayField(TEXT("columns")))
        {
            const auto Column = Value->AsObject();
            if (Column->GetStringField(TEXT("key")) != Slot) continue;
            for (const auto& Option : Column->GetArrayField(TEXT("options")))
                if (Option->AsObject()->GetStringField(TEXT("id")) == Id) return Option->AsObject();
        }
        return nullptr;
    }

    inline FString Specialty(const ColdSteelStaff::FParts& Parts)
    {
        const auto Head = Part(TEXT("head_crystal"), Parts.FindRef(TEXT("head_crystal")));
        FString Result;
        if (Head) Head->GetObjectField(TEXT("effects"))->TryGetStringField(TEXT("staffSpecialty"), Result);
        return Result;
    }

    inline FString SpecialtyName(const FString& Key)
    {
        if (Key == TEXT("fire")) return TEXT("火系");
        if (Key == TEXT("ice")) return TEXT("冰系");
        if (Key == TEXT("electric")) return TEXT("电系");
        if (Key == TEXT("light")) return TEXT("光系");
        return Key.IsEmpty() ? TEXT("通用") : Key;
    }

    struct FCrownState
    {
        FString Text = TEXT("未安装");
        bool bInstalled = false;
        bool bActive = false;
    };

    inline FCrownState Crown(const ColdSteelStaff::FParts& Parts)
    {
        FCrownState Result;
        const auto Crown = Part(TEXT("crown"), Parts.FindRef(TEXT("crown")));
        if (!Crown) return Result;
        FString Required;
        Crown->TryGetStringField(TEXT("requires_specialty"), Required);
        Result.bInstalled = true;
        Result.bActive = Required.IsEmpty() || Required == Specialty(Parts);
        if (Required.IsEmpty()) Result.Text = TEXT("已激活");
        else Result.Text = (Result.bActive ? FString(TEXT("已激活 · ")) : FString(TEXT("未激活 · 需"))) + SpecialtyName(Required);
        return Result;
    }
}
