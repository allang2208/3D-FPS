#include "M66IncineratorMonster.h"
#include "M66BackMist.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"

void AM66IncineratorMonster::PrepareBackSmokeOutlets()
{
    const auto* Asset=GetMesh()->GetSkeletalMeshAsset();if(!Asset)return;
    const auto& Ref=Asset->GetRefSkeleton();
    const FName Names[]={TEXT("M66_Vent_High_Tip"),TEXT("M66_Vent_Rear_Tip"),TEXT("M66_Vent_Front_Tip"),TEXT("M66_Vent_Lateral_Tip")};
    // V10 rim centres, source-derived and converted by ForceFrontXAxis. Bind
    // inversion includes the imported container's 100x scale and bone axes.
    const FVector Points[]={FVector(-20.1609,-31.7492,381.1637),FVector(-7.7330,5.7901,370.2825),
        FVector(16.6050,-7.1127,370.8715),FVector(-19.9401,-55.3581,368.4476)};
    for(int32 I=0;I<4;++I)
    {
        BackSmokeBones[I]=Ref.FindBoneIndex(Names[I]);if(BackSmokeBones[I]==INDEX_NONE)continue;
        FTransform Bind=Ref.GetRefBonePose()[BackSmokeBones[I]];
        for(int32 Parent=Ref.GetParentIndex(BackSmokeBones[I]);Parent!=INDEX_NONE;Parent=Ref.GetParentIndex(Parent))Bind*=Ref.GetRefBonePose()[Parent];
        BackSmokeLocalOutlets[I]=Bind.InverseTransformPosition(Points[I]);
    }
}
FVector AM66IncineratorMonster::BackSmokeOutlet(int32 Index) const
{
    const int32 I=FMath::Clamp(Index,0,3);
    return BackSmokeBones[I]!=INDEX_NONE?GetMesh()->GetBoneTransform(BackSmokeBones[I]).TransformPosition(BackSmokeLocalOutlets[I]):GetNavAgentLocation()+FVector(0,0,360);
}
void AM66IncineratorMonster::StartBackSmoke()
{
    if(!HasAuthority()||!bEnableBackSmoke||Dead()||BackMist)return;
    const FTransform Spawn(GetActorRotation(),BackSmokeOutlet(0));
    BackMist=GetWorld()->SpawnActorDeferred<AM66BackMist>(AM66BackMist::StaticClass(),Spawn,this,this,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
    if(!BackMist)return;
    BackMist->Radius=BackSmokeRadius;BackMist->BlindSeconds=BackSmokeBlindSeconds;BackMist->SmokeLifetime=BackSmokeHoldSeconds;
    UGameplayStatics::FinishSpawningActor(BackMist,Spawn);
    BackMist->AttachToActor(this,FAttachmentTransformRules::KeepWorldTransform);
}
void AM66IncineratorMonster::StopBackSmoke()
{if(BackMist){BackMist->StopEmission();BackMist=nullptr;}}
void AM66IncineratorMonster::EndPlay(const EEndPlayReason::Type Reason)
{StopBackSmoke();Super::EndPlay(Reason);}
