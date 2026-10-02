#include "FPSBlizzardComponent.h"
#include "FPSBlizzardZone.h"
#include "FPSFireballComponent.h"
#include "FireMagicArea.h"
#include "../FPSGAMECharacter.h"
#include "../FPSGAMEPlayerController.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Building/VoxelBuildComponent.h"
#include "../Weapons/RuneSwordComponent.h"
#include "../Weapons/Staff/StaffWeaponComponent.h"
#include "../Weapons/Staff/StaffChargeFlow.h"
#include "Camera/CameraComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"
#include "Components/DecalComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "NiagaraComponent.h"
#include "NiagaraFunctionLibrary.h"
#include "NiagaraSystem.h"

UFPSBlizzardComponent::UFPSBlizzardComponent(){PrimaryComponentTick.bCanEverTick=true;PrimaryComponentTick.TickGroup=TG_PostUpdateWork;}
void UFPSBlizzardComponent::BeginPlay()
{
    Super::BeginPlay();AddTickPrerequisiteActor(GetOwner());
    if(auto* Sword=GetOwner()->FindComponentByClass<URuneSwordComponent>())AddTickPrerequisiteComponent(Sword);
    const TCHAR* Paths[]={TEXT("/Game/Skills/Blizzard/ChargedV3/NS_BlizzardStormCloud.NS_BlizzardStormCloud"),TEXT("/Game/Skills/Blizzard/ChargedV3/NS_BlizzardPrecipitation.NS_BlizzardPrecipitation"),
        TEXT("/Game/Skills/Blizzard/ChargedV3/NS_BlizzardBoundaryMist.NS_BlizzardBoundaryMist"),TEXT("/Game/Skills/Blizzard/ChargedV3/M_BlizzardIceHeart.M_BlizzardIceHeart"),
        TEXT("/Game/Skills/IceSpike/SM_IceShard.SM_IceShard"),TEXT("/Game/Skills/IceSpike/FrostV2/SM_IceSpike_01.SM_IceSpike_01"),
        TEXT("/Game/Skills/Blizzard/ChargedV3/M_BlizzardIceShell.M_BlizzardIceShell"),TEXT("/Game/Skills/Blizzard/ChargedV3/M_BlizzardGroundFrost.M_BlizzardGroundFrost"),
        TEXT("/Game/Skills/IceWall/BlockV1/S_IceWallCast.S_IceWallCast"),TEXT("/Game/Skills/IceSpike/S_IceImpact.S_IceImpact"),
        TEXT("/Game/Skills/Blizzard/StormV2/S_BlizzardIceLanding.S_BlizzardIceLanding"),
        TEXT("/Game/Skills/Blizzard/ChargedV3/NS_BlizzardGatherCloud.NS_BlizzardGatherCloud"),
        TEXT("/Game/Skills/Blizzard/ChargedV3/M_BlizzardAimPreview.M_BlizzardAimPreview"),
        TEXT("/Game/Skills/IceSpike/FrostV2/SM_IceSpike_02.SM_IceSpike_02"),TEXT("/Game/Skills/IceSpike/FrostV2/SM_IceSpike_03.SM_IceSpike_03")};
    TArray<FSoftObjectPath> Requests;for(const TCHAR* Path:Paths)Requests.Emplace(Path);
    AssetLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(Requests,FStreamableDelegate::CreateWeakLambda(this,[this,Requests]()
    {
        bAssetsReady=true;for(const auto& Path:Requests){UObject* Asset=Path.ResolveObject();bAssetsReady&=Asset!=nullptr;Assets.Add(Asset);}
    }));
}
UColdSteelStatusModel* UFPSBlizzardComponent::Model() const
{return GetWorld()&&GetWorld()->GetGameInstance()?GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;}
UFPSFireballComponent* UFPSBlizzardComponent::Hands() const{return GetOwner()->FindComponentByClass<UFPSFireballComponent>();}
bool UFPSBlizzardComponent::InputAvailable() const
{
    const auto* P=Cast<AFPSGAMECharacter>(GetOwner());const auto* PC=P?Cast<APlayerController>(P->GetController()):nullptr;
    if(!PC||PC->bShowMouseCursor||PC->IsMoveInputIgnored()||PC->IsLookInputIgnored()||AFPSGAMEPlayerController::BlocksOngoingActions(PC)||P->IsChoosingAmmo())return false;
    const auto* Builder=PC->FindComponentByClass<UVoxelBuildComponent>();return !Builder||!Builder->IsBuilding();
}
void UFPSBlizzardComponent::Feedback(const FString& Text){Message=Text;MessageUntil=GetWorld()->GetTimeSeconds()+1.6;}
bool UFPSBlizzardComponent::IsHandOccupiedNotice() const
{const auto* P=Cast<AFPSGAMECharacter>(GetOwner());return P&&P->IsSpellHandHeld()&&GetWorld()&&HandNotice.Active(GetWorld()->GetTimeSeconds());}
float UFPSBlizzardComponent::HandNoticeAlpha() const{return GetWorld()?HandNotice.Alpha(GetWorld()->GetTimeSeconds()):0;}
float UFPSBlizzardComponent::HandNoticeRise() const{return GetWorld()?HandNotice.Rise(GetWorld()->GetTimeSeconds()):0;}
float UFPSBlizzardComponent::CooldownFraction() const
{const auto* M=Model();return M&&!bCommitted?FMath::Clamp(M->BlizzardCooldown()/FMath::Max(.1f,M->BlizzardCooldownDuration()),0.f,1.f):0;}
FString UFPSBlizzardComponent::StatusText() const
{
    if(IsHandOccupiedNotice())return TEXT("左手占用");
    if(GetWorld()->GetTimeSeconds()<MessageUntil)return Message;
    if(bCommitted)
    {
        if(!bGathered)return TEXT("凝聚");
        if(bReleaseRequested)return TEXT("释放");
        if(bAimPreview)return bPreviewValid?TEXT("选择落点"):PreviewFailure;
        return TEXT("释放");
    }
    if(bQueued)return TEXT("等待施法");
    if(const auto* M=Model();M&&M->BlizzardCooldown()>0)return FString::Printf(TEXT("%.1f"),M->BlizzardCooldown());
    return TEXT("");
}
bool UFPSBlizzardComponent::Allowed(const FBlizzardCast& Spell,FString& Failure) const
{
    const auto* M=Model();if(!M)return false;
    if(Spell.bRequiresStaff&&!M->HasEquippedStaff()){Failure=TEXT("需要法杖");return false;}
    if(M->BlizzardCooldown()>0){Failure=TEXT("冷却");return false;}
    if(!M->CanSpendMana(Spell.ManaCost)){Failure=TEXT("缺蓝");return false;}
    if(!bAssetsReady){Failure=TEXT("冰雪素材加载中");return false;}
    if(Zones.Num()>=4){Failure=TEXT("暴风雪数量上限");return false;}
    return true;
}
bool UFPSBlizzardComponent::SelectGround(const FBlizzardCast& Spell,FString& Failure)
{
    const auto* Camera=GetOwner()->FindComponentByClass<UCameraComponent>();auto* P=Cast<APawn>(GetOwner());if(!Camera||!P)return false;
    FHitResult Hit;
    // Skip creature bodies so the locked point is the ground beneath the crosshair.
    if(!FireMagic::TraceSurface(P,Camera->GetComponentLocation(),Camera->GetComponentLocation()+Camera->GetForwardVector()*(Spell.Range+250),Hit))
    {Failure=TEXT("准星未指向地面");return false;}
    if(Hit.ImpactNormal.Z<.45f){Failure=TEXT("需要可落地表面");return false;}
    if(FVector::Dist2D(P->GetActorLocation(),Hit.ImpactPoint)>Spell.Range){Failure=TEXT("超出施法距离");return false;}
    LockedPoint=Hit.ImpactPoint;LockedNormal=Hit.ImpactNormal;
    LockedAxis=FVector::VectorPlaneProject(Camera->GetRightVector(),LockedNormal).GetSafeNormal();
    if(LockedAxis.IsNearlyZero()){FVector Other;LockedNormal.FindBestAxisVectors(LockedAxis,Other);}
    return true;
}
void UFPSBlizzardComponent::Trigger()
{
    auto* P=Cast<AFPSGAMECharacter>(GetOwner());auto* M=Model();
    if(!P||!M||!P->IsLocallyControlled()||GetWorld()->GetNetMode()!=NM_Standalone||!InputAvailable())return;
    if(const auto* Health=P->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())return;
    if(const auto* H=Hands();H&&H->HasOtherPreparedSpell(this))
    {bQueued=false;Feedback(TEXT("先释放已积蓄魔法"));return;}
    if(P->IsSpellHandHeld()){bQueued=false;HandNotice.Show(GetWorld()->GetTimeSeconds());return;}
    if(bCommitted)
    {
        if(bReleaseRequested)return;
        FString Failure;
        if(!SelectGround(CastSnapshot,Failure)){Feedback(Failure);return;}
        bReleaseRequested=true;SetAimPreview(false);ServiceQueue();return;
    }
    FString Failure;if(!Allowed(M->BlizzardStats(),Failure)){Feedback(Failure);return;}
    if(auto* Sword=P->FindComponentByClass<URuneSwordComponent>();Sword&&Sword->IsGuarding())Sword->ReleaseGuard();
    bQueued=true;MessageUntil=0;ServiceQueue();
}
void UFPSBlizzardComponent::ServiceQueue()
{
    if(!bQueued&&!bReleaseRequested)return;
    auto* P=Cast<AFPSGAMECharacter>(GetOwner());auto* M=Model();auto* H=Hands();if(!P||!M||!H)return;
    if(H->HasOtherPreparedSpell(this)){bQueued=bReleaseRequested=false;Feedback(TEXT("先释放已积蓄魔法"));return;}
    if(!InputAvailable()){SuspendPreview();return;}
    if(P->IsSpellHandHeld()){bQueued=bReleaseRequested=false;HandNotice.Show(GetWorld()->GetTimeSeconds());return;}
    if(H->BlocksNewLeftHandAction()||P->IsSpellHandBusy())return;
    if(bQueued)
    {
        const auto Spell=M->BlizzardStats();FString Failure;
        if(!Allowed(Spell,Failure)){bQueued=false;Feedback(Failure);return;}
        if(!H->TryBeginSpellGesture(this,false,Spell.CastSpeed,FSimpleDelegate::CreateUObject(this,&ThisClass::Gathered)))return;
        bQueued=false;const float Before=M->Snapshot().Mana;
        if(!M->BeginBlizzardCast(Spell)){H->CancelSpellGesture(this);return;}
        CastSnapshot=Spell;bCommitted=true;bGathered=bReleaseRequested=false;bStaffCloud=H->IsStaffCasting();
        PaidMana=FMath::Max(0.f,Before-M->Snapshot().Mana);PreparedAge=PreviewAge=0;
        // Like the ice wall, payment belongs to this held spell beyond hand recovery.
        GatherFX=UNiagaraFunctionLibrary::SpawnSystemAtLocation(GetWorld(),Cast<UNiagaraSystem>(Assets[11]),CloudOrigin(),FRotator::ZeroRotator,FVector(1),false,false);
        if(!GatherFX){CancelPending();Feedback(TEXT("乌云凝聚失败"));return;}
        GatherFX->AddTickPrerequisiteComponent(this);GatherFX->SetTickBehavior(ENiagaraTickBehavior::UsePrereqs);GatherFX->SetCastShadow(false);
        UpdateGatherCloud();GatherFX->Activate(true);MessageUntil=0;
        if(auto* Status=P->FindComponentByClass<UCombatStatusFormula>())Status->ConsumeChainSpell();
        return;
    }
    if(bReleaseRequested&&bCommitted&&bGathered)
        H->TryBeginSpellGesture(this,true,CastSnapshot.CastSpeed,FSimpleDelegate::CreateUObject(this,&ThisClass::ReleaseAtContact));
}
void UFPSBlizzardComponent::Gathered(){if(bCommitted){bGathered=true;PreparedAge=0;}}
void UFPSBlizzardComponent::ReleaseAtContact()
{
    if(!bCommitted||!bGathered||!bReleaseRequested)return;
    auto* P=Cast<APawn>(GetOwner());auto* M=Model();const auto* Camera=GetOwner()->FindComponentByClass<UCameraComponent>();FHitResult Hit;
    if(!P||!M||!Camera||!InputAvailable()||(CastSnapshot.bRequiresStaff&&!M->HasEquippedStaff())||
        FVector::Dist2D(P->GetActorLocation(),LockedPoint)>CastSnapshot.Range||
        FireMagic::TraceSurface(P,Camera->GetComponentLocation(),LockedPoint+LockedNormal*12,Hit))
    {bReleaseRequested=false;Feedback(TEXT("落点被遮挡或超距"));return;}
    FActorSpawnParameters Params;Params.Owner=P;Params.Instigator=P;Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    auto* Zone=GetWorld()->SpawnActor<AFPSBlizzardZone>(LockedPoint,FRotator::ZeroRotator,Params);
    if(!Zone||!Zone->InitializeZone(P,CastSnapshot,LockedPoint,LockedNormal,LockedAxis,Assets)||!M->CommitBlizzardRelease())
    {if(Zone)Zone->Destroy();CancelPending();Feedback(TEXT("暴风雪释放失败"));return;}
    bCommitted=bGathered=bReleaseRequested=false;PaidMana=0;SetAimPreview(false);
    if(GatherFX){GatherFX->DestroyComponent();GatherFX=nullptr;}
    Zones.Add(Zone);Zone->ActivateZone();
    UGameplayStatics::PlaySoundAtLocation(this,Cast<USoundBase>(Assets[8]),P->GetActorLocation());
    if(auto* Status=UCombatStatusFormula::GetOrAdd(P))
    {if(CastSnapshot.bGrantChain)Status->AddChainSpell();if(CastSnapshot.CastHasteStacks>0)Status->AddHaste(CastSnapshot.CastHasteStacks,CastSnapshot.CastHasteDuration);}
}
void UFPSBlizzardComponent::CancelPending()
{
    bQueued=bAimPreview=bPreviewValid=bReleaseRequested=bGathered=false;
    if(AimDecal)AimDecal->SetHiddenInGame(true);
    if(GatherFX){GatherFX->DestroyComponent();GatherFX=nullptr;}
    if(bCommitted)
    {
        bCommitted=false;if(auto* M=Model())M->RefundUnreleasedCast(PaidMana,TEXT("blizzard"));
        if(auto* H=Hands())H->CancelSpellGesture(this);
    }
    PaidMana=0;PreparedAge=0;
}
void UFPSBlizzardComponent::InterruptPending(bool bCancelCloud)
{
    if(bCancelCloud||(bCommitted&&!bGathered))CancelPending();
    else SuspendPreview();
}
void UFPSBlizzardComponent::SuspendPreview()
{
    bQueued=bReleaseRequested=false;SetAimPreview(false);
    if(bCommitted&&!bGathered){CancelPending();return;}
    if(auto* H=Hands();H&&H->IsSpellGesture(this))H->CancelSpellGesture(this);
}
void UFPSBlizzardComponent::SetAimPreview(bool bActive)
{
    if(bActive&&(!IsPrepared()||!InputAvailable()))return;
    bAimPreview=bActive;
    if(!bActive){bPreviewValid=false;if(AimDecal)AimDecal->SetHiddenInGame(true);return;}
    MessageUntil=0;PreviewAge=0;RefreshPreview();
}
void UFPSBlizzardComponent::RefreshPreview()
{
    if(!bAimPreview||!IsPrepared())return;
    PreviewFailure.Reset();bPreviewValid=SelectGround(CastSnapshot,PreviewFailure);
    if(!bPreviewValid){if(AimDecal)AimDecal->SetHiddenInGame(true);return;}
    if(!AimDecal)
    {
        AimDecal=NewObject<UDecalComponent>(GetOwner(),TEXT("BlizzardAimDecal"));GetOwner()->AddInstanceComponent(AimDecal);
        AimDecal->SetDecalMaterial(Cast<UMaterialInterface>(Assets[12]));AimDecal->RegisterComponent();AimMID=AimDecal->CreateDynamicMaterialInstance();
    }
    AimDecal->SetWorldLocation(LockedPoint+LockedNormal*8);
    AimDecal->SetWorldRotation(FRotationMatrix::MakeFromXZ(-LockedNormal,FVector::CrossProduct(LockedNormal,LockedAxis)).Rotator());
    const FVector Size(45,CastSnapshot.RadiusX,CastSnapshot.RadiusY);
    if(AimDecal->DecalSize!=Size){AimDecal->DecalSize=Size;AimDecal->MarkRenderStateDirty();}
    AimDecal->SetHiddenInGame(false);
    if(AimMID)AimMID->SetScalarParameterValue(TEXT("Fade"),1.f);
}
void UFPSBlizzardComponent::ReleaseAimPreview()
{
    if(!bAimPreview||!IsPrepared())return;
    const bool Valid=bPreviewValid;const FString Failure=PreviewFailure;SetAimPreview(false);
    if(!Valid){Feedback(Failure);return;}
    // Preserve exactly the displayed position through the release gesture.
    bReleaseRequested=true;ServiceQueue();
}
FVector UFPSBlizzardComponent::CloudOrigin() const
{
    const auto* Camera=GetOwner()->FindComponentByClass<UCameraComponent>();const auto* H=Hands();
    if(!Camera)return GetOwner()->GetActorLocation();
    if(bStaffCloud)
    {
        const auto* Staff=GetOwner()->FindComponentByClass<UStaffWeaponComponent>();
        FVector Focus=StaffCastMotion::Focus(Staff&&Staff->IsEquipped()?
            StaffChargeFlow::Settled(*Staff):StaffCastMotion::Raised());
        if(!bGathered&&H&&H->IsSpellGesture(this)&&H->IsStaffCasting())
            if(Staff&&Staff->IsEquipped())
                Focus=StaffCastMotion::Focus(H->SampleStaffMotion(Staff->CarryPoseInCamera()));
        return Camera->GetComponentTransform().TransformPosition(Focus);
    }
    return H?H->HeldOrbPosition():Camera->GetComponentLocation()+Camera->GetForwardVector()*70;
}
void UFPSBlizzardComponent::UpdateGatherCloud()
{
    if(!GatherFX)return;
    const auto* H=Hands();const auto* Camera=GetOwner()->FindComponentByClass<UCameraComponent>();
    const float Progress=!bGathered&&H&&H->IsSpellGesture(this)?H->HandPhaseFraction():1.f;
    const float Scale=.25f+.75f*FMath::Sqrt(FMath::Clamp(Progress,0.f,1.f));
    const FVector Position=CloudOrigin();FVector Side=Camera?FVector::VectorPlaneProject(Camera->GetRightVector(),FVector::UpVector).GetSafeNormal():FVector::RightVector;
    if(Side.IsNearlyZero())Side=FVector::RightVector;
    GatherFX->SetWorldLocation(Position);
    GatherFX->SetVariablePosition(TEXT("User.CurrentPosition"),Position-FVector(0,0,30*Scale));
    GatherFX->SetVariableVec3(TEXT("User.Side"),Side);GatherFX->SetVariableVec3(TEXT("User.Up"),FVector::CrossProduct(FVector::UpVector,Side));
    GatherFX->SetVariableVec3(TEXT("User.SurfaceNormal"),FVector::UpVector);GatherFX->SetVariableVec3(TEXT("User.Wind"),FVector::ZeroVector);
    GatherFX->SetVariableFloat(TEXT("User.RadiusX"),42*Scale);GatherFX->SetVariableFloat(TEXT("User.RadiusY"),30*Scale);
    GatherFX->SetVariableFloat(TEXT("User.CloudHeight"),60*Scale);
    GatherFX->SetVariableFloat(TEXT("User.StormDuration"),32.f+(H?H->RaiseDuration:.95f)/FMath::Max(.1f,CastSnapshot.CastSpeed));
    GatherFX->SetVariableFloat(TEXT("User.CloudEmission"),1.f);GatherFX->SetVariableFloat(TEXT("User.Strength"),.18f+.82f*Progress);
    GatherFX->SetVariableFloat(TEXT("User.DetailReduction"),0.f);GatherFX->SetSystemFixedBounds(FBox(FVector(-90,-90,-90),FVector(90,90,90)));
}
void UFPSBlizzardComponent::ClearZones(){for(auto& Zone:Zones)if(Zone.IsValid())Zone->Destroy();Zones.Reset();}
void UFPSBlizzardComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);Zones.RemoveAll([](const auto& Z){return !Z.IsValid();});
    const auto* Health=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();
    if(Health&&Health->IsDead()){CancelPending();ClearZones();return;}
    if(!InputAvailable())SuspendPreview();else ServiceQueue();
    if(bCommitted)
    {
        UpdateGatherCloud();
        if(bGathered){PreparedAge+=Delta;if(PreparedAge>=30.f){CancelPending();Feedback(TEXT("凝聚到期"));return;}}
        if(bAimPreview){PreviewAge+=Delta;if(PreviewAge>=.05f){PreviewAge=0;RefreshPreview();}}
    }
}
void UFPSBlizzardComponent::EndPlay(EEndPlayReason::Type Reason)
{CancelPending();ClearZones();if(AimDecal){AimDecal->DestroyComponent();AimDecal=nullptr;AimMID=nullptr;}if(AssetLoad)AssetLoad->CancelHandle();AssetLoad.Reset();Assets.Reset();Super::EndPlay(Reason);}
