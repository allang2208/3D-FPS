#include "RootCrownRigPreview.h"
#include "RootCrownSlashTiming.h"
#include "RootCrownNeedleProjectile.h"
#include "RootCrownNeedleOutlets.h"
#include "FPSCombatHealthComponent.h"
#include "../Combat/RangedAttackQuery.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/World.h"
#include "Engine/SkeletalMesh.h"
#include "Kismet/GameplayStatics.h"

void ARootCrownRigPreview::InitializeNeedleOutlets()
{
    if(!VisualMesh)return;
    const auto& Ref=VisualMesh->GetRefSkeleton();
    for(int32 I=0;I<3;++I)
    {
        const auto& Outlet=RootCrownNeedleOutlets::Points[I];
        const int32 Index=Ref.FindBoneIndex(Outlet.Bone);if(Index==INDEX_NONE)continue;
        FTransform Bone=Ref.GetRefBonePose()[Index];
        for(int32 Parent=Ref.GetParentIndex(Index);Parent!=INDEX_NONE;Parent=Ref.GetParentIndex(Parent))
            Bone*=Ref.GetRefBonePose()[Parent];
        NeedleOutletLocal[I]=Bone.InverseTransformPosition(Outlet.MeshPoint);
    }
}
FVector ARootCrownRigPreview::NeedleMuzzle(int32 Wave) const
{
    const int32 I=FMath::Clamp(Wave,0,2);
    // Actual front-surface points on the upper three blades, driven by their
    // rim bones rather than fixed actor-space points in the middle of the fan.
    return GetMesh()->GetSocketTransform(RootCrownNeedleOutlets::Points[I].Bone).TransformPosition(NeedleOutletLocal[I])
        +GetActorForwardVector()*4.f;
}
bool ARootCrownRigPreview::CanNeedle(APawn* Victim) const
{
    if(Busy() || !NeedleClip || !NeedleMesh || !NeedleMaterial || ActionClock()<NextNeedleAt ||
        !GetCharacterMovement()->IsMovingOnGround() || !IsValid(Victim) || !Victim->IsPlayerControlled())return false;
    const auto* Vitals=Victim->FindComponentByClass<UFPSCombatHealthComponent>();if(Vitals&&Vitals->IsDead())return false;
    const FVector Delta=Victim->GetActorLocation()-GetActorLocation();
    if(Delta.Size2D()<NeedleMinRange || Delta.Size()>NeedleMaxRange ||
        FVector::DotProduct(Delta.GetSafeNormal2D(),GetActorForwardVector())<.8f)return false;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(RootCrownNeedleSight),false,this);Query.AddIgnoredActor(Victim);
    FHitResult Block;
    return !RangedAttackQuery::LineTraceSingle(GetWorld(),this,Block,NeedleMuzzle(1),Victim->GetActorLocation(),ECC_Visibility,Query);
}
void ARootCrownRigPreview::TickNeedles(float Age)
{
    if(NextNeedleWave==0 && Age>=RootCrownNeedleTiming::FirstShot)
    {
        const auto* Vitals=Target.IsValid()?Target->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
        if(!Target.IsValid() || (Vitals&&Vitals->IsDead())){FinishSlash();return;}
        FCollisionQueryParams Query(SCENE_QUERY_STAT(RootCrownNeedleLock),false,this);Query.AddIgnoredActor(Target.Get());FHitResult Block;
        if(RangedAttackQuery::LineTraceSingle(GetWorld(),this,Block,NeedleMuzzle(1),Target->GetActorLocation(),ECC_Visibility,Query)){FinishSlash();return;}
        // Every volley aims around this one immutable point. Subsequent player
        // motion cannot steer the two unreleased sectors or any flying needle.
        LockedNeedleAim=Target->GetActorLocation();
    }
    while(IsNeedleFiring() && NextNeedleWave<3 && Age>=RootCrownNeedleTiming::FirstShot+RootCrownNeedleTiming::Interval*NextNeedleWave)
        ReleaseNeedles(NextNeedleWave++);
    if(Age>=RootCrownNeedleTiming::End)FinishSlash();
}
void ARootCrownRigPreview::ReleaseNeedles(int32 Wave)
{
    const FVector Origin=NeedleMuzzle(Wave);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(RootCrownNeedleMuzzle),false,this);FHitResult Block;
    if(RangedAttackQuery::LineTraceSingle(GetWorld(),this,Block,GetNavAgentLocation()+FVector(0,0,120),Origin,ECC_Visibility,Query))return;
    const FVector Aim=(LockedNeedleAim-Origin).GetSafeNormal();
    const float Sector=(Wave-1)*12.f;
    for(int32 I=0;I<5;++I)
    {
        const FVector Direction=Aim.RotateAngleAxis(Sector+(I-2)*2.5f,FVector::UpVector);
        const FTransform Transform(Direction.Rotation(),Origin);
        auto* Needle=GetWorld()->SpawnActorDeferred<ARootCrownNeedleProjectile>(ARootCrownNeedleProjectile::StaticClass(),Transform,this,this,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
        if(!Needle)continue;
        FlyingNeedles.RemoveAll([](const auto& Existing){return !Existing.IsValid();});FlyingNeedles.Add(Needle);
        Needle->Launch(this,Direction,NeedleSalvo,Wave);UGameplayStatics::FinishSpawningActor(Needle,Transform);
    }
}
bool ARootCrownRigPreview::RegisterNeedleHit(uint32 Salvo,int32 Wave,AActor* Victim)
{
    if(!HasAuthority() || Salvo!=NeedleSalvo || Wave<0 || Wave>=3 || !IsValid(Victim) || NeedleVictims[Wave].Contains(Victim))return false;
    // Five visible pins define each lane, but one player takes one hit per
    // volley. Earlier pins remain valid while the actor starts a melee action.
    NeedleVictims[Wave].Add(Victim);return true;
}
