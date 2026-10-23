#pragma once
#include "CoreMinimal.h"
struct FColdSteelItem;
struct FColdSteelProfile;

namespace RuneboundHammer
{
    inline constexpr const TCHAR* Definition=TEXT("ue_runebound_warhammer");
    inline constexpr int32 HitsToAwaken=10;
    inline constexpr int32 SwiftHitsToAwaken=5;
    FPSGAME_API bool HasSwiftRune(const FColdSteelItem& Item);
    FPSGAME_API bool HasDestructionRune(const FColdSteelItem& Item);
    inline constexpr const TCHAR* StarOathHead=TEXT("star_oath_sealing_anvil");
    inline constexpr double StarOathAttackMultiplier=1.1,DetonationMagicAttackScale=2.;
    inline constexpr int32 DetonationHits=3,DetonationMotes=384;
    inline constexpr float DetonationRadiusCM=250.f;
    inline constexpr const TCHAR* FinalTollHead=TEXT("final_toll_soul_bell");
    inline constexpr const TCHAR* FinalTollMotes=TEXT("/Game/Weapons/RuneboundWarhammer20261022/FinalTollV1/M_FinalToll_Mote.M_FinalToll_Mote");
    FPSGAME_API bool HasFinalToll(const FColdSteelItem& Item);
    FPSGAME_API bool HasStarOath(const FColdSteelItem& Item);
    FPSGAME_API double AttackMultiplier(const FColdSteelItem& Item);
    FPSGAME_API double AttackMultiplier(const FColdSteelProfile& State);
    inline constexpr double DestructionAttributeMultiplier=1.1,DestructionAwakeningMultiplier=2.;
    FPSGAME_API double AttributeMultiplier(const FColdSteelItem& Item);
    FPSGAME_API double AttributeMultiplier(const FColdSteelProfile& State,FName Key);
    FPSGAME_API int32 RequiredHits(const FColdSteelItem& Item);
    inline constexpr float ActiveSeconds=20.f;
    // The crystal sword uses 0.10 INT + 0.10 WIS. This temporary awakening uses 1.5x.
    inline constexpr double Intelligence=.15,Wisdom=.15;
    inline constexpr const TCHAR* Hud=TEXT("/Game/Weapons/RuneboundWarhammer20261022/HudSymmetricCapsV3/M_RuneboundEnergyHud.M_RuneboundEnergyHud");
    inline constexpr const TCHAR* Motes=TEXT("/Game/Weapons/RuneboundWarhammer20261022/PassiveV1/M_RuneboundMote.M_RuneboundMote");
    inline constexpr const TCHAR* DestructionMotes=TEXT("/Game/Weapons/RuneboundWarhammer20261022/DestructionRedImpactV2/M_RuneboundDestructionMote.M_RuneboundDestructionMote");
    inline constexpr int32 MoteCount=36;
    inline constexpr int32 HitMotes=160,HitBurstSlots=4;
    inline constexpr int32 SwiftMoteCount=60,SwiftHitMotes=240;
    inline constexpr int32 DestructionMoteCount=60,DestructionHitMotes=240;
    inline constexpr float HitMoteSeconds=2.35f,HeadHeightCM=91.6f;
    inline constexpr int32 AmbientMoteCapacity=60,HitMoteCapacity=DetonationMotes;
    inline constexpr int32 SealQuadCapacity=64;
    inline constexpr int32 MoteBudget=AmbientMoteCapacity+HitMoteCapacity*HitBurstSlots+SealQuadCapacity;
}
