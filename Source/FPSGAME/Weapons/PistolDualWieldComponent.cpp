#include "PistolDualWieldComponent.h"
#include "G18WeaponAssets.h"
#include "Staff/StaffCatalog.h"
#include "../FPSGAMECharacter.h"
#include "../FPSGAMEPlayerController.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelPickupStudio.h"
#include "FPSGunplayAnimInstance.h"
#include "WeaponGripProfile.h"
#include "FPSWeaponFXComponent.h"
#include "FPSBallisticsComponent.h"
#include "WeaponStatEvaluation.h"
#include "DanWesson715WeaponAssets.h"
#include "DanWesson715FittedParts.h"
#include "M1911MagazineVisual.h"
#include "M1911WeaponAssets.h"
#include "WeaponReloadStages.h"
#include "TacticalDeviceComponent.h"
#include "../Skills/FPSCastingMeshComponent.h"
#include "../Skills/FPSQuickCombatComponent.h"
#include "QuickCombatRecovery.h"
#include "DualPistolQuickCombatMotion.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/AudioComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Camera/CameraComponent.h"
#include "Animation/AnimSequence.h"
#include "Engine/GameInstance.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"

namespace
{
FString Root(bool Revolver,int32 Side)
{
    return FString::Printf(TEXT("/Game/Weapons/PistolDualWield20260914/%s/%s"),Revolver?TEXT("DW715"):TEXT("M1911"),Side?TEXT("l"):TEXT("r"));
}
FString Stem(bool Revolver,int32 Side)
{
    return FString::Printf(TEXT("Dual_%s_%s"),Revolver?TEXT("DW715"):TEXT("M1911"),Side?TEXT("l"):TEXT("r"));
}
FName PistolPoseFamily(const FString& Kind)
{
    return Kind.Contains(TEXT("_long"))?FName(TEXT("long")):Kind.Contains(TEXT("_fitted"))?FName(TEXT("fitted")):FName(NAME_None);
}
}

UPistolDualWieldComponent::UPistolDualWieldComponent()
{
    PrimaryComponentTick.bCanEverTick=false;
    Hands.SetNum(2);
}

bool UPistolDualWieldComponent::LeftBusy() const
{
    return bActive && (Hands[1].Reloading || Hands[1].Action || Hands[1].Held || Hands[1].Pending);
}

bool UPistolDualWieldComponent::InputAvailable() const
{
    if(!Player || !bActive || Player->IsTraversing() || IsQuickCombatActive())return false;
    const auto* PC=Cast<APlayerController>(Player->GetController());
    if(AFPSGAMEPlayerController::BlocksOngoingActions(PC))return false;
    const auto* Health=Player->FindComponentByClass<UFPSCombatHealthComponent>();
    return !Health || !Health->IsDead();
}

