#include "PistolDualWieldComponent.h"
#include "../FPSGAMECharacter.h"
#include "../FPSGAMEPlayerController.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelPickupStudio.h"
#include "FPSGunplayAnimInstance.h"
#include "FPSWeaponFXComponent.h"
#include "FPSBallisticsComponent.h"
#include "WeaponStatEvaluation.h"
#include "DanWesson715WeaponAssets.h"
#include "TacticalDeviceComponent.h"
#include "../Skills/FPSCastingMeshComponent.h"
#include "../Movement/FPSFootstepAudioComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/AudioComponent.h"
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
    if(!Player || !Player->HasInventoryWeapon() || Player->IsTraversing())return false;
    const auto* PC=Cast<APlayerController>(Player->GetController());
    if(AFPSGAMEPlayerController::BlocksOngoingActions(PC))return false;
    const auto* Health=Player->FindComponentByClass<UFPSCombatHealthComponent>();
    return !Health || !Health->IsDead();
}

void UPistolDualWieldComponent::LoadHand(int32 Index,const FColdSteelItem& Item)
{
    auto& H=Hands[Index];H.Item=Item;H.Revolver=Item.Definition==TEXT("ue_dan_wesson715");
    const FString Base=Root(H.Revolver,Index),Name=Stem(H.Revolver,Index);
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
    auto Clip=[&](const FString& Kind)
    {
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
    H.Sounds.Empty();
    for(const TCHAR* CueName:{TEXT("Fire"),TEXT("DryClick"),TEXT("MagOut"),TEXT("MagInsert"),TEXT("MagSeat"),TEXT("ChargePull"),TEXT("ChargeRelease"),TEXT("Equip")})
    {
        FString Path=H.Revolver?DanWesson715WeaponAssets::SoundPath(CueName)
            :FString(CueName)==TEXT("Fire")?TEXT("/Game/Weapons/M1911/Integrated20260913/Audio/S_M1911_Fire")
            :FString::Printf(TEXT("/Game/Weapons/AKM/Audio/S_AKM_%s"),CueName);
        if(!H.Revolver && FString(CueName).StartsWith(TEXT("Mag")))Path=FString::Printf(TEXT("/Game/Weapons/M4HK416Audio/S_HK416_%s"),CueName);
        if(!H.Revolver && FString(CueName)==TEXT("Equip"))Path=TEXT("/Game/Weapons/M4AnimationAuditFinal/S_HK416_Equip");
        H.Sounds.Add(CueName,LoadObject<USoundBase>(nullptr,*Path));
    }
    H.Sounds.Add(TEXT("BoltRelease"),H.Sounds.FindRef(TEXT("ChargeRelease")));
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

void UPistolDualWieldComponent::RefreshEquipment(UColdSteelStatusModel* Model)
{
    Player=Cast<AFPSGAMECharacter>(GetOwner());Profile=Model;
    if(!Player || !Profile)return;
    const auto* Main=Profile->Equipped();
    const auto* Off=Main?Profile->Equipped(Main->Cell==6?8:11):nullptr;
    const bool Want=Player->HasInventoryWeapon() && Main && Off
        && ColdSteelInventory::IsDualPistol(*Main) && ColdSteelInventory::IsDualPistol(*Off);
    // Autosaves and progression republish the same equipment. An inactive
    // dual-wield controller must not clear the rifle's held trigger or stop
    // the shared main-hand presentation on an unchanged non-dual loadout.
    if(!bActive && !Want)return;
    const bool Changed=Want && (!bActive || Hands[0].Item.InstanceId!=Main->InstanceId || Hands[1].Item.InstanceId!=Off->InstanceId);
    if(!Want || Changed)
    {
        CancelInputs();
        for(int32 Side=0;Side<2;++Side){StopAction(Side);if(Hands[Side].FX)Hands[Side].FX->StopEmission();}
    }
    if(!Want)
    {
        const bool WasActive=bActive;bActive=false;
        for(auto& H:Hands)if(H.Anim){H.Anim->bDualPistolAim=false;H.Anim->DualPistolAimAlpha=0.f;}
        if(Hands[1].Mesh)Hands[1].Mesh->SetVisibility(false,true);
        if(Hands[1].Tactical)Hands[1].Tactical->Configure(TEXT(""),TEXT(""),Hands[1].Mesh,false);
        if(auto* CastMesh=Cast<UFPSCastingMeshComponent>(Player->AKMViewmodel))CastMesh->bApplyLeftHandCast=true;
        if(WasActive && Player->HasInventoryWeapon() && Main && Main->InstanceId==Hands[0].Item.InstanceId)
        {
            Player->InitializeWeaponVisuals();Player->ApplyColdSteelProfile(Profile);Player->StartEquipCharge();
        }
        return;
    }
    bActive=true;
    if(Changed)
    {
        Player->StopMechanicalAudio();Player->ActiveActionAnimation=nullptr;
        Player->WeaponState=EAKMWeaponState::Idle;Player->WeaponStateElapsed=Player->WeaponStateDuration=0;
        Player->bReloadAfterCasting=Player->bRevolverReloadAfterFire=Player->bPistolShotPending=false;
        Player->bAimHeld=false;Player->SetAimingState(false);
        Player->ADSProgress=Player->WeaponADSFactor=Player->CameraADSFactor=0;
        Player->WeaponFX->StopEmission();
        LoadHand(0,*Main);LoadHand(1,*Off);
    }
    auto* G=Player->GetGameInstance()->GetSubsystem<UGunsmithSystem>();
    for(int32 Side=0;Side<2;++Side)
    {
        auto& H=Hands[Side];H.Item=Side?*Off:*Main;
        const auto Parts=G->Installed(H.Item);
        H.Stats=G->Calculate(H.Item.Definition,Parts);
        H.Stats.Damage=ColdSteelWeaponStats::Damage(H.Item,Profile,H.Stats.Damage);
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
    Player->MagazineAmmo=Hands[0].Rounds;Player->RevolverCaseCount=Hands[0].Cases;
    if(Changed)UpdateAimTarget(0.f);
    Pose(0,0);Pose(1,0);
}

void UPistolDualWieldComponent::CopyLeftAttachments(const FColdSteelItem& Item,const FGunsmithParts& Parts)
{
    for(auto& C:LeftAttachments)if(C)C->DestroyComponent();LeftAttachments.Empty();
    bool Created=false;
    auto* Rig=Player->GetGameInstance()->GetSubsystem<UColdSteelPickupStudio>()->Acquire(Item.Definition,Created);
    if(!Rig)return;
    if(Created){Rig->bUseM4Infima=Rig->bUseQBZ191=false;Rig->bUseM1911=!Hands[1].Revolver;Rig->bUseDanWesson715=Hands[1].Revolver;Rig->InitializeWeaponVisuals();}
    Rig->SetGunsmithOpticVariant(Parts.FindRef(TEXT("optic")));Rig->SetGunsmithMuzzle(Parts.FindRef(TEXT("muzzle")));
    Rig->SetGunsmithRearGrip(Parts.FindRef(TEXT("reargrip")));Rig->SetGunsmithTactical(TEXT(""));
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
    Hands[1].Tactical->Configure(Hands[1].Revolver?TEXT("DanWesson715"):TEXT("M1911"),Parts.FindRef(TEXT("tactical")),Hands[1].Mesh,true);
    Hands[1].Sounds.Add(TEXT("Suppressed"),Rig->SuppressedFireSound);
    Hands[0].Sounds.Add(TEXT("Suppressed"),Player->SuppressedFireSound);
}

void UPistolDualWieldComponent::StartAction(int32 Index,const FString& Name,float Rate)
{
    auto& H=Hands[Index];H.Action=H.Clips.FindRef(Name);H.ActionTime=0;H.ActionRate=Rate;H.ActionStarted=GetWorld()->GetTimeSeconds();H.PlayedCues.Empty();
}
void UPistolDualWieldComponent::StopAction(int32 Index)
{
    auto& H=Hands[Index];H.Action=nullptr;H.Reloading=H.ReloadQueued=false;
    for(auto& Voice:H.Voices)if(IsValid(Voice))Voice->Stop();H.Voices.Empty();
}
void UPistolDualWieldComponent::CancelInputs()
{
    for(auto& H:Hands)H.Held=H.Pending=false;
    if(Player)Player->bFireHeld=false;
}
void UPistolDualWieldComponent::Trigger(int32 Index,bool Pressed)
{
    if(!bActive)return;
    auto& H=Hands[Index];
    if(!Pressed){H.Held=H.Pending=false;Player->bFireHeld=Hands[0].Held || Hands[1].Held;return;}
    if(!InputAvailable() || (Index==1 && Player->IsCastBlockingLeftHandAction()))return;
    if(!H.Held)H.Pending=true;H.Held=true;Player->bFireHeld=true;
    Player->ExitSprintForWeapon();
    if(H.Action==H.Clips.FindRef(TEXT("equip")))H.Action=nullptr;
    TryFire(Index);
}
int32 UPistolDualWieldComponent::Reserve(int32 Index) const
{
    return Profile?Profile->AmmoCountFor(Hands[Index].Item):0;
}
void UPistolDualWieldComponent::SyncInventory(TArray<FColdSteelItem>& Items) const
{
    if(!bActive)return;
    for(const auto& H:Hands)for(auto& I:Items)if(I.InstanceId==H.Item.InstanceId)
    {
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
    if(const auto* Steps=Player->FindComponentByClass<UFPSFootstepAudioComponent>())Phase=Steps->GetStridePhaseRadians();
    // Hold the last running stroke during recovery. The footstep clock resets
    // its partial step when stationary; that reset must not flip the raised guns.
    if(Player->IsSprinting() && Player->GetCharacterMovement()->IsMovingOnGround() && Player->HorizontalSpeed()>15.f)
        SprintPhase=Phase;
    if(!InputAvailable())
    {
        CancelInputs();
        // Menus suspend input, while already started reloads retain their clock.
        if(Player->IsTraversing())for(int32 Side=0;Side<2;++Side)StopAction(Side);
        if(const auto* H=Player->FindComponentByClass<UFPSCombatHealthComponent>();H && H->IsDead())for(int32 Side=0;Side<2;++Side)StopAction(Side);
    }
    for(int32 Side=0;Side<2;++Side)
    {
        // Bloom follows the single-weapon contract: rise per shot, recover only
        // after the hand actually stops firing. The old continuous 0.028/s decay
        // outran the 0.003 rise at both pistol cadences (0.18 s and 0.32 s), so
        // sustained fire could never open the cone and the reticle only blipped
        // per shot. The hold scales with this hand's own cadence, so a fast pistol
        // and a slow revolver both reach full bloom in a few seconds of fire.
        auto& H=Hands[Side];
        const float Hold=FMath::Max(.12f,float(H.Stats.Interval)*DualPistolSpread::BloomHold);
        const float Recovery=FMath::Clamp(float(GetWorld()->GetTimeSeconds()-H.LastShot-Hold),0.f,Delta);
        H.Bloom=FMath::Max(0.f,H.Bloom-Recovery*DualPistolSpread::BloomRecovery);
        if(H.Action)
        {
            const float Previous=H.ActionTime/FMath::Max(.001f,H.Action->GetPlayLength())*H.SourceLength;
            H.ActionTime=FMath::Max(H.ActionTime,float(GetWorld()->GetTimeSeconds()-H.ActionStarted)*H.ActionRate);
            if(H.Reloading)AdvanceReload(Side,Previous);
            if(H.Action && H.ActionTime>=H.Action->GetPlayLength())
            {
                const bool Queued=H.ReloadQueued;StopAction(Side);H.ReloadQueued=Queued;
            }
        }
        if(InputAvailable() && !H.Action && (H.ReloadQueued || (H.Rounds==0 && Player->HasInfiniteReserveAmmo())))BeginReload(Side);
        TryFire(Side);Pose(Side,Delta);
    }
    Player->MagazineAmmo=Hands[0].Rounds;Player->RevolverCaseCount=Hands[0].Cases;
    Player->ReserveAmmo=Reserve(0);
}

void UPistolDualWieldComponent::Pose(int32 Index,float Delta)
{
    auto& H=Hands[Index];if(!H.Mesh || !H.Anim)return;
    const bool Cast=Player->IsCastingWithLeftHand();
    const bool Visible=!Player->IsTraversing() && Player->HasInventoryWeapon();
    H.Mesh->SetVisibility(Visible);
    if(Index==1)
    {
        if(Cast)H.Mesh->HideBoneByName(TEXT("WPN_root"),EPhysBodyOp::PBO_None);
        else H.Mesh->UnHideBoneByName(TEXT("WPN_root"));
        for(auto& C:LeftAttachments)if(C)C->SetVisibility(Visible && !Cast);
        if(H.Tactical)H.Tactical->SetPresentationHidden(Cast || !Visible);
    }
    const bool Running=Player->IsSprinting() && Player->GetCharacterMovement()->IsMovingOnGround()
        && Player->HorizontalSpeed()>15.f && !Player->IsSliding() && !H.Action && !Cast;
    // Finite ease-in/out: lift over 0.24 s and settle within the existing
    // sprint-to-fire window. An interrupted lift resumes from its current pose.
    const float BlendDuration=Running?.24f:FMath::Max(.01f,FMath::Min(.16f,Player->SprintToFireDuration));
    H.SprintBlend=FMath::FInterpConstantTo(H.SprintBlend,Running?1.f:0.f,Delta,1.f/BlendDuration);
    const float U=H.SprintBlend;
    H.Sprint=U*U*U*(U*(U*6.f-15.f)+10.f);
    const bool Empty=!H.Revolver && H.Rounds==0;
    H.Anim->IdleClip=H.Clips.FindRef(Empty?TEXT("idle_empty"):TEXT("idle"));H.Anim->AimClip=H.Anim->IdleClip;
    H.Anim->AimAlpha=0;H.Anim->BaseTime=Clock;
    H.Anim->SprintClip=H.Clips.FindRef(Empty?TEXT("sprint_empty"):TEXT("sprint"));
    H.Anim->SprintTime=H.Anim->SprintClip?SprintPhase/(2.f*PI)*H.Anim->SprintClip->GetPlayLength():0.f;
    H.Anim->SprintAlpha=H.Sprint;
    H.Anim->ActionClip=H.Action;H.Anim->ActionTime=H.ActionTime;
    H.Anim->ActionAlpha=H.Action?FMath::Min(FMath::Clamp(H.ActionTime/.025f,0.f,1.f),FMath::Clamp((H.Action->GetPlayLength()-H.ActionTime)/.035f,0.f,1.f)):0;
    const bool FireAction=H.Action && (H.Action==H.Clips.FindRef(TEXT("fire")) || H.Action==H.Clips.FindRef(TEXT("fire_last")));
    H.Anim->bDualPistolAim=true;H.Anim->DualPistolSide=Index;
    H.Anim->DualPistolAimTargetWorld=AimTargetWorld;
    H.Anim->DualPistolAimAlpha=Visible && !(Index==1 && Cast)
        ?(1-H.Sprint)*(1-Player->NearWallAlpha)*(1-Player->DodgePresentationWeight())*(FireAction?1.f:1-H.Anim->ActionAlpha):0.f;
    H.Anim->bRevolver=H.Revolver;H.Anim->RevolverLiveRounds=H.Rounds;H.Anim->RevolverCartridges=H.Cases;
    const float Walk=Player->GetCharacterMovement()->IsMovingOnGround() && !Player->IsSliding()
        ?FMath::Clamp(Player->HorizontalSpeed()/Player->WalkSpeed,0.f,1.f)*(1-H.Sprint):0;
    const float HandPhase=Phase+(Index?PI:0);
    FVector Offset(-Player->NearWallAlpha*12,0,Player->LandingOffset*.35f-Player->NearWallAlpha*6);
    Offset+=FVector(-2,0,-6)*Player->DodgePresentationWeight();
    if(!H.Action)Offset+=FVector(.10f*FMath::Sin(2*HandPhase)*Walk,.24f*FMath::Cos(HandPhase)*Walk,.15f*FMath::Sin(Clock*1.9f)*(1-H.Sprint)-.24f*FMath::Cos(2*HandPhase)*Walk);
    // Shot recoil: one spring set per hand, sampled through the same
    // camera-space conversion as the single-pistol rig and mirrored for the left
    // hand. The authored fire clip and the ballistic pattern stay untouched.
    Player->AdvanceDualWieldHandRecoil(Index,H.Revolver,H.Stats.Handling,Delta);
    FVector KickOffset,KickAngles;Player->GetDualWieldHandRecoil(Index,KickOffset,KickAngles);
    const float Mirror=Index?-1.f:1.f;
    Offset+=FVector(-KickOffset.Z*100.f,KickOffset.X*100.f*Mirror,KickOffset.Y*100.f);
    FRotator Rotation(0,-90,0);
    Rotation.Pitch+=FMath::RadiansToDegrees(KickAngles.X);
    Rotation.Yaw-=FMath::RadiansToDegrees(KickAngles.Y)*Mirror;
    Rotation.Roll-=FMath::RadiansToDegrees(KickAngles.Z)*Mirror;
    H.Mesh->SetRelativeLocation(Offset);
    H.Mesh->SetRelativeRotation(Rotation);
}
