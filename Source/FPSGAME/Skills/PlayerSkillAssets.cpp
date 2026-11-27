#include "PlayerSkillPreparation.h"
#include "../Weapons/PojunGrip.h"
#include "ChainSlashAssets.h"
#include "MagicArrowRainTypes.h"
#include "ElementalArrowTypes.h"
#include "IlluminationArrowTypes.h"
#include "FlameArmorAssets.h"
#include "MeteorAssets.h"
#include "LeapStrikeMotion.h"
#include "DragonBreathAudioAssets.h"
#include "IceArmorTypes.h"
#include "LightningHasteTypes.h"
#include "FPSBlizzardZone.h"
#include "FPSAbsoluteZeroNova.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "../Weapons/ModularSwordVisual.h"
#include "../Production/WarhammerQuickCombatMotion.h"
#include "../Production/WarhammerConicalThrustMotion.h"
#include "../Weapons/Kukri/KukriRhythm.h"
#include "../Weapons/Kukri/KukriDrawRhythm.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "Serialization/JsonSerializer.h"
#include "Dom/JsonObject.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "HAL/IConsoleManager.h"

namespace
{
void AddSkillAsset(TArray<FSoftObjectPath>& Out, const FString& Path)
{
    if (Path.StartsWith(TEXT("/")))
        Out.AddUnique(FSoftObjectPath(Path.Contains(TEXT(".")) ? Path : Path + TEXT(".") + FPaths::GetCleanFilename(Path)));
}
}