void UPistolDualWieldComponent::LoadHand(int32 Index,const FColdSteelItem& Item)
{
    auto& H=Hands[Index];H.Item=Item;H.Revolver=Item.Definition==TEXT("ue_dan_wesson715");
    const bool G18=Item.Definition==G18WeaponAssets::Definition;
    const FString Base=G18?G18WeaponAssets::DualRoot(Index):Root(H.Revolver,Index),Name=G18?G18WeaponAssets::DualStem(Index):Stem(H.Revolver,Index);
    if(Index==0)H.Mesh=Player->AKMViewmodel;
    else if(!H.Mesh)
    {
        H.Mesh=NewObject<UFPSCastingMeshComponent>(Player,TEXT("DualPistolLeft"));
        Player->AddInstanceComponent(H.Mesh);
        H.Mesh->SetupAttachment(Player->FirstPersonCamera);
        H.Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        H.Mesh->SetCastShadow(false);H.Mesh->SetOnlyOwnerSee(true);
        H.Mesh->SetFirstPersonPrimitiveType(Player->AKMViewmodel->FirstPersonPrimitiveType);
        H.Mesh->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
        H.Mesh->RegisterComponent();
        H.Mesh->AddTickPrerequisiteActor(Player);
    }
    H.Mesh->EmptyOverrideMaterials();
    H.Mesh->SetSkeletalMesh(LoadObject<USkeletalMesh>(nullptr,*(Base+TEXT("/SK_")+Name)));
    H.Mesh->SetBoundsScale(7.f);
    if(auto* CastMesh=Cast<UFPSCastingMeshComponent>(H.Mesh))CastMesh->bApplyLeftHandCast=Index==1;
    H.Mesh->SetAnimationMode(EAnimationMode::AnimationBlueprint);
    H.Mesh->SetAnimInstanceClass(UFPSGunplayAnimInstance::StaticClass());
    H.Anim=Cast<UFPSGunplayAnimInstance>(H.Mesh->GetAnimInstance());
    if(Index==0)Player->GunplayAnimation=H.Anim;
    H.Clips.Empty();
    H.PoseProfiles.Reset();H.ActionPoseProfile=NAME_None;
    for(const TCHAR* Family:{TEXT("fitted"),TEXT("long")})
    {
        const FString Path=FString::Printf(TEXT("/Game/Weapons/AnimationProfiles20261001/%s/Dual_%s/DA_%s"),*Item.Definition,Index?TEXT("l"):TEXT("r"),Family);
        if(auto* Layer=LoadObject<UWeaponGripProfile>(nullptr,*Path,nullptr,LOAD_NoWarn);Layer&&Layer->Family==Family)
            H.PoseProfiles.Add(Family,Layer);
    }
    const auto SharedQuickClip=[&](const FString& Kind)->UAnimSequence*
    {
        // V5 supported the wrist only during the recovery flourish. The left
        // M1911 strike now carries its held group through the full arm solve.
        if(bOffhandOnly&&Index==1&&Item.Definition==TEXT("ue_m1911")&&Kind.StartsWith(TEXT("quickcombat_left")))
        {
            const FString Path=TEXT("/Game/Weapons/StaffQuickCombatFix20261001/M1911/l/Animations/A_Dual_M1911_l_")+Kind;
            if(auto* Revised=LoadObject<UAnimSequence>(nullptr,*Path,nullptr,LOAD_NoWarn))return Revised;
        }
        const auto* Layer=H.PoseProfiles.FindRef(PistolPoseFamily(Kind)).Get();
        if(!Layer)return nullptr;
        const FString BaseKind=Kind.Replace(TEXT("_fitted"),TEXT("")).Replace(TEXT("_long"),TEXT(""));
        const auto* Motion=Layer->FindAction(*BaseKind);
        return Motion?Motion->Playback():nullptr;
    };
    auto Clip=[&](const FString& Kind)
    {
        if(auto* Shared=SharedQuickClip(Kind)){H.Clips.Add(Kind,Shared);return;}
        if(G18){H.Clips.Add(Kind,LoadObject<UAnimSequence>(nullptr,*G18WeaponAssets::DualAnimationPath(Index,Kind)));return;}
        const TCHAR* Revision=Kind.StartsWith(TEXT("sprint"))?TEXT("/SprintSmoothV5/Animations/A_"):TEXT("/NaturalAimV3/Animations/A_");
        if(H.Revolver && (Kind.StartsWith(TEXT("single_")) || Kind.StartsWith(TEXT("speed_"))))
            Revision=TEXT("/RevolverReloadFlickV6/Animations/A_");
        H.Clips.Add(Kind,LoadObject<UAnimSequence>(nullptr,*(Base+Revision+Name+TEXT("_")+Kind)));
    };
    for(const TCHAR* Kind:{TEXT("idle"),TEXT("sprint"),TEXT("fire"),TEXT("equip")})Clip(Kind);
    if(H.Revolver)
    {
        Clip(TEXT("speed_0"));
        for(int32 Start=0;Start<6;++Start)for(int32 Count=1;Count<=6-Start;++Count)Clip(FString::Printf(TEXT("single_%d_%d"),Start,Count));
    }
    else for(const TCHAR* Kind:{TEXT("idle_empty"),TEXT("sprint_empty"),TEXT("fire_last"),TEXT("reload"),TEXT("reload_empty")})Clip(Kind);
    for(const TCHAR* Kind:{TEXT("quickcombat"),TEXT("quickcombat_empty"),TEXT("quickcombat_left"),TEXT("quickcombat_left_empty"),
        TEXT("quickcombat_fitted"),TEXT("quickcombat_fitted_empty"),TEXT("quickcombat_left_fitted"),TEXT("quickcombat_left_fitted_empty"),
        TEXT("quickcombat_long"),TEXT("quickcombat_long_empty"),TEXT("quickcombat_left_long"),TEXT("quickcombat_left_long_empty")})
    {
        if(auto* Shared=SharedQuickClip(Kind)){H.Clips.Add(Kind,Shared);continue;}
        if(G18){Clip(Kind);continue;}
        if(H.Revolver && FString(Kind).EndsWith(TEXT("_empty")))continue;
        const TCHAR* Revision=TEXT("SpinRecoveryV5");
        const FString Path=FString::Printf(TEXT("/Game/Weapons/DualPistolQuickCombat20260920/%s/%s/%s/Animations/A_%s_%s"),
            Revision,H.Revolver?TEXT("DW715"):TEXT("M1911"),Index?TEXT("l"):TEXT("r"),*Name,Kind);
        H.Clips.Add(Kind,LoadObject<UAnimSequence>(nullptr,*Path));
    }
    H.Sounds.Empty();
    for(const TCHAR* CueName:{TEXT("Fire"),TEXT("DryClick"),TEXT("MagOut"),TEXT("MagInsert"),TEXT("MagSeat"),TEXT("ChargePull"),TEXT("ChargeRelease"),TEXT("Equip")})
    {
        FString Path=H.Revolver?DanWesson715WeaponAssets::SoundPath(CueName)
            :FString(CueName)==TEXT("Fire")?TEXT("/Game/Weapons/M1911/Integrated20260913/Audio/S_M1911_Fire")
            :FString::Printf(TEXT("/Game/Weapons/AKM/Audio/S_AKM_%s"),CueName);
        if(!H.Revolver && FString(CueName).StartsWith(TEXT("Mag")))Path=FString::Printf(TEXT("/Game/Weapons/M4HK416Audio/S_HK416_%s"),CueName);
        if(!H.Revolver && FString(CueName)==TEXT("Equip"))Path=TEXT("/Game/Weapons/M4AnimationAuditFinal/S_HK416_Equip");
        if(G18)Path=G18WeaponAssets::SoundPath(CueName);
        H.Sounds.Add(CueName,LoadObject<USoundBase>(nullptr,*Path));
    }
    H.Sounds.Add(TEXT("BoltRelease"),H.Sounds.FindRef(TEXT("ChargeRelease")));
    if(G18)
    {
        for(int32 Variant=1;Variant<=4;++Variant)
            for(const TCHAR* Group:{TEXT("Fire"),TEXT("Suppressed")})
            {
                const FString Key=FString::Printf(TEXT("%s_%02d"),Group,Variant);
                H.Sounds.Add(Key,LoadObject<USoundBase>(nullptr,*G18WeaponAssets::SoundPath(Key)));
            }
        H.Sounds.Add(TEXT("Suppressed"),LoadObject<USoundBase>(nullptr,*G18WeaponAssets::SoundPath(TEXT("Suppressed"))));
    }
    H.Sounds.Add(TEXT("SingleOpen"),H.Sounds.FindRef(TEXT("MagOut")));
    H.Sounds.Add(TEXT("SingleEject"),H.Sounds.FindRef(TEXT("ChargePull")));
    H.Sounds.Add(TEXT("SingleClose"),H.Sounds.FindRef(TEXT("ChargeRelease")));
    if(H.Revolver)for(const auto& C:DanWesson715WeaponAssets::SpeedloaderSoundCues)
        H.Sounds.Add(C.Name,LoadObject<USoundBase>(nullptr,*DanWesson715WeaponAssets::SpeedloaderSoundPath(C.Name)));
    if(!H.FX)
    {
        H.FX=NewObject<UFPSWeaponFXComponent>(Player);Player->AddInstanceComponent(H.FX);H.FX->RegisterComponent();
        H.Ballistics=NewObject<UFPSBallisticsComponent>(Player);Player->AddInstanceComponent(H.Ballistics);H.Ballistics->RegisterComponent();
    }
    H.FX->SetIndependentPistol(H.Revolver,false,nullptr);
    H.FX->Initialize(H.Mesh,Player->FirstPersonCamera);
    H.NextShot=GetWorld()->GetTimeSeconds();H.LastShot=-10;H.Pattern=0;H.Bloom=0;H.Sprint=H.SprintBlend=0;H.Recipe.Empty();
    StartAction(Index,TEXT("equip"));
}

