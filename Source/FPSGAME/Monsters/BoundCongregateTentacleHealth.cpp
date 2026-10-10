#include "BoundCongregate.h"
#include "BoundCongregateTentacleGround.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"

namespace BoundTentacleHealth
{
constexpr int32 First=7,Last=56;
const FName HitTag(TEXT("BoundCongregateTentacle"));
FName Bone(int32 I){return FName(FString::Printf(TEXT("attack_tentacle_%02d"),I));}
}

void ABoundCongregate::UpdateTentacleHitShapeState()
{
    using namespace BoundTentacleHealth;
    if(!GetWorld()||!GetWorld()->IsGameWorld())return;
    const bool Enabled=TentacleActive()&&!TentacleRecovering()&&!Dead()&&TentacleHealth>0.f;
    if(Enabled&&TentacleHitShapes.IsEmpty())
        for(int32 I=First;I<Last;++I)
        {
            auto* Shape=NewObject<UCapsuleComponent>(this,FName(FString::Printf(TEXT("TentacleShot_%02d"),I)));
            AddInstanceComponent(Shape);Shape->SetupAttachment(GetMesh(),Bone(I));
            Shape->ComponentTags.Add(HitTag);Shape->SetCanEverAffectNavigation(false);
            Shape->SetGenerateOverlapEvents(false);Shape->SetCollisionEnabled(ECollisionEnabled::NoCollision);
            Shape->SetCollisionObjectType(ECC_WorldDynamic);Shape->SetCollisionResponseToAllChannels(ECR_Ignore);
            Shape->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);
            Shape->SetAbsolute(true,true,true);Shape->RegisterComponent();TentacleHitShapes.Add(Shape);
        }
    if(Enabled&&!TentaclePoseHandle.IsValid())
        TentaclePoseHandle=GetMesh()->RegisterOnBoneTransformsFinalizedDelegate(
            FOnBoneTransformsFinalizedMultiCast::FDelegate::CreateUObject(this,&ThisClass::UpdateTentacleHitShapes));
    if(!Enabled&&TentaclePoseHandle.IsValid())
    {GetMesh()->UnregisterOnBoneTransformsFinalizedDelegate(TentaclePoseHandle);TentaclePoseHandle.Reset();}
    for(const auto& Weak:TentacleHitShapes)if(auto* Shape=Weak.Get())
        Shape->SetCollisionEnabled(Enabled?ECollisionEnabled::QueryOnly:ECollisionEnabled::NoCollision);
    if(Enabled)UpdateTentacleHitShapes();
}

void ABoundCongregate::UpdateTentacleHitShapes()
{
    using namespace BoundTentacleHealth;
    // A fixed set of query-only capsules follows the final visible bone pose.
    // No additional actor tick, collision simulation or skeleton refresh.
    for(int32 I=0;I<TentacleHitShapes.Num();++I)if(auto* Shape=TentacleHitShapes[I].Get())
    {
        const int32 Index=First+I;
        const FVector A=GetMesh()->GetSocketLocation(Bone(Index)),B=GetMesh()->GetSocketLocation(Bone(Index+1));
        const float Radius=FCongregateTentacleGround::Radius(Index);
        Shape->SetCapsuleSize(Radius,FVector::Distance(A,B)*.5f+Radius,false);
        Shape->SetWorldLocationAndRotation((A+B)*.5f,FRotationMatrix::MakeFromZ(B-A).ToQuat(),false,nullptr,ETeleportType::TeleportPhysics);
    }
}

bool ABoundCongregate::IsTentaclePart(const FHitResult& Hit)
{
    using namespace BoundTentacleHealth;
    if(!Cast<ABoundCongregate>(Hit.GetActor()))return false;
    if(const auto* Shape=Hit.GetComponent();Shape&&Shape->ComponentHasTag(HitTag))return true;
    const FString Name=Hit.BoneName.ToString();
    if(!Name.StartsWith(TEXT("attack_tentacle_")))return false;
    int32 Index=INDEX_NONE;
    return LexTryParseString(Index,*Name.RightChop(16))&&Index>=0&&Index<=Last;
}

bool ABoundCongregate::IsTentacleHit(const FHitResult& Hit) const
{
    using namespace BoundTentacleHealth;
    if(!TentacleActive()||TentacleRecovering()||Dead()||TentacleHealth<=0.f||!IsTentaclePart(Hit))return false;
    if(const auto* Shape=Hit.GetComponent();Shape&&Shape->ComponentHasTag(HitTag))return true;
    int32 Index=INDEX_NONE;
    if(!LexTryParseString(Index,*Hit.BoneName.ToString().RightChop(16)))return false;
    const FVector A=GetMesh()->GetSocketLocation(Bone(Index));
    const FVector B=GetMesh()->GetSocketLocation(Bone(FMath::Min(Last,Index+1)));
    // Remote receipts carry the hit bone. Require proximity to its current
    // segment as well; a body hit must not spend the restraint's health pool.
    return FMath::PointDistToSegment(Hit.ImpactPoint,A,B)<=FCongregateTentacleGround::Radius(Index)+20.f;
}

float ABoundCongregate::ApplyTentacleShot(float Damage)
{
    if(!HasAuthority()||!TentacleActive()||TentacleRecovering()||Dead()||Damage<=0.f)return 0.f;
    const float Applied=FMath::Min(TentacleHealth,Damage);
    TentacleHealth-=Applied;ForceNetUpdate();
    if(TentacleHealth<=0.f){CancelTentacle();UpdateTentacleHitShapeState();}
    return Applied;
}
