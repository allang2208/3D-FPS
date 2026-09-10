#include "NurseZombie.h"
#include "FPSCombatHealthComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Engine/GameInstance.h"
#include "GameFramework/PlayerController.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Animation/Skeleton.h"
#if WITH_EDITOR
#include "Animation/AnimData/IAnimationDataModel.h"
#include "Animation/AnimData/IAnimationDataController.h"
#endif
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "Engine/Engine.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"

ANurseZombie::ANurseZombie()
{
    PrimaryActorTick.bCanEverTick = true;
    GetCapsuleComponent()->InitCapsuleSize(34.f, 92.f);
    GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Visibility, ECR_Ignore);
    GetMesh()->SetRelativeLocation(FVector(0,0,-92.f));
    GetMesh()->SetRelativeRotation(FRotator(0,-90.f,0));
    GetMesh()->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    GetMesh()->SetCollisionObjectType(ECC_Pawn);
    GetMesh()->SetCollisionResponseToAllChannels(ECR_Ignore);
    GetMesh()->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);
    GetMesh()->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    bUseControllerRotationYaw = false;
    GetCharacterMovement()->bRunPhysicsWithNoController = true;
    GetCharacterMovement()->bOrientRotationToMovement = true;
    GetCharacterMovement()->RotationRate = FRotator(0,180,0);
    GetCharacterMovement()->MaxStepHeight = 35.f;
    GetCharacterMovement()->bCanWalkOffLedges = false;
    Tags.Add(TEXT("Enemy"));
    Tags.Add(TEXT("NurseZombie"));
}

void ANurseZombie::OnConstruction(const FTransform& Transform)
{
    Super::OnConstruction(Transform);
    if (VisualMesh) GetMesh()->SetSkeletalMeshAsset(VisualMesh);
}

void ANurseZombie::BeginPlay()
{
    Super::BeginPlay();
    SpawnPosition=GetActorLocation();
    Health = MaxHealth;
    if (VisualMesh) GetMesh()->SetSkeletalMeshAsset(VisualMesh);
    GetCharacterMovement()->MaxWalkSpeed = WalkSpeed;
    if (!GetMesh()->GetSkeletalMeshAsset() || !IdleClip || !WalkClip || !AttackClip)
    {
        UE_LOG(LogTemp, Error, TEXT("NURSE_ASSET_MISSING %s"), *GetName());
        SetActorTickEnabled(false);
        return;
    }
    SetState(ENurseState::Idle);
    UE_LOG(LogTemp, Display, TEXT("NURSE_READY %s location=%s attack=%.3f"), *GetName(), *GetActorLocation().ToString(), AttackClip->GetPlayLength());
}

void ANurseZombie::SetState(ENurseState NewState)
{
    State = NewState;
    StateTime = 0.f;
    UAnimSequence* Clip = State == ENurseState::Chase ? WalkClip : State == ENurseState::Attack ? AttackClip : IdleClip;
    if (State != ENurseState::Dead && Clip)
    {
        GetMesh()->PlayAnimation(Clip, State != ENurseState::Attack);
        GetMesh()->SetPlayRate(1.f);
        if (State == ENurseState::Attack) GetMesh()->SetPlayRate(0.f); // Combat clock owns the exact animation time.
    }
    if (State != ENurseState::Chase) GetCharacterMovement()->StopMovementImmediately();
    if (State == ENurseState::Attack) bAttackConsumed = false;
}

bool ANurseZombie::CanSee(const AActor* Actor) const
{
    if (!IsValid(Actor)) return false;
    FHitResult Hit;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(NurseSight), false, this);
    Params.AddIgnoredActor(Actor);
    return !GetWorld()->LineTraceSingleByChannel(Hit, GetActorLocation()+FVector(0,0,35), Actor->GetActorLocation(), ECC_Visibility, Params);
}

