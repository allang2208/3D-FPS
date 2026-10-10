#include "FPSIceWallComponent.h"
#include "../Monsters/BoundCongregateCaptureComponent.h"
#include "NetCastUtils.h"
#include "FPSIceWall.h"
#include "IceWallPlacement.h"
#include "FPSFireballComponent.h"
#include "../FPSGAMECharacter.h"
#include "../FPSGAMEPlayerController.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Building/VoxelBuildComponent.h"
#include "../Weapons/Staff/StaffWeaponComponent.h"
#include "../Weapons/Staff/StaffChargeFlow.h"
#include "Camera/CameraComponent.h"
#include "GameFramework/PlayerController.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Engine/OverlapResult.h"
#include "Engine/StaticMesh.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "NiagaraSystem.h"
#include "Materials/MaterialInterface.h"
#include "Particles/ParticleSystem.h"
#include "Sound/SoundBase.h"
#include "Components/PrimitiveComponent.h"
#include "Kismet/GameplayStatics.h"

UFPSIceWallComponent::UFPSIceWallComponent(){PrimaryComponentTick.bCanEverTick=true;}
void UFPSIceWallComponent::BeginPlay()
{
    Super::BeginPlay();AddTickPrerequisiteActor(GetOwner());
    for(int32 I=1;I<=4;++I)BlockMeshes.Add(LoadObject<UStaticMesh>(nullptr,*FString::Printf(TEXT("/Game/Skills/IceWall/FabIceV3/SM_IceBlock_%02d.SM_IceBlock_%02d"),I,I)));
    IceMaterial=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Skills/IceWall/FabIceV3/M_IceWall.M_IceWall"));
    PreviewMaterial=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Skills/IceWall/BlockV1/M_IceWallPreview.M_IceWallPreview"));
    BreakFX=LoadObject<UParticleSystem>(nullptr,TEXT("/Game/Skills/IceSpike/P_IceSpikeImpact.P_IceSpikeImpact"));
    BreakSound=LoadObject<USoundBase>(nullptr,TEXT("/Game/Skills/IceSpike/S_IceImpact.S_IceImpact"));
    CastSound=LoadObject<USoundBase>(nullptr,TEXT("/Game/Skills/IceWall/BlockV1/S_IceWallCast.S_IceWallCast"));
    const TArray<FSoftObjectPath> Effects={ColdMistTemplate.ToSoftObjectPath(),LandingTemplate.ToSoftObjectPath()};
    ColdMistLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(Effects,
        FStreamableDelegate::CreateWeakLambda(this,[this](){ColdMistAsset=ColdMistTemplate.Get();LandingAsset=LandingTemplate.Get();}));
}
UColdSteelStatusModel* UFPSIceWallComponent::Model() const
{return GetWorld()&&GetWorld()->GetGameInstance()?GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;}
UFPSFireballComponent* UFPSIceWallComponent::Hands() const {return GetOwner()->FindComponentByClass<UFPSFireballComponent>();}
bool UFPSIceWallComponent::InputAvailable() const
{
    const auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());const auto* PC=Pawn?Cast<APlayerController>(Pawn->GetController()):nullptr;
    if(!PC||PC->bShowMouseCursor||PC->IsMoveInputIgnored()||PC->IsLookInputIgnored()||AFPSGAMEPlayerController::BlocksOngoingActions(PC)||Pawn->IsChoosingAmmo())return false;
    const auto* Builder=PC->FindComponentByClass<UVoxelBuildComponent>();
    return !Builder||!Builder->IsBuilding();
}
bool UFPSIceWallComponent::IsPlacementActive() const {return IsPrepared()&&InputAvailable()&&Preview.IsValid()&&!Preview->IsHidden();}
void UFPSIceWallComponent::Feedback(const FString& Text){Message=Text;MessageUntil=GetWorld()->GetTimeSeconds()+1.5;}
void UFPSIceWallComponent::RejectHeldHand(){bQueuedGather=bReleaseRequested=false;HandNotice.Show(GetWorld()->GetTimeSeconds());}
bool UFPSIceWallComponent::IsHandOccupiedNotice() const
{const auto* P=Cast<AFPSGAMECharacter>(GetOwner());return P&&P->IsSpellHandHeld()&&GetWorld()&&HandNotice.Active(GetWorld()->GetTimeSeconds());}
float UFPSIceWallComponent::HandNoticeAlpha() const {return GetWorld()?HandNotice.Alpha(GetWorld()->GetTimeSeconds()):0.f;}
float UFPSIceWallComponent::HandNoticeRise() const {return GetWorld()?HandNotice.Rise(GetWorld()->GetTimeSeconds()):0.f;}
FString UFPSIceWallComponent::StatusText() const
{
    if(IsHandOccupiedNotice())return TEXT("左手占用");
    if(GetWorld()->GetTimeSeconds()<MessageUntil)return Message;
    if(bQueuedGather)return TEXT("等待施法");
    if(Seed.IsValid()&&!bGathered)return TEXT("凝聚");
    if(bReleaseRequested)return TEXT("释放");
    if(IsPrepared())
    {
        if(!Displayed.bValid)return Displayed.Reason;
        const FString Label=Shape==EIceWallShape::Low?TEXT("矮墙·R"):TEXT("高墙·R");
        return Displayed.bTrimmed?Label+TEXT("·截短"):Label;
    }
    if(auto* M=Model();M&&M->IceWallCooldown()>0)return FString::Printf(TEXT("%.1f"),M->IceWallCooldown());
    return TEXT("");
}
float UFPSIceWallComponent::CooldownFraction() const
{const auto* M=Model();return M&&!Seed.IsValid()?FMath::Clamp(M->IceWallCooldown()/FMath::Max(.1f,M->IceWallCooldownDuration()),0.f,1.f):0.f;}
AFPSIceWall* UFPSIceWallComponent::SpawnWall(bool bGhost,const FIceWallCast& Cast)
{
    FActorSpawnParameters Params;Params.Owner=GetOwner();Params.Instigator=::Cast<APawn>(GetOwner());Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    auto* Wall=GetWorld()->SpawnActor<AFPSIceWall>(GetOwner()->GetActorLocation(),FRotator::ZeroRotator,Params);
    if(Wall)Wall->Initialize(this,Cast,BlockMeshes,IceMaterial,PreviewMaterial,BreakFX,BreakSound,bGhost);
    return Wall;
}
void UFPSIceWallComponent::Trigger()
{
    if(UBoundCongregateCaptureComponent::IsCaptured(GetOwner()))return;
    auto* P=Cast<AFPSGAMECharacter>(GetOwner());auto* M=Model();
    if(!P||!M||!P->IsLocallyControlled()||!InputAvailable())return;
    if(auto* Health=P->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())return;
    if(const auto* H=Hands();H&&H->HasOtherPreparedSpell(this))
    {bQueuedGather=false;Feedback(TEXT("先释放已积蓄魔法"));return;}
    if(M->IceWallDefinition().IceWall.bRequiresStaff&&!M->HasEquippedStaff()){Cancel();Feedback(TEXT("需要法杖"));return;}
    if(P->IsSpellHandHeld()){RejectHeldHand();return;}
    if(Seed.IsValid())
    {
        if(!IsPrepared())return;
        FString Reason;
        // Commit exactly the displayed plan. Contact may revalidate it, never retarget it.
        if(!Displayed.bValid||!ValidatePlacement(Displayed,Seed->Snapshot(),Reason))
        {Feedback(Reason.IsEmpty()?Displayed.Reason:Reason);return;}
        Committed=Displayed;bReleaseRequested=true;if(Preview.IsValid())Preview->SetActorHiddenInGame(true);
    }
    else
    {
        if(M->IceWallCooldown()>0){Feedback(TEXT("冷却"));return;}
        if(!M->CanSpendMana(M->IceWallStats().ManaCost)){Feedback(TEXT("缺蓝"));return;}
        if(BlockMeshes.Num()!=4||BlockMeshes.Contains(nullptr)||!IceMaterial||!PreviewMaterial){Feedback(TEXT("缺素材"));return;}
        bQueuedGather=true;
    }
    ServiceQueue();
}
void UFPSIceWallComponent::ServiceQueue()
{
    auto* M=Model();auto* H=Hands();auto* P=Cast<AFPSGAMECharacter>(GetOwner());
    if(!M||!H||!P||!InputAvailable())return;
    if((bQueuedGather||bReleaseRequested)&&H->HasOtherPreparedSpell(this))
    {bQueuedGather=false;bReleaseRequested=false;Feedback(TEXT("先释放已积蓄魔法"));return;}
    if((bQueuedGather||bReleaseRequested)&&M->IceWallDefinition().IceWall.bRequiresStaff&&!M->HasEquippedStaff())
    {Cancel();Feedback(TEXT("需要法杖"));return;}
    if((bQueuedGather||bReleaseRequested)&&P->IsSpellHandHeld()){RejectHeldHand();return;}
    if(bQueuedGather)
    {
        const auto C=M->IceWallStats();
        if(M->IceWallCooldown()>0||!M->CanSpendMana(C.ManaCost)){bQueuedGather=false;Feedback(TEXT("未就绪"));return;}
        if(!H->TryBeginSpellGesture(this,false,C.CastSpeed,FSimpleDelegate::CreateUObject(this,&ThisClass::Gathered)))return;
        auto* NewSeed=SpawnWall(false,C);auto* NewPreview=SpawnWall(true,C);
        if(!NewSeed||!NewPreview)
        {if(NewSeed)NewSeed->Destroy();if(NewPreview)NewPreview->Destroy();bQueuedGather=false;H->CancelSpellGesture(this);return;}
        const float Before=M->Snapshot().Mana;
        if(!M->BeginIceWallCast(C)){NewSeed->Destroy();NewPreview->Destroy();bQueuedGather=false;H->CancelSpellGesture(this);return;}
        // The wall owns payment through the entire placement phase, beyond the gather gesture.
        PaidMana=FMath::Max(0.f,Before-M->Snapshot().Mana);
        Seed=NewSeed;Preview=NewPreview;NewPreview->SetActorHiddenInGame(true);
        bQueuedGather=false;bGathered=false;PreparedAge=PreviewAge=0;MessageUntil=0;
        Displayed=FIceWallPlacement();
        if(auto* Status=P->FindComponentByClass<UCombatStatusFormula>())Status->ConsumeChainSpell();
        if(CastSound)UGameplayStatics::PlaySoundAtLocation(this,CastSound,P->GetActorLocation(),.5f);
        // 联机客人：种子/预览是本地表现壳；权威墙等 Phase1 上报后由服务端生成。
        if(GetWorld()->GetNetMode()==NM_Client){bNetPaid=true;NetPaidAt=GetWorld()->GetTimeSeconds();NetCast::Send(P,TEXT("iceWall"),0);}
    }
    if(bReleaseRequested&&Seed.IsValid())
        H->TryBeginSpellGesture(this,true,Seed->Snapshot().CastSpeed,FSimpleDelegate::CreateUObject(this,&ThisClass::LaunchAtContact));
}
void UFPSIceWallComponent::Gathered(){if(Seed.IsValid()){bGathered=true;PreparedAge=0;PreviewAge=1;}}
void UFPSIceWallComponent::LaunchAtContact()
{
    if(!Seed.IsValid()||!bReleaseRequested)return;
    if(auto* M=Model();M&&M->IceWallDefinition().IceWall.bRequiresStaff&&!M->HasEquippedStaff())
    {Cancel();Feedback(TEXT("需要法杖"));return;}
    FString Reason;
    if(!InputAvailable()||!ValidatePlacement(Committed,Seed->Snapshot(),Reason))
    {bReleaseRequested=false;Feedback(Reason.IsEmpty()?TEXT("释放取消"):Reason);PreviewAge=1;return;}
    auto* M=Model();auto* H=Hands();
    if(!M||!H||!M->CommitIceWallRelease()){Cancel();return;}
    // 联机客人：放置点上报服务端，权威墙复制回来；本地种子/预览即刻消隐。
    if(GetWorld()->GetNetMode()==NM_Client)
    {
        const auto C=Seed->Snapshot();
        const FVector Forward=Committed.Rotation.Vector(); // 朝向走 AimNormal，服务端按它重建 yaw
        NetCast::Send(GetOwner(),TEXT("iceWall"),1,Committed.Location,Forward,uint8(Committed.Shape));
        if(Preview.IsValid())Preview->Destroy();Preview.Reset();
        if(Seed.IsValid())Seed->Destroy();Seed.Reset();
        PaidMana=0;bNetPaid=false;bGathered=bReleaseRequested=false;
        if(auto* S=GetOwner()->FindComponentByClass<UCombatStatusFormula>())
        {if(C.bGrantChain)S->AddChainSpell();if(C.CastHasteStacks>0)S->AddHaste(C.CastHasteStacks,C.CastHasteDuration);}
        return;
    }
    auto* Wall=Seed.Get();const auto C=Wall->Snapshot();
    Wall->Gather(1.f,SeedOrigin());
    Wall->Launch(Wall->GetActorLocation(),Committed);
    if(Preview.IsValid())Preview->Destroy();Preview.Reset();Seed.Reset();
    PaidMana=0;bGathered=bReleaseRequested=false;ReleasedWalls.RemoveAll([](const auto& W){return !W.IsValid();});
    if(ReleasedWalls.Num()>=4){if(ReleasedWalls[0].IsValid())ReleasedWalls[0]->Shatter();ReleasedWalls.RemoveAt(0);}
    ReleasedWalls.Add(Wall);
    if(auto* S=GetOwner()->FindComponentByClass<UCombatStatusFormula>())
    {if(C.bGrantChain)S->AddChainSpell();if(C.CastHasteStacks>0)S->AddHaste(C.CastHasteStacks,C.CastHasteDuration);}
}
bool UFPSIceWallComponent::ToggleShape()
{
    if(!IsPlacementActive())return false;
    Shape=Shape==EIceWallShape::High?EIceWallShape::Low:EIceWallShape::High;
    UpdatePreview();return true;
}
void UFPSIceWallComponent::SuspendPreview()
{
    if(Preview.IsValid())Preview->SetActorHiddenInGame(true);
    bReleaseRequested=false;PreviewAge=1;Displayed.bValid=false;
    if(auto* H=Hands();H&&H->IsSpellGesture(this)&&bGathered)H->CancelSpellGesture(this);
}
bool UFPSIceWallComponent::ValidatePlacement(const FIceWallPlacement& P,const FIceWallCast& C,FString& Reason) const
{
    if(FVector::DistSquared2D(GetOwner()->GetActorLocation(),P.Location)>FMath::Square(C.Range))
    {Reason=TEXT("超距");return false;}
    return IceWallPlacement::Validate(GetWorld(),P,C,Reason);
}
void UFPSIceWallComponent::UpdatePreview()
{
    if(!IsPrepared()||!Preview.IsValid()||!InputAvailable())return;
    auto* Camera=GetOwner()->FindComponentByClass<UCameraComponent>();if(!Camera)return;
    const auto& C=Seed->Snapshot();FIceWallPlacement P;P.Shape=Shape;
    P.Rotation=FRotator(0,Camera->GetComponentRotation().Yaw,0);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(IceWallAim),false,GetOwner());Query.AddIgnoredActor(Seed.Get());Query.AddIgnoredActor(Preview.Get());
    const FVector Eye=Camera->GetComponentLocation();FHitResult Aim,Floor;
    const FVector End=Eye+Camera->GetForwardVector()*C.Range;
    const bool bAim=IceWallPlacement::TraceWithoutCreatures(GetWorld(),Eye,End,Query,Aim);
    const FVector Target=bAim?Aim.ImpactPoint:End;
    P.Location=Target;
    const bool bFloor=IceWallPlacement::TraceWithoutCreatures(GetWorld(),Target+FVector(0,0,25),Target-FVector(0,0,C.Range),Query,Floor);
    if(bFloor)P.Location=Floor.ImpactPoint;
    if(!bFloor||Floor.ImpactNormal.Z<.5735764f)P.Reason=TEXT("指向可支撑的坡面");
    else if(FVector::DistSquared2D(GetOwner()->GetActorLocation(),P.Location)>FMath::Square(C.Range))P.Reason=TEXT("超距");
    else P.bValid=IceWallPlacement::Build(GetWorld(),P,C,P.Reason);
    // A visible ground point behind a foreground obstacle cannot become a placement candidate.
    if(P.bValid)
    {
        FHitResult Sight;
        if(IceWallPlacement::TraceWithoutCreatures(GetWorld(),Eye,P.Location+FVector(0,0,12),Query,Sight)
            &&FVector::DistSquared(Sight.ImpactPoint,P.Location)>FMath::Square(32.f))
        {P.bValid=false;P.Reason=TEXT("落点遮挡");}
    }
    Displayed=P;Preview->PreviewAt(P);
}
FVector UFPSIceWallComponent::SeedOrigin() const
{
    const auto* H=Hands();const auto* Camera=GetOwner()->FindComponentByClass<UCameraComponent>();
    if(!Camera)return GetOwner()->GetActorLocation();
    if(H&&H->IsSpellGesture(this)&&!bGathered&&H->IsStaffCasting())
    {
        if(const auto* Staff=GetOwner()->FindComponentByClass<UStaffWeaponComponent>();Staff&&Staff->IsEquipped())
            return Camera->GetComponentTransform().TransformPosition(StaffCastMotion::Focus(H->SampleStaffMotion(Staff->CarryPoseInCamera())));
    }
    // Same camera-space focus as a staff-gathered fireball, including its release windup.
    const auto* Staff=GetOwner()->FindComponentByClass<UStaffWeaponComponent>();
    return Camera->GetComponentTransform().TransformPosition(StaffCastMotion::Focus(
        Staff&&Staff->IsEquipped()?StaffChargeFlow::Settled(*Staff):StaffCastMotion::Raised()));
}
void UFPSIceWallComponent::InterruptPending(bool bCancelSeed)
{bQueuedGather=false;SuspendPreview();if(bCancelSeed)Cancel();}
void UFPSIceWallComponent::Cancel()
{
    // 联机客人：凝聚期取消——服务端按 Phase2 退预留蓝；本地壳即时清。
    if(GetWorld()&&GetWorld()->GetNetMode()==NM_Client&&bNetPaid)NetCast::Send(GetOwner(),TEXT("iceWall"),2);
    bNetPaid=false;
    bQueuedGather=bReleaseRequested=bGathered=false;
    auto* OldSeed=Seed.Get();Seed.Reset();if(OldSeed)OldSeed->Destroy();
    auto* OldPreview=Preview.Get();Preview.Reset();if(OldPreview)OldPreview->Destroy();
    if(auto* M=Model();M&&OldSeed)M->RefundUnreleasedCast(PaidMana,TEXT("iceWall"));
    PaidMana=0;if(auto* H=Hands())H->CancelSpellGesture(this);
}
// ── 联机服务端入口：客人上报放置点→重验→权威墙生成（复制回各端） ──
bool UFPSIceWallComponent::NetCommitWall(APawn* Caster,const FColdSteelNetCastRequest& Req,UColdSteelStatusModel* Shadow,const FIceWallCast& C)
{
    FIceWallPlacement Plan;
    Plan.Location=Req.AimPoint;
    Plan.Shape=Req.Variant==1?EIceWallShape::Low:EIceWallShape::High;
    const FVector Facing=Req.AimNormal.GetSafeNormal2D(SMALL_NUMBER,FVector::ForwardVector);
    Plan.Rotation=FRotator(0,FMath::RadiansToDegrees(FMath::Atan2(Facing.Y,Facing.X)),0);
    Plan.bValid=true;
    if(FVector::DistSquared2D(Caster->GetActorLocation(),Plan.Location)>FMath::Square(C.Range))return false;
    FString Reason;
    if(!IceWallPlacement::Build(GetWorld(),Plan,C,Reason))return false;
    // 服务端权威墙：直接生成终态——种子凝聚段只在本地端有过表现意义。
    FActorSpawnParameters Params;Params.Owner=Caster;Params.Instigator=Caster;Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    auto* Wall=GetWorld()->SpawnActor<AFPSIceWall>(Plan.Location,Plan.Rotation,Params);
    if(!Wall)return false;
    Wall->Initialize(this,C,BlockMeshes,IceMaterial,PreviewMaterial,BreakFX,BreakSound,false);
    Wall->Gather(1.f,Plan.Location);
    Wall->Launch(Plan.Location,Plan);
    Shadow->CommitIceWallRelease();
    ReleasedWalls.RemoveAll([](const auto& W){return !W.IsValid();});
    if(ReleasedWalls.Num()>=4){if(ReleasedWalls[0].IsValid())ReleasedWalls[0]->Shatter();ReleasedWalls.RemoveAt(0);}
    ReleasedWalls.Add(Wall);
    if(auto* S=Caster->FindComponentByClass<UCombatStatusFormula>())
    {if(C.bGrantChain)S->AddChainSpell();if(C.CastHasteStacks>0)S->AddHaste(C.CastHasteStacks,C.CastHasteDuration);}
    return true;
}
void UFPSIceWallComponent::NetCastRejected(uint8 /*Phase*/,uint8 /*Code*/)
{
    bQueuedGather=false;bNetPaid=false;
    if(Seed.IsValid())Seed->Destroy();Seed.Reset();
    if(Preview.IsValid())Preview->Destroy();Preview.Reset();
    bGathered=bReleaseRequested=false;
    if(auto* M=Model())M->RefundUnreleasedCast(PaidMana,TEXT("iceWall"));
    PaidMana=0;if(auto* H=Hands())H->CancelSpellGesture(this);
    Feedback(TEXT("施法失败"));
}
void UFPSIceWallComponent::NetCastCancelled(uint8 /*Phase*/)
{
    bNetPaid=false; // 本地壳的销毁与退蓝在 Cancel() 走完了
}
void UFPSIceWallComponent::WallEnded(AFPSIceWall* Wall)
{
    if(Seed.Get()==Wall)
    {Seed.Reset();if(Preview.IsValid())Preview->Destroy();Preview.Reset();bGathered=bReleaseRequested=false;if(auto* M=Model())M->RefundUnreleasedCast(PaidMana,TEXT("iceWall"));PaidMana=0;}
}
void UFPSIceWallComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    if(auto* Health=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead()){Cancel();return;}
    // 联机：扣账已发生但服务端权威墙久久未达——超时本地收尾退款。
    if(bNetPaid&&!Seed.IsValid()&&!bReleaseRequested&&GetWorld()&&GetWorld()->GetTimeSeconds()-NetPaidAt>2.5)
    {
        bNetPaid=false;
        if(auto* M=Model())M->RefundUnreleasedCast(PaidMana,TEXT("iceWall"));
        PaidMana=0;
    }
    if(Seed.IsValid()||bQueuedGather||bReleaseRequested)
        if(auto* M=Model();M&&M->IceWallDefinition().IceWall.bRequiresStaff&&!M->HasEquippedStaff())
        {Cancel();Feedback(TEXT("需要法杖"));return;}
    if(!InputAvailable()){bQueuedGather=false;SuspendPreview();return;}
    ServiceQueue();
    if(!Seed.IsValid())return;
    auto* Camera=GetOwner()->FindComponentByClass<UCameraComponent>();if(!Camera)return;
    const auto* H=Hands();float Fraction=1.f;
    if(!bGathered&&H&&H->IsSpellGesture(this))Fraction=H->HandPhaseFraction();
    Seed->Gather(Fraction,SeedOrigin());
    if(bGathered){PreparedAge+=Delta;if(PreparedAge>=Seed->Snapshot().HoverDuration){Cancel();Feedback(TEXT("凝聚到期"));return;}}
    PreviewAge+=Delta;if(PreviewAge>=.12f){PreviewAge=0;UpdatePreview();}
}
void UFPSIceWallComponent::EndPlay(EEndPlayReason::Type Reason)
{
    if(ColdMistLoad){ColdMistLoad->CancelHandle();ColdMistLoad.Reset();}
    Cancel();
    for(auto W:ReleasedWalls)if(W.IsValid())W->Destroy();ReleasedWalls.Reset();
    ColdMistAsset=nullptr;LandingAsset=nullptr;
    Super::EndPlay(Reason);
}
