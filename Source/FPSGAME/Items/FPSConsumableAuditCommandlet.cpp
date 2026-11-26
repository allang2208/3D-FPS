#include "FPSConsumableAuditCommandlet.h"
#include "FPSPotionUseComponent.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Characters/FPSBodyConsumeMotion.h"
#include "../FPSGAMECharacter.h"
#include "../Weapons/RuneSwordComponent.h"
#include "../Weapons/Bow/BowWeaponComponent.h"
#include "../Weapons/Bow/BowArmsMeshComponent.h"
#include "../Weapons/Staff/StaffWeaponComponent.h"
#include "../Weapons/Staff/StaffArmsMeshComponent.h"
#include "../Weapons/Unarmed/FPSUnarmedIdleComponent.h"
#include "../Weapons/PistolDualWieldComponent.h"
#include "../Weapons/Kukri/KukriWeaponComponent.h"
#include "../Weapons/Kukri/KukriArmsMeshComponent.h"
#include "../Weapons/Kukri/KukriRhythm.h"
#include "Camera/CameraComponent.h"
#include "Engine/SkeletalMesh.h"
#include "../Production/ProductionToolComponent.h"
#include "../Skills/FPSCastingMeshComponent.h"
#include "Animation/AnimSequence.h"
#include "Components/StaticMeshComponent.h"
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
    // In-memory authority receipt checks only. No BeginPlay, subsystem or save.
    auto* Authority=World->SpawnActor<AColdSteelPlayerState>();
    Controller->SetPlayerState(Authority);Authority->SetOwner(Controller);
    Controller->UnPossess();Controller->Possess(Player);Player->SetPlayerState(Authority);
    const FGuid FirstUse=FGuid::NewGuid();
    Authority->ServerBeginConsumableUse_Implementation(Player,FirstUse,TEXT("audit-food"),TEXT("bread"));
    Check(Authority->HasAuthorityConsumableReservation(Player),TEXT("authority reserves current living pawn"));
    const double Contact=Authority->ConsumableContactAt;
    Authority->ServerBeginConsumableUse_Implementation(Player,FirstUse,TEXT("audit-food"),TEXT("bread"));
    Check(Authority->ConsumableContactAt==Contact,TEXT("repeated begin cannot restart contact clock"));
    Check(Player->IsCastBlockingLeftHandAction(),TEXT("authority reservation blocks subsequent hand actions"));
    Authority->ServerCancelConsumableUse_Implementation(FGuid::NewGuid());
    Check(Authority->HasAuthorityConsumableReservation(Player),TEXT("stale cancel cannot retire current use"));
    Authority->ServerCancelConsumableUse_Implementation(FirstUse);
    Check(!Authority->HasAuthorityConsumableReservation(Player),TEXT("matching cancel releases reservation"));
    Authority->ServerBeginConsumableUse_Implementation(Player,FirstUse,TEXT("audit-food"),TEXT("bread"));
    Check(!Authority->HasAuthorityConsumableReservation(Player),TEXT("last cancelled begin cannot replay"));
    Authority->PendingCastSkill=TEXT("fireball");
    Check(!Authority->CanAuthorityBeginConsumable(Player),TEXT("authority pending spell blocks consumption"));
    Authority->PendingCastSkill=NAME_None;
    Authority->KukriAttack.Pawn=Player;Authority->KukriReadyAt=World->GetTimeSeconds()+1.;
    Check(!Authority->CanAuthorityBeginConsumable(Player),TEXT("authority attack receipt blocks consumption"));
    Authority->KukriAttack.Pawn.Reset();
    Authority->ServerBeginConsumableUse_Implementation(Player,FGuid::NewGuid(),TEXT("audit-food"),TEXT("bread"));
    Authority->ConsumableExpiresAt=World->GetTimeSeconds()-1.;
    Check(!Authority->HasAuthorityConsumableReservation(Player),TEXT("abandoned reservation expires"));
    Authority->ConsumableExpiresAt=World->GetTimeSeconds()+1.;
    Controller->UnPossess();
    Check(!Authority->HasAuthorityConsumableReservation(Player),TEXT("unpossessed pawn cannot retain reservation"));
    Controller->Possess(Player);Player->SetPlayerState(Authority);
    Authority->ConsumableUseId.Invalidate();
    // Registered launch identity survives a later food reservation. No ammo
    // or profile is involved in these lookup/lifecycle cases.
    FColdSteelNetHitReport LaunchHit;LaunchHit.FireSequence=71;LaunchHit.ItemInstance=TEXT("audit-rifle");
    LaunchHit.ItemDefinition=TEXT("ue_akm");LaunchHit.ConvergenceRounds=1;
    auto& Launch=Authority->GenericLaunches.Add(71);Launch.Pawn=Player;
    Launch.Item.InstanceId=LaunchHit.ItemInstance;Launch.Item.Definition=LaunchHit.ItemDefinition;
    Launch.Rounds=1;Launch.Expires=World->GetTimeSeconds()+2.;
    Check(Authority->FindGenericLaunch(LaunchHit,Player)!=nullptr,TEXT("registered generic launch matches exact identity"));
    Authority->ConsumablePawn=Player;Authority->ConsumableUseId=FGuid::NewGuid();
    Authority->ConsumableExpiresAt=World->GetTimeSeconds()+1.;
    Check(Authority->HasAuthorityConsumableReservation(Player)&&Authority->FindGenericLaunch(LaunchHit,Player),TEXT("old registered launch survives food reservation"));
    ++LaunchHit.FireSequence;Check(!Authority->FindGenericLaunch(LaunchHit,Player),TEXT("unknown launch cannot reuse old receipt"));
    --LaunchHit.FireSequence;LaunchHit.ItemInstance=TEXT("other-rifle");
    Check(!Authority->FindGenericLaunch(LaunchHit,Player),TEXT("launch cannot change weapon instance"));
    LaunchHit.ItemInstance=TEXT("audit-rifle");Launch.Expires=World->GetTimeSeconds()-1.;
    Check(!Authority->FindGenericLaunch(LaunchHit,Player),TEXT("generic launch expires instead of unlimited pre-registration"));
    Authority->GenericLaunches.Reset();Authority->ConsumableUseId.Invalidate();
    const auto CanUse=[&](){return Player->CanBeginConsumableUse();};
    Player->WeaponState=EAKMWeaponState::Idle;Player->bInventoryWeaponReady=true;
    // Every single-firearm family shares this path, independently of its rig.
    for(const TCHAR* Definition:{TEXT("ue_m4a1"),TEXT("ue_hk416"),TEXT("ue_akm"),TEXT("ue_a762"),TEXT("ue_lmg201"),
        TEXT("ue_svd"),TEXT("ue_svch"),TEXT("ue_pkm_lowpoly"),TEXT("ue_qbz191"),TEXT("ue_ash12"),TEXT("ue_m16a2"),
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

    Bow->InstanceId=TEXT("test-bow");Bow->bPresentationReady=true;Bow->Viewmodel=NewObject<UBowArmsMeshComponent>(Player);
    for(auto Stage:{EBowStage::Ready,EBowStage::Stowed,EBowStage::DrawEntry,EBowStage::Drawing,EBowStage::Holding,EBowStage::LetDown})
    {Bow->Stage=Stage;Check(CanUse(),FString::Printf(TEXT("bow held stage %d can yield"),int32(Stage)));}
    for(auto Stage:{EBowStage::Equip,EBowStage::Nocking,EBowStage::Release,EBowStage::Recover,EBowStage::QuickCombat})
    {Bow->Stage=Stage;Check(!CanUse(),FString::Printf(TEXT("bow action stage %d retains hand"),int32(Stage)));}
    Bow->Stage=EBowStage::Holding;Bow->bArrowNocked=Bow->bTriggerHeld=Bow->bSteadyHeld=true;
    Player->PrepareForConsumableUse();
    Check(Bow->bArrowNocked&&!Bow->bTriggerHeld&&!Bow->bSteadyHeld,TEXT("stow draw without firing or consuming arrow"));
    Check(Player->ConsumableHands()==Bow->Viewmodel,TEXT("bow selects its native shared consumable arm"));Bow->InstanceId.Reset();

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
    // Sample the real dual blade binding without BeginPlay, inventory or a map.
    // Both hatchets and kukris use this carry; the right hand must never move
    // when the consumable borrows the left hand.
    auto* Blade=Player->FindComponentByClass<UKukriWeaponComponent>();
    Blade->InstanceId=TEXT("consumable-handoff-blade");Blade->bDual=true;
    auto* Arms=NewObject<UKukriArmsMeshComponent>(Player);
    Blade->Viewmodel=Arms;
    Arms->SetupAttachment(Player->FirstPersonCamera);Arms->SetRelativeRotation(FRotator(0,90,0));
    auto* ArmAsset=LoadObject<USkeletalMesh>(nullptr,KukriRhythm::ArmsMesh);
    auto* Carry=LoadObject<UAnimSequence>(nullptr,TEXT("/Game/Weapons/Kukri20261020/Animations/A_Kukri_DualIdle.A_Kukri_DualIdle"));
    Check(ArmAsset&&Carry,TEXT("dual blade native carry resources available"));
    Check(Player->ConsumableHands()==Arms,TEXT("dual hatchet/kukri selects its native left arm, not fallback arms"));
    if(ArmAsset&&Carry)
    {
        Potion->Bottle=NewObject<UStaticMeshComponent>(Player);
        Potion->Liquid=NewObject<UStaticMeshComponent>(Player);
        Potion->Stopper=NewObject<UStaticMeshComponent>(Player);
        Arms->SetSkeletalMesh(ArmAsset);Arms->RegisterComponent();Arms->PlayAnimation(Carry,true);Arms->SetPlayRate(0.f);
        Potion->bActive=true;Potion->bStowOffhand=true;Potion->UseRate=1.f;
        Potion->Motion.Load(false);Potion->ActiveHands=Arms;
        const auto Sample=[&](float Age)
        {
            Potion->StartTime=World->GetTimeSeconds()-Age;
            Arms->SetPosition(0.f,false);Arms->TickAnimation(0.f,false);Arms->RefreshBoneTransforms();
            return Player->FirstPersonCamera->GetComponentTransform().InverseTransformPosition(Arms->GetSocketLocation(TEXT("hand_l")));
        };
        const auto Lengths=[&]()
        {
            return FVector2D(FVector::Dist(Arms->GetSocketLocation(TEXT("upperarm_l")),Arms->GetSocketLocation(TEXT("lowerarm_l"))),
                FVector::Dist(Arms->GetSocketLocation(TEXT("lowerarm_l")),Arms->GetSocketLocation(TEXT("hand_l"))));
        };
        const FVector Start=Sample(-Potion->OffhandLowerSeconds);
        const FTransform Right=Arms->GetSocketTransform(TEXT("hand_r"));const FVector2D NativeLengths=Lengths();
        float MaxRightDrift=0.f,MaxLengthDrift=0.f,MaxStep=0.f;
        FVector Previous=Start;
        for(int32 I=1;I<=36;++I)
        {
            const float Age=-Potion->OffhandLowerSeconds+Potion->OffhandLowerSeconds*I/36.f;
            const FVector Current=Sample(Age);
            MaxStep=FMath::Max(MaxStep,float(FVector::Dist(Current,Previous)));Previous=Current;
            MaxRightDrift=FMath::Max(MaxRightDrift,float(FVector::Dist(Right.GetLocation(),Arms->GetSocketLocation(TEXT("hand_r")))));
            MaxLengthDrift=FMath::Max(MaxLengthDrift,float((Lengths()-NativeLengths).Size()));
        }
        const FVector Lowered=Previous;
        Check(Lowered.Z<Start.Z-15.f&&Lowered.Z<-30.f,TEXT("consuming blade hand lowers below the camera before use"));
        Check(MaxRightDrift<.01f,TEXT("stow preserves opposite hand position"));
        Check(MaxLengthDrift<.02f,TEXT("stow preserves native upper/forearm lengths"));
        Check(MaxStep<5.f,TEXT("stow is continuous at 100 Hz"));
        Sample(-.001f);Check(!Potion->IsOffhandWeaponHidden(),TEXT("weapon remains visible until stow completes"));
        const FVector Before=Sample(-.0001f),After=Sample(.0001f);
        Check(FVector::Dist(Before,After)<.1f&&Potion->IsOffhandWeaponHidden(),TEXT("no hand jump at stow-to-consume handoff"));
        const FVector Return=Sample(Potion->Motion.Duration+Potion->OffhandRaiseSeconds);
        Check(FVector::Dist(Return,Start)<.1f&&!Potion->IsOffhandWeaponHidden(),TEXT("completion raises the native equipped hand back"));
        Report+=FString::Printf(TEXT("DUAL_HAND start=%s lowered=%s right_drift_cm=%.6f length_drift_cm=%.6f max_step_cm=%.4f\n"),
            *Start.ToString(),*Lowered.ToString(),MaxRightDrift,MaxLengthDrift,MaxStep);
        Potion->Finish();Arms->DestroyComponent();
    }
    Blade->InstanceId.Reset();Blade->bDual=false;Blade->Viewmodel=nullptr;
    Unarmed->bEquipmentResolved=Unarmed->bHandsEmpty=true;Unarmed->Arms=NewObject<UFPSUnarmedArmsMeshComponent>(Player);
    Check(CanUse(),TEXT("unarmed idle can consume"));Check(Player->ConsumableHands()==Unarmed->Arms,TEXT("unarmed uses current arms"));
    Potion->bActive=true;Check(!CanUse(),TEXT("active consumable prevents reentry"));Potion->Finish();
    Check(CanUse(),TEXT("finish returns action ownership"));
    Potion->Bottle=NewObject<UStaticMeshComponent>(Player);
    Potion->Liquid=NewObject<UStaticMeshComponent>(Player);
    Potion->Stopper=NewObject<UStaticMeshComponent>(Player);
    Dual->bActive=true;Dual->bOffhandOnly=false;
    Dual->Hands[0].Pending=true;
    Check(!CanUse(),TEXT("a pending right shot prevents starting a meal"));
    Dual->CancelInputs();
    for(const FString Id:{FString(TEXT("roasted_large_lamb")),FString(TEXT("bread")),FString(TEXT("mineral_water")),FString(TEXT("soda_can")),FString(TEXT("hp_potion"))})
    {
        Potion->bActive=true;Potion->bStowOffhand=true;
        Potion->bFood=UFPSPotionUseComponent::IsFood(Id);
        Potion->bSoda=Id==TEXT("soda_can");Potion->bWater=Id==TEXT("mineral_water");
        Potion->Motion.Duration=6.f;Potion->Motion.Contact=4.65f;Potion->StartTime=World->GetTimeSeconds()-2.f;
        Player->AimPressed();
        Player->ReloadInputPressed();
        Player->FirePressed();
        Check(!Dual->HasHeldTrigger()&&!Dual->Hands[0].Pending&&!Dual->Hands[1].Pending &&
            !Player->IsChoosingAmmo()&&!Player->CanStartQuickCombatPriority(),Id+TEXT(" blocks both triggers, reload input and quick combat"));
        Check(Potion->bReturningFromMeal==(Id!=TEXT("hp_potion")),Id+TEXT(" has the intended cancellation policy"));
        Potion->TickComponent(.01f,LEVELTICK_All,nullptr);
        Check(Potion->IsActive()&&!Potion->bCommitted,Id+TEXT(" blocked input cannot commit an item"));
        Player->FireInputReleased();
        Check(!Potion->bOwnsPrimaryRelease,Id+TEXT(" consumes the paired release"));
        Potion->Finish();
    }
    Dual->bActive=false;
    for(const TCHAR* Definition:{TEXT("bread"),TEXT("baguette_bread"),TEXT("mineral_water"),TEXT("soda_can"),
        TEXT("hp_potion"),TEXT("hp_potion_high"),TEXT("mp_potion"),TEXT("mp_potion_high")})
        Check(UFPSPotionUseComponent::IsAnimatedConsumable(Definition),FString(Definition)+TEXT(" uses shared action path"));
    for(float Rate:{.75f,1.f,1.5f,2.f})for(float SourceAge:{-.27f,-.12f,1.f,2.15f,2.30f})
    {
        FFPSBodyState S;S.Action=EFPSBodyAction::Consume;S.ConsumeHands=2;S.bHasActionProgress=true;
        S.ActionDuration=2.1f;S.ActionProgressRate=Rate/S.ActionDuration;
        S.PresentationSampledAt=100.f;S.ActionStartedAt=100.f-SourceAge/Rate;
        S.ConsumeStowWeight=PotionEquipmentHandoff::Weight(SourceAge,S.ActionDuration);
        S.bConsumeWeaponsHidden=SourceAge>=0.f&&SourceAge<S.ActionDuration;
        FPSBodyConsumeMotion::Advance(S,.08f);
        Check(FMath::IsNearlyEqual(S.ConsumeStowWeight,PotionEquipmentHandoff::Weight(SourceAge+.08f*Rate,S.ActionDuration),.0002f),
            FString::Printf(TEXT("remote stow/return follows source clock at rate %.2f age %.2f"),Rate,SourceAge));
        Check(FMath::IsNearlyEqual(S.ActionProgress,FMath::Clamp((SourceAge+.08f*Rate)/S.ActionDuration,0.f,1.f),.0002f),
            TEXT("remote use progress never advances from a clamped lead-in sample"));
    }
    FFPSBodyState EmptyHand;EmptyHand.Action=EFPSBodyAction::Consume;EmptyHand.ConsumeHands=2;
    EmptyHand.ActionDuration=2.1f;EmptyHand.ActionProgressRate=1.f/2.1f;
    EmptyHand.ActionStartedAt=100.f;EmptyHand.PresentationSampledAt=100.2f;
    FPSBodyConsumeMotion::Advance(EmptyHand,.08f);
    Check(EmptyHand.ConsumeStowWeight==0.f,TEXT("empty offhand/bow support does not acquire a network stow"));
    World->DestroyWorld(false);
    Report+=FString::Printf(TEXT("RESULT passed=%d failed=%d\n"),Passed,Failed);
    const FString Folder=FPaths::ProjectSavedDir()/TEXT("ConsumableWeaponFix20261006");
    IFileManager::Get().MakeDirectory(*Folder,true);FFileHelper::SaveStringToFile(Report,*(Folder/TEXT("state-check.txt")));
    UE_LOG(LogTemp,Display,TEXT("CONSUMABLE_WEAPON_STATE_CHECK passed=%d failed=%d"),Passed,Failed);
    if(Failed)UE_LOG(LogTemp,Error,TEXT("%s"),*Report);
    return Failed?1:0;
}
