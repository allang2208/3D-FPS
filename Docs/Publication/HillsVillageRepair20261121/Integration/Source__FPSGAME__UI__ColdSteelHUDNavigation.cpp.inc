// Source/FPSGAME/UI/ColdSteelHUDNavigation.cpp
// Merge each excerpt at the named target and scope. Line numbers locate the 2026-11-21 production source.

// Lines 11-13 | file scope
#include "../WorldGeneration/VillageDefenseSection.h"
#include "../WorldGeneration/VillageDefenseStairs.h"
#include "../WorldGeneration/HighVillageDefense.h"

// Lines 23-40 | bool UColdSteelHUDWidget::ReadHUDTarget(const AFPSGAMECharacter& Player,FMonsterHitFeedback& Out) const
bool UColdSteelHUDWidget::ReadHUDTarget(const AFPSGAMECharacter& Player,FMonsterHitFeedback& Out) const
{
    if(const auto* Section=FocusedDefense.Get())
    {
        Out=FMonsterHitFeedback{};
        Out.Target=FocusedDefense.Get();
        if(Section->IsA<AHighVillageGate>())Out.Name=NSLOCTEXT("VillageDefense","HighGate","石城门 · 升降铁闸");
        else if(Section->IsA<AHighVillageWall>())Out.Name=NSLOCTEXT("VillageDefense","HighWall","石砌高墙");
        else if(Section->IsA<AVillageDefenseStairs>())Out.Name=NSLOCTEXT("VoxelBuilding","VillageWallStairs","城墙石阶");
        else Out.Name=Section->IsA<AVillageDefenseGate>()
            ? NSLOCTEXT("VillageDefense","Gate","村庄城门") : NSLOCTEXT("VillageDefense","Wall","村庄围墙");
        Out.Health=Section->GetHealth();
        Out.MaxHealth=Section->GetMaximumHealth();
        Out.Opacity=1.f;
        return Out.MaxHealth>0.f;
    }
    return Player.GetMonsterHitFeedback(Out);
}

// Lines 62-63 | void UColdSteelHUDWidget::RefreshHUDTargetDisplay()
            if(FocusedDefense.IsValid())
                Snapshot.RemoveAll([](const FStatusEffectView& Effect){return Effect.Kind!=TEXT("debuff");});