void ANurseZombie::TryMelee()
{
    if (bAttackConsumed || !Target.IsValid()) return;
    const FVector Offset = Target->GetActorLocation() - GetActorLocation();
    if (Offset.Size2D() > AttackRange || FMath::Abs(Offset.Z) > 90.f ||
        FVector::DotProduct(GetActorForwardVector(),Offset.GetSafeNormal2D()) < .55f || !CanSee(Target.Get())) return;
    bAttackConsumed = true;
    UGameplayStatics::ApplyDamage(Target.Get(),AttackDamage,GetController(),this,nullptr);
    ++SuccessfulHits;
    UE_LOG(LogTemp, Display, TEXT("NURSE_MELEE time=%.3f hit=%d"),StateTime,SuccessfulHits);
}

void ANurseZombie::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (!HasAuthority() || State == ENurseState::Dead) return;
    const float Previous = StateTime;
    StateTime += DeltaSeconds;
    Cooldown = FMath::Max(0.f,Cooldown-DeltaSeconds);
    if (!Target.IsValid()) Target = UGameplayStatics::GetPlayerPawn(this,0);
    const UFPSCombatHealthComponent* TargetHealth = Target.IsValid() ? Target->FindComponentByClass<UFPSCombatHealthComponent>() : nullptr;
    if (!Target.IsValid() || (TargetHealth && TargetHealth->IsDead()))
    {
        Target.Reset();
        if (State != ENurseState::Idle) SetState(ENurseState::Idle);
        return;
    }
    if (State == ENurseState::Stagger)
    {
        if (StateTime >= StaggerSeconds) SetState(ENurseState::Idle);
        return;
    }
    if (State == ENurseState::Attack)
    {
        GetMesh()->SetPosition(FMath::Min(StateTime,AttackClip->GetPlayLength()),false);
        if (Previous <= ContactEnd && StateTime >= ContactTime) TryMelee();
        if (StateTime >= AttackClip->GetPlayLength())
        {
            Cooldown = RecoveryTime;
            SetState(ENurseState::Idle);
        }
        return;
    }
    const FVector Offset = Target->GetActorLocation() - GetActorLocation();
    const float Distance = Offset.Size2D();
    if (Distance > AggroRadius || !CanSee(Target.Get()))
    {
        if (State != ENurseState::Idle) SetState(ENurseState::Idle);
        return;
    }
    if (Distance <= AttackRange-15.f)
    {
        if (State != ENurseState::Idle) SetState(ENurseState::Idle);
        SetActorRotation(FRotator(0,Offset.Rotation().Yaw,0));
        if (Cooldown <= 0.f) SetState(ENurseState::Attack);
        return;
    }
    if (State != ENurseState::Chase) SetState(ENurseState::Chase);
    AddMovementInput(Offset.GetSafeNormal2D(),1.f,true);
    GetMesh()->SetPlayRate(FMath::Clamp(GetVelocity().Size2D()/26.f,.15f,3.5f));
}

void ANurseZombie::InterruptAttack(float Seconds)
{
    if (State == ENurseState::Dead) return;
    bAttackConsumed = true;
    StaggerSeconds = FMath::Max(.01f,Seconds);
    Cooldown = FMath::Max(Cooldown,.6f);
    SetState(ENurseState::Stagger);
}

float ANurseZombie::TakeDamage(float Damage, const FDamageEvent& Event, AController* EventInstigator, AActor* Causer)
{
    if (!HasAuthority() || State == ENurseState::Dead || Damage <= 0.f) return 0.f;
    const float Applied = FMath::Min(Health,Damage);
    Health -= Applied;
    Super::TakeDamage(Applied,Event,EventInstigator,Causer);
    if (Health > 0.f) InterruptAttack();
    else
    {
        SetState(ENurseState::Dead);
        bAttackConsumed = true;
        Target.Reset();
        GetCharacterMovement()->DisableMovement();
        GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        GetMesh()->SetCollisionProfileName(TEXT("Ragdoll"));
        GetMesh()->SetCollisionResponseToChannel(ECC_Pawn,ECR_Ignore);
        GetMesh()->SetSimulatePhysics(true);
        GetMesh()->WakeAllRigidBodies();
        GetMesh()->AddImpulse(-GetActorForwardVector()*110.f,TEXT("pelvis"),true);
        SetLifeSpan(CorpseSeconds);
        UE_LOG(LogTemp, Display, TEXT("NURSE_KILLED %s"),*GetName());
        if(auto* PlayerController=Cast<APlayerController>(EventInstigator))
            if(PlayerController->IsLocalController()&&GetGameInstance())
                GetGameInstance()->GetSubsystem<UColdSteelStatusModel>()->AwardKill(this,ExperienceReward);
    }
    return Applied;
}

