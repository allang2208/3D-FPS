#include "M66IncineratorMonster.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"

namespace M66Cleft
{
// Accepted V17 source rig coordinates, metres (X lateral, -Y front, Z up).
// The same four landmarks are used by V17's mouth import to preserve FBX
// axis conversion and the 100x container scale without actor-space guesses.
const FName Bones[]={TEXT("Bone_001"),TEXT("Bone_006"),TEXT("Bone_010"),TEXT("Bone_015")};
const FVector Source[]={
    FVector(.319140494,.244921774,1.818359017),
    FVector(.185546815,-.066796809,2.144921303),
    FVector(.898047745,.081640244,.452735305),
    FVector(-.215236038,.541796803,.452733755)};
}

void AM66IncineratorMonster::PrepareCleftWeakpoint(const TArray<FTransform>& ReferencePose)
{
    bCleftFrameReady=false;
    const auto* RigAsset=GetMesh()->GetSkeletalMeshAsset();if(!RigAsset)return;
    const auto& Ref=RigAsset->GetRefSkeleton();int32 Indices[4];FVector Imported[4];
    for(int32 I=0;I<4;++I)
    {
        Indices[I]=Ref.FindBoneIndex(M66Cleft::Bones[I]);
        if(!ReferencePose.IsValidIndex(Indices[I]))return;
        Imported[I]=ReferencePose[Indices[I]].GetLocation();
    }
    const FMatrix ImportedBasis(Imported[1]-Imported[0],Imported[2]-Imported[0],Imported[3]-Imported[0],Imported[0]);
    if(FMath::Abs(ImportedBasis.Determinant())<SMALL_NUMBER)return;
    const auto& P=M66Cleft::Source;
    const FMatrix SourceBasis(P[1]-P[0],P[2]-P[0],P[3]-P[0],P[0]);
    const FMatrix ReferenceToSource=ImportedBasis.Inverse()*SourceBasis;
    for(int32 I=0;I<2;++I)
        CleftBoneToSource[I]=ReferencePose[Indices[I]].ToMatrixWithScale()*ReferenceToSource;
    bCleftFrameReady=true;
}

bool AM66IncineratorMonster::IsWeakpointHit(const FHitResult& Hit) const
{
    // Classify the actual first skeletal contact, never a second trace through
    // an intervening hand/arm. Network hit receipts can omit Component.
    // Keep classification after lethal damage for the existing hit feedback.
    if(!bCleftFrameReady||Hit.GetActor()!=this||(Hit.GetComponent()&&Hit.GetComponent()!=GetMesh()))return false;
    const int32 Slot=Hit.BoneName==M66Cleft::Bones[0]?0:(Hit.BoneName==M66Cleft::Bones[1]?1:INDEX_NONE);
    if(Slot==INDEX_NONE)return false;
    const FTransform Current=GetMesh()->GetSocketTransform(Hit.BoneName);
    const FVector Point(CleftBoneToSource[Slot].TransformPosition(Current.InverseTransformPosition(Hit.ImpactPoint)));
    // A tapered central opening, not the whole torso bone. Depth excludes the
    // back and inner side surfaces of the existing convex collision bodies.
    if(Point.Y< -1.02||Point.Y>-.30)return false;
    const double Side=(Point.X-.08)/.30,Height=(Point.Z-2.15)/.75;
    if(Side*Side+Height*Height>1.)return false;
    FVector Incoming=Hit.TraceEnd-Hit.TraceStart;
    if(Incoming.IsNearlyZero())Incoming=-Hit.ImpactNormal;
    if(!Incoming.IsNearlyZero())
    {
        const FVector Direction(CleftBoneToSource[Slot].TransformVector(Current.InverseTransformVector(Incoming)));
        if(Direction.GetSafeNormal().Y<.20)return false;
    }
    return true;
}
