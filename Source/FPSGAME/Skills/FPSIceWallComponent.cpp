#include "FPSIceWallComponent.h"
#include "FPSIceWall.h"
#include "FPSFireballComponent.h"
#include "../FPSGAMECharacter.h"
#include "../FPSGAMEPlayerController.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Building/VoxelBuildComponent.h"
#include "../Weapons/Staff/StaffWeaponComponent.h"
#include "Camera/CameraComponent.h"
#include "GameFramework/PlayerController.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Engine/OverlapResult.h"
#include "Engine/StaticMesh.h"
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
    if(IsPrepared())return Displayed.bValid?(Shape==EIceWallShape::Low?TEXT("矮墙·R"):TEXT("高墙·R")):Displayed.Reason;
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
    auto* P=Cast<AFPSGAMECharacter>(GetOwner());auto* M=Model();
    if(!P||!M||!P->IsLocallyControlled()||GetWorld()->GetNetMode()!=NM_Standalone||!InputAvailable())return;
    if(auto* Health=P->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())return;
    if(M->IceWallDefinition().IceWall.bRequiresStaff&&!M->HasEquippedStaff()){Cancel();Feedback(TEXT("需要法杖"));return;}
    if(P->IsSpellHandHeld()){RejectHeldHand();return;}
    if(Seed.IsValid())
    {
        if(!IsPrepared())return;
        FString Reason;
        // Commit exactly the displayed plan. Contact may revalidate it, never retarget it.
        if(!Displayed.bValid||!ValidatePlacement(Displayed,Seed->Snapshot(),true,Reason))
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
    if(!InputAvailable()||!ValidatePlacement(Committed,Seed->Snapshot(),true,Reason))
    {bReleaseRequested=false;Feedback(Reason.IsEmpty()?TEXT("释放取消"):Reason);PreviewAge=1;return;}
    auto* M=Model();auto* H=Hands();
    if(!M||!H||!M->CommitIceWallRelease()){Cancel();return;}
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
bool UFPSIceWallComponent::ValidatePlacement(const FIceWallPlacement& P,const FIceWallCast& C,bool bAllowEnemies,FString& Reason) const
{
    auto Reject=[&](const TCHAR* Text){Reason=Text;return false;};
    if(FVector::DistSquared2D(GetOwner()->GetActorLocation(),P.Location)>FMath::Square(C.Range))return Reject(TEXT("超距"));
    FCollisionQueryParams Query(SCENE_QUERY_STAT(IceWallPlacement),false);
    if(Seed.IsValid())Query.AddIgnoredActor(Seed.Get());if(Preview.IsValid())Query.AddIgnoredActor(Preview.Get());
    TArray<FOverlapResult> Hits;
    GetWorld()->OverlapMultiByChannel(Hits,P.Location+FVector(0,0,C.Height(P.Shape)*.5f+5),P.Rotation.Quaternion(),ECC_Pawn,
        FCollisionShape::MakeBox(FVector(C.Thickness*.5f,C.Width()*.5f,C.Height(P.Shape)*.5f-5)),Query);
    for(const auto& Hit:Hits)
    {
        auto* A=Hit.GetActor();auto* Primitive=Hit.GetComponent();
        if(!A||!Primitive||Primitive->GetCollisionResponseToChannel(ECC_Pawn)!=ECR_Block)continue;
        const auto* Enemy=A->FindComponentByClass<UMonsterCombatComponent>();
        if(Enemy&&Enemy->IsDead())continue;
        if(Enemy&&bAllowEnemies&&!A->ActorHasTag(TEXT("Friendly")))continue;
        return Reject(Cast<APawn>(A)?TEXT("有人占位"):TEXT("位置遮挡"));
    }
    Query.AddIgnoredActor(GetOwner());
    // Both wall ends and the center need real support on the same floor.
    for(float Along:{-C.Width()*.5f+2,0.f,C.Width()*.5f-2})
    {
        const FVector Base=P.Location+P.Rotation.RotateVector(FVector(0,Along,0));FHitResult Floor;
        if(!GetWorld()->LineTraceSingleByChannel(Floor,Base+FVector(0,0,25),Base-FVector(0,0,45),ECC_Visibility,Query)
            ||Floor.ImpactNormal.Z<.9||FMath::Abs(Floor.ImpactPoint.Z-P.Location.Z)>6||Cast<APawn>(Floor.GetActor()))return Reject(TEXT("地面不平"));
    }
    Reason.Reset();return true;
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
    const bool bAim=GetWorld()->LineTraceSingleByChannel(Aim,Eye,End,ECC_Visibility,Query);
    const FVector Target=bAim?Aim.ImpactPoint:End;
    P.Location=Target;
    const bool bFloor=GetWorld()->LineTraceSingleByChannel(Floor,Target+FVector(0,0,25),Target-FVector(0,0,C.Range),ECC_Visibility,Query);
    if(bFloor)P.Location=Floor.ImpactPoint;
    if(!bFloor||Floor.ImpactNormal.Z<.9||Cast<APawn>(Floor.GetActor()))P.Reason=TEXT("指向地面");
    else P.bValid=ValidatePlacement(P,C,true,P.Reason);
    // A visible ground point behind a foreground obstacle cannot become a placement candidate.
    if(P.bValid)
    {
        FHitResult Sight;
        if(GetWorld()->LineTraceSingleByChannel(Sight,Eye,P.Location+FVector(0,0,12),ECC_Visibility,Query)
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
    return Camera->GetComponentTransform().TransformPosition(StaffCastMotion::Focus(StaffCastMotion::Raised()));
}
void UFPSIceWallComponent::InterruptPending(bool bCancelSeed)
{bQueuedGather=false;SuspendPreview();if(bCancelSeed)Cancel();}
void UFPSIceWallComponent::Cancel()
{
    bQueuedGather=bReleaseRequested=bGathered=false;
    auto* OldSeed=Seed.Get();Seed.Reset();if(OldSeed)OldSeed->Destroy();
    auto* OldPreview=Preview.Get();Preview.Reset();if(OldPreview)OldPreview->Destroy();
    if(auto* M=Model();M&&OldSeed)M->RefundUnreleasedCast(PaidMana,TEXT("iceWall"));
    PaidMana=0;if(auto* H=Hands())H->CancelSpellGesture(this);
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
    PreviewAge+=Delta;if(PreviewAge>=.05f){PreviewAge=0;UpdatePreview();}
}
void UFPSIceWallComponent::EndPlay(EEndPlayReason::Type Reason)
{
    Cancel();
    for(auto W:ReleasedWalls)if(W.IsValid())W->Destroy();ReleasedWalls.Reset();
    Super::EndPlay(Reason);
}