bool UPistolDualWieldComponent::MatchesEquipment(const UColdSteelStatusModel* Model,bool bWeaponReady) const
{
    const auto* Main=Model?Model->Equipped():nullptr;
    const auto* Off=Main?Model->Equipped(Main->Cell==6?8:11):nullptr;
    const bool Staff=Main && ColdSteelStaff::IsStaff(*Main) && !Model->ActiveProductionTool();
    const bool Want=Main && Off && ColdSteelInventory::IsDualPistol(*Off)
        && (Staff || (bWeaponReady && ColdSteelInventory::IsDualPistol(*Main)));
    if(!Want)return !bActive;
    return bActive && bOffhandOnly==Staff && MainHandInstance==Main->InstanceId
        && (Staff || Hands[0].Item.Definition==Main->Definition)
        && Hands[1].Item.InstanceId==Off->InstanceId && Hands[1].Item.Definition==Off->Definition;
}

void UPistolDualWieldComponent::Deactivate()
{
    if(!bActive)return;
    if(IsQuickCombatActive())Player->QuickCombatPistol->Cancel();
    CancelInputs();
    for(int32 Side=FirstHand();Side<2;++Side)
    {
        auto& H=Hands[Side];
        StopAction(Side);
        if(H.FX)H.FX->StopEmission();
        if(H.Anim){H.Anim->bDualPistolAim=false;H.Anim->DualPistolAimAlpha=0.f;}
    }
    bActive=false;
    MainHandInstance.Reset();
    if(Hands[1].Mesh)Hands[1].Mesh->SetVisibility(false,true);
    if(Hands[1].Tactical)Hands[1].Tactical->Configure(TEXT(""),TEXT(""),Hands[1].Mesh,false);
    if(auto* CastMesh=Cast<UFPSCastingMeshComponent>(Player->AKMViewmodel))CastMesh->bApplyLeftHandCast=true;
}

void UPistolDualWieldComponent::RefreshEquipment(UColdSteelStatusModel* Model)
{
    Player=Cast<AFPSGAMECharacter>(GetOwner());Profile=Model;
    if(!Player || !Profile)return;
    const auto* Main=Profile->Equipped();
    const auto* Off=Main?Profile->Equipped(Main->Cell==6?8:11):nullptr;
    const bool Staff=Main && ColdSteelStaff::IsStaff(*Main) && !Profile->ActiveProductionTool();
    const bool Want=Main && Off && ColdSteelInventory::IsDualPistol(*Off)
        && (Staff || (Player->HasInventoryWeapon() && ColdSteelInventory::IsDualPistol(*Main)));
    // Leaving/replacing a loadout is owned by the character, before it rebuilds
    // the shared main-hand mesh. Repeated data application never cancels actions.
    if(!Want)return;
    const bool Changed=!bActive;
    bOffhandOnly=Staff;MainHandInstance=Main->InstanceId;
    bActive=true;
    if(Changed)
    {
        Player->StopMechanicalAudio();Player->ActiveActionAnimation=nullptr;
        Player->WeaponState=EAKMWeaponState::Idle;Player->WeaponStateElapsed=Player->WeaponStateDuration=0;
        Player->bReloadAfterCasting=Player->bRevolverReloadAfterFire=Player->bPistolShotPending=false;
        Player->bAimHeld=false;Player->SetAimingState(false);
        Player->ADSProgress=Player->WeaponADSFactor=Player->CameraADSFactor=0;
        Player->WeaponFX->StopEmission();
        if(!bOffhandOnly)LoadHand(0,*Main);
        LoadHand(1,*Off);
    }
    auto* G=Player->GetGameInstance()->GetSubsystem<UGunsmithSystem>();
    for(int32 Side=FirstHand();Side<2;++Side)
    {
        auto& H=Hands[Side];H.Item=Side?*Off:*Main;
        const auto Parts=G->Installed(H.Item);
        H.Stats=G->Calculate(H.Item.Definition,Parts);
        H.Stats.Damage=ColdSteelWeaponStats::Damage(H.Item,Profile,H.Stats.Damage)*Profile->AmmoDamageMultiplier(H.Item);
        H.Stats.Interval=ColdSteelWeaponStats::Interval(&H.Item,Profile,H.Stats.Interval);
        H.Stats.Reload=ColdSteelWeaponStats::Reload(&H.Item,Profile,H.Stats.Reload);
        H.Stats.EmptyReload=ColdSteelWeaponStats::Reload(&H.Item,Profile,H.Stats.EmptyReload);
        H.Rounds=FMath::Clamp(H.Item.Magazine,0,H.Stats.Capacity);
        H.Cases=H.Revolver?FMath::Clamp(int32(ColdSteelInventory::Number(H.Item,TEXT("revolver_case_count"),H.Rounds)),H.Rounds,6):H.Rounds;
        H.Speedloader=H.Revolver && Parts.FindRef(TEXT("reload_device"))==TEXT("dw715_speedloader");
        H.Suppressed=Parts.FindRef(TEXT("muzzle"))==TEXT("tactical_suppressor") || Parts.FindRef(TEXT("muzzle"))==TEXT("true");
        // Right FX uses the primary attachment interface, left FX uses its own copied exit.
        H.FX->IndependentSuppressed=H.Suppressed;
        if(Side==0){H.FX->bUseCharacterMuzzle=true;H.Sounds.Add(TEXT("Suppressed"),Player->SuppressedFireSound);}
        else
        {
            auto* Studio=Player->GetGameInstance()->GetSubsystem<UColdSteelPickupStudio>();
            const FString Key=Studio->Key(H.Item);
            if(Key!=H.Recipe){CopyLeftAttachments(H.Item,Parts);H.Recipe=Key;}
        }
    }
    if(!bOffhandOnly){Player->MagazineAmmo=Hands[0].Rounds;Player->RevolverCaseCount=Hands[0].Cases;}
    if(Changed)UpdateAimTarget(0.f);
    if(!bOffhandOnly)Pose(0,0);
    Pose(1,0);
}

