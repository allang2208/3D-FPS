#include "BoundCongregate.h"
#include "BoundCongregateAnimInstance.h"
#include "Animation/AnimSequence.h"
#include "Components/BoxComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

// Explicit user-requested melee review. No BeginPlay, AI, player or saves.
int32 ReviewBoundCongregateMeleeV17()
{
    const auto Settings=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(true)
        .RequiresHitProxies(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    auto* World=UWorld::CreateWorld(EWorldType::Game,false,TEXT("CongregateMeleeV17Review"),nullptr,true,ERHIFeatureLevel::Num,&Settings);
    if(!World)return 1;
    UClass* Type=LoadClass<ABoundCongregate>(nullptr,TEXT("/Game/Monsters/BoundCongregate/BP_BoundCongregate.BP_BoundCongregate_C"));
    if(!Type){World->DestroyWorld(false);return 1;}
    FActorSpawnParameters Spawn;Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    auto* Ground=World->SpawnActor<AActor>(AActor::StaticClass(),FVector(0,0,-50),FRotator::ZeroRotator,Spawn);
    auto* Box=NewObject<UBoxComponent>(Ground);Ground->SetRootComponent(Box);Box->SetBoxExtent(FVector(5000,5000,50));
    Box->SetCollisionProfileName(TEXT("BlockAll"));Box->RegisterComponent();Box->SetWorldLocation(FVector(0,0,-50));
    FString Report=TEXT("Scope: current saved Bite/Flurry through actual animation proxy, with/without floor IK at 60/120 Hz. Cloth/AI/combat execution/PIE not simulated.\n");
    bool Finite=true;
    for(const bool Flurry:{false,true})for(const int32 Fps:{60,120})
    {
        TArray<TArray<FTransform>> Baseline;
        for(const bool WithFloor:{false,true})
        {
            auto* Monster=World->SpawnActor<ABoundCongregate>(Type,FVector(0,0,225),FRotator::ZeroRotator,Spawn);
            auto* Mesh=Monster->GetMesh();auto* Move=Monster->GetCharacterMovement();
            Mesh->bDisableClothSimulation=true;Mesh->bEnableUpdateRateOptimizations=false;
            Move->SetMovementMode(WithFloor?MOVE_Walking:MOVE_Flying);Mesh->InitAnim(true);
            auto* Anim=Cast<UBoundCongregateAnimInstance>(Mesh->GetAnimInstance());
            auto* Clip=Flurry?Monster->FlurryClip.Get():Monster->BiteClip.Get();
            if(!Anim||!Clip){World->DestroyWorld(false);return 1;}
            Monster->NetState.State=Flurry?EBoundCongregateState::Flurry:EBoundCongregateState::Bite;
            Anim->TransitionTo(Clip,false,true,0.f);Anim->PreviousPose.Reset();Anim->OutgoingLoop=nullptr;
            const auto& Ref=Mesh->GetSkeletalMeshAsset()->GetRefSkeleton();
            const float Dt=1.f/Fps;const int32 Last=FMath::RoundToInt(Clip->GetPlayLength()*Fps);
            TArray<FTransform> First,Previous;
            double SupportDrift=0,KneeDeviation=0,MaxAngle=0,MinFootZ=1.e9;
            // Settle floor traces/correction before measuring the clip.
            for(int32 Warm=0;Warm<30;++Warm){Anim->SetCombatTime(0);++GFrameCounter;Mesh->TickAnimation(Dt,false);Mesh->RefreshBoneTransforms();}
            for(int32 Frame=0;Frame<=Last;++Frame)
            {
                const float Time=FMath::Min(Frame*Dt,Clip->GetPlayLength());
                Monster->NetState.StartedAt=World->GetTimeSeconds()-Time;
                Anim->SetCombatTime(Time);++GFrameCounter;Mesh->TickAnimation(Dt,false);Mesh->RefreshBoneTransforms();
                const auto& Pose=Mesh->GetComponentSpaceTransforms();
                if(!WithFloor)Baseline.Add(Pose);
                if(Frame==0)First=Pose;
                for(int32 Bone=0;Bone<Pose.Num();++Bone)
                {
                    Finite&=!Pose[Bone].ContainsNaN();
                    const FString Name=Ref.GetBoneName(Bone).ToString();
                    if(!Name.StartsWith(TEXT("leg_")))continue;
                    if(Frame>0)MaxAngle=FMath::Max(MaxAngle,double(FMath::RadiansToDegrees(Pose[Bone].GetRotation().AngularDistance(Previous[Bone].GetRotation()))));
                    if(WithFloor&&Name.EndsWith(TEXT("_lower")))KneeDeviation=FMath::Max(KneeDeviation,FVector::Distance(Pose[Bone].GetLocation(),Baseline[Frame][Bone].GetLocation()));
                    if(Name.EndsWith(TEXT("_foot")))
                    {
                        MinFootZ=FMath::Min(MinFootZ,Mesh->GetComponentTransform().TransformPosition(Pose[Bone].GetLocation()).Z);
                        if(!(Flurry&&(Name==TEXT("leg_L1_foot")||Name==TEXT("leg_R1_foot"))))
                            SupportDrift=FMath::Max(SupportDrift,FVector::Distance(Pose[Bone].GetLocation(),First[Bone].GetLocation()));
                    }
                }
                Previous=Pose;
            }
            Report+=FString::Printf(TEXT("clip=%s fps=%d floor_ik=%d finite=%d support_drift_cm=%.6f knee_ik_deviation_cm=%.6f max_leg_angle_per_frame=%.6f min_ankle_world_z_cm=%.6f\n"),
                *Clip->GetName(),Fps,WithFloor,Finite,SupportDrift,KneeDeviation,MaxAngle,MinFootZ);
            Monster->Destroy();
        }
    }
    const FString Path=FPaths::ProjectDir()/TEXT("SourceAssets/BoundCongregateMeshy20261006/MeleeV17/Review/native_proxy_review.txt");
    const bool Saved=FFileHelper::SaveStringToFile(Report,*Path,FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
    World->DestroyWorld(false);UE_LOG(LogTemp,Display,TEXT("MELEE_V17_PROXY_REVIEW finite=%d saved=%d"),Finite,Saved);
    return Finite&&Saved?0:1;
}
