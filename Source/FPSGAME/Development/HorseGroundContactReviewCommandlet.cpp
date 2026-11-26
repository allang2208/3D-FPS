#include "HorseGroundContactReviewCommandlet.h"
#if WITH_EDITOR
#include "../Movement/StableRidingHorse.h"
#include "../Movement/StableHorseGroundMesh.h"
#include "../Movement/StableHorseAnimInstance.h"
#include "../Movement/HorseRiderComponent.h"
#include "../FPSGAMECharacter.h"
#include "Serialization/JsonSerializer.h"
#include "../Monsters/MonsterSurfaceAudit.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "Engine/Engine.h"
#include "Physics/Experimental/PhysScene_Chaos.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Animation/AnimSequence.h"
#include "AssetCompilingManager.h"
#include "Misc/FileHelper.h"

namespace HorseContactReview
{
constexpr double Length=700.;
double Height(double X,double Grade){return FMath::Clamp(X,0.,Length)*Grade;}
// Within each terrain segment both the triangle and the floor are planar. A
// minimum can only occur at a mesh vertex or where an edge crosses the crest.
double AtCrest(TConstArrayView<FVector> Points,TConstArrayView<uint32> Indices,double Grade,double Lowest)
{
    if(Grade==0.)return Lowest;
    FBox Bounds(ForceInit);for(const auto& P:Points)Bounds+=P;
    if(Bounds.Max.X<=Length||Bounds.Min.X>=Length)return Lowest;
    for(int I=0;I<Indices.Num();I+=3)
    {
        for(int J=0;J<3;++J)
        {
            const auto& A=Points[Indices[I+J]];const auto& B=Points[Indices[I+(J+1)%3]];
            if((A.X<Length)==(B.X<Length))continue;
            const double Z=FMath::Lerp(A.Z,B.Z,(Length-A.X)/(B.X-A.X));
            Lowest=FMath::Min(Lowest,Z-Length*Grade);
        }
    }
    return Lowest;
}
void AddSurface(UWorld& World,FVector A,FVector B)
{
    auto* Actor=World.SpawnActor<AActor>();
    auto* Box=NewObject<UBoxComponent>(Actor);
    Actor->AddInstanceComponent(Box);Actor->SetRootComponent(Box);
    const FRotator Rotation=(B-A).Rotation();
    Box->SetBoxExtent(FVector((B-A).Size()*.5,1600.,12.));
    Box->SetCollisionProfileName(TEXT("BlockAll"));
    Box->SetWorldLocationAndRotation((A+B)*.5-Rotation.RotateVector(FVector(0,0,12)),Rotation);
    Box->RegisterComponent();
}
}
#endif
int32 UHorseGroundContactReviewCommandlet::Main(const FString& Params)
{
#if WITH_EDITOR
    using namespace HorseContactReview;
    FString Dir;if(!FParse::Value(*Params,TEXT("Output="),Dir))return 1;
    IFileManager::Get().MakeDirectory(*Dir,true);
    const auto Settings=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(true)
        .RequiresHitProxies(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    auto* World=UWorld::CreateWorld(EWorldType::Game,false,TEXT("HorseContactReview"),nullptr,true,ERHIFeatureLevel::Num,&Settings);
    if(!World)return 2;
    GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
    World->InitializeActorsForPlay(FURL());
    auto* Horse=World->SpawnActor<AStableRidingHorse>();
    auto* Skin=Horse->GetMesh();auto* Move=Horse->GetCharacterMovement();
    if(!Skin->GetSkeletalMeshAsset()||!Horse->CanterAnimation||!Horse->WalkAnimation)return 3;
    FAssetCompilingManager::Get().FinishAllCompilation();
    const bool Raw=FParse::Param(*Params,TEXT("Raw"));
    if(Raw)
    {
        auto* Unfitted=NewObject<USkeletalMeshComponent>(Horse);
        Unfitted->SetupAttachment(Horse->GetRootComponent());
        Unfitted->SetSkeletalMeshAsset(Skin->GetSkeletalMeshAsset());
        Unfitted->SetRelativeTransform(Skin->GetRelativeTransform());
        Unfitted->SetCollisionEnabled(ECollisionEnabled::NoCollision);Unfitted->RegisterComponent();
        Skin=Unfitted;
    }
    Skin->SetAnimInstanceClass(UStableHorseAnimInstance::StaticClass());
    Skin->bEnableUpdateRateOptimizations=false;Skin->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    Skin->SetForcedLOD(1);
    auto* Asset=Skin->GetSkeletalMeshAsset();
    const auto& Ref=Asset->GetRefSkeleton();
    FName Feet[]={TEXT("finger_L"),TEXT("finger_R"),TEXT("toe_L"),TEXT("toe_R")};
    FVector BindFeet[4];
    FString Bones=TEXT("foot,x,y,z,qx,qy,qz,qw\n");
    for(int I=0;I<4;++I)
    {
        const auto B=Ref.GetBoneAbsoluteTransform(Ref.FindBoneIndex(Feet[I]));BindFeet[I]=B.GetTranslation();
        auto P=B.GetTranslation();auto Q=B.GetRotation();
        Bones+=FString::Printf(TEXT("%s,%.6f,%.6f,%.6f,%.9f,%.9f,%.9f,%.9f\n"),*Feet[I].ToString(),P.X,P.Y,P.Z,Q.X,Q.Y,Q.Z,Q.W);
    }
    FFileHelper::SaveStringToFile(Bones,*(Dir/TEXT("bones.csv")));
    const auto& LOD=Asset->GetResourceForRendering()->LODRenderData[0];
    const auto& Positions=LOD.StaticVertexBuffers.PositionVertexBuffer;
    FString LowestParts=TEXT("angle,yaw,x,clip,phase,min_cm,index,dominant_bone,bind_x,bind_y,bind_z,world_x,world_y,world_z\n");
    TArray<int8> Groups;Groups.Init(-1,Positions.GetNumVertices());
    FString Bind=TEXT("index,foot,x,y,z\n");
    for(int32 I=0;I<Groups.Num();++I)
    {
        const FVector P(Positions.VertexPosition(I));if(P.Z>24.)continue;
        int Best=0;for(int J=1;J<4;++J)if(FVector::DistSquared(P,BindFeet[J])<FVector::DistSquared(P,BindFeet[Best]))Best=J;
        Groups[I]=Best;
        Bind+=FString::Printf(TEXT("%d,%d,%.5f,%.5f,%.5f\n"),I,Best,P.X,P.Y,P.Z);
    }
    FFileHelper::SaveStringToFile(Bind,*(Dir/TEXT("bind.csv")));
    // Export the hull candidates directly from the formal LOD, with real skin weights.
    const auto* Weights=Skin->GetSkinWeightBuffer(0);
    FString Hull=TEXT("index,x,y,z,influences\n");
    for(int I=0;I<Groups.Num();++I)
    {
        int32 Section,Local;LOD.GetSectionFromVertexIndex(I,Section,Local);
        const auto& SectionData=LOD.RenderSections[Section];FString Influences;
        for(uint32 J=0;J<Weights->GetMaxBoneInfluences();++J)
        {
            const int32 W=Weights->GetBoneWeight(I,J);if(!W)continue;
            const int32 Bone=SectionData.BoneMap[Weights->GetBoneIndex(I,J)];
            Influences+=FString::Printf(TEXT("%s:%d;"),*Ref.GetBoneName(Bone).ToString(),W);
        }
        const FVector P(Positions.VertexPosition(I));
        Hull+=FString::Printf(TEXT("%d,%.4f,%.4f,%.4f,%s\n"),I,P.X,P.Y,P.Z,*Influences);
    }
    FFileHelper::SaveStringToFile(Hull,*(Dir/TEXT("vertices.csv")));
    TArray<uint32> Indices;LOD.MultiSizeIndexContainer.GetIndexBuffer(Indices);
    FFileHelper::SaveArrayToFile(MakeArrayView(reinterpret_cast<const uint8*>(Indices.GetData()),Indices.Num()*4),*(Dir/TEXT("triangles.bin")));
    auto* Pawn=World->SpawnActor<AFPSGAMECharacter>(FVector(-3000,0,120),FRotator::ZeroRotator);
    if(!Pawn)return 5;
    Pawn->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    auto* Ride=Pawn->FindComponentByClass<UHorseRiderComponent>();
    if(!Ride)return 5;
    Ride->Player=Pawn;Ride->State.Horse=Horse;Ride->State.Phase=ERiderPhase::Seated;
    FString Json;TSharedPtr<FJsonObject> Config;
    if(!FFileHelper::LoadFileToString(Json,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/player_body.json"))) ||
        !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Config))return 5;
    auto* RiderMesh=LoadObject<USkeletalMesh>(nullptr,*Config->GetStringField(TEXT("body_mesh")));
    if(!RiderMesh)return 5;
    auto* Body=NewObject<USkeletalMeshComponent>(Pawn);
    Body->SetupAttachment(Pawn->GetRootComponent());Body->RegisterComponent();Body->SetSkeletalMeshAsset(RiderMesh);
    Body->SetRelativeLocationAndRotation(FVector(0,0,-Pawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()),FRotator(0,-90,0));
    const auto& RiderRef=RiderMesh->GetRefSkeleton();
    auto RefCS=RiderRef.GetRefBonePose();
    for(int B=1;B<RefCS.Num();++B)RefCS[B]=RefCS[B]*RefCS[RiderRef.GetParentIndex(B)];
    const int Hip=RiderRef.FindBoneIndex(TEXT("pelvis")),Left=RiderRef.FindBoneIndex(TEXT("ball_l")),Right=RiderRef.FindBoneIndex(TEXT("ball_r"));
    if(Hip<0||Left<0||Right<0)return 5;
    auto SeatErrors=[&](double Yaw)
    {
        const FVector Root=Ride->RiderRoot(1.f);
        Pawn->SetActorLocationAndRotation(Root,FRotator(0,Yaw,0),false,nullptr,ETeleportType::TeleportPhysics);
        auto Pose=RefCS;Ride->BuildContactPose(*Body,Pose);
        auto W=[&](int B){return Body->GetComponentTransform().TransformPosition(Pose[B].GetLocation());};
        const auto Up=Horse->GroundTilt().GetUpVector();
        return FVector(FVector::Dist(W(Hip),Horse->Saddle()+Up*6.),FVector::Dist(W(Left),Horse->Stirrup(true)+Up*3.5),FVector::Dist(W(Right),Horse->Stirrup(false)+Up*3.5));
    };
    Move->SetUpdatedComponent(Horse->GetCapsuleComponent());
    const bool SmoothOffset=FParse::Param(*Params,TEXT("SmoothOffset"));
    const FTransform RestMesh=Skin->GetRelativeTransform();
    Move->SetWalkableFloorAngle(60.f);
    Move->SetMovementMode(MOVE_Walking);
    auto* Measured=Cast<UStableHorseGroundMesh>(Skin);
    if(Measured)Measured->bMeasureGroundFit=true;
    FString Timing=TEXT("slope,yaw,site,phase,fit_us\n");
    FString Rows=TEXT("angle,yaw,x,clip,phase,grounded,mesh_min_cm,surface_min_cm,front_l,front_r,rear_l,rear_r,saddle_x,saddle_y,saddle_z,seat_error,left_tread_error,right_tread_error\n");
    int Lane=0;
    for(double Angle:{0.,30.,45.,55.,59.,60.})
    {
        const double Grade=FMath::Tan(FMath::DegreesToRadians(Angle));
        const double Y=Lane++*4000.;
        AddSurface(*World,{-4000.,Y,0.},{0.,Y,0.});
        AddSurface(*World,{0.,Y,0.},{Length,Y,Length*Grade});
        AddSurface(*World,{Length,Y,Length*Grade},{4000.,Y,Length*Grade});
        World->GetPhysicsScene()->EnsureCollisionTreeIsBuilt(World);
        for(double Yaw:{0.,45.,90.,135.,180.,225.,270.,315.})for(double X:{-220.,-45.,0.,45.,350.,655.,700.,745.,920.})
        {
            const double Radius=Horse->GetCapsuleComponent()->GetScaledCapsuleRadius();
            double Base=Height(X,Grade);
            for(int K=-90;K<=90;++K)
            {
                const double A=FMath::DegreesToRadians(double(K));
                Base=FMath::Max(Base,Height(X+Radius*FMath::Sin(A),Grade)-Radius*(1.-FMath::Cos(A)));
            }
            Horse->SetActorLocationAndRotation(FVector(X,Y,Base+Horse->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+2.15),
                FRotator(0,Yaw,0),false,nullptr,ETeleportType::TeleportPhysics);
            if(SmoothOffset)
            {
                Skin->SetRelativeTransform(RestMesh);
                Skin->AddWorldOffset(FVector(-90.,0.,0.));
            }
            Move->FindFloor(Horse->GetActorLocation(),Move->CurrentFloor,false);
            if(X==350. && Yaw==0.){FHitResult H;FCollisionQueryParams Q(SCENE_QUERY_STAT(HorseContactDatum),false,Horse);
                const FVector P=Horse->GetActorLocation();bool Ray=World->LineTraceSingleByChannel(H,P,P-FVector(0,0,300),ECC_Pawn,Q);
                UE_LOG(LogTemp,Display,TEXT("Contact review slope %.0f centre %s ray %d hit %s normal %s floor %d walkable %d"),Angle,*P.ToString(),Ray,*GetNameSafe(H.GetActor()),*H.ImpactNormal.ToString(),Move->CurrentFloor.bBlockingHit,Move->CurrentFloor.IsWalkableFloor());}
            for(auto* Clip:{Horse->WalkAnimation.Get(),Horse->CanterAnimation.Get()})
            {
                Skin->SetAnimation(Clip);Skin->Play(true);Skin->SetPlayRate(0.f);
                for(int Frame=-10;Frame<24;++Frame)
                {
                    const double Phase=FMath::Max(0,Frame)/24.;
                    Skin->SetPosition(Phase*Clip->GetPlayLength(),false);
                    Skin->TickAnimation(1.f/60.f,false);Skin->RefreshBoneTransforms();
                    if(Frame<0)continue;
                    if(Measured)Timing+=FString::Printf(TEXT("%.0f,%.0f,%.0f,%d,%.3f\n"),Angle,Yaw,X,Frame,Measured->LastGroundFitUs);
                    const auto Points=MonsterSurfaceAudit::WorldVertices(Skin);
                    if(Points.Num()!=Groups.Num()||Points.IsEmpty())return 4;
                    double Mins[]={1.e8,1.e8,1.e8,1.e8};double Lowest=1.e8;int Worst=0;
                    for(int I=0;I<Points.Num();++I)
                    {
                        const auto& P=Points[I];const double H=P.Z-Height(P.X,Grade);
                        if(H<Lowest){Lowest=H;Worst=I;}
                        if(Groups[I]>=0)Mins[Groups[I]]=FMath::Min(Mins[Groups[I]],H);
                    }
                    if(Angle==59. && Yaw==0. && (X==0.||X==350.||X==700.) && Frame==8 && Clip==Horse->CanterAnimation)
                    {
                        TArray<FVector3f> Local;for(const auto& P:Points)Local.Add(FVector3f(P-FVector(X,Y,Height(X,Grade))));
                        FFileHelper::SaveArrayToFile(MakeArrayView(reinterpret_cast<const uint8*>(Local.GetData()),int32(Local.Num()*sizeof(FVector3f))),
                            *(Dir/FString::Printf(TEXT("horse-%.0f.bin"),X)));
                    }
                    if(Lowest<.05)
                    {
                        int32 Section,Local;LOD.GetSectionFromVertexIndex(Worst,Section,Local);
                        const int Bone=LOD.RenderSections[Section].BoneMap[Weights->GetBoneIndex(Worst,0)];
                        const FVector BindP(Positions.VertexPosition(Worst));const auto& V=Points[Worst];
                        LowestParts+=FString::Printf(TEXT("%.0f,%.0f,%.0f,%s,%d,%.3f,%d,%s,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f\n"),Angle,Yaw,X,*Clip->GetName(),Frame,Lowest,Worst,*Ref.GetBoneName(Bone).ToString(),BindP.X,BindP.Y,BindP.Z,V.X,V.Y-Y,V.Z);
                    }
                    auto S=Skin->GetSocketLocation(TEXT("saddle_socket"));
                    const FVector Errors=(!Raw && Frame%6==0)?SeatErrors(Yaw):FVector(-1.);
                    Rows+=FString::Printf(TEXT("%.0f,%.0f,%.0f,%s,%d,%d,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f\n"),
                        Angle,Yaw,X,*Clip->GetName(),Frame,Move->CurrentFloor.IsWalkableFloor(),Lowest,AtCrest(Points,Indices,Grade,Lowest),Mins[0],Mins[1],Mins[2],Mins[3],S.X,S.Y-Y,S.Z,Errors.X,Errors.Y,Errors.Z);
                }
            }
        }
    }
    if(!Raw && !SmoothOffset)
    {
        FString Motion=TEXT("frame,x,z,speed,grounded,mesh_min_cm,surface_min_cm,seat_error,left_tread_error,right_tread_error\n");
        const double Y=16000.,Grade=FMath::Tan(FMath::DegreesToRadians(59.));
        Horse->SetActorLocationAndRotation(FVector(-400,Y,96.15),FRotator::ZeroRotator,false,nullptr,ETeleportType::TeleportPhysics);
        Horse->SetRider(Pawn);Horse->Drive(1,0,true);
        Move->FindFloor(Horse->GetActorLocation(),Move->CurrentFloor,false);
        constexpr float Dt=1.f/60.f;
        World->DeltaTimeSeconds=Dt;
        for(int Frame=0;Frame<240;++Frame)
        {
            ++GFrameCounter;
            Horse->Tick(Dt);Move->TickComponent(Dt,LEVELTICK_All,&Move->PrimaryComponentTick);
            Skin->TickAnimation(Dt,false);Skin->RefreshBoneTransforms();
            const FVector P=Horse->GetActorLocation();
            double Lowest=BIG_NUMBER;
            const auto Points=MonsterSurfaceAudit::WorldVertices(Skin);
            for(const auto& V:Points)Lowest=FMath::Min(Lowest,V.Z-Height(V.X,Grade));
            const auto Errors=SeatErrors(0.);
            Motion+=FString::Printf(TEXT("%d,%.3f,%.3f,%.3f,%d,%.4f,%.4f,%.5f,%.5f,%.5f\n"),
                Frame,P.X,P.Z,Move->Velocity.Size2D(),Move->CurrentFloor.IsWalkableFloor(),Lowest,AtCrest(Points,Indices,Grade,Lowest),Errors.X,Errors.Y,Errors.Z);
            if(P.X>1050)break;
        }
        FFileHelper::SaveStringToFile(Motion,*(Dir/TEXT("ridden.csv")));
    }
    if(Measured)FFileHelper::SaveStringToFile(Timing,*(Dir/TEXT("ground-timing.csv")));
    if(Measured && FParse::Param(*Params,TEXT("CrowdCost")))
    {
        FString Cost=TEXT("visible_horses,parked,frame,solver_total_us\n");
        TArray<AStableRidingHorse*> Herd;
        for(int I=0;I<8;++I)
        {
            auto* Other=World->SpawnActor<AStableRidingHorse>(FVector(-2800.+I*310.,0,96.15),FRotator::ZeroRotator);
            if(!Other)return 5;
            auto* HorseMesh=CastChecked<UStableHorseGroundMesh>(Other->GetMesh());
            HorseMesh->SetAnimationMode(EAnimationMode::AnimationSingleNode);
            HorseMesh->bEnableUpdateRateOptimizations=false;
            HorseMesh->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
            HorseMesh->bMeasureGroundFit=true;
            Herd.Add(Other);
        }
        constexpr float Dt=1.f/60.f;
        for(bool Parked:{true,false})for(int Count:{1,8})
        {
            for(auto* Other:Herd)
            {
                Other->GetCharacterMovement()->SetMovementMode(Parked?MOVE_None:MOVE_Walking);
                Other->GetMesh()->SetAnimation(Parked?Other->IdleAnimation.Get():Other->CanterAnimation.Get());
                Other->GetMesh()->Play(true);
            }
            for(int Frame=-20;Frame<240;++Frame)
            {
                ++GFrameCounter;World->TimeSeconds+=Dt;World->DeltaTimeSeconds=Dt;
                double Total=0.;
                for(int I=0;I<Count;++I)
                {
                    auto* HorseMesh=CastChecked<UStableHorseGroundMesh>(Herd[I]->GetMesh());
                    HorseMesh->TickAnimation(Dt,false);HorseMesh->RefreshBoneTransforms();
                    Total+=HorseMesh->LastGroundFitUs;
                }
                if(Frame>=0)Cost+=FString::Printf(TEXT("%d,%d,%d,%.3f\n"),Count,int(Parked),Frame,Total);
            }
        }
        FFileHelper::SaveStringToFile(Cost,*(Dir/TEXT("herd-cost.csv")));
    }
    FFileHelper::SaveStringToFile(LowestParts,*(Dir/TEXT("lowest-parts.csv")));
    const bool Saved=FFileHelper::SaveStringToFile(Rows,*(Dir/TEXT("frames.csv")));
    GEngine->DestroyWorldContext(World);World->DestroyWorld(false);
    return Saved?0:5;
#else
    return 1;
#endif
}