void UPistolDualWieldComponent::CopyLeftAttachments(const FColdSteelItem& Item,const FGunsmithParts& Parts)
{
    for(auto& C:LeftAttachments)if(C)C->DestroyComponent();LeftAttachments.Empty();
    bool Created=false;
    auto* Rig=Player->GetGameInstance()->GetSubsystem<UColdSteelPickupStudio>()->Acquire(Item.Definition,Created);
    if(!Rig)return;
    if(Created){Rig->ActiveInventoryWeaponDefinition=Item.Definition;Rig->bUseM4Infima=Rig->bUseQBZ191=false;Rig->bUseM1911=!Hands[1].Revolver;Rig->bUseDanWesson715=Hands[1].Revolver;Rig->InitializeWeaponVisuals();}
    Rig->SetGunsmithOpticVariant(Parts.FindRef(TEXT("optic")));Rig->SetGunsmithMuzzle(Parts.FindRef(TEXT("muzzle")));
    Rig->SetGunsmithRearGrip(Parts.FindRef(TEXT("reargrip")),Player->GetGameInstance()->GetSubsystem<UGunsmithSystem>()->Weapon(Item.Definition));Rig->SetGunsmithTactical(TEXT(""));
    Rig->SetGunsmithMagazineAttachment(Parts.FindRef(TEXT("magazine")));
    if (!Hands[1].Revolver)
        M1911MagazineVisual::ShowFactoryMagazine(Hands[1].Mesh,
            !(Rig->LargeDrum && Rig->LargeDrum->IsVisible()));
    if (Hands[1].Revolver)
        DanWesson715FittedParts::ShowFactoryGrip(Hands[1].Mesh,
            !(Rig->RearGripAttachment && Rig->RearGripAttachment->IsVisible()));
    TMap<USceneComponent*,USceneComponent*> Copies;Copies.Add(Rig->AKMViewmodel,Hands[1].Mesh);
    TFunction<USceneComponent*(USceneComponent*)> Copy=[&](USceneComponent* Source)->USceneComponent*
    {
        if(auto** Existing=Copies.Find(Source))return *Existing;
        if(!Source || !Source->GetAttachParent())return nullptr;
        auto* Parent=Copy(Source->GetAttachParent());if(!Parent)return nullptr;
        USceneComponent* New=nullptr;
        if(auto* Static=Cast<UStaticMeshComponent>(Source))
        {
            auto* Mesh=NewObject<UStaticMeshComponent>(Player);New=Mesh;
            Mesh->SetStaticMesh(Static->GetStaticMesh());
            for(int32 M=0;M<Static->GetNumMaterials();++M)Mesh->SetMaterial(M,Static->GetMaterial(M));
            Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);Mesh->SetCastShadow(false);Mesh->SetOnlyOwnerSee(true);
            Mesh->SetFirstPersonPrimitiveType(Player->AKMViewmodel->FirstPersonPrimitiveType);
        }
        else New=NewObject<USceneComponent>(Player);
        Player->AddInstanceComponent(New);New->SetupAttachment(Parent,Source->GetAttachSocketName());
        New->SetRelativeTransform(Source->GetRelativeTransform());New->SetVisibility(Source->IsVisible());New->RegisterComponent();
        Copies.Add(Source,New);LeftAttachments.Add(New);return New;
    };
    TArray<USceneComponent*> Children;Rig->AKMViewmodel->GetChildrenComponents(true,Children);
    for(auto* C:Children)if(auto* Mesh=Cast<UStaticMeshComponent>(C);Mesh && Mesh->IsVisible() && Mesh->GetStaticMesh())Copy(C);
    USceneComponent* Tip=nullptr;
    if(Rig->MuzzleAttachment && Rig->MuzzleAttachment->IsVisible())if(auto** Parent=Copies.Find(Rig->MuzzleAttachment))
    {
        Tip=NewObject<USceneComponent>(Player);Player->AddInstanceComponent(Tip);Tip->SetupAttachment(*Parent);
        Tip->SetRelativeLocation(Rig->MuzzleLocalTip);Tip->SetRelativeRotation(Rig->MuzzleLocalAxis.Rotation());Tip->RegisterComponent();LeftAttachments.Add(Tip);
    }
    Hands[1].FX->SetIndependentPistol(Hands[1].Revolver,Hands[1].Suppressed,Tip);
    if(!Hands[1].Tactical)
    {
        Hands[1].Tactical=NewObject<UTacticalDeviceComponent>(Player);Player->AddInstanceComponent(Hands[1].Tactical);Hands[1].Tactical->RegisterComponent();
    }
    Hands[1].Tactical->Configure(Hands[1].Item.Definition==G18WeaponAssets::Definition?TEXT("G18"):Hands[1].Revolver?TEXT("DanWesson715"):TEXT("M1911"),Parts.FindRef(TEXT("tactical")),Hands[1].Mesh,true);
    Hands[1].Sounds.Add(TEXT("Suppressed"),Rig->SuppressedFireSound);
    Hands[0].Sounds.Add(TEXT("Suppressed"),Player->SuppressedFireSound);
}

