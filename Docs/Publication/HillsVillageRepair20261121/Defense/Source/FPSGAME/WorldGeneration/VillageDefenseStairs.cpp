#include "VillageDefenseStairs.h"
#include "HighVillageCollapse.h"
#include "TemperateHillsWorld.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "PhysicsEngine/BodySetup.h"

const FSoftObjectPath& AVillageDefenseStairs::StairMeshPath()
{
    static const FSoftObjectPath Path(TEXT("/Game/WorldGeneration/TemperateHills/HighVillageDefense/SM_WallAccessStairs.SM_WallAccessStairs"));
    return Path;
}

void AVillageDefenseStairs::PostInitializeComponents()
{
    Super::PostInitializeComponents();
    if(HasAuthority() && IsPlayerBuilt())
        if(auto* Hills=Cast<ATemperateHillsWorld>(GetOwner()))
            Hills->RefreshVillageGateStairs(this);
}

void AVillageDefenseStairs::Destroyed()
{
    auto* Hills=Cast<ATemperateHillsWorld>(GetOwner());
    Super::Destroyed();
    if(HasAuthority() && IsPlayerBuilt() && IsValid(Hills) && GetWorld() && !GetWorld()->bIsTearingDown)
        Hills->RefreshVillageGateStairs();
}

FVector AVillageDefenseStairs::TargetPoint(const FVector& From) const
{
    // Both a low first riser and the 3.6 m landing are valid attack surfaces.
    FVector Point;
    if(Masonry->GetClosestPointOnCollision(From,Point)>=0.f)return Point;
    return Super::TargetPoint(From);
}

void AVillageDefenseStairs::GetRepairBounds(TArray<FBox>& OutBounds) const
{
    const UStaticMesh* Mesh=Masonry->GetStaticMesh();
    const UBodySetup* Body=Mesh?Mesh->GetBodySetup():nullptr;
    OutBounds.Reset();
    if(!Body)return;
    OutBounds.Reserve(Body->AggGeom.BoxElems.Num());
    for(const FKBoxElem& Tread:Body->AggGeom.BoxElems)
        OutBounds.Add(Tread.CalcAABB(FTransform::Identity,1.f));
}

bool AVillageDefenseStairs::IsRepairSiteClear() const
{
    TArray<FBox> Treads;
    GetRepairBounds(Treads);
    if(Treads.IsEmpty())return false;
    const FTransform& Placement=Masonry->GetComponentTransform();
    const FCollisionQueryParams Query(SCENE_QUERY_STAT(VillageStairRepair),false,this);
    const FCollisionObjectQueryParams Pawns(ECC_Pawn);
    for(const FBox& Tread:Treads)
        if(GetWorld()->OverlapAnyTestByObjectType(Placement.TransformPosition(Tread.GetCenter()),
            Placement.GetRotation(),Pawns,FCollisionShape::MakeBox(Tread.GetExtent()*Placement.GetScale3D().GetAbs()),Query))
            return false;
    return true;
}

void AVillageDefenseStairs::PresentCollapse(const FVector& Direction,int32 Seed,float)
{
    AHighVillageCollapse::Stairs(*this,Direction,Seed);
}
