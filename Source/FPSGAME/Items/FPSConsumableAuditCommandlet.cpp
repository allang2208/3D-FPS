#include "FPSConsumableAuditCommandlet.h"
#include "FPSPotionUseComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Weapons/RuneSwordComponent.h"
#include "../Weapons/Bow/BowWeaponComponent.h"
#include "../Weapons/Staff/StaffWeaponComponent.h"
#include "../Weapons/Staff/StaffArmsMeshComponent.h"
#include "../Weapons/Unarmed/FPSUnarmedIdleComponent.h"
#include "../Weapons/PistolDualWieldComponent.h"
#include "../Production/ProductionToolComponent.h"
#include "../Skills/FPSCastingMeshComponent.h"
#include "Animation/AnimSequence.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

int32 UFPSConsumableAuditCommandlet::Main(const FString& Params)
{
    const auto Settings=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(true)
        .RequiresHitProxies(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    auto* World=UWorld::CreateWorld(EWorldType::Game,false,TEXT("ConsumableWeaponStateCheck"),nullptr,true,ERHIFeatureLevel::Num,&Settings);
    if(!World)return 1;
    // A bare, uninitialized game instance satisfies GetSubsystem callers but
    // owns no subsystems: the test cannot read or publish a player profile.
    World->SetGameInstance(NewObject<UGameInstance>());
    auto* Player=World->SpawnActor<AFPSGAMECharacter>();
    auto* Controller=World->SpawnActor<APlayerController>();
    Controller->Possess(Player);Controller->bShowMouseCursor=false;
    // Deliberately no BeginPlay or subsystem initialization: no inventory loads/commits,
    // gameplay map, projectile, cooldown or user save can be touched here.
    auto* Sword=Player->RuneSword.Get();Sword->Character=Player;
    auto* Bow=Player->Bow.Get();Bow->Character=Player;
    auto* Staff=Player->Staff.Get();
    auto* Tool=Player->FindComponentByClass<UProductionToolComponent>();
    auto* Dual=Player->DualPistols.Get();Dual->Player=Player;
    auto* Unarmed=Player->UnarmedIdle.Get();
    auto* Potion=Player->FindComponentByClass<UFPSPotionUseComponent>();
    int32 Passed=0,Failed=0;FString Report;
    const auto Check=[&](bool OK,const FString& Label)
    {
        OK?++Passed:++Failed;
        Report+=FString::Printf(TEXT("%s %s\n"),OK?TEXT("PASS"):TEXT("FAIL"),*Label);
    };
    const auto CanUse=[&](){return Player->CanBeginConsumableUse();};
    Player->WeaponState=EAKMWeaponState::Idle;Player->bInventoryWeaponReady=true;
    // Every single-firearm family shares this path, independently of its rig.
    for(const TCHAR* Definition:{TEXT("ue_m4a1"),TEXT("ue_hk416"),TEXT("ue_akm"),TEXT("ue_a762"),TEXT("ue_lmg201"),
        TEXT("ue_svd"),TEXT("ue_pkm_lowpoly"),TEXT("ue_qbz191"),TEXT("ue_ash12"),TEXT("ue_m16a2"),
        TEXT("ue_m1911"),TEXT("ue_g18"),TEXT("ue_pit_viper2011"),TEXT("ue_dan_wesson715"),TEXT("ue_rsh12")})
    {Player->ActiveInventoryWeaponDefinition=Definition;Check(CanUse(),FString(Definition)+TEXT(" idle permits consumption"));}
    Player->bAimHeld=Player->bIsAiming=true;Player->ADSProgress=1.f;
    Check(CanUse(),TEXT("ADS can yield"));Player->PrepareForConsumableUse();
    Check(!Player->bAimHeld&&!Player->bIsAiming,TEXT("use releases ADS intent and state"));
    Check(Player->ConsumableHands()==Player->AKMViewmodel,TEXT("firearm owns its native arms"));
    for(auto State:{EAKMWeaponState::Reloading,EAKMWeaponState::ReloadingEmpty,EAKMWeaponState::Equipping,EAKMWeaponState::QuickCombat})
    {Player->WeaponState=State;Check(!CanUse(),FString::Printf(TEXT("firearm action %d retains hand"),int32(State)));}
    Player->WeaponState=EAKMWeaponState::Inspecting;Check(CanUse(),TEXT("inspect can yield"));

    // Reproduce the former cross-family gate with an inactive firearm clock.
    Player->bInventoryWeaponReady=false;Player->WeaponState=EAKMWeaponState::Equipping;
    Sword->InstanceId=TEXT("test-sword");
    Sword->Viewmodel=NewObject<UFPSCastingMeshComponent>(Player);Sword->Viewmodel->SetVisibility(false);
    Check(Player->IsLeftHandBusyForCast(),TEXT("old spell gate rejects stale gun state with sword"));
    Check(CanUse(),TEXT("two-handed sword idle ignores inactive firearm state"));
    Check(Player->ConsumableHands()==Sword->Viewmodel,TEXT("menu-hidden sword retains native hand ownership"));
    Player->WeaponState=EAKMWeaponState::Idle;
    Sword->bGuardHeld=Sword->bGuarding=true;
    Check(CanUse(),TEXT("held sword guard can yield"));Player->PrepareForConsumableUse();
    Check(!Sword->bGuarding&&!Sword->bGuardHeld&&!Sword->IsBusy(),TEXT("guard ends before the hand takes food"));
    Sword->bReturningGuard=true;Check(CanUse(),TEXT("sword guard return can yield"));Sword->bReturningGuard=false;
    Sword->bInspecting=true;Check(CanUse(),TEXT("sword inspect can yield"));Player->PrepareForConsumableUse();
    Check(!Sword->bInspecting,TEXT("sword inspect releases its pose"));
    for(bool* Busy:{&Sword->bAttacking,&Sword->bEquipping,&Sword->bCharging,&Sword->bReturningCharge,
        &Sword->bUppercut,&Sword->bWhirlwind,&Sword->bGuardReacting,&Sword->bGuardBreakPose})
    {*Busy=true;Check(!CanUse(),TEXT("sword committed action retains hand"));*Busy=false;}
    Sword->InstanceId.Reset();

    Tool->EquippedId=TEXT("test-tool");Tool->bUsesArms=true;
    Tool->Viewmodel=NewObject<UFPSCastingMeshComponent>(Player);Tool->Viewmodel->SetVisibility(false);
    Check(CanUse(),TEXT("axe/pickaxe/shovel idle can release support hand"));
    Check(Player->ConsumableHands()==Tool->Viewmodel,TEXT("menu-hidden tool retains native arms"));
    Tool->Elapsed=0;Check(!CanUse(),TEXT("tool swing retains hand"));Tool->Elapsed=-1;
    Tool->EquipElapsed=0;Check(!CanUse(),TEXT("tool equip retains hand"));Tool->EquipElapsed=-1;Tool->EquippedId.Reset();

    Bow->InstanceId=TEXT("test-bow");
    for(auto Stage:{EBowStage::Ready,EBowStage::Stowed,EBowStage::DrawEntry,EBowStage::Drawing,EBowStage::Holding,EBowStage::LetDown})
    {Bow->Stage=Stage;Check(CanUse(),FString::Printf(TEXT("bow held stage %d can yield"),int32(Stage)));}
    for(auto Stage:{EBowStage::Equip,EBowStage::Nocking,EBowStage::Release,EBowStage::Recover,EBowStage::QuickCombat})
    {Bow->Stage=Stage;Check(!CanUse(),FString::Printf(TEXT("bow action stage %d retains hand"),int32(Stage)));}
    Bow->Stage=EBowStage::Holding;Bow->bArrowNocked=Bow->bTriggerHeld=Bow->bSteadyHeld=true;
    Player->PrepareForConsumableUse();
    Check(Bow->bArrowNocked&&!Bow->bTriggerHeld&&!Bow->bSteadyHeld,TEXT("stow draw without firing or consuming arrow"));
    Check(Player->ConsumableHands()==nullptr,TEXT("bow selects dedicated fallback arm"));Bow->InstanceId.Reset();

    Staff->Instance=TEXT("test-staff");Staff->EquipAge=1;
    Staff->Arms=NewObject<UStaffArmsMeshComponent>(Player);Staff->Arms->SetVisibility(false);
    Check(!Staff->CanBeginCast(),TEXT("old spell gate rejects menu-hidden staff"));
    Check(CanUse(),TEXT("menu-hidden staff permits consumption"));
    Check(Player->ConsumableHands()==Staff->Arms,TEXT("staff selects native arms"));
    Staff->Age=0;Check(!CanUse(),TEXT("staff strike retains hand"));Staff->Age=-1;
    Staff->EquipAge=0;Check(!CanUse(),TEXT("staff equip retains hand"));Staff->EquipAge=1;

    Dual->bActive=true;Dual->Hands[1].Mesh=NewObject<UFPSCastingMeshComponent>(Player);
    for(bool OffhandOnly:{true,false})
    {
        Dual->bOffhandOnly=OffhandOnly;
        if(!OffhandOnly)Staff->Instance.Reset();
        const FString Family=OffhandOnly?TEXT("staff/offhand"):TEXT("dual pistols");
        Check(CanUse(),Family+TEXT(" idle can lower left gun"));
        Check(Player->ConsumableHands()==Dual->Hands[1].Mesh,Family+TEXT(" uses left pistol arm"));
        Dual->Hands[1].Reloading=true;Check(!CanUse(),Family+TEXT(" left reload retains hand"));Dual->Hands[1].Reloading=false;
        Dual->Hands[1].Held=true;Check(!CanUse(),Family+TEXT(" left trigger retains hand"));Dual->Hands[1].Held=false;
        Dual->Hands[1].Action=NewObject<UAnimSequence>(Player);Check(!CanUse(),Family+TEXT(" left action retains hand"));Dual->Hands[1].Action=nullptr;
    }
    Dual->bActive=false;
    Unarmed->bEquipmentResolved=Unarmed->bHandsEmpty=true;Unarmed->Arms=NewObject<UFPSUnarmedArmsMeshComponent>(Player);
    Check(CanUse(),TEXT("unarmed idle can consume"));Check(Player->ConsumableHands()==Unarmed->Arms,TEXT("unarmed uses current arms"));
    Potion->bActive=true;Check(!CanUse(),TEXT("active consumable prevents reentry"));Potion->Finish();
    Check(CanUse(),TEXT("finish returns action ownership"));
    for(const TCHAR* Definition:{TEXT("bread"),TEXT("baguette_bread"),TEXT("mineral_water"),TEXT("soda_can"),
        TEXT("hp_potion"),TEXT("hp_potion_high"),TEXT("mp_potion"),TEXT("mp_potion_high")})
        Check(UFPSPotionUseComponent::IsAnimatedConsumable(Definition),FString(Definition)+TEXT(" uses shared action path"));
    World->DestroyWorld(false);
    Report+=FString::Printf(TEXT("RESULT passed=%d failed=%d\n"),Passed,Failed);
    const FString Folder=FPaths::ProjectSavedDir()/TEXT("ConsumableWeaponFix20261006");
    IFileManager::Get().MakeDirectory(*Folder,true);FFileHelper::SaveStringToFile(Report,*(Folder/TEXT("state-check.txt")));
    UE_LOG(LogTemp,Display,TEXT("CONSUMABLE_WEAPON_STATE_CHECK passed=%d failed=%d"),Passed,Failed);
    if(Failed)UE_LOG(LogTemp,Error,TEXT("%s"),*Report);
    return Failed?1:0;
}