bool ANurseZombie::PrepareInPlaceAnimation(UAnimSequence* Clip)
{
#if WITH_EDITOR
    if (!Clip || !Clip->GetPathName().StartsWith(TEXT("/Game/Monsters/NurseZombie/")) || !Clip->GetSkeleton()) return false;
    const FName Root = Clip->GetSkeleton()->GetReferenceSkeleton().GetBoneName(0);
    TArray<FTransform> Keys;
    Clip->GetDataModel()->GetBoneTrackTransforms(Root, Keys);
    if (Keys.Num()<2) return false;
    const FVector Drift = (Keys.Last().GetTranslation()-Keys[0].GetTranslation())*FVector(1,1,0);
    TArray<FVector> Positions,Scales;
    TArray<FQuat> Rotations;
    for (int32 Index=0;Index<Keys.Num();++Index)
    {
        Positions.Add(Keys[Index].GetTranslation()-Drift*(double(Index)/(Keys.Num()-1)));
        Rotations.Add(Keys[Index].GetRotation());
        Scales.Add(Keys[Index].GetScale3D());
    }
    const bool OK=Clip->GetController().SetBoneTrackKeys(Root,Positions,Rotations,Scales,false);
    UE_LOG(LogTemp,Display,TEXT("NURSE_INPLACE root=%s drift=%s frames=%d success=%d"),*Root.ToString(),*Drift.ToString(),Keys.Num(),OK);
    return OK;
#else
    return false;
#endif
}

bool ANurseZombie::FindTestSpawn(UObject* WorldContextObject,FVector Origin,FRotator Facing,float PreferredDistance,float Side,FVector& Location)
{
    UWorld* World=GEngine->GetWorldFromContextObject(WorldContextObject,EGetWorldErrorMode::ReturnNull);
    if (!World) return false;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(NursePlacement),false);
    for (TActorIterator<ANurseZombie> It(World);It;++It) Params.AddIgnoredActor(*It);
    for (float Distance : {PreferredDistance,350.f,250.f,450.f})
        for (float Yaw : {0.f,30.f,-30.f,60.f,-60.f,90.f,-90.f,180.f})
        {
            const FRotator Rotation(0,Facing.Yaw+Yaw,0);
            const FVector Near=Origin+Rotation.Vector()*Distance+FRotationMatrix(Rotation).GetUnitAxis(EAxis::Y)*Side;
            FHitResult Ground,Wall;
            if (!World->LineTraceSingleByChannel(Ground,Near+FVector(0,0,250),Near-FVector(0,0,600),ECC_Pawn,Params) || Ground.ImpactNormal.Z<.72f) continue;
            const FVector Candidate=Ground.ImpactPoint+FVector(0,0,96.f);
            if (FMath::Abs(Candidate.Z-Origin.Z)>75.f) continue;
            if (World->OverlapBlockingTestByChannel(Candidate,FQuat::Identity,ECC_Pawn,FCollisionShape::MakeCapsule(36.f,92.f),Params)) continue;
            if (World->LineTraceSingleByChannel(Wall,Origin+FVector(0,0,35),Candidate+FVector(0,0,35),ECC_Visibility,Params)) continue;
            // Swept capsule across the clearing avoids placement behind a low wall that sight rays clear.
            if (World->SweepSingleByChannel(Wall,Origin+FVector(0,0,15),Candidate+FVector(0,0,15),FQuat::Identity,ECC_Pawn,FCollisionShape::MakeCapsule(34.f,75.f),Params)) continue;
            Location=Candidate;
            return true;
        }
    return false;
}
