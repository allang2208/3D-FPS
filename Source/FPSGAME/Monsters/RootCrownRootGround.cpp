#include "RootCrownRootField.h"
#include "RootCrownRigPreview.h"
#include "RootCrownSlashTiming.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"

bool ARootCrownRootField::TraceScene(const FVector& A,const FVector& B,FHitResult& Hit) const
{
    FCollisionQueryParams Query(SCENE_QUERY_STAT(RootCrownGroundPath),true,this);
    if(Source)Query.AddIgnoredActor(Source);
    for(int32 Skip=0;Skip<16;++Skip)
    {
        if(!GetWorld()->LineTraceSingleByChannel(Hit,A,B,ECC_Visibility,Query))return false;
        AActor* Actor=Hit.GetActor();
        // Ownership alone does not make an obstacle transparent: a player's
        // ice wall or placed cover must still stop roots at ground level.
        if(!Actor||(!Cast<APawn>(Actor)&&!Cast<APawn>(Actor->GetAttachParentActor())))return true;
        Query.AddIgnoredActor(Actor);
    }
    return true;
}
bool ARootCrownRootField::FloorAt(const FVector& Expected,FVector& Out,FVector* Normal) const
{
    FHitResult Hit;
    if(!TraceScene(Expected+FVector(0,0,45),Expected-FVector(0,0,65),Hit)||Hit.bStartPenetrating||Hit.ImpactNormal.Z<.65f)return false;
    Out=Hit.ImpactPoint;if(Normal)*Normal=Hit.ImpactNormal;return true;
}
bool ARootCrownRootField::GroundPath(const FVector& Start,const FVector& End,FRootCrownGroundPath& Path) const
{
    FVector Previous;if(!FloorAt(Start,Previous))return false;
    Path.Points.Reset();Path.Points.Add(Previous);
    const int32 Steps=FMath::CeilToInt(FVector::Dist2D(Start,End)/35.f);if(Steps<1||Steps>64)return false;
    for(int32 I=1;I<=Steps;++I)
    {
        FVector Expected=FMath::Lerp(Start,End,float(I)/Steps);Expected.Z=Previous.Z;
        FVector Floor;if(!FloorAt(Expected,Floor)||FMath::Abs(Floor.Z-Previous.Z)>40.f)return false;
        // Stepped support is allowed; vertical floors/walls and unsupported
        // gaps stop propagation. The query never drops to a lower storey.
        FHitResult Block;const float Top=FMath::Max(Previous.Z,Floor.Z)+12.f;
        if(TraceScene(FVector(Previous.X,Previous.Y,Top),FVector(Floor.X,Floor.Y,Top),Block))return false;
        Path.Points.Add(Floor);Previous=Floor;
    }
    return FMath::Abs(Previous.Z-End.Z)<=40.f;
}
bool ARootCrownRootField::PathOpen(const FRootCrownGroundPath& Path) const
{
    for(int32 I=1;I<Path.Points.Num();++I)
    {
        const FVector A=Path.Points[I-1],B=Path.Points[I];FHitResult Block;
        const float Top=FMath::Max(A.Z,B.Z)+12.f;
        if(TraceScene(FVector(A.X,A.Y,Top),FVector(B.X,B.Y,Top),Block))return false;
        FVector Floor;if(!FloorAt(B,Floor)||FMath::Abs(Floor.Z-B.Z)>10.f)return false;
    }
    return true;
}
bool ARootCrownRootField::Prepare(ARootCrownRigPreview* Crown,APawn* Target)
{
    Source=Crown;StartedAt=Crown->ActionClock();
    TriggerRadius=FMath::Max(1.f,Crown->MineTriggerRadius);BlastRadius=FMath::Max(TriggerRadius,Crown->MineBlastRadius);
    FuseSeconds=FMath::Max(.1f,Crown->MineFuseSeconds);Lifetime=FMath::Max(1.f,Crown->MineLifetime);BlastDamage=Crown->RootDamage;
    FVector Center;if(!FloorAt(Target->GetNavAgentLocation(),Center))return false;
    const FVector Forward=(Center-Crown->GetActorLocation()).GetSafeNormal2D();
    FVector Nodes[3];Mines.SetNum(3);
    for(int32 I=0;I<3;++I)
    {
        FVector Normal;
        if(!FloorAt(Center+Forward.RotateAngleAxis(120.f*I,FVector::UpVector)*RootCrownRootTiming::AreaRadius,Nodes[I],&Normal))return false;
        Mines[I].Position=Nodes[I];Mines[I].Normal=Normal;Mines[I].ChangedAt=StartedAt;
        Health[I]=Crown->RootKnotHealth;
    }
    static const FName Feet[]={TEXT("Bone_002"),TEXT("Bone_005"),TEXT("Bone_009")};
    Paths.SetNum(3);
    for(int32 I=0;I<3;++I)
        if(!GroundPath(Crown->GetMesh()->GetSocketLocation(Feet[I]),Nodes[I],Paths[I]))return false;
    SetLifeSpan(RootCrownRootTiming::Warning+Lifetime+FuseSeconds+RootCrownRootTiming::BurstVisualSeconds+.5f);return true;
}
