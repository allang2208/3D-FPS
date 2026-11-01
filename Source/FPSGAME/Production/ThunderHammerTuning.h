#pragma once
#include "CoreMinimal.h"
struct FColdSteelItem;
class UColdSteelStatusModel;

namespace ThunderHammer
{
    inline constexpr const TCHAR* Definition=TEXT("ue_thunder_god_hammer");
    inline constexpr float MagicAttackScale=1.f,RadiusCM=300.f,StunSeconds=1.5f;
    inline constexpr int32 ElectrifyStacks=2;
    inline constexpr float SkyHeightCM=2400.f,VisualSeconds=.65f;
    // Native 100% magic-attack strike, with the same attacker bonuses as the
    // weapon's magic panel. Heavy scaling belongs only to that existing panel.
    float LightningMagic(const FColdSteelItem& Item,const UColdSteelStatusModel* Profile);
}