void UPistolDualWieldComponent::StartAction(int32 Index,const FString& Name,float Rate)
{
    auto& H=Hands[Index];H.Action=H.Clips.FindRef(Name);H.ActionTime=0;H.ActionRate=Rate;H.ActionStarted=GetWorld()->GetTimeSeconds();H.PlayedCues.Empty();
    H.ActionBlendStarted=H.ActionStarted;
    H.ActionPoseProfile=PistolPoseFamily(Name);
}
void UPistolDualWieldComponent::StopAction(int32 Index)
{
    auto& H=Hands[Index];H.Action=nullptr;H.Reloading=H.ReloadQueued=false;H.PendingAmmoType.Reset();
    for(auto& Voice:H.Voices)if(IsValid(Voice))Voice->Stop();H.Voices.Empty();
}
void UPistolDualWieldComponent::CancelInputs()
{
    for(auto& H:Hands)H.Held=H.Pending=false;
}

void UPistolDualWieldComponent::InterruptReloads()
{
    for(int32 Side=0;Side<Hands.Num();++Side)if(Hands[Side].Reloading)StopAction(Side);
}

void UPistolDualWieldComponent::TryCowboyReload()
{
    if(!bActive || !Profile)return;
    // Main then offhand share one pouch. Each successful transaction refreshes
    // both hand counters before the next hand calculates its remaining reserve.
    for(int32 Side=FirstHand();Side<Hands.Num();++Side)
    {
        const FString WeaponId=Hands[Side].Item.InstanceId;
        if(Profile->ReloadCowboyPistol(WeaponId,Hands[Side].Stats.Capacity)<=0)continue;
        if(Hands[Side].Reloading)StopAction(Side);
        auto& H=Hands[Side];
        H.ReloadQueued=false;
        H.PendingAmmoType.Reset();
        if(auto* Sound=H.Sounds.FindRef(H.Revolver?TEXT("SingleOpen"):TEXT("MagInsert")).Get())
            UGameplayStatics::PlaySound2D(this,Sound,.8f);
    }
}

bool UPistolDualWieldComponent::IsEquipping() const
{
    if(!bActive)return false;
    for(int32 Side=FirstHand();Side<2;++Side)
        if(Hands[Side].Action && Hands[Side].Action==Hands[Side].Clips.FindRef(TEXT("equip")))return true;
    return false;
}

void UPistolDualWieldComponent::InterruptActions()
{
    CancelInputs();
    for(int32 Side=0;Side<Hands.Num();++Side)StopAction(Side);
}

void UPistolDualWieldComponent::PrepareSingleInspect()
{
    // Single-weapon setup runs again after leaving dual wield (LoadHand clears
    // the old clip map). Keep this small variant alive without loading on L.
    const auto* OwnerPlayer=Cast<AFPSGAMECharacter>(GetOwner());
    Hands[0].Clips.Add(TEXT("single_inspect_empty"),LoadObject<UAnimSequence>(nullptr,*(OwnerPlayer && OwnerPlayer->IsG18Weapon() ? G18WeaponAssets::AnimationPath(TEXT("inspect_empty")) : M1911WeaponAssets::AnimationPath(TEXT("inspect_empty")))));
}

UAnimSequence* UPistolDualWieldComponent::SingleEmptyInspect() const
{
    return Hands[0].Clips.FindRef(TEXT("single_inspect_empty"));
}

bool UPistolDualWieldComponent::IsQuickCombatActive() const
{
    return bActive && Player && Player->QuickCombatPistol
        && Player->QuickCombatPistol->GetStyle()==(bOffhandOnly?EQuickCombatStyle::StaffOffhandPistol:EQuickCombatStyle::DualPistol)
        && Player->QuickCombatPistol->IsOccupyingLeftHand();
}

bool UPistolDualWieldComponent::IsQuickCombatClip(int32 Index) const
{
    const auto& H=Hands[Index];
    if(!H.Action)return false;
    for(const auto& Clip:H.Clips)
        if(Clip.Key.StartsWith(TEXT("quickcombat")) && H.Action==Clip.Value)return true;
    return false;
}

FString UPistolDualWieldComponent::QuickCombatClipKind(int32 Side,bool LeftStrike) const
{
    const auto& H=Hands[Side];
    FString Kind=LeftStrike?TEXT("quickcombat_left"):TEXT("quickcombat");
    const auto* Instance=Player?Player->GetGameInstance():nullptr;
    const auto* Gunsmith=Instance?Instance->GetSubsystem<UGunsmithSystem>():nullptr;
    if(Gunsmith)
    {
        const auto Parts=Gunsmith->Installed(H.Item);
        const FString Optic=Parts.FindRef(TEXT("optic")),Muzzle=Parts.FindRef(TEXT("muzzle")),Tactical=Parts.FindRef(TEXT("tactical"));
        // Every profile retains the full recovery revolution. Long cans use
        // the most canted axis, including when an optic/tactical is also fitted.
        if(Muzzle==TEXT("true") || Muzzle==TEXT("tactical_suppressor"))Kind+=TEXT("_long");
        else if(Optic==TEXT("holographic") || Optic==TEXT("panoramic_red_dot")
            || Tactical==TEXT("laser") || Tactical==TEXT("flashlight"))Kind+=TEXT("_fitted");
    }
    if(!H.Revolver && H.Rounds==0)Kind+=TEXT("_empty");
    return Kind;
}

const TCHAR* UPistolDualWieldComponent::QuickCombatBlockReason() const
{
    if(!bActive || !Player || !Player->QuickCombatPistol)return TEXT("双持/副手控制器未就绪");
    if(!Player->CanStartQuickCombatPriority())return TEXT("切换武器或输入不可用");
    const bool LeftStrike=bOffhandOnly||DualPistolQuickCombatMotion::StrikingHand(Player->QuickCombatPistol->GetActionSerial()+1u)==1;
    UAnimSequence* Clips[2]={nullptr,nullptr};
    for(int32 Side=FirstHand();Side<2;++Side)
    {
        const auto& H=Hands[Side];
        if(!H.Mesh || !H.Anim)return TEXT("单手视模/动画实例缺失");
        const FString Kind=QuickCombatClipKind(Side,LeftStrike);
        Clips[Side]=H.Clips.FindRef(Kind);
        if(!Clips[Side])return TEXT("当前出手侧/空仓近战动画缺失");
    }
    if(!bOffhandOnly&&!FMath::IsNearlyEqual(Clips[0]->GetPlayLength(),Clips[1]->GetPlayLength(),.001f))return TEXT("左右近战动画时长不一致");
    return nullptr;
}

