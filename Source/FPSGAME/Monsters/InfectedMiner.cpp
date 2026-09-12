#include "InfectedMiner.h"
#include "MonsterCombatComponent.h"
#include "Components/SceneComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "TimerManager.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Engine/SkeletalMesh.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"
#include "PhysicsEngine/PhysicsConstraintTemplate.h"
#include "Misc/PackageName.h"
#include "Engine/Engine.h"
#include "EngineUtils.h"
#include "NavigationSystem.h"
#include "NavigationData.h"
#if WITH_EDITOR
#include "Animation/Skeleton.h"
#include "Rendering/SkeletalMeshModel.h"
#include "Rendering/SkeletalMeshLODModel.h"
#endif

AInfectedMiner::AInfectedMiner():Super()
{
    Tags.Remove(TEXT("NurseZombie")); Tags.Add(TEXT("InfectedMiner"));
    MaxHealth=180.f; AttackDamage=24.f; AttackRange=150.f;
    AggroRadius=1100.f; WalkSpeed=55.f; ContactTime=1.5f; ContactEnd=1.75f;
    RecoveryTime=1.15f; CorpseSeconds=20.f; ExperienceReward=280;
}
void AInfectedMiner::BeginPlay()
{
    Super::BeginPlay();
    UE_LOG(LogTemp,Display,TEXT("MINER_READY %s mesh=%s"),*GetName(),*GetNameSafe(GetMesh()->GetSkeletalMeshAsset()));
}
float AInfectedMiner::TakeDamage(float Damage,const FDamageEvent& Event,AController* EventInstigator,AActor* Causer)
{
    const float Applied=Super::TakeDamage(Damage,Event,EventInstigator,Causer);
    if(State==ENurseState::Dead&&GetMesh()->GetSkeletalMeshAsset())
    {
        const FName Root=GetMesh()->GetSkeletalMeshAsset()->GetRefSkeleton().GetBoneName(0);
        if(Root!=TEXT("pelvis"))if(auto* Body=GetMesh()->GetBodyInstance(Root))Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    }
    return Applied;
}
UPhysicsAsset* AInfectedMiner::CreatePhysicsAsset(USkeletalMesh* Mesh)
{
#if WITH_EDITOR
    if(!Mesh)return nullptr;
    const FString Path=FPackageName::GetLongPackagePath(Mesh->GetOutermost()->GetName())/TEXT("PA_InfectedMiner");auto* Package=CreatePackage(*Path);
    auto* Asset=FindObject<UPhysicsAsset>(Package,TEXT("PA_InfectedMiner"));if(!Asset)Asset=NewObject<UPhysicsAsset>(Package,TEXT("PA_InfectedMiner"),RF_Public|RF_Standalone|RF_Transactional);
    Asset->Modify();Asset->SkeletalBodySetups.Empty();Asset->ConstraintSetup.Empty();Asset->CollisionDisableTable.Empty();
    const auto& Ref=Mesh->GetRefSkeleton();TArray<FTransform> CS=Ref.GetRefBonePose();for(int32 I=0;I<CS.Num();++I)if(Ref.GetParentIndex(I)>=0)CS[I]=CS[I]*CS[Ref.GetParentIndex(I)];
    TArray<FName> Names;
    if(Ref.GetBoneName(0)!=TEXT("pelvis"))Names.Add(Ref.GetBoneName(0));
    for(const TCHAR* Name:{TEXT("pelvis"),TEXT("spine_01"),TEXT("spine_03"),TEXT("spine_05"),TEXT("neck_02"),TEXT("head"),TEXT("upperarm_l"),TEXT("lowerarm_l"),TEXT("hand_l"),TEXT("upperarm_r"),TEXT("lowerarm_r"),TEXT("hand_r"),TEXT("thigh_l"),TEXT("calf_l"),TEXT("foot_l"),TEXT("thigh_r"),TEXT("calf_r"),TEXT("foot_r")})if(Ref.FindBoneIndex(Name)!=INDEX_NONE)Names.Add(Name);
    TArray<TArray<FVector>> Points;Points.SetNum(Names.Num());
    if(auto* Model=Mesh->GetImportedModel())if(Model->LODModels.Num())for(const auto& Section:Model->LODModels[0].Sections)for(const auto& V:Section.SoftVertices)
    {
        int32 Best=0;for(int32 J=1;J<MAX_TOTAL_INFLUENCES;++J)if(V.InfluenceWeights[J]>V.InfluenceWeights[Best])Best=J;
        int32 Bone=Section.BoneMap[V.InfluenceBones[Best]],Region=INDEX_NONE;
        while(Bone>=0){Region=Names.Find(Ref.GetBoneName(Bone));if(Region!=INDEX_NONE)break;Bone=Ref.GetParentIndex(Bone);}
        if(Region!=INDEX_NONE)Points[Region].Add(CS[Bone].InverseTransformPosition(FVector(V.Position)));
    }
    for(int32 I=0;I<Names.Num();++I)
    {
        const int32 B=Ref.FindBoneIndex(Names[I]);auto* Setup=NewObject<USkeletalBodySetup>(Asset,NAME_None,RF_Transactional);Setup->BoneName=Names[I];Setup->PhysicsType=PhysType_Default;Setup->CollisionTraceFlag=CTF_UseSimpleAsComplex;
        if(Points[I].Num()>8){FKConvexElem Hull;Hull.VertexData=Points[I];Hull.UpdateElemBox();Setup->AggGeom.ConvexElems.Add(Hull);}
        else{FKSphereElem Sphere;Sphere.Radius=2.f/CS[B].GetScale3D().GetAbsMax();Setup->AggGeom.SphereElems.Add(Sphere);}
        Setup->DefaultInstance.SetCollisionProfileName(TEXT("Ragdoll"));Setup->DefaultInstance.LinearDamping=2;Setup->DefaultInstance.AngularDamping=5;Setup->DefaultInstance.SetMassOverride(Names[I]==TEXT("pelvis")?12.f:4.f);Setup->DefaultInstance.bUseCCD=true;Setup->DefaultInstance.PositionSolverIterationCount=16;Setup->DefaultInstance.VelocitySolverIterationCount=8;
        Setup->InvalidatePhysicsData();Setup->CreatePhysicsMeshes();Asset->SkeletalBodySetups.Add(Setup);
        int32 Parent=Ref.GetParentIndex(B);while(Parent>=0&&!Names.Contains(Ref.GetBoneName(Parent)))Parent=Ref.GetParentIndex(Parent);
        if(Parent>=0)
        {
            auto* C=NewObject<UPhysicsConstraintTemplate>(Asset,NAME_None,RF_Transactional);auto& D=C->DefaultInstance;D.JointName=Names[I];D.ConstraintBone1=Names[I];D.ConstraintBone2=Ref.GetBoneName(Parent);
            FTransform Anchor(FQuat::Identity,CS[B].GetLocation());D.SetRefFrame(EConstraintFrame::Frame1,Anchor.GetRelativeTransform(CS[B]));D.SetRefFrame(EConstraintFrame::Frame2,Anchor.GetRelativeTransform(CS[Parent]));
            D.SetLinearXLimit(LCM_Locked,0);D.SetLinearYLimit(LCM_Locked,0);D.SetLinearZLimit(LCM_Locked,0);D.SetAngularSwing1Limit(ACM_Limited,40);D.SetAngularSwing2Limit(ACM_Limited,35);D.SetAngularTwistLimit(ACM_Limited,22);D.SetDisableCollision(true);Asset->ConstraintSetup.Add(C);
        }
    }
    for(int32 I=0;I<Names.Num();++I)for(int32 J=I+1;J<Names.Num();++J)Asset->DisableCollision(I,J);
    // Non-adjacent head/torso and leg bodies keep a fallen miner from folding
    // through itself, while adjacent skinning regions can safely overlap.
    for(FName Torso:{FName(TEXT("head")),FName(TEXT("spine_05")),FName(TEXT("pelvis"))})
        for(FName Leg:{FName(TEXT("calf_l")),FName(TEXT("calf_r"))})
            if(Names.Contains(Torso)&&Names.Contains(Leg))Asset->EnableCollision(Names.IndexOfByKey(Torso),Names.IndexOfByKey(Leg));
    Asset->UpdateBodySetupIndexMap();Asset->UpdateBoundsBodiesArray();Asset->MarkPackageDirty();Mesh->SetPhysicsAsset(Asset);Mesh->MarkPackageDirty();return Asset;
#else
    return nullptr;
#endif
}
bool AInfectedMiner::BakeTestNavigation(UObject* Context)
{
#if WITH_EDITOR
    UWorld* World=GEngine->GetWorldFromContextObject(Context,EGetWorldErrorMode::ReturnNull);
    if(!World||!World->GetPackage()->GetName().StartsWith(TEXT("/Game/Tests/InfectedMiner/")))return false;
    auto* Nav=FNavigationSystem::GetCurrent<UNavigationSystemV1>(World);if(!Nav)return false;
    Nav->Build();
    for(TActorIterator<ANavigationData> It(World);It;++It){It->EnsureBuildCompletion();It->MarkPackageDirty();}
    FNavLocation P;const bool Ready=Nav->ProjectPointToNavigation(FVector(-450,0,0),P,FVector(80,80,160));
    UE_LOG(LogTemp,Display,TEXT("MINER_NAV_BAKED projected=%d point=%s"),Ready,*P.Location.ToString());return Ready;
#else
    return false;
#endif
}
AInfectedMinerSpawner::AInfectedMinerSpawner()
{
    RootComponent=CreateDefaultSubobject<USceneComponent>(TEXT("SpawnOrigin"));
    PrimaryActorTick.bCanEverTick=false;
}
void AInfectedMinerSpawner::BeginPlay()
{
    Super::BeginPlay();
    // The legacy nurse fixture expects two nurses; this subclass is a separate encounter.
    if(HasAuthority()&&!FParse::Param(FCommandLine::Get(),TEXT("NurseAudit")))SpawnMiner();
}
void AInfectedMinerSpawner::EndPlay(const EEndPlayReason::Type Reason)
{
    GetWorldTimerManager().ClearTimer(RespawnTimer);
    if(IsValid(LiveMiner))LiveMiner->OnDestroyed.RemoveDynamic(this,&AInfectedMinerSpawner::MinerDestroyed);
    Super::EndPlay(Reason);
}
void AInfectedMinerSpawner::SpawnMiner()
{
    if(!HasAuthority()||IsValid(LiveMiner)||!MonsterClass)return;
    FActorSpawnParameters Params;Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButDontSpawnIfColliding;
    LiveMiner=GetWorld()->SpawnActor<AInfectedMiner>(MonsterClass,GetActorTransform(),Params);
    if(LiveMiner){LiveMiner->OnDestroyed.AddDynamic(this,&AInfectedMinerSpawner::MinerDestroyed);UE_LOG(LogTemp,Display,TEXT("MINER_SPAWNED %s at %s"),*LiveMiner->GetName(),*LiveMiner->GetActorLocation().ToString());}
    else GetWorldTimerManager().SetTimer(RespawnTimer,this,&AInfectedMinerSpawner::SpawnMiner,5.f,false);
}
void AInfectedMinerSpawner::MinerDestroyed(AActor* Actor)
{
    LiveMiner=nullptr;
    if(!IsActorBeingDestroyed())GetWorldTimerManager().SetTimer(RespawnTimer,this,&AInfectedMinerSpawner::SpawnMiner,FMath::Max(.1f,RespawnSeconds),false);
}
