#include "HorseRiderComponent.h"
#include "PlayerKnockdownComponent.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../UI/ColdSteelStatusModel.h"
#include "StableRidingHorse.h"
#include "../FPSGAMECharacter.h"
#include "../FPSGAMEPlayerController.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../UI/ColdSteelWorldInteraction.h"
#include "FPSFurnitureRestComponent.h"
#include "../Production/ProductionToolComponent.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Animation/AnimSequence.h"
#include "Engine/SkeletalMesh.h"
#include "Misc/Paths.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/GameStateBase.h"
#include "Net/UnrealNetwork.h"
#include "TimerManager.h"
#include "Engine/GameViewportClient.h"
#include "UnrealClient.h"

namespace StableRide
{
    constexpr float MountTime=1.7f, DismountTime=1.4f;
    constexpr float HoldSeconds=.45f;
    static float Ease(float P,float A,float B){return FMath::SmoothStep(A,B,P);}
}
UHorseRiderComponent::UHorseRiderComponent()
{
    SetIsReplicatedByDefault(true);
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.bStartWithTickEnabled=false;
}
void UHorseRiderComponent::BeginPlay()
{
    Super::BeginPlay();
    Player=Cast<AFPSGAMECharacter>(GetOwner());
    ApplyState();
}
bool UHorseRiderComponent::IsRiding(const AActor* Actor)
{
    const auto* Ride=Actor?Actor->FindComponentByClass<UHorseRiderComponent>():nullptr;
    return Ride&&Ride->Active();
}
AStableRidingHorse* UHorseRiderComponent::MountOf(const AActor* Actor)
{
    const auto* Pawn=Cast<AFPSGAMECharacter>(Actor);
    const auto* Ride=Pawn?Pawn->FindComponentByClass<UHorseRiderComponent>():nullptr;
    return Ride&&Ride->Active()?Ride->GetMount():nullptr;
}
FVector AFPSGAMECharacter::GetNavAgentLocation() const
{
    if(const auto* Mount=UHorseRiderComponent::MountOf(this))return Mount->GetNavAgentLocation();
    return Super::GetNavAgentLocation();
}
bool UHorseRiderComponent::IsSeated(const AActor* Actor)
{
    const auto* Ride=Actor?Actor->FindComponentByClass<UHorseRiderComponent>():nullptr;
    return Ride&&Ride->State.Phase==ERiderPhase::Seated;
}
bool UHorseRiderComponent::IsCantering(const AActor* Actor)
{
    const auto* Ride=Actor?Actor->FindComponentByClass<UHorseRiderComponent>():nullptr;
    return Ride&&Ride->State.Phase==ERiderPhase::Seated&&IsValid(Ride->State.Horse)&&
        Ride->State.Horse->GetVelocity().SizeSquared2D()>FMath::Square(325.f)&&
        FVector::DotProduct(Ride->State.Horse->GetVelocity(),Ride->State.Horse->GetActorForwardVector())>0.f;
}
bool UHorseRiderComponent::UsesSaddleHands(const AActor* Actor)
{
    const auto* Ride=Actor?Actor->FindComponentByClass<UHorseRiderComponent>():nullptr;
    return Ride&&Ride->Transferring();
}
void UHorseRiderComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(UHorseRiderComponent,State);
    DOREPLIFETIME_CONDITION(UHorseRiderComponent,OwnedHorse,COND_OwnerOnly);
}
float UHorseRiderComponent::Clock() const
{
    if(const auto* GS=GetWorld()->GetGameState())return GS->GetServerWorldTimeSeconds();
    return GetWorld()->GetTimeSeconds();
}
float UHorseRiderComponent::MountAmount() const
{
    const float Age=Clock()-State.Since;
    if(State.Phase==ERiderPhase::Mounting)return FMath::Clamp(Age/StableRide::MountTime,0.f,1.f);
    if(State.Phase==ERiderPhase::Dismounting)return 1.f-FMath::Clamp(Age/StableRide::DismountTime,0.f,1.f);
    return 1.f;
}
AStableRidingHorse* UHorseRiderComponent::Focus() const
{
    const auto* PC=Player.IsValid()?Cast<APlayerController>(Player->GetController()):nullptr;
    if(!PC||PC->bShowMouseCursor)return nullptr;
    FVector Eye; FRotator View;
    ColdSteelWorldInteraction::GetReachViewPoint(PC,Eye,View);
    FHitResult Hit;
    FCollisionQueryParams Q(SCENE_QUERY_STAT(StableHorseUse),false,Player.Get());
    GetWorld()->LineTraceSingleByChannel(Hit,Eye,Eye+View.Vector()*ColdSteelWorldInteraction::DefaultUseReach,ECC_Visibility,Q);
    auto* Horse=Cast<AStableRidingHorse>(Hit.GetActor());
    return Horse&&!Horse->IsMarketShowcase()&&!Horse->IsRetreating()&&Horse->Visit()==EStableHorseVisit::Present?Horse:nullptr;
}
bool UHorseRiderComponent::ClearGround(const AStableRidingHorse& Horse,const FVector& At) const
{
    const auto* Cap=Player->GetCapsuleComponent();
    FCollisionQueryParams Q(SCENE_QUERY_STAT(StableHorseStand),false,Player.Get());
    Q.AddIgnoredActor(&Horse);
    return !GetWorld()->OverlapBlockingTestByChannel(At,FQuat::Identity,ECC_Pawn,
        FCollisionShape::MakeCapsule(Cap->GetScaledCapsuleRadius(),Cap->GetScaledCapsuleHalfHeight()),Q);
}
bool UHorseRiderComponent::SideSpot(const AStableRidingHorse& Horse,FVector& Out,bool bRight,bool bCheckApproach) const
{
    const auto* Cap=Player->GetCapsuleComponent();
    const FVector Seat=Horse.Saddle(), Side=Horse.GetActorRightVector()*(bRight?1.f:-1.f);
    FCollisionQueryParams Q(SCENE_QUERY_STAT(StableHorseSide),false,Player.Get());
    Q.AddIgnoredActor(&Horse);
    if(bCheckApproach&&FVector::DotProduct(Player->GetActorLocation()-Seat,Side)<15.)return false;
    const float H=Cap->GetScaledCapsuleHalfHeight(),R=Cap->GetScaledCapsuleRadius();
    const FVector Point=Seat+Side*(51.f+R);
    FHitResult Floor;
    if(!GetWorld()->LineTraceSingleByChannel(Floor,Point+FVector(0,0,12),Point-FVector(0,0,240),
        ECC_Pawn,Q)||Floor.ImpactNormal.Z<.72f)return false;
    const float HoofZ=Horse.GetActorLocation().Z-Horse.GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    if(FMath::Abs(Floor.ImpactPoint.Z-HoofZ)>Horse.GetCharacterMovement()->MaxStepHeight)return false;
    const FVector At=Floor.ImpactPoint+FVector(0,0,H+2.5f);
    if(!ClearGround(Horse,At))return false;
    // A clear landing behind a gate is not a reachable stirrup.
    if(GetWorld()->SweepTestByChannel(Seat,At+FVector(0,0,20),FQuat::Identity,ECC_Pawn,
        FCollisionShape::MakeSphere(R*.77f),Q))return false;
    const FVector OverIron=Seat+Side*42.f+FVector(0,0,78);
    const FVector SeatedHead=Seat+Horse.GetActorForwardVector()*14.f+FVector(0,0,77);
    const auto Head=FCollisionShape::MakeSphere(13.f);
    if(GetWorld()->SweepTestByChannel(At+FVector(0,0,65),OverIron,FQuat::Identity,ECC_Pawn,Head,Q)||
        GetWorld()->SweepTestByChannel(OverIron,SeatedHead,FQuat::Identity,ECC_Pawn,Head,Q))return false;
    if(bCheckApproach&&GetWorld()->SweepTestByChannel(Player->GetActorLocation(),At,FQuat::Identity,ECC_Pawn,
        FCollisionShape::MakeCapsule(R-1.f,H-4.f),Q))return false;
    Out=At;return true;
}
bool UHorseRiderComponent::PressUse(AStableRidingHorse* Horse)
{
    if(Active())Horse=State.Horse;
    if(!Horse)return Active();
    if(Transferring())return true;
    bUsePressed=true;bHoldHandled=false;
    PressedHorse=Horse;
    UseStarted=GetWorld()->GetTimeSeconds();
    GetWorld()->GetTimerManager().SetTimer(HoldTimer,this,&ThisClass::HandleHold,StableRide::HoldSeconds,false);
    return true;
}
bool UHorseRiderComponent::CanCompleteUse() const
{
    const auto* PC=Player.IsValid()?Cast<AFPSGAMEPlayerController>(Player->GetController()):nullptr;
    if(!PC||!PC->IsLocalController()||PC->bShowMouseCursor||PC->IsGameMenuOpen()||PC->IsInBuildMode()||
        PC->IsActionPreservingPanelOpen()||PC->IsWoodworkingOpen()||PC->IsAlchemyOpen()||
        !PressedHorse.IsValid()||Transferring())return false;
    const auto* Viewport=GetWorld()->GetGameViewport();
    if(Viewport&&Viewport->Viewport&&!Viewport->Viewport->HasFocus()&&!Viewport->Viewport->HasMouseCapture())return false;
    return Active()?State.Horse==PressedHorse.Get():Focus()==PressedHorse.Get();
}
void UHorseRiderComponent::HandleHold()
{
    if(!bUsePressed||bHoldHandled)return;
    bHoldHandled=true;
    if(CanCompleteUse())ServerUse(PressedHorse.Get(),true);
}
bool UHorseRiderComponent::ReleaseUse()
{
    if(!bUsePressed)return false;
    GetWorld()->GetTimerManager().ClearTimer(HoldTimer);
    if(!bHoldHandled&&CanCompleteUse())
    {
        const bool LongPress=GetWorld()->GetTimeSeconds()-UseStarted>=StableRide::HoldSeconds;
        if(LongPress||!Active())ServerUse(PressedHorse.Get(),LongPress);
    }
    bUsePressed=false;PressedHorse.Reset();
    return true;
}
void UHorseRiderComponent::ServerUse_Implementation(AStableRidingHorse* Horse,bool bHold)
{
    if(!Player.IsValid()||!IsValid(Horse)||Horse->IsMarketShowcase()||Horse->IsRetreating()||Horse->Visit()!=EStableHorseVisit::Present||bAwaitingHorseImpact||
        UPlayerKnockdownComponent::IsKnockedDown(Player.Get()))return;
    if(Active())
    {
        if(!bHold||State.Horse!=Horse||State.Phase!=ERiderPhase::Seated||Horse->InJump()||
            !Horse->GetCharacterMovement()->IsMovingOnGround())return;
        if(const auto* Tool=Player->FindComponentByClass<UProductionToolComponent>();Tool&&Tool->IsLeapStrikeActive())return;
        FVector Floor;
        bool bRight=State.bFromRight;
        if(!SideSpot(*Horse,Floor,bRight,false))
        {
            bRight=!bRight;
            if(!SideSpot(*Horse,Floor,bRight,false))return;
        }
        if(GetNetMode()!=NM_DedicatedServer && !LoadTransfer(Player->GetMesh()->GetSkeletalMeshAsset(),bRight,false))return;
        State.bFromRight=bRight;
        Horse->Halt();
        State.Ground=Floor;
        State.Start=FTransform(FRotator(0,Horse->GetActorRotation().Yaw+(bRight?-68.f:68.f),0),Floor);
        SetPhase(ERiderPhase::Dismounting);
        return;
    }
    const auto* Health=Player->FindComponentByClass<UFPSCombatHealthComponent>();
    if(AFPSGAMEPlayerController::BlocksOngoingActions(Cast<APlayerController>(Player->GetController()))||
        Focus()!=Horse||Horse->InJump()||Horse->GetRider()||(Horse->GetLeader()&&Horse->GetLeader()!=Player.Get())||(Health&&Health->IsDead())||
        UFPSFurnitureRestComponent::IsResting(Player.Get())||Player->IsTraversing()||Player->IsDodging()||
        Player->IsSliding())return;
    if(!MayUseResident(*Horse))return;
    if(!bHold)
    {
        if(Horse->GetLeader()==Player.Get()){Horse->SetLeader(nullptr);LedHorse.Reset();return;}
        if(!ClaimHorse(*Horse))return;
        if(LedHorse.IsValid()&&LedHorse->GetLeader()==Player.Get())LedHorse->SetLeader(nullptr);
        Horse->SetLeader(Player.Get());LedHorse=Horse;
        return;
    }
    // Rebind a streamed-back titled horse before a rider can use its fresh default vitals.
    if(Horse->Keeper().IsValid() && Horse!=GetOwnedHorse() && !ClaimHorse(*Horse))return;
    FVector Floor;
    const bool bRight=FVector::DotProduct(Player->GetActorLocation()-Horse->Saddle(),Horse->GetActorRightVector())>0.;
    if(Player->bIsCrouched||!Player->GetCharacterMovement()->IsMovingOnGround()||!SideSpot(*Horse,Floor,bRight,true))return;
    if(GetNetMode()!=NM_DedicatedServer && !LoadTransfer(Player->GetMesh()->GetSkeletalMeshAsset(),bRight,true))return;
    if(LedHorse.IsValid()&&LedHorse->GetLeader()==Player.Get())LedHorse->SetLeader(nullptr);
    LedHorse.Reset();
    State.Horse=Horse;
    State.bFromRight=bRight;
    State.bLeapExit=false;
    State.ThrowVelocity=FVector::ZeroVector;
    State.Start=FTransform(FRotator(0,Horse->GetActorRotation().Yaw+(bRight?-68.f:68.f),0),Floor);
    State.Ground=Floor;
    Horse->SetRider(Player.Get());
    SetPhase(ERiderPhase::Mounting);
}
FString UHorseRiderComponent::TransferPackage(bool Female,bool Right,bool Mount)
{
    return FString::Printf(TEXT("/Game/WorldGeneration/TemperateHills/VillageStable/Horses/RiderTransferR18/A_%s_%s_%s"),
        Female?TEXT("Kaitlin"):TEXT("Jason"),Mount?TEXT("Mount"):TEXT("Dismount"),Right?TEXT("R"):TEXT("L"));
}
UAnimSequence* UHorseRiderComponent::LoadTransfer(const USkeletalMesh* Asset,bool Right,bool Mount)
{
    if(!Asset)return nullptr;
    if(Asset!=TransferBody.Get() || Right!=bClipFromRight || Mount!=bClipMount || !TransferClip)
    {
        const FString Path=TransferPackage(Asset->GetName().Contains(TEXT("Kaitlin")),Right,Mount);
        TransferClip=LoadObject<UAnimSequence>(nullptr,*(Path+TEXT(".")+FPaths::GetCleanFilename(Path)));
        TransferBody=Asset;bClipFromRight=Right;bClipMount=Mount;
    }
    return TransferClip;
}
UAnimSequence* UHorseRiderComponent::FixedTransferFor(const USkeletalMesh* Asset)
{
    return Transferring()?LoadTransfer(Asset,State.bFromRight,IsMounting()):nullptr;
}
void UHorseRiderComponent::SetPhase(ERiderPhase Phase)
{
    State.Phase=Phase;
    State.Since=Clock();
    ApplyState();
    Player->ForceNetUpdate();
}
void UHorseRiderComponent::ApplyState()
{
    if(!Player.IsValid())return;
    auto* Pawn=Player.Get();
    // An observer can receive a different mount without receiving the intermediate on-foot update.
    if(Active() && IsValid(State.Horse) && bApplied && AppliedHorse.Get()!=State.Horse)
    {
        if(auto* Previous=AppliedHorse.Get())
        {
            RemoveTickPrerequisiteComponent(Previous->GetCharacterMovement());
            RemoveTickPrerequisiteComponent(Previous->GetMesh());
            Pawn->GetCapsuleComponent()->IgnoreActorWhenMoving(Previous,false);
        }
        Pawn->bUseControllerRotationYaw=bSavedControllerYaw;
        bApplied=false;
    }
    if(Active()&&IsValid(State.Horse)&&!bApplied)
    {
        bApplied=true;
        AppliedHorse=State.Horse;
        LastDrive=FIntPoint::ZeroValue;bLastCanter=false;
        LastHeading=State.Horse->GetActorRotation().Yaw;
        EntryYawTravel=FMath::FindDeltaAngleDegrees(Pawn->GetControlRotation().Yaw,LastHeading);
        AppliedEntryYaw=0.f;
        bSavedControllerYaw=Pawn->bUseControllerRotationYaw;
        Pawn->bUseControllerRotationYaw=false;
        if(IsMounting())Pawn->SetActorLocationAndRotation(State.Start.GetLocation(),State.Start.GetRotation(),
            false,nullptr,ETeleportType::TeleportPhysics);
        Pawn->GetCharacterMovement()->StopMovementImmediately();
        Pawn->GetCharacterMovement()->DisableMovement();
        Pawn->GetCapsuleComponent()->IgnoreActorWhenMoving(State.Horse,true);
        AddTickPrerequisiteComponent(State.Horse->GetCharacterMovement());
        AddTickPrerequisiteComponent(State.Horse->GetMesh());
        Pawn->GetMesh()->AddTickPrerequisiteComponent(this);
        SetComponentTickEnabled(true);
    }
    else if(!Active()&&bApplied)
    {
        bApplied=false;
        if(AppliedHorse.IsValid())
        {
            RemoveTickPrerequisiteComponent(AppliedHorse->GetCharacterMovement());
            RemoveTickPrerequisiteComponent(AppliedHorse->GetMesh());
            if(State.bLeapExit)DepartedHorse=AppliedHorse;
            else Pawn->GetCapsuleComponent()->IgnoreActorWhenMoving(AppliedHorse.Get(),false);
        }
        Pawn->GetMesh()->RemoveTickPrerequisiteComponent(this);
        AppliedHorse.Reset();
        Pawn->bUseControllerRotationYaw=bSavedControllerYaw;
        const auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();
        if(!State.bLeapExit&&(!Health||!Health->IsDead()))
        {
            Pawn->SetActorLocation(State.Ground,false,nullptr,ETeleportType::TeleportPhysics);
            Pawn->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
        }
        if(!State.ThrowVelocity.IsNearlyZero() && (!Health||!Health->IsDead()) &&
            (Pawn->HasAuthority()||Pawn->IsLocallyControlled()))
        {
            // Autonomous riders also leave MOVE_None locally. A delayed state packet
            // must not replay an old launch after a server movement correction.
            auto* Move=Pawn->GetCharacterMovement();
            if(Pawn->HasAuthority() || Clock()-State.Since<.35f)
            {
                Move->SetMovementMode(MOVE_Falling);
                Pawn->LaunchCharacter(State.ThrowVelocity,true,true);
            }
            else if(Move->MovementMode==MOVE_None)Move->SetMovementMode(MOVE_Falling);
        }
        SetComponentTickEnabled(bAwaitingHorseImpact||DepartedHorse.IsValid());
        ViewSeatHorse.Reset();ViewSeatCorrection=FVector::ZeroVector;ViewStrideWeight=0.f;
        Axes=FVector2D::ZeroVector;bCanter=false;EyeBob=0;CanterEnvelope=0;EyeInertia=FVector::ZeroVector;SeatCompression=0.f;CanterRotation=FRotator::ZeroRotator;
    }
    // The seated capsule already has MOVE_None. Combat uses the controller's
    // movement lock to detect interruptions, so only take our lock for the transfer.
    auto* DesiredLock=Transferring()?Pawn->GetController():nullptr;
    if(InputOwner.Get()!=DesiredLock)
    {
        if(InputOwner.IsValid())InputOwner->SetIgnoreMoveInput(false);
        InputOwner=DesiredLock;
        if(DesiredLock)
        {
            if(Pawn->IsLocallyControlled())Pawn->InterruptActionsForPriority(false);
            DesiredLock->SetIgnoreMoveInput(true);
        }
    }
    LastDrive=FIntPoint::ZeroValue;bLastCanter=false;
    if(auto* Body=Pawn->FindComponentByClass<UFPSPlayerBodyComponent>())Body->RefreshViewMode();
}
FRotator UHorseRiderComponent::RiderFacing(float P) const
{
    if(State.Phase==ERiderPhase::Seated && Player.IsValid())
    {
        // The normal weapon graph is authored facing aim. Simulated riders receive that yaw
        // in the character's replicated movement, independently of the horse's heading.
        const float Yaw=Player->GetController()?Player->GetControlRotation().Yaw:Player->GetActorRotation().Yaw;
        return FRotator(0,Yaw,0);
    }
    const float StartYaw=State.Start.Rotator().Yaw;
    const float HorseYaw=State.Horse->GetActorRotation().Yaw;
    const float FaceStirrup=HorseYaw+(State.bFromRight?-68.f:68.f);
    const float Approach=StartYaw+FMath::FindDeltaAngleDegrees(StartYaw,FaceStirrup)*StableRide::Ease(P,0.f,.23f);
    return FRotator(0,Approach+FMath::FindDeltaAngleDegrees(FaceStirrup,HorseYaw)*StableRide::Ease(P,.30f,.81f),0);
}
FVector UHorseRiderComponent::RiderRoot(float P) const
{
    const FVector SeatUp=State.Phase==ERiderPhase::Seated?State.Horse->GroundTilt().GetUpVector():FVector::UpVector;
    const FVector Seat=State.Horse->Saddle()+SeatUp*6.f;
    const FVector NearSide=State.Horse->GetActorRightVector()*(State.bFromRight?1.f:-1.f);
    const FVector Approach=State.Ground;
    const FVector AboveStirrup=Seat+NearSide*35.f+State.Horse->GetActorForwardVector()*7.f+FVector(0,0,15);
    // Load the ground leg before rising into the near iron; land with flexed knees on descent.
    const float Load=StableRide::Ease(P,.14f,.28f)*(1.f-StableRide::Ease(P,.28f,.46f));
    const FVector Loaded=Approach-FVector(0,0,(State.Phase==ERiderPhase::Dismounting?8.f:5.f)*Load);
    const FVector Stand=FMath::Lerp(Loaded,AboveStirrup,StableRide::Ease(P,.31f,.64f));
    return FMath::Lerp(Stand,Seat,StableRide::Ease(P,.57f,.99f));
}
void UHorseRiderComponent::UpdateInput()
{
    auto* PC=Cast<AFPSGAMEPlayerController>(Player->GetController());
    const auto* Tool=Player->FindComponentByClass<UProductionToolComponent>();
    const auto* Client=GetWorld()->GetGameViewport();
    const FViewport* Viewport=Client?Client->Viewport:nullptr;
    const bool bHasFocus=!Viewport || Viewport->HasFocus() || Viewport->HasMouseCapture();
    const bool Allowed=PC&&bHasFocus&&!PC->bShowMouseCursor&&!PC->IsGameMenuOpen()&&(!Tool||!Tool->IsLeapStrikeActive());
    const FIntPoint Drive=Allowed?FIntPoint(FMath::RoundToInt(Axes.X*100),FMath::RoundToInt(Axes.Y*100)):FIntPoint::ZeroValue;
    const bool Fast=Allowed&&bCanter;
    if(Drive==LastDrive&&Fast==bLastCanter)return;
    LastDrive=Drive;bLastCanter=Fast;
    ServerDrive(State.Horse,Drive.Y,Drive.X,Fast);
}
void UHorseRiderComponent::RequestHorseJump()
{
    const auto* PC=Player.IsValid()?Cast<AFPSGAMEPlayerController>(Player->GetController()):nullptr;
    if(PC&&PC->IsLocalController()&&!PC->IsGameMenuOpen()&&!AFPSGAMEPlayerController::BlocksOngoingActions(PC)&&
        State.Phase==ERiderPhase::Seated&&IsValid(State.Horse)&&!State.Horse->InJump())
        ServerHorseJump(State.Horse);
}
void UHorseRiderComponent::ServerHorseJump_Implementation(AStableRidingHorse* Horse)
{
    if(!Player.IsValid()||!IsValid(Horse)||Horse!=State.Horse||Horse->GetRider()!=Player.Get()||
        State.Phase!=ERiderPhase::Seated)return;
    if(AFPSGAMEPlayerController::BlocksOngoingActions(Cast<APlayerController>(Player->GetController())))return;
    if(const auto* Tool=Player->FindComponentByClass<UProductionToolComponent>();Tool&&Tool->IsLeapStrikeActive())return;
    Horse->BeginRiddenJump();
}
void UHorseRiderComponent::ServerDrive_Implementation(AStableRidingHorse* Horse,int8 Forward,int8 Turn,bool Fast)
{
    if(IsValid(Horse)&&!Horse->IsRetreating()&&Horse==State.Horse&&Horse->GetRider()==Player.Get()&&State.Phase==ERiderPhase::Seated)
    {
        const auto* Tool=Player->FindComponentByClass<UProductionToolComponent>();
        if(!Tool||!Tool->IsLeapStrikeActive())Horse->Drive(Forward*.01f,Turn*.01f,Fast);
    }
}
void UHorseRiderComponent::LeaveSeatForLeap()
{
    if(State.Phase!=ERiderPhase::Seated||!Player.IsValid())return;
    State.Ground=Player->GetActorLocation();
    State.bLeapExit=true;
    if(Player->HasAuthority())Release();
    else
    {
        State.Horse=nullptr;
        State.Phase=ERiderPhase::OnFoot;
        ApplyState();
    }
}
void UHorseRiderComponent::ThrowFromHorse(AStableRidingHorse& Horse)
{
    auto* Pawn=Player.Get();
    if(!Pawn||!Pawn->HasAuthority()||State.Horse!=&Horse||Horse.GetRider()!=Pawn||!Active())return;
    // Prefer the side the rider came from; when a wall is close, throw into
    // the clearest available lane. Character movement sweeps the actual fall.
    const FVector Side=Horse.GetActorRightVector()*(State.bFromRight?1.f:-1.f);
    const FVector Back=-Horse.GetActorForwardVector();
    const FVector At=Pawn->GetActorLocation();
    const auto* Capsule=Pawn->GetCapsuleComponent();
    const auto Shape=FCollisionShape::MakeCapsule(Capsule->GetScaledCapsuleRadius(),Capsule->GetScaledCapsuleHalfHeight());
    FCollisionQueryParams Query(SCENE_QUERY_STAT(HorseThrow),false,Pawn);
    Query.AddIgnoredActor(&Horse);
    FVector Direction=Side;
    float Best=-1.f;
    for(const FVector& Option:{(Side+.45f*Back).GetSafeNormal2D(),(-Side+.45f*Back).GetSafeNormal2D(),Back,-Back})
    {
        FHitResult Hit;
        const bool Blocked=GetWorld()->SweepSingleByChannel(Hit,At,At+Option*140.f,FQuat::Identity,ECC_Pawn,Shape,Query);
        const float Room=Blocked?Hit.Time:1.f;
        if(Room>Best){Best=Room;Direction=Option;}
        if(!Blocked)break;
    }
    State.Ground=At;
    State.bLeapExit=true;
    State.ThrowVelocity=Direction*290.f+FVector(0,0,125.f);
    bAwaitingHorseImpact=true;
    Release();
}
void UHorseRiderComponent::Release()
{
    auto* Previous=State.Horse.Get();
    if(IsValid(Previous)&&Previous->GetRider()==Player.Get())Previous->SetRider(nullptr);
    if(Previous && DismissAfterDismount.Get()==Previous)
    {
        DismissAfterDismount.Reset();
        if(!State.bLeapExit&&!Previous->IsRetreating())Previous->BeginVisit(EStableHorseVisit::Departing,Player.Get());
    }
    State.Horse=nullptr;
    SetPhase(ERiderPhase::OnFoot);
}
void UHorseRiderComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Fn)
{
    Super::TickComponent(Delta,Type,Fn);
    if(!Player.IsValid())return;
    auto* Pawn=Player.Get();
    if(DepartedHorse.IsValid())
    {
        const auto* Former=DepartedHorse.Get();
        const auto* A=Pawn->GetCapsuleComponent();const auto* B=Former->GetCapsuleComponent();
        const FVector Gap=A->GetComponentLocation()-B->GetComponentLocation();
        if(Former==State.Horse)DepartedHorse.Reset();
        else if(Gap.Size2D()>A->GetScaledCapsuleRadius()+B->GetScaledCapsuleRadius()+2.f ||
            FMath::Abs(Gap.Z)>A->GetScaledCapsuleHalfHeight()+B->GetScaledCapsuleHalfHeight()+2.f)
        {
            Pawn->GetCapsuleComponent()->IgnoreActorWhenMoving(DepartedHorse.Get(),false);
            DepartedHorse.Reset();
        }
    }
    if(!Active())
    {
        if(bAwaitingHorseImpact)
        {
            auto* Move=Pawn->GetCharacterMovement();
            auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();
            if(!Health||Health->IsDead()||!Pawn->GetController()||Move->IsSwimming()||Move->IsFlying())bAwaitingHorseImpact=false;
            else if(Move->IsMovingOnGround())
            {
                bAwaitingHorseImpact=false;
                // The same fixed environmental HP loss as other survival impacts:
                // one fifth of CURRENT HP, after the triggering hit, without armor or a second horse hit.
                Health->ApplySurvivalDamage(Health->Health*.20f);
                if(auto* Down=UPlayerKnockdownComponent::GetOrCreate(Pawn))Down->Apply();
            }
        }
        SetComponentTickEnabled(bAwaitingHorseImpact||DepartedHorse.IsValid());
        return;
    }
    auto* Horse=State.Horse.Get();
    if(Pawn->HasAuthority())
    {
        const auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();
        if(!IsValid(Horse)||!Pawn->GetController()||(Health&&Health->IsDead()))
        {
            if(!IsValid(Horse))State.Ground=Pawn->GetActorLocation();
            else if(!SideSpot(*Horse,State.Ground,State.bFromRight,false))
                SideSpot(*Horse,State.Ground,!State.bFromRight,false);
            Release();return;
        }
    }
    if(!IsValid(Horse))return;
    float P=MountAmount();
    if(Pawn->HasAuthority()&&!Horse->IsRetreating()&&State.Phase==ERiderPhase::Dismounting&&P<=0.f)
    {
        if(ClearGround(*Horse,State.Ground)){Release();return;}
        DismissAfterDismount.Reset();
        SetPhase(ERiderPhase::Seated);P=1.f;
    }
    if(Pawn->IsLocallyControlled()&&State.Phase==ERiderPhase::Mounting)
    {
        if(auto* PC=Pawn->GetController())
        {
            const float Desired=EntryYawTravel*StableRide::Ease(P,.22f,.94f);
            FRotator Look=PC->GetControlRotation();
            Look.Yaw+=Desired-AppliedEntryYaw;
            PC->SetControlRotation(Look);
            AppliedEntryYaw=Desired;
        }
    }
    if(Pawn->HasAuthority()&&State.Phase==ERiderPhase::Mounting&&P>=1.f)SetPhase(ERiderPhase::Seated);
    const float Heading=Horse->GetActorRotation().Yaw;
    if(Pawn->IsLocallyControlled()&&State.Phase==ERiderPhase::Seated)
    {
        UpdateInput();
        if(auto* PC=Pawn->GetController())
        {
            FRotator Look=PC->GetControlRotation();
            Look.Yaw+=FMath::FindDeltaAngleDegrees(LastHeading,Heading);
            PC->SetControlRotation(Look);
        }
    }
    LastHeading=Heading;
    Pawn->SetActorLocationAndRotation(RiderRoot(P),RiderFacing(P),false,nullptr,ETeleportType::None);
    const float Speed=Horse->GetVelocity().Size2D();
    auto* Gait=Horse->GetMesh()->GetSingleNodeInstance();
    const float Cycle=Gait?Gait->GetLength():0.f;
    const float Phase=Cycle>0.f?2.f*PI*Gait->GetCurrentTime()/Cycle:0.f;
    const bool Canter=State.Phase==ERiderPhase::Seated&&Horse->PlayingCanter()&&Cycle>0.f;
    const float Alpha=1.f-FMath::Exp(-12.f*Delta);
    CanterEnvelope=FMath::Lerp(CanterEnvelope,Canter?FMath::SmoothStep(300.f,900.f,Speed):0.f,Alpha);
    const bool bWalking=State.Phase==ERiderPhase::Seated&&!Canter&&!Horse->InJump()&&(Speed>10.f||Horse->IsSteppingInPlace())&&Cycle>0.f;
    // The capsule follows the animated saddle. Remove the requested share of its local
    // stride only from the rendered view. Terrain elevation, jumps and the rider's seat stay physical.
    if (Pawn->IsLocallyControlled() && State.Phase==ERiderPhase::Seated && !Horse->InJump())
    {
        const FTransform& MeshWorld=Horse->GetMesh()->GetComponentTransform();
        const FVector FittedSeatLocal=Horse->GetMesh()->GetSocketTransform(TEXT("saddle_socket"),RTS_Component).GetLocation();
        // Strip ground-fit tilt & stair offset so ViewSeatCorrection damps only authored gait stride bob.
        const FQuat LocalGroundTilt=MeshWorld.GetRotation().Inverse()*Horse->GroundTilt()*MeshWorld.GetRotation();
        const FVector LocalGroundShift=MeshWorld.InverseTransformVector(Horse->GroundOffset());
        const FVector SeatLocal=LocalGroundTilt.UnrotateVector(FittedSeatLocal-LocalGroundShift);
        if (ViewSeatHorse.Get()!=Horse)
        {
            ViewSeatHorse=Horse;
            RestSeatLocal=SeatLocal;
            ViewStrideWeight=0.f;
        }
        const bool bStride=bWalking || Canter;
        ViewStrideWeight=FMath::FInterpConstantTo(ViewStrideWeight,bStride?1.f:0.f,Delta,6.f);
        if (!bStride && ViewStrideWeight<=0.f) RestSeatLocal=SeatLocal;
        ViewSeatCorrection=Horse->GroundTilt().RotateVector(MeshWorld.TransformVector(RestSeatLocal-SeatLocal))*((1.f-GaitViewScale)*ViewStrideWeight);
    }
    else
    {
        ViewSeatHorse.Reset();
        ViewStrideWeight=0.f;
        ViewSeatCorrection=FVector::ZeroVector;
    }
    const float WalkBob=bWalking?2.f*FMath::Sin(2.f*Phase):0.f;
    EyeBob=FMath::Lerp(EyeBob,WalkBob,Alpha);
    // Keep the seat, rider and rendered eye on the evaluated stride, including remote mounts.
    const float Walk=bWalking?FMath::Max(FMath::Clamp(Speed/220.f,0.f,1.f),.35f*FMath::Abs(Horse->GetPivotWeight())):0.f;
    const float Bounce=FMath::Sin(Phase-.42f);
    const float Run=Canter?CanterEnvelope:0.f;
    SeatCompression=FMath::Lerp(SeatCompression,Run*1.85f*Bounce+Walk*.5f*FMath::Sin(2.f*Phase),Alpha);
    const FVector RelativeEye=Horse->GetActorForwardVector()*(Run*.95f*FMath::Cos(Phase))
        +Horse->GetActorRightVector()*(Run*.65f*FMath::Sin(Phase)+Walk*.4f*FMath::Cos(Phase))
        +FVector::UpVector*(Run*2.35f*Bounce+Walk*.72f*FMath::Sin(2.f*Phase));
    EyeInertia=FMath::Lerp(EyeInertia,RelativeEye,1.f-FMath::Exp(-26.f*Delta));
    // The native canter reaches its lowest saddle at 1/4 cycle, highest at 3/4.
    // The pelvis and eye already follow that socket. Add only the rider's settling motion.
    const FRotator Beat=Canter?FRotator(.72f*FMath::Cos(Phase)-.18f*FMath::Sin(2.f*Phase),0,
        .30f*FMath::Sin(Phase)):FRotator::ZeroRotator;
    CanterRotation=FMath::Lerp(CanterRotation,Beat*CanterEnvelope,Alpha);
}
void UHorseRiderComponent::EndPlay(EEndPlayReason::Type Reason)
{
    GetWorld()->GetTimerManager().ClearTimer(HoldTimer);
    if(GetOwner()->HasAuthority()&&LedHorse.IsValid()&&LedHorse->GetLeader()==Player.Get())LedHorse->SetLeader(nullptr);
    if(bApplied&&Player.IsValid())
    {
        if(GetOwner()->HasAuthority()&&IsValid(State.Horse)&&State.Horse->GetRider()==Player.Get())State.Horse->SetRider(nullptr);
        State.Ground=Player->GetActorLocation();
        State.Phase=ERiderPhase::OnFoot;
        ApplyState();
    }
    if(GetOwner()->HasAuthority()&&IsValid(OwnedHorse)&&!OwnedHorse->IsRetreating())
    {
        OwnedHorse->CacheKeeperCondition();
        if(Reason==EEndPlayReason::Destroyed && !GetWorld()->bIsTearingDown && !OwnedHorse->GetRider())
            OwnedHorse->BeginVisit(EStableHorseVisit::Departing,Player.Get());
    }
    Super::EndPlay(Reason);
}