// Exact runtime assets, including impact/preview resources used only on release.
// Keep these entries aligned when changing the corresponding spell's load sites.
void PlayerSkillAssets::Gather(FName Skill, const FColdSteelProfile& Profile, TArray<FSoftObjectPath>& Out)
{
    if(Skill==TEXT("leapStrike"))for(const TCHAR* Path:{
        LeapStrike::Asset,MeteorSpellAssets::Preview,
        TEXT("/Game/Weapons/SteelWarhammer20261014/UppercutV1/A_Warhammer_Uppercut"),
        TEXT("/Game/Weapons/SteelWarhammer20261014/HeavySlamV4/A_Warhammer_HeavyCharge"),
        TEXT("/Game/Weapons/SteelWarhammer20261014/HeavySlamV4/A_Warhammer_HeavyRelease"),
        TEXT("/Game/Weapons/SteelWarhammer20261014/HeavySlamV1/M_WarhammerGroundWave"),
        TEXT("/Game/Weapons/SteelWarhammer20261014/LeapStrikeV2/SM_LeapGroundWave"),
        TEXT("/Game/Weapons/SteelWarhammer20261014/GroundImpactAudioV1/S_Warhammer_GroundImpact")})AddSkillAsset(Out,Path);
    if(Skill==TEXT("illuminationArrow"))for(const auto* P:{IlluminationArrow::Glow,IlluminationArrow::Outline,IlluminationArrow::Depth})AddSkillAsset(Out,P);
    if(Skill==TEXT("heartPiercingArrow"))AddSkillAsset(Out,TEXT("/Game/Skills/HeartPiercingArrow/Audio20261026/S_HeartPiercingArrow_Release.S_HeartPiercingArrow_Release"));
    if(Skill==TEXT("elementalArrow"))for(const auto& P:ElementalArrow::Assets())Out.AddUnique(P);
    if(Skill==TEXT("magicArrowRain")){for(const auto* Name:MagicArrowRainAssets::Names)AddSkillAsset(Out,MagicArrowRainAssets::Path(Name));AddSkillAsset(Out,MagicArrowRainAssets::Path(TEXT("ATT_ArrowRain")));AddSkillAsset(Out,TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));}
    if(Skill==TEXT("lightningHaste"))for(const TCHAR* Path:{LightningHasteAssets::Arc,LightningHasteAssets::CastSound,LightningHasteAssets::EndSound})AddSkillAsset(Out,Path);
    if (Skill == TEXT("quickCombat"))
        for (const TCHAR* Path : {
            TEXT("/Game/Audio/QuickCombat20260918/S_QuickCombatSwing.S_QuickCombatSwing"),
            TEXT("/Game/Audio/WeaponHit20260916/S_MeleeHit_Quick.S_MeleeHit_Quick"),
            TEXT("/Game/Weapons/DanWesson715/QuickCombat20260918/Animations/A_DW715_quickcombat.A_DW715_quickcombat")}) AddSkillAsset(Out, Path);
    if (Skill == TEXT("chainSlash"))
    {
        AddSkillAsset(Out, ChainSlash::Standard);
        AddSkillAsset(Out, ChainSlash::LongGrip);
        AddSkillAsset(Out, ChainSlash::Pojun);
        for(const TCHAR* Path:ChainSlash::CutRibbons)AddSkillAsset(Out,Path);
        AddSkillAsset(Out,ChainSlash::ImpactWave);
    }
    if (Skill == TEXT("swordUppercut"))
        for (const TCHAR* Path : {
            TEXT("/Game/Weapons/SwordUppercut20261003/Standard/A_Sword_UppercutV1_Standard.A_Sword_UppercutV1_Standard"),
            TEXT("/Game/Weapons/SwordUppercut20261003/LongGrip/A_Sword_UppercutV1_LongGrip.A_Sword_UppercutV1_LongGrip")}) AddSkillAsset(Out, Path);
    if (Skill == TEXT("whirlwind"))
        for (const TCHAR* Path : {
            TEXT("/Game/Skills/Whirlwind20260920/M_WhirlwindFocus.M_WhirlwindFocus")}) AddSkillAsset(Out, Path);
    if (Skill == TEXT("shadowStepSlash"))
    {
        for (const TCHAR* Path : {
            TEXT("/Game/Weapons/Kukri20261020/Animations/A_Kukri_ShadowStep.A_Kukri_ShadowStep"),
            TEXT("/Game/Weapons/Kukri20261020/Animations/A_Kukri_ShadowStepFollow.A_Kukri_ShadowStepFollow"),
            TEXT("/Game/Weapons/Kukri20261020/Animations/A_Kukri_DualShadowStep.A_Kukri_DualShadowStep"),
            TEXT("/Game/Weapons/Kukri20261020/Animations/A_Kukri_DualShadowStepFollow.A_Kukri_DualShadowStepFollow"),
            TEXT("/Game/Weapons/AzureRunesword20260913/WristRiftV3/M_RuneRift.M_RuneRift"),
            TEXT("/Game/Skills/Whirlwind20260920/M_WhirlwindFocus.M_WhirlwindFocus"),
            TEXT("/Game/Audio/MeleeBlock20260927/S_MeleeBlock_02.S_MeleeBlock_02"),
            KukriRhythm::StabWhoosh,
            KukriDrawRhythm::CatchSound}) AddSkillAsset(Out, Path);
        for (const TCHAR* Path : KukriRhythm::StabThud) AddSkillAsset(Out, Path);
        for (const auto& Item : Profile.Items)
        {
            if ((Item.Place != 0 && Item.Place != 1 && Item.Place != 5) || !ColdSteelInventory::IsOneHandedMelee(Item)) continue;
            AddSkillAsset(Out, ColdSteelInventory::Text(Item, TEXT("swing_sound")));
            AddSkillAsset(Out, ColdSteelInventory::Text(Item, TEXT("hit_sound")));
        }
    }
    if (Skill == TEXT("fireball"))
        for (const TCHAR* Path : {
            TEXT("/Game/Skills/Fireball/NS_FireballSlowBurnCore.NS_FireballSlowBurnCore"),
            TEXT("/Game/Skills/Fireball/NS_FireballVelocityTrail.NS_FireballVelocityTrail"),
            TEXT("/Game/Skills/Fireball/ImpactRealistic20260914/NS_FireballImpactRealistic.NS_FireballImpactRealistic"),
            TEXT("/Game/Skills/Fireball/ImpactRealistic20260914/M_FireballHeatShockwave.M_FireballHeatShockwave"),
            TEXT("/Game/Skills/Fireball/ImpactRealistic20260914/S_FireballImpactLayered.S_FireballImpactLayered"),
            TEXT("/Engine/BasicShapes/Plane.Plane"),
            TEXT("/Engine/BasicShapes/Sphere.Sphere")}) AddSkillAsset(Out, Path);
    if (Skill == TEXT("iceSpike"))
        for (const TCHAR* Path : {
            TEXT("/Game/Skills/IceSpike/SM_IceShard.SM_IceShard"),
            TEXT("/Game/Skills/IceSpike/FrostV2/M_IceSpikeHeartV3.M_IceSpikeHeartV3"),
            TEXT("/Game/Skills/IceSpike/FrostV2/M_IceSpikeShellV3.M_IceSpikeShellV3"),
            TEXT("/Game/Skills/IceSpike/P_IceSpikeImpact.P_IceSpikeImpact"),
            TEXT("/Game/Skills/IceSpike/S_IceImpact.S_IceImpact"),
            TEXT("/Game/Skills/IceSpike/FrostV2/NS_FrostCrystalsV2.NS_FrostCrystalsV2"),
            TEXT("/Game/Skills/IceSpike/FrostV2/NS_ColdMist.NS_ColdMist"),
            TEXT("/Game/Skills/IceSpike/FrostV2/SM_IceSpike_01.SM_IceSpike_01"),
            TEXT("/Game/Skills/IceSpike/FrostV2/SM_IceSpike_02.SM_IceSpike_02"),
            TEXT("/Game/Skills/IceSpike/FrostV2/SM_IceSpike_03.SM_IceSpike_03")}) AddSkillAsset(Out, Path);
    if (Skill == TEXT("iceWall"))
        for (const TCHAR* Path : {
            TEXT("/Game/Skills/IceWall/FabIceV3/M_IceWall.M_IceWall"),
            TEXT("/Game/Skills/IceWall/BlockV1/M_IceWallPreview.M_IceWallPreview"),
            TEXT("/Game/Skills/IceSpike/P_IceSpikeImpact.P_IceSpikeImpact"),
            TEXT("/Game/Skills/IceSpike/S_IceImpact.S_IceImpact"),
            TEXT("/Game/Skills/IceWall/BlockV1/S_IceWallCast.S_IceWallCast"),
            TEXT("/Game/Skills/IceWall/TerrainV1/NS_IceWallColdMist.NS_IceWallColdMist"),
            TEXT("/Game/Skills/IceWall/TerrainV1/NS_IceWallLanding.NS_IceWallLanding"),
            TEXT("/Game/Skills/IceWall/FabIceV3/SM_IceBlock_01.SM_IceBlock_01"),
            TEXT("/Game/Skills/IceWall/FabIceV3/SM_IceBlock_02.SM_IceBlock_02"),
            TEXT("/Game/Skills/IceWall/FabIceV3/SM_IceBlock_03.SM_IceBlock_03"),
            TEXT("/Game/Skills/IceWall/FabIceV3/SM_IceBlock_04.SM_IceBlock_04"),
            TEXT("/Game/Skills/AbsoluteZero/M_FrostSurfaceSheet.M_FrostSurfaceSheet"),
            TEXT("/Game/Skills/IceSpike/FrostV2/NS_FrostCrystalsV2.NS_FrostCrystalsV2")}) AddSkillAsset(Out, Path);
    if (Skill == TEXT("meteor"))
    {
        for (const TCHAR* Path : MeteorSpellAssets::Visuals) AddSkillAsset(Out, Path);
        AddSkillAsset(Out, MeteorSpellAssets::Preview);
        AddSkillAsset(Out, MeteorSpellAssets::CastSound);
    }
    if (Skill == TEXT("iceArmor"))
    {
        for(const TCHAR* Path:IceArmorAssets::Shells)AddSkillAsset(Out,Path);
        for(const TCHAR* Path:{IceArmorAssets::Lens,IceArmorAssets::Material,IceArmorAssets::LensMaterial,IceArmorAssets::Chip,IceArmorAssets::ChipMaterial,IceArmorAssets::Mist,IceArmorAssets::CastSound})AddSkillAsset(Out,Path);
    }
    if (Skill == TEXT("flameArmor"))
        for (const TCHAR* Path : {
            FlameArmorAssets::Body,
            FlameArmorAssets::Weapon,
            FlameArmorAssets::Hammer,
            FlameArmorAssets::Sword,
            FlameArmorAssets::Arrow,
            TEXT("/Game/Skills/FireMagic20260921/NS_FireMagicSparks.NS_FireMagicSparks"),
            TEXT("/Game/Skills/FireMagic20260921/S_FireMagicCast.S_FireMagicCast")}) AddSkillAsset(Out, Path);
    if (Skill == TEXT("dragonBreath"))
        for (const TCHAR* Path : {
            DragonBreathAudio::Start,DragonBreathAudio::Loop,DragonBreathAudio::Stop,
            TEXT("/Game/Skills/FireMagic20260921/S_FireMagicCast.S_FireMagicCast"),
            TEXT("/Game/Skills/DragonBreath20261013/Range2x20261019/NS_DragonVolume.NS_DragonVolume")}) AddSkillAsset(Out, Path);
    if (Skill == TEXT("lightningStrike"))
        for (const TCHAR* Path : {
            TEXT("/Game/Skills/Lightning/NS_LightningChain.NS_LightningChain"),
            TEXT("/Game/Skills/ElectricMagic/LanceRay/FX/SM_ThunderLanceRibbon.SM_ThunderLanceRibbon"),
            TEXT("/Game/Skills/ElectricMagic/LanceRay/FX/SM_ThunderLanceIris.SM_ThunderLanceIris"),
            TEXT("/Game/Skills/ElectricMagic/LanceRay/Materials/M_ThunderLanceBeam.M_ThunderLanceBeam"),
            TEXT("/Game/Skills/ElectricMagic/LanceRay/Materials/M_ThunderLanceIris.M_ThunderLanceIris"),
            TEXT("/Game/Skills/Lightning/S_LightningCast1.S_LightningCast1"),
            TEXT("/Game/Skills/Lightning/S_LightningCast2.S_LightningCast2")}) AddSkillAsset(Out, Path);
    if (Skill == TEXT("stormDomain"))
        for (const TCHAR* Path : {
            TEXT("/Game/Skills/ElectricMagic/StormDomainV4/NS_StormDomainSmoke.NS_StormDomainSmoke"),
            TEXT("/Game/Skills/Lightning/NS_LightningChain.NS_LightningChain"),
            TEXT("/Game/Skills/ElectricMagic/LanceRay/Materials/M_ThunderLanceBeam.M_ThunderLanceBeam"),
            TEXT("/Game/Skills/ElectricMagic/NS_ThunderCharge.NS_ThunderCharge"),
            TEXT("/Game/Skills/ElectricMagic/NS_ElectricImpact.NS_ElectricImpact"),
            TEXT("/Game/Skills/ElectricMagic/S_ElectricCast1.S_ElectricCast1"),
            TEXT("/Game/Skills/ElectricMagic/S_ElectricCast2.S_ElectricCast2"),
            TEXT("/Game/Skills/ElectricMagic/ThunderLanceV2/M_ThunderLanceCircle.M_ThunderLanceCircle"),
            TEXT("/Engine/BasicShapes/Plane.Plane"),
            TEXT("/Game/Skills/ElectricMagic/LanceRay/FX/SM_ThunderLanceRibbon.SM_ThunderLanceRibbon"),
            TEXT("/Game/Skills/ElectricMagic/LanceRay/FX/SM_ThunderLanceIris.SM_ThunderLanceIris"),
            TEXT("/Game/Skills/ElectricMagic/LanceRay/Materials/M_ThunderLanceIris.M_ThunderLanceIris"),
            TEXT("/Game/Skills/ElectricMagic/LanceRay/NS_ThunderLanceGather.NS_ThunderLanceGather"),
            TEXT("/Game/Skills/ElectricMagic/S_ThunderLanceCharge.S_ThunderLanceCharge"),
            TEXT("/Game/Skills/ElectricMagic/S_ThunderLanceDischarge.S_ThunderLanceDischarge"),
            TEXT("/Game/Skills/ElectricMagic/NS_ThunderLanceMuzzle.NS_ThunderLanceMuzzle"),
            TEXT("/Game/Skills/ElectricMagic/StormDomainV3/NS_StormCloudArc.NS_StormCloudArc"),
            TEXT("/Game/Skills/ElectricMagic/StormDomainV4/NS_StormDomainVolume.NS_StormDomainVolume")}) AddSkillAsset(Out, Path);
    if (Skill == TEXT("thunderLance"))
        for (const TCHAR* Path : {
            TEXT("/Game/Skills/ElectricMagic/StormDomainV4/NS_StormDomainSmoke.NS_StormDomainSmoke"),
            TEXT("/Game/Skills/Lightning/NS_LightningChain.NS_LightningChain"),
            TEXT("/Game/Skills/ElectricMagic/LanceRay/Materials/M_ThunderLanceBeam.M_ThunderLanceBeam"),
            TEXT("/Game/Skills/ElectricMagic/NS_ThunderCharge.NS_ThunderCharge"),
            TEXT("/Game/Skills/ElectricMagic/NS_ElectricImpact.NS_ElectricImpact"),
            TEXT("/Game/Skills/ElectricMagic/S_ElectricCast1.S_ElectricCast1"),
            TEXT("/Game/Skills/ElectricMagic/S_ElectricCast2.S_ElectricCast2"),
            TEXT("/Game/Skills/ElectricMagic/ThunderLanceV2/M_ThunderLanceCircle.M_ThunderLanceCircle"),
            TEXT("/Engine/BasicShapes/Plane.Plane"),
            TEXT("/Game/Skills/ElectricMagic/LanceRay/FX/SM_ThunderLanceRibbon.SM_ThunderLanceRibbon"),
            TEXT("/Game/Skills/ElectricMagic/LanceRay/FX/SM_ThunderLanceIris.SM_ThunderLanceIris"),
            TEXT("/Game/Skills/ElectricMagic/LanceRay/Materials/M_ThunderLanceIris.M_ThunderLanceIris"),
            TEXT("/Game/Skills/ElectricMagic/LanceRay/NS_ThunderLanceGather.NS_ThunderLanceGather"),
            TEXT("/Game/Skills/ElectricMagic/S_ThunderLanceCharge.S_ThunderLanceCharge"),
            TEXT("/Game/Skills/ElectricMagic/S_ThunderLanceDischarge.S_ThunderLanceDischarge"),
            TEXT("/Game/Skills/ElectricMagic/NS_ThunderLanceMuzzle.NS_ThunderLanceMuzzle"),
            TEXT("/Game/Skills/ElectricMagic/StormDomainV3/NS_StormCloudArc.NS_StormCloudArc"),
            TEXT("/Game/Skills/ElectricMagic/StormDomainV4/NS_StormDomainVolume.NS_StormDomainVolume")}) AddSkillAsset(Out, Path);
    if (Skill == TEXT("holyLight"))
        for (const TCHAR* Path : {
            TEXT("/Game/Skills/HolyLight/NS_HolyLightMotes.NS_HolyLightMotes"),
            TEXT("/Game/Skills/HolyLight/S_HolyLightCast.S_HolyLightCast"),
            TEXT("/Game/Skills/HolyLight/M_HolyBeam.M_HolyBeam"),
            TEXT("/Game/Skills/HolyLight/M_HolyPool.M_HolyPool")}) AddSkillAsset(Out, Path);
    if (Skill == TEXT("blizzard"))
    {
        const TCHAR* const* Paths = AFPSBlizzardZone::ZoneAssetPaths();
        for (int32 I = 0; I < AFPSBlizzardZone::AssetCount; ++I) AddSkillAsset(Out, Paths[I]);
    }
    if (Skill == TEXT("absoluteZero"))
    {
        const TCHAR* const* Paths = AFPSAbsoluteZeroNova::AssetPaths();
        for (int32 I = 0; I < AFPSAbsoluteZeroNova::AssetCount; ++I) AddSkillAsset(Out, Paths[I]);
    }
    const bool bSwordSkill = Skill == TEXT("heavyStrike") || Skill == TEXT("swordUppercut") ||
        Skill == TEXT("whirlwind") || Skill == TEXT("dashAttack") || Skill == TEXT("quickCombat");
    if (bSwordSkill)
    {
        AddSkillAsset(Out, TEXT("/Game/Audio/SwordAttack20260914/S_Sword_Attack.S_Sword_Attack"));
        const bool HasWarhammer=Profile.Items.ContainsByPredicate([](const FColdSteelItem& Item)
        {return (Item.Place==0||Item.Place==1||Item.Place==5)&&PojunGrip::UsesHammerMotion(Item);});
        if(HasWarhammer)
        {
            for(const TCHAR* Key:{TEXT("tool_sound"),TEXT("tool_swing_sound")})
                for(const auto& Item:Profile.Items)
                    if((Item.Place==0||Item.Place==1||Item.Place==5)&&PojunGrip::UsesHammerMotion(Item))
                        AddSkillAsset(Out,ColdSteelInventory::Text(Item,Key));
            AddSkillAsset(Out,TEXT("/Game/Weapons/SteelWarhammer20261014/RhythmClearanceV2/DA_Warhammer_Clearance"));
            if(Skill==TEXT("quickCombat"))
            {
                AddSkillAsset(Out,WarhammerQuickCombat::Asset);
                AddSkillAsset(Out,WarhammerConicalThrust::Asset);
            }
            if(Skill==TEXT("heavyStrike"))
                for(const TCHAR* Path:{
                    TEXT("/Game/Weapons/SteelWarhammer20261014/HeavySlamV4/A_Warhammer_HeavyCharge"),
                    TEXT("/Game/Weapons/SteelWarhammer20261014/HeavySlamV4/A_Warhammer_HeavyRelease"),
                    TEXT("/Game/Weapons/SteelWarhammer20261014/HeavySlamV1/M_WarhammerGroundWave"),
                    TEXT("/Game/Weapons/SteelWarhammer20261014/GroundImpactAudioV1/S_Warhammer_GroundImpact"),
                    TEXT("/Game/Weapons/SteelWarhammer20261014/SlamFXV2/M_WarhammerDust"),
                    TEXT("/Game/Weapons/SteelWarhammer20261014/SlamFXV2/SM_WarhammerDebris"),
                    TEXT("/Game/Weapons/SteelWarhammer20261014/SlamFXV2/M_WarhammerDebris"),
                    TEXT("/Game/Weapons/SteelWarhammer20261014/CrackReliefV3/M_WarhammerFractureRelief")})AddSkillAsset(Out,Path);
            if(Skill==TEXT("whirlwind"))
                for(const TCHAR* Path:{TEXT("/Game/Weapons/SteelWarhammer20261014/WhirlwindV1/A_Warhammer_Whirlwind"),
                    TEXT("/Game/Weapons/SteelWarhammer20261014/NormalSwingAudioV1/S_Warhammer_NormalSwing")})AddSkillAsset(Out,Path);
            if(Skill==TEXT("swordUppercut"))
                for(const TCHAR* Path:{TEXT("/Game/Weapons/SteelWarhammer20261014/UppercutV1/A_Warhammer_Uppercut"),
                    TEXT("/Game/Weapons/SteelWarhammer20261014/UppercutAudioV1/S_Warhammer_Uppercut")})AddSkillAsset(Out,Path);
        }
        // Both carried loadouts, not warehouse/catalog weapons. Respect installed grips.
        for (const auto& Item : Profile.Items)
        {
            if ((Item.Place != 0 && Item.Place != 1 && Item.Place != 5) || !ColdSteelInventory::IsTwoHandedSword(Item)) continue;
            AddSkillAsset(Out,TEXT("/Game/Weapons/AzureRunesword20260913/WristRiftV3/M_RuneRift"));
            if(Skill==TEXT("heavyStrike"))AddSkillAsset(Out,TEXT("/Game/Weapons/AzureRunesword20260913/WristRiftV3/SM_RuneRift_Heavy"));
            if(Skill==TEXT("quickCombat"))AddSkillAsset(Out,TEXT("/Game/Weapons/AzureRunesword20260913/WristRiftV3/SM_RuneRift_Pommel"));
            if(Skill==TEXT("dashAttack"))AddSkillAsset(Out,TEXT("/Game/Weapons/AzureRunesword20260913/SprintOverhead20260920/SM_RuneRift_Overhead"));
            AddSkillAsset(Out, ColdSteelInventory::Text(Item, TEXT("swing_sound")));
            AddSkillAsset(Out, ColdSteelInventory::Text(Item, TEXT("hit_sound")));
            const FString Folder = ColdSteelModularSword::AnimationFolder(Item);
            if (Folder.IsEmpty()) continue;
            if (Folder == TEXT("/Game/Weapons/FrostCrystalSword20260915/Grips20260919/LongGripAnimations"))
                AddSkillAsset(Out, TEXT("/Game/Weapons/AnimationProfiles20261001/Melee/DA_Sword_LongGrip"));
            if (Skill == TEXT("heavyStrike"))
                for (const TCHAR* Clip : {TEXT("HeavyCharge"), TEXT("HeavyRelease")})
                    AddSkillAsset(Out, Folder + TEXT("/A_RuneSword_") + Clip);
            if (Skill == TEXT("whirlwind")) AddSkillAsset(Out, Folder + TEXT("/A_RuneSword_WhirlwindV5"));
            if (Skill == TEXT("dashAttack"))
            {
                AddSkillAsset(Out, Folder + TEXT("/A_RuneSword_Overhead"));
                for(const TCHAR* Clip:{TEXT("SprintEnter"),TEXT("SprintLoop"),TEXT("SprintExit"),TEXT("SprintOverhead")})
                    AddSkillAsset(Out,Folder+TEXT("/TacticalSprint20260921/A_RuneSword_")+Clip);
            }
            if(Skill==TEXT("lightningHaste"))for(const TCHAR* Path:{LightningHasteAssets::Arc,LightningHasteAssets::CastSound,LightningHasteAssets::EndSound})AddSkillAsset(Out,Path);
    if (Skill == TEXT("quickCombat")) AddSkillAsset(Out, Folder + TEXT("/A_RuneSword_PommelStrike"));
        }
    }
    if (Skill == TEXT("whirlwind"))
    {
        const auto* Enabled = IConsoleManager::Get().FindConsoleVariable(TEXT("r.Velocity.TemporalResponsiveness.Supported"));
        if (!Enabled || Enabled->GetInt() == 0) return;
        // Resolve only sources belonging to carried swords and installed parts.
        // The old code loaded the entire replacement catalog (67 resources even
        // for one sword), including unrelated weapon finishes and attachments.
        TArray<FSoftObjectPath> Sources;
        for (const auto& Item : Profile.Items)
        {
            if ((Item.Place != 0 && Item.Place != 1 && Item.Place != 5) || !ColdSteelInventory::IsTwoHandedSword(Item)) continue;
            AddSkillAsset(Sources, ColdSteelModularSword::ArmsMesh(Item));
            ColdSteelModularSword::GatherVisualResources(Item, Sources);
        }
        TSet<FName> SourcePackages;
        auto& Registry = FModuleManager::LoadModuleChecked<FAssetRegistryModule>(TEXT("AssetRegistry")).Get();
        for (const auto& Source : Sources)
        {
            const FName Package = Source.GetLongPackageFName();
            SourcePackages.Add(Package);
            // Mesh hard references include their material slots. No folder scan,
            // package load, or traversal into unrelated item/texture catalogs.
            TArray<FName> Dependencies;
            Registry.GetDependencies(Package, Dependencies);
            for (FName Dependency : Dependencies) SourcePackages.Add(Dependency);
        }
        FString Json;
        TSharedPtr<FJsonObject> Materials;
        if (FFileHelper::LoadFileToString(Json, *(FPaths::ProjectContentDir() / TEXT("ColdSteelData/whirlwind-temporal-materials.json"))) &&
            FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json), Materials) && Materials)
            for (const auto& Pair : Materials->Values)
            {
                if (!SourcePackages.Contains(FSoftObjectPath(Pair.Key).GetLongPackageFName())) continue;
                FString Path;
                if (Pair.Value->TryGetString(Path)) AddSkillAsset(Out, Path);
            }
    }
}