bool UPistolDualWieldComponent::BeginQuickCombat()
{
    if(const TCHAR* Reason=QuickCombatBlockReason())
    {
        UE_LOG(LogTemp,Log,TEXT("[QuickCombatDual] 拒绝=%s 单持状态=%d 右=%s/%.3f/换弹%d 左=%s/%.3f/换弹%d"),
            Reason,Player?int32(Player->GetWeaponState()):-1,
            *GetNameSafe(Hands[0].Action),Hands[0].ActionTime,Hands[0].Reloading,
            *GetNameSafe(Hands[1].Action),Hands[1].ActionTime,Hands[1].Reloading);
        return false;
    }
    FString Kinds[2];
    UAnimSequence* Clips[2]={nullptr,nullptr};
    const bool LeftStrike=bOffhandOnly||DualPistolQuickCombatMotion::StrikingHand(Player->QuickCombatPistol->GetActionSerial()+1u)==1;
    for(int32 Side=FirstHand();Side<2;++Side)
    {
        const auto& H=Hands[Side];
        Kinds[Side]=QuickCombatClipKind(Side,LeftStrike);
        Clips[Side]=H.Clips.FindRef(Kinds[Side]);
    }
    Player->InterruptActionsForPriority(false);
    Player->ExitSprintForWeapon();
    if(bOffhandOnly)Player->QuickCombatPistol->ConfigureForStaffOffhandPistol(Clips[1]->GetPlayLength());
    else Player->QuickCombatPistol->ConfigureForClipLength(Clips[0]->GetPlayLength(),true);
    if(!Player->QuickCombatPistol->BeginAction())return false;
    const double Started=GetWorld()->GetTimeSeconds();
    for(int32 Side=FirstHand();Side<2;++Side)
    {
        // Pending mechanical reload state lives on the item and is resumed
        // after melee; the interrupted exchange itself is never queued again.
        const bool Queued=Hands[Side].ReloadQueued;
        StopAction(Side);Hands[Side].ReloadQueued=Queued;
        StartAction(Side,Kinds[Side]);
        Hands[Side].ActionStarted=Started;
        Pose(Side,0.f);
    }
    UE_LOG(LogTemp,Log,TEXT("[QuickCombatDual] 开始 主攻=%s 右=%s 左=%s"),
        LeftStrike?TEXT("左"):TEXT("右"),*GetNameSafe(Clips[0]),*GetNameSafe(Clips[1]));
    return true;
}

bool UPistolDualWieldComponent::GetQuickCombatStrikeProbe(FVector& OutOrigin,float ContactTime)
{
    if(!IsQuickCombatActive())return false;
    // Resolve both meshes at the shared contact frame before tracing, even if
    // this frame crossed 0.18 s. Only the current striking hand supplies a hit.
    for(int32 Side=FirstHand();Side<2;++Side)
    {
        auto& H=Hands[Side];
        if(!IsQuickCombatClip(Side) || !H.Mesh || !H.Anim)return false;
        H.ActionTime=ContactTime;
        Pose(Side,0.f);
        H.Mesh->TickAnimation(0.f,false);
        H.Mesh->RefreshBoneTransforms();
    }
    const int32 Strike=bOffhandOnly?1:DualPistolQuickCombatMotion::StrikingHand(Player->QuickCombatPistol->GetActionSerial());
    const auto* Mesh=Hands[Strike].Mesh.Get();
    const FName ContactBone=Strike?TEXT("middle_01_l"):TEXT("middle_01_r");
    // This transverse whip contacts with the gun-holding fist. Sample the
    // anatomical knuckle instead of the old downward bash's camera-Z offset.
    if(!Mesh || Mesh->GetBoneIndex(ContactBone)==INDEX_NONE)return false;
    OutOrigin=Mesh->GetSocketLocation(ContactBone);
    return true;
}
void UPistolDualWieldComponent::Trigger(int32 Index,bool Pressed)
{
    if(!bActive || Index<FirstHand() || Index>=2)return;
    auto& H=Hands[Index];
    if(!Pressed){H.Held=H.Pending=false;return;}
    if(!InputAvailable() || (IsEquipping() && H.Item.Definition!=G18WeaponAssets::Definition) || (Index==1 && Player->IsCastBlockingLeftHandAction()))return;
    if(!H.Held)H.Pending=true;H.Held=true;
    Player->ExitSprintForWeapon();
    if(H.Action==H.Clips.FindRef(TEXT("equip")))StopAction(Index);
    TryFire(Index);
}
int32 UPistolDualWieldComponent::Reserve(int32 Index) const
{
    return Profile?Profile->AmmoCountFor(Hands[Index].Item):0;
}
bool UPistolDualWieldComponent::InfiniteReserve(int32 Index) const
{return Player&&Profile&&Player->HasInfiniteReserveAmmoFor(Profile->AmmoDefinitionFor(Hands[Index].Item));}
void UPistolDualWieldComponent::SyncInventory(TArray<FColdSteelItem>& Items) const
{
    if(!bActive)return;
    for(int32 Side=FirstHand();Side<2;++Side)for(auto& I:Items)if(I.InstanceId==Hands[Side].Item.InstanceId)
    {
        const auto& H=Hands[Side];
        I.VirtualMagazineAmmo=FMath::Clamp(I.VirtualMagazineAmmo-FMath::Max(0,I.Magazine-H.Rounds),0,H.Rounds);
        I.Magazine=H.Rounds;
        if(H.Revolver)
        {
            TSharedPtr<FJsonObject> O;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(I.Data),O);
            if(O){O->SetNumberField(TEXT("revolver_case_count"),H.Cases);I.Data.Reset();FJsonSerializer::Serialize(O.ToSharedRef(),TJsonWriterFactory<>::Create(&I.Data));}
        }
    }
}

