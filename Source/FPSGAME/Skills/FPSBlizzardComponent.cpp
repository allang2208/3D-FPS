#include "FPSBlizzardComponent.h"
#include "../Monsters/BoundCongregateCaptureComponent.h"
#include "FPSBlizzardZone.h"
#include "BlizzardEnvironment.h"
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
#include "NetCastUtils.h"

UFPSBlizzardComponent::UFPSBlizzardComponent(){PrimaryComponentTick.bCanEverTick=true;PrimaryComponentTick.TickGroup=TG_PostUpdateWork;}
void UFPSBlizzardComponent::BeginPlay()
{
    Super::BeginPlay();AddTickPrerequisiteActor(GetOwner());
    if(auto* Sword=GetOwner()->FindComponentByClass<URuneSwordComponent>())AddTickPrerequisiteComponent(Sword);
    const TCHAR* const* Paths=AFPSBlizzardZone::ZoneAssetPaths(); // 与远端副本自载共用同一张清单
    TArray<FSoftObjectPath> Requests;for(int32 I=0;I<15;++I)Requests.Emplace(Paths[I]);
    AssetLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(Requests,FStreamableDelegate::CreateWeakLambda(this,[this,Requests]()
    {
        for(const auto& Path:Requests)Assets.Add(Path.ResolveObject());
        bAssetsReady=Assets.Num()==15&&Assets[11]&&Assets[12]&&AFPSBlizzardZone::HasBasicAssets(Assets);
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
    if(!bAssetsReady){Failure=Assets.Num()==15?TEXT("冰雪基础素材不可用"):TEXT("冰雪素材加载中");return false;}
    if(GetWorld()->GetNetMode()==NM_Client&&!NetCast::StateFor(Cast<APawn>(GetOwner())))
    {Failure=TEXT("等待联机角色就绪");return false;}
    if(Zones.Num()>=4){Failure=TEXT("暴风雪数量上限");return false;}
    return true;
}
bool UFPSBlizzardComponent::SelectGround(const FBlizzardCast& Spell,FString& Failure)
{
    const auto* Camera=GetOwner()->FindComponentByClass<UCameraComponent>();auto* P=Cast<APawn>(GetOwner());if(!Camera||!P)return false;
    LockedAxis=Camera->GetRightVector();
    return BlizzardEnvironment::Select(P,Spell.Range,P->GetPawnViewLocation(),P->GetViewRotation().Vector(),
        LockedPoint,LockedNormal,LockedAxis,Failure);
}
void UFPSBlizzardComponent::Trigger()
{
    if(bNetAwaitingRelease||bNetAwaitingCancel)return;
    if(UBoundCongregateCaptureComponent::IsCaptured(GetOwner()))return;
    auto* P=Cast<AFPSGAMECharacter>(GetOwner());auto* M=Model();
    if(!P||!M||!P->IsLocallyControlled()||!InputAvailable())return;
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
    if(bNetAwaitingRelease||bNetAwaitingCancel)return;
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
        // 联机客人：凝聚云/预览是本地表现；权威暴风雪区由服务端生成复制回来。
        if(GetWorld()->GetNetMode()==NM_Client){bNetPaid=true;bNetPrepared=false;NetCast::Send(P,TEXT("blizzard"),0);}
        return;
    }
    if(bReleaseRequested&&bCommitted&&bGathered&&(GetWorld()->GetNetMode()!=NM_Client||bNetPrepared))
        H->TryBeginSpellGesture(this,true,CastSnapshot.CastSpeed,FSimpleDelegate::CreateUObject(this,&ThisClass::ReleaseAtContact));
}
void UFPSBlizzardComponent::Gathered(){if(bCommitted){bGathered=true;PreparedAge=0;}}
void UFPSBlizzardComponent::ReleaseAtContact()
{
    if(!bCommitted||!bGathered||!bReleaseRequested||bNetAwaitingRelease)return;
    auto* P=Cast<APawn>(GetOwner());auto* M=Model();
    if(!P||!M||!InputAvailable()||(CastSnapshot.bRequiresStaff&&!M->HasEquippedStaff()))
    {bReleaseRequested=false;Feedback(TEXT("当前无法施法"));return;}
    FString Failure;
    if(!ValidateGround(P,CastSnapshot,LockedPoint,LockedNormal,LockedAxis,Failure))
    {bReleaseRequested=false;Feedback(Failure);return;}
    // Keep the reservation until the authoritative receipt: rejection must still refund it.
    if(GetWorld()->GetNetMode()==NM_Client)
    {
        bNetAwaitingRelease=true;SetAimPreview(false);
        if(GatherFX)GatherFX->SetVisibility(false);
        NetCast::Send(P,TEXT("blizzard"),1,LockedPoint,LockedNormal,0,nullptr,0.f,LockedAxis);
        return;
    }
    Zones.RemoveAll([](const auto& Z){return !Z.IsValid();});
    if(Zones.Num()>=4){bReleaseRequested=false;Feedback(TEXT("暴风雪数量上限"));return;}
    FActorSpawnParameters Params;Params.Owner=P;Params.Instigator=P;Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    auto* Zone=GetWorld()->SpawnActor<AFPSBlizzardZone>(LockedPoint,FRotator::ZeroRotator,Params);
    if(!Zone||!Zone->InitializeZone(P,CastSnapshot,LockedPoint,LockedNormal,LockedAxis,Assets)||!M->CommitBlizzardRelease())
    {if(Zone)Zone->Destroy();CancelPending();Feedback(TEXT("暴风雪释放失败"));return;}
    Zones.Add(Zone);Zone->ActivateZone();
    CompleteRelease();
}
void UFPSBlizzardComponent::CompleteRelease()
{
    bCommitted=bGathered=bReleaseRequested=bNetPaid=bNetPrepared=bNetAwaitingRelease=false;
    PaidMana=0;PreparedAge=0;SetAimPreview(false);
    if(GatherFX){GatherFX->DestroyComponent();GatherFX=nullptr;}
    auto* P=Cast<APawn>(GetOwner());if(!P)return;
    UGameplayStatics::PlaySoundAtLocation(this,Cast<USoundBase>(Assets[8]),P->GetActorLocation());
    if(auto* Status=UCombatStatusFormula::GetOrAdd(P))
    {if(CastSnapshot.bGrantChain)Status->AddChainSpell();if(CastSnapshot.CastHasteStacks>0)Status->AddHaste(CastSnapshot.CastHasteStacks,CastSnapshot.CastHasteDuration);}
}
void UFPSBlizzardComponent::CancelPending()
{
    bQueued=bAimPreview=bPreviewValid=bReleaseRequested=bGathered=false;
    if(AimDecal)AimDecal->SetHiddenInGame(true);
    if(GatherFX){GatherFX->DestroyComponent();GatherFX=nullptr;}
    if(auto* H=Hands())H->CancelSpellGesture(this);
    // Phase 1 has already left this client. Its receipt owns commit/refund even
    // if the player dies or opens a menu before that receipt arrives.
    if(bNetAwaitingRelease)return;
    if(bCommitted)
    {
        bCommitted=false;if(auto* M=Model())M->RefundUnreleasedCast(PaidMana,TEXT("blizzard"));
        // 联机客人：把已扣账的凝聚取消上报，服务端同口径退预留。
        if(GetWorld()&&GetWorld()->GetNetMode()==NM_Client&&bNetPaid)
        {bNetAwaitingCancel=true;NetCast::Send(GetOwner(),TEXT("blizzard"),2);}
    }
    bNetPaid=bNetPrepared=false;
    PaidMana=0;PreparedAge=0;
}
bool UFPSBlizzardComponent::ValidateGround(APawn* Caster,const FBlizzardCast& Spell,FVector& Point,FVector& Normal,FVector& Axis,FString& Failure) const
{
    return BlizzardEnvironment::Validate(Caster,Spell.Range,Point,Normal,Axis,Failure);
}
// ── 联机服务端入口：客人上报落点→重验→权威暴风雪区生成（复制回各端） ──
bool UFPSBlizzardComponent::NetCommitZone(APawn* Caster,const FColdSteelNetCastRequest& Req,UColdSteelStatusModel* Shadow,const FBlizzardCast& Spell)
{
    Zones.RemoveAll([](const auto& Z){return !Z.IsValid();});
    if(!Caster||!Caster->HasAuthority()||!Shadow||!bAssetsReady||Zones.Num()>=4||
        (Spell.bRequiresStaff&&!Shadow->HasEquippedStaff()))return false;
    FVector Point=Req.AimPoint,Normal=Req.AimNormal,Axis=Req.AimAxis;
    FString Failure;if(!ValidateGround(Caster,Spell,Point,Normal,Axis,Failure))return false;
    FActorSpawnParameters Params;Params.Owner=Caster;Params.Instigator=Caster;Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    auto* Zone=GetWorld()->SpawnActor<AFPSBlizzardZone>(Point,FRotator::ZeroRotator,Params);
    if(!Zone||!Zone->InitializeZone(Caster,Spell,Point,Normal,Axis,Assets)||!Shadow->CommitBlizzardRelease())
    {if(Zone)Zone->Destroy();return false;}
    Zones.Add(Zone);Zone->ActivateZone();
    if(auto* Status=UCombatStatusFormula::GetOrAdd(Caster))
    {if(Spell.bGrantChain)Status->AddChainSpell();if(Spell.CastHasteStacks>0)Status->AddHaste(Spell.CastHasteStacks,Spell.CastHasteDuration);}
    return true;
}
void UFPSBlizzardComponent::NetCastAccepted(uint8 Phase)
{
    if(Phase==0){if(bNetPaid&&!bNetAwaitingCancel)bNetPrepared=true;return;}
    if(Phase!=1||!bNetAwaitingRelease)return;
    // A profile mirror may already have committed the same reservation.
    if(auto* M=Model();M&&M->Snapshot().bBlizzardReserved)M->CommitBlizzardRelease();
    CompleteRelease();
}
void UFPSBlizzardComponent::NetCastRejected(uint8 Phase,uint8 /*Code*/)
{
    if(bNetAwaitingCancel&&Phase<2)return; // The ordered cancel receipt still owns this slot.
    if(!bNetPaid&&!bNetAwaitingRelease&&!bNetAwaitingCancel)return;
    bNetPaid=bNetAwaitingRelease=bNetAwaitingCancel=false;
    CancelPending();Feedback(TEXT("施法失败，已退还消耗"));
}
void UFPSBlizzardComponent::NetCastCancelled(uint8 /*Phase*/)
{
    bNetAwaitingCancel=false;
}
void UFPSBlizzardComponent::InterruptPending(bool bCancelCloud)
{
    if(bCancelCloud||(bCommitted&&!bGathered))CancelPending();
    else SuspendPreview();
}
void UFPSBlizzardComponent::SuspendPreview()
{
    if(bNetAwaitingRelease){SetAimPreview(false);return;}
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
    AimDecal->SetWorldLocation(LockedPoint+FVector(0,0,8));
    AimDecal->SetWorldRotation(FRotationMatrix::MakeFromXZ(-FVector::UpVector,FVector::CrossProduct(FVector::UpVector,LockedAxis)).Rotator());
    const FVector Size(900,CastSnapshot.RadiusX,CastSnapshot.RadiusY);
    if(AimDecal->DecalSize!=Size){AimDecal->DecalSize=Size;AimDecal->MarkRenderStateDirty();}
    AimDecal->SetHiddenInGame(false);
    if(AimMID)
    {
        TArray<FVector> Cells;
        BlizzardEnvironment::BuildCells(Cast<APawn>(GetOwner()),LockedPoint,LockedAxis,CastSnapshot.RadiusX,CastSnapshot.RadiusY,Cells);
        BlizzardEnvironment::MaterialCells(AimMID,LockedPoint,LockedAxis,CastSnapshot.RadiusX,CastSnapshot.RadiusY,Cells);
        AimMID->SetScalarParameterValue(TEXT("Fade"),1.f);
    }
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
    if(bCommitted&&!bNetAwaitingRelease)
    {
        UpdateGatherCloud();
        if(bGathered){PreparedAge+=Delta;if(PreparedAge>=30.f){CancelPending();Feedback(TEXT("凝聚到期"));return;}}
        if(bAimPreview){PreviewAge+=Delta;if(PreviewAge>=.2f){PreviewAge=0;RefreshPreview();}}
    }
}
void UFPSBlizzardComponent::EndPlay(EEndPlayReason::Type Reason)
{
    // A sent release can already be dealing authoritative damage. Do not leave
    // a refundable held-cloud save behind when its pawn disappears before ACK.
    // A rejected request is refunded in the server profile and mirrored back.
    if(bNetAwaitingRelease)
    {
        if(auto* M=Model();M&&M->Snapshot().bBlizzardReserved)M->CommitBlizzardRelease();
        bCommitted=bNetPaid=bNetAwaitingRelease=false;
    }
    CancelPending();ClearZones();
    if(AimDecal){AimDecal->DestroyComponent();AimDecal=nullptr;AimMID=nullptr;}
    if(AssetLoad)AssetLoad->CancelHandle();AssetLoad.Reset();Assets.Reset();Super::EndPlay(Reason);
}