void UPistolDualWieldComponent::Advance(float Delta)
{
    if(!bActive)return;
    Clock+=Delta;
    UpdateAimTarget(Delta);
    const FVector Eye=Player->FirstPersonCamera->GetComponentLocation();FHitResult Wall;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(DualPistolNearWall),false,Player);
    const bool Close=GetWorld()->LineTraceSingleByChannel(Wall,Eye,Eye+Player->FirstPersonCamera->GetForwardVector()*80.f,ECC_Visibility,Query);
    const float WallTarget=Close?1.f-FMath::Clamp((Wall.Distance-25.f)/55.f,0.f,1.f):0.f;
    Player->NearWallAlpha=FMath::FInterpTo(Player->NearWallAlpha,WallTarget,Delta,12.f);
    // The character retains the last grounded phase through slide/jump. Reading
    // the audio clock here would pick up its airborne partial-step reset.
    Phase=Player->M4SprintPhase;
    // Hold the last running stroke during recovery. The footstep clock resets
    // its partial step when stationary; that reset must not flip the raised guns.
    if(Player->IsSprinting() && !Player->bWeaponJumpAirborne && Player->GetCharacterMovement()->IsMovingOnGround() && Player->HorizontalSpeed()>15.f)
        SprintPhase=Phase;
    if(!InputAvailable())
    {
        CancelInputs();
        // Menu entry interrupts reload presentation through SuspendWeaponForMenu.
        // Traversal and death also release these per-hand action clocks.
        if(Player->IsTraversing())for(int32 Side=0;Side<2;++Side)StopAction(Side);
        if(const auto* H=Player->FindComponentByClass<UFPSCombatHealthComponent>();H && H->IsDead())for(int32 Side=0;Side<2;++Side)StopAction(Side);
    }
    auto* Bash=Player->QuickCombatPistol.Get();
    if(bActive && Bash && Bash->GetStyle()==(bOffhandOnly?EQuickCombatStyle::StaffOffhandPistol:EQuickCombatStyle::DualPistol))
    {
        if(IsQuickCombatActive() && ((!bOffhandOnly&&!IsQuickCombatClip(0)) || !IsQuickCombatClip(1)))Bash->Cancel();
        const float SinceStart=float(FMath::Max(0.0,GetWorld()->GetTimeSeconds()-Hands[FirstHand()].ActionStarted));
        Bash->AdvanceAction(IsQuickCombatActive()?FMath::Min(Delta,SinceStart):Delta);
        Player->RefreshQuickCombatCamera();
    }
    for(int32 Side=FirstHand();Side<2;++Side)
    {
        // Bloom follows the single-weapon contract: rise per shot, recover only
        // after the hand actually stops firing. The old continuous 0.028/s decay
        // outran the 0.003 rise at both pistol cadences (0.18 s and 0.32 s), so
        // sustained fire could never open the cone and the reticle only blipped
        // per shot. The hold scales with this hand's own cadence, so a fast pistol
        // and a slow revolver both reach full bloom in a few seconds of fire.
        auto& H=Hands[Side];
        if(Side==1 && H.Reloading && Player->IsCastBlockingLeftHandAction())StopAction(Side);
        const float Hold=FMath::Max(.12f,float(H.Stats.Interval)*DualPistolSpread::BloomHold);
        const float Recovery=FMath::Clamp(float(GetWorld()->GetTimeSeconds()-H.LastShot-Hold),0.f,Delta);
        H.Bloom=FMath::Max(0.f,H.Bloom-Recovery*DualPistolSpread::BloomRecovery);
        if(IsQuickCombatClip(Side))
        {
            if(IsQuickCombatActive())H.ActionTime=Bash->GetActionAge();
            else
            {
                const bool Queued=H.ReloadQueued;StopAction(Side);H.ReloadQueued=Queued;
            }
        }
        else if(H.Action)
        {
            const float Previous=H.ActionTime/FMath::Max(.001f,H.Action->GetPlayLength())*H.SourceLength;
            H.ActionTime=FMath::Max(H.ActionTime,float(GetWorld()->GetTimeSeconds()-H.ActionStarted)*H.ActionRate);
            if(H.Reloading)AdvanceReload(Side,Previous);
            if(H.Action && H.ActionTime>=H.Action->GetPlayLength())
            {
                const bool Queued=H.ReloadQueued;StopAction(Side);H.ReloadQueued=Queued;
            }
        }
        if(InputAvailable() && !Player->IsChoosingAmmo() && !H.Action && (H.ReloadQueued || WeaponReloadStages::NeedsCycle(H.Item)
            || (H.Rounds==0 && (InfiniteReserve(Side)||Reserve(Side)>0))))BeginReload(Side);
        if(H.Item.Definition==G18WeaponAssets::Definition)
        {
            // Preserve this hand's cadence across variable frame times, with
            // bounded catch-up. Action gates remain owned by TryFire.
            for(int32 Shot=0;Shot<4;++Shot)
            {
                const double Before=H.NextShot;TryFire(Side);
                if(H.NextShot==Before || !H.Held || H.Reloading)break;
            }
        }
        else TryFire(Side);
        Pose(Side,Delta);
    }
    if(!bOffhandOnly)
    {Player->MagazineAmmo=Hands[0].Rounds;Player->RevolverCaseCount=Hands[0].Cases;Player->ReserveAmmo=Reserve(0);}
}

void UPistolDualWieldComponent::Pose(int32 Index,float Delta)
{
    auto& H=Hands[Index];if(!H.Mesh || !H.Anim)return;
    H.Anim->GripProfile=H.Action?H.PoseProfiles.FindRef(H.ActionPoseProfile).Get():nullptr;
    // Quick melee occupies the left hand, but it continues holding its gun.
    // Only spell casting uses the hidden off-hand weapon presentation.
    const bool Cast=Player->IsCastingWithLeftHand() && !IsQuickCombatActive();
    const bool Visible=bActive && !Player->IsTraversing();
    H.Mesh->SetVisibility(Visible);
    if(Index==1)
    {
        if(Cast)H.Mesh->HideBoneByName(TEXT("WPN_root"),EPhysBodyOp::PBO_None);
        else H.Mesh->UnHideBoneByName(TEXT("WPN_root"));
        for(auto& C:LeftAttachments)if(C)C->SetVisibility(Visible && !Cast);
        if(H.Tactical)H.Tactical->SetPresentationHidden(Cast || !Visible);
    }
    const bool Running=Player->IsSprinting() && !Player->bWeaponJumpAirborne && Player->GetCharacterMovement()->IsMovingOnGround()
        && Player->HorizontalSpeed()>15.f && !Player->IsSliding() && !H.Action && !Cast;
    // Finite ease-in/out: lift over 0.24 s and settle within the existing
    // sprint-to-fire window. An interrupted lift resumes from its current pose.
    const float BlendDuration=Running?.24f:FMath::Max(.01f,FMath::Min(.16f,Player->SprintToFireDuration));
    H.SprintBlend=FMath::FInterpConstantTo(H.SprintBlend,Running?1.f:0.f,Delta,1.f/BlendDuration);
    const float U=H.SprintBlend;
    H.Sprint=U*U*U*(U*(U*6.f-15.f)+10.f);
    const bool Empty=!H.Revolver && (H.Rounds==0 || WeaponReloadStages::NeedsCycle(H.Item));
    H.Anim->IdleClip=H.Clips.FindRef(Empty?TEXT("idle_empty"):TEXT("idle"));H.Anim->AimClip=H.Anim->IdleClip;
    H.Anim->AimAlpha=0;H.Anim->BaseTime=Clock;
    H.Anim->SprintClip=H.Clips.FindRef(Empty?TEXT("sprint_empty"):TEXT("sprint"));
    H.Anim->SprintTime=H.Anim->SprintClip?SprintPhase/(2.f*PI)*H.Anim->SprintClip->GetPlayLength():0.f;
    H.Anim->SprintAlpha=H.Sprint;
    H.Anim->ActionClip=H.Action;H.Anim->ActionTime=H.ActionTime;
    const float BlendAge=float(GetWorld()->GetTimeSeconds()-H.ActionBlendStarted)*H.ActionRate;
    H.Anim->ActionAlpha=H.Action?FMath::Min(FMath::Clamp(BlendAge/.025f,0.f,1.f),FMath::Clamp((H.Action->GetPlayLength()-H.ActionTime)/.035f,0.f,1.f)):0;
    const bool QuickAction=IsQuickCombatClip(Index);
    if(QuickAction)H.Anim->ActionAlpha=FMath::Min(FMath::Clamp(H.ActionTime/.025f,0.f,1.f),
        QuickCombatRecovery::RemainingWeight(H.ActionTime,H.Action->GetPlayLength(),DualPistolQuickCombatMotion::IdleHandoffStart));
    const bool FireAction=H.Action && (H.Action==H.Clips.FindRef(TEXT("fire")) || H.Action==H.Clips.FindRef(TEXT("fire_last")));
    H.Anim->bDualPistolAim=true;H.Anim->DualPistolSide=Index;
    H.Anim->DualPistolAimTargetWorld=AimTargetWorld;
    H.Anim->DualPistolAimAlpha=Visible && !(Index==1 && Cast)
        ?(1-H.Sprint)*(1-Player->NearWallAlpha)*(1-Player->DodgePresentationWeight())*(FireAction?1.f:1-H.Anim->ActionAlpha):0.f;
    H.Anim->bRevolver=H.Revolver;H.Anim->RevolverLiveRounds=H.Rounds;H.Anim->RevolverCartridges=H.Cases;
    // Fade the final step out/in with the camera and rifle instead of dropping
    // the arm offset to zero on takeoff or restoring its full value on landing.
    const float Walk=Player->GroundLocomotionWeight*(1-H.Sprint);
    const float HandPhase=Phase+(Index?PI:0);
    FVector Offset(-Player->NearWallAlpha*12,0,-Player->NearWallAlpha*6);
    Offset+=FVector(-2,0,-6)*Player->DodgePresentationWeight();
    if(!H.Action)Offset+=FVector(.10f*FMath::Sin(2*HandPhase)*Walk,.24f*FMath::Cos(HandPhase)*Walk,.15f*FMath::Sin(Clock*1.9f)*(1-H.Sprint)-.24f*FMath::Cos(2*HandPhase)*Walk);
    // Shot recoil: one spring set per hand, sampled through the same
    // camera-space conversion as the single-pistol rig and mirrored for the left
    // hand. The authored fire clip and the ballistic pattern stay untouched.
    Player->AdvanceDualWieldHandRecoil(Index,H.Revolver,H.Stats.Handling,Delta);
    FVector KickOffset,KickAngles;Player->GetDualWieldHandRecoil(Index,KickOffset,KickAngles);
    const float SecondaryWeight=QuickAction?1.f-H.Anim->ActionAlpha:1.f;
    Offset*=SecondaryWeight;KickOffset*=SecondaryWeight;KickAngles*=SecondaryWeight;
    const float Mirror=Index?-1.f:1.f;
    Offset+=FVector(-KickOffset.Z*100.f,KickOffset.X*100.f*Mirror,KickOffset.Y*100.f);
    FRotator Rotation(0,-90,0);
    Rotation.Pitch+=FMath::RadiansToDegrees(KickAngles.X);
    Rotation.Yaw-=FMath::RadiansToDegrees(KickAngles.Y)*Mirror;
    Rotation.Roll-=FMath::RadiansToDegrees(KickAngles.Z)*Mirror;
    FQuat PoseRotation=Rotation.Quaternion();
    Player->ApplyWeaponCrouchPose(Offset,PoseRotation,true,Index==1);
    const FTransform JumpPose=Player->GetWeaponJumpTransform(EFirstPersonJumpRig::Pistol,Index==1);
    Offset=JumpPose.TransformPosition(Offset);PoseRotation=JumpPose.GetRotation()*PoseRotation;
    H.Mesh->SetRelativeLocation(Offset);
    H.Mesh->SetRelativeRotation(PoseRotation);
}
