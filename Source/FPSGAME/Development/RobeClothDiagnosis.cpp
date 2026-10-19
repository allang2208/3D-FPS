// Explicit, read-only cloth diagnostics for the reported stair regression.
#if WITH_EDITOR
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Pawn.h"
#include "HAL/IConsoleManager.h"
#include "HAL/FileManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#include "ClothingAsset.h"
#include "ClothingSystemRuntimeTypes.h"
#include "Rendering/SkeletalMeshModel.h"
#include "Rendering/SkeletalMeshLODModel.h"
#include "AssetCompilingManager.h"
#include "ClothingSimulationInstance.h"
#include "ClothingSimulationFactory.h"
#include "TwoBoneIK.h"
#include "ChaosCloth/ChaosClothConfig.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"
namespace RobeClothDiagnosis
{
TSharedPtr<FJsonValue> Vector(const FVector& P)
{return MakeShared<FJsonValueArray>(TArray<TSharedPtr<FJsonValue>>{MakeShared<FJsonValueNumber>(P.X),MakeShared<FJsonValueNumber>(P.Y),MakeShared<FJsonValueNumber>(P.Z)});}
void Capture(const TArray<FString>& Args,UWorld* World)
{
    if(!World)return;
    TArray<TSharedPtr<FJsonValue>> Rows;
    for(TActorIterator<APawn> It(World);It;++It)
    {
        TArray<USkeletalMeshComponent*> Parts;It->GetComponents(Parts);
        for(auto* Part:Parts)
        {
            if(!Part->ComponentHasTag(TEXT("OutfitRobeDrape")))continue;
            auto* Mesh=Part->GetSkeletalMeshAsset();if(!Mesh||!Mesh->GetImportedModel())continue;
            auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("component"),Part->GetName());Row->SetStringField(TEXT("mesh"),Mesh->GetPathName());
            Row->SetBoolField(TEXT("suspended"),Part->IsClothingSimulationSuspended());Row->SetNumberField(TEXT("blend"),Part->ClothBlendWeight);Row->SetNumberField(TEXT("lod"),Part->GetPredictedLODLevel());
            auto* Parent=Cast<USkeletalMeshComponent>(Part->GetAttachParent());auto* Leader=Parent&&Parent->LeaderPoseComponent.IsValid()?Cast<USkeletalMeshComponent>(Parent->LeaderPoseComponent.Get()):Parent;
            TArray<TSharedPtr<FJsonValue>> Bones;
            for(const TCHAR* Name:{TEXT("pelvis"),TEXT("thigh_l"),TEXT("thigh_r"),TEXT("calf_l"),TEXT("calf_r"),TEXT("foot_l"),TEXT("foot_r"),TEXT("ball_l"),TEXT("ball_r")})
            {
                auto B=MakeShared<FJsonObject>();B->SetStringField(TEXT("name"),Name);B->SetField(TEXT("position"),Vector(Part->GetSocketTransform(Name,RTS_Component).GetLocation()));
                if(Leader)B->SetNumberField(TEXT("source_delta_cm"),FVector::Distance(Part->GetSocketTransform(Name,RTS_Component).GetLocation(),Leader->GetSocketTransform(Name,RTS_Component).GetLocation()));
                Bones.Add(MakeShared<FJsonValueObject>(B));
            }
            Row->SetArrayField(TEXT("bones"),Bones);
            const auto& Data=Part->GetCurrentClothingData_AnyThread();TArray<TSharedPtr<FJsonValue>> Cloths;
            for(int32 CI=0;CI<Mesh->GetMeshClothingAssets().Num();++CI)
            {
                auto* Cloth=Cast<UClothingAssetCommon>(Mesh->GetMeshClothingAssets()[CI]);if(!Cloth||Cloth->LodData.IsEmpty())continue;
                auto C=MakeShared<FJsonObject>();const auto& Physical=Cloth->LodData[0].PhysicalMeshData;
                TArray<TSharedPtr<FJsonValue>> Rest,Current,Indices,Distances;
                for(const auto& P:Physical.Vertices)Rest.Add(Vector(FVector(P)));
                for(auto I:Physical.Indices)Indices.Add(MakeShared<FJsonValueNumber>(I));
                if(const auto* Map=Physical.FindWeightMap(EWeightMapTargetCommon::MaxDistance))for(int32 I=0;I<Map->Num();++I)Distances.Add(MakeShared<FJsonValueNumber>((*Map)[I]));
                if(const auto* Sim=Data.Find(CI))for(const auto& P:Sim->Positions)Current.Add(Vector(Sim->ComponentRelativeTransform.TransformPosition(FVector(P))));
                C->SetArrayField(TEXT("rest"),Rest);C->SetArrayField(TEXT("current_component_space"),Current);C->SetArrayField(TEXT("indices"),Indices);C->SetArrayField(TEXT("max_distances"),Distances);
                TArray<TSharedPtr<FJsonValue>> Shapes;
                if(auto* Physics=Cloth->PhysicsAsset.Get())for(USkeletalBodySetup* Body:Physics->SkeletalBodySetups)
                {
                    const FTransform Bone=Part->GetSocketTransform(Body->BoneName,RTS_Component);const double Scale=Bone.GetScale3D().GetAbsMax();
                    auto Add=[&](const FVector& Center,const FRotator& Rotation,double Length,double R0,double R1)
                    {
                        auto S=MakeShared<FJsonObject>();S->SetStringField(TEXT("bone"),Body->BoneName.ToString());
                        const FVector Half=Rotation.RotateVector(FVector::UpVector)*Length*.5;
                        S->SetField(TEXT("a"),Vector(Bone.TransformPosition(Center+Half)));S->SetField(TEXT("b"),Vector(Bone.TransformPosition(Center-Half)));
                        S->SetNumberField(TEXT("r0"),R0*Scale);S->SetNumberField(TEXT("r1"),R1*Scale);Shapes.Add(MakeShared<FJsonValueObject>(S));
                    };
                    for(const auto& S:Body->AggGeom.SphylElems)Add(S.Center,S.Rotation,S.Length,S.Radius,S.Radius);
                    for(const auto& S:Body->AggGeom.TaperedCapsuleElems)Add(S.Center,S.Rotation,S.Length,S.Radius0,S.Radius1);
                    for(const auto& S:Body->AggGeom.SphereElems)Add(S.Center,FRotator::ZeroRotator,0,S.Radius,S.Radius);
                }
                C->SetArrayField(TEXT("collision_shapes"),Shapes);
                TArray<TSharedPtr<FJsonValue>> Sections;
                for(const auto& Section:Mesh->GetImportedModel()->LODModels[0].Sections)
                {
                    if(Section.CorrespondClothAssetIndex!=CI||Section.ClothMappingDataLODs.IsEmpty())continue;
                    auto S=MakeShared<FJsonObject>();S->SetNumberField(TEXT("material"),Section.MaterialIndex);S->SetBoolField(TEXT("disabled"),Section.bDisabled);
                    TArray<TSharedPtr<FJsonValue>> Mapping;
                    for(const auto& M:Section.ClothMappingDataLODs[0])
                    {
                        auto J=MakeShared<FJsonObject>();J->SetField(TEXT("bary"),Vector(FVector(M.PositionBaryCoordsAndDist.X,M.PositionBaryCoordsAndDist.Y,M.PositionBaryCoordsAndDist.Z)));
                        J->SetNumberField(TEXT("offset"),M.PositionBaryCoordsAndDist.W);J->SetNumberField(TEXT("skin"),M.SourceMeshVertIndices[3]);Mapping.Add(MakeShared<FJsonValueObject>(J));
                    }
                    S->SetArrayField(TEXT("mapping"),Mapping);Sections.Add(MakeShared<FJsonValueObject>(S));
                }
                C->SetArrayField(TEXT("sections"),Sections);Cloths.Add(MakeShared<FJsonValueObject>(C));
            }
            Row->SetArrayField(TEXT("cloths"),Cloths);Rows.Add(MakeShared<FJsonValueObject>(Row));
        }
    }
    auto Result=MakeShared<FJsonObject>();Result->SetArrayField(TEXT("parts"),Rows);Result->SetNumberField(TEXT("time"),World->GetTimeSeconds());
    FString Json;FJsonSerializer::Serialize(Result,TJsonWriterFactory<>::Create(&Json));
    FString Label=Args.IsEmpty()?TEXT("current"):Args[0];Label=FPaths::MakeValidFileName(Label);
    const FString Dir=FPaths::ProjectDir()/TEXT("SourceAssets/BlueMageRobe20261018/StairRepair20261019");IFileManager::Get().MakeDirectory(*Dir,true);
    FFileHelper::SaveStringToFile(Json,*(Dir/(TEXT("cloth-")+Label+TEXT(".json"))));
    UE_LOG(LogTemp,Display,TEXT("ROBE_CLOTH_CAPTURE %s parts=%d"),*Label,Rows.Num());
}
FAutoConsoleCommandWithWorldAndArgs Command(TEXT("fps.Robe.Capture"),TEXT("Read current robe particles, binding and posed collision. Does not change gameplay."),FConsoleCommandWithWorldAndArgsDelegate::CreateStatic(&Capture));
// Isolated solver reproduction: no PIE, rendering, player inventory or package writes.
void Offline(const TArray<FString>& Args)
{
    const FString Dir=FPaths::ProjectDir()/TEXT("SourceAssets/BlueMageRobe20261018/StairRepair20261019");
    FString Text;TSharedPtr<FJsonObject> Request;
    if(!FFileHelper::LoadFileToString(Text,*(Dir/TEXT("simulation-request.json")))||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Request))return;
    auto* Mesh=LoadObject<USkeletalMesh>(nullptr,*Request->GetStringField(TEXT("mesh")));if(!Mesh)return;
    auto* Cloth=Mesh->GetMeshClothingAssets().IsEmpty()?nullptr:Cast<UClothingAssetCommon>(Mesh->GetMeshClothingAssets()[0]);if(!Cloth)return;
    // Candidate overrides live only in this commandlet's memory; no package save.
    const TSharedPtr<FJsonObject>* SettingsObject=nullptr;
    if(Request->TryGetObjectField(TEXT("settings"),SettingsObject))
    {
        const auto& S=**SettingsObject;
        for(auto& Pair:Cloth->ClothConfigs)
        {
            if(auto* C=Cast<UChaosClothConfig>(Pair.Value))
            {
                double Value;
                if(S.TryGetNumberField(TEXT("anim_drive"),Value))C->AnimDriveStiffness={float(Value),float(Value)};
                if(S.TryGetNumberField(TEXT("anim_damping"),Value))C->AnimDriveDamping={float(Value),float(Value)};
                bool Flag;
                if(S.TryGetBoolField(TEXT("triangle_self_collision"),Flag)){C->bUseSelfCollisions=Flag;C->bUseSelfCollisionSpheres=!Flag;C->SelfCollisionThickness=.5f;C->SelfCollisionFriction=.05f;}
            }
        }
        auto& Lod=Cloth->LodData[0];double Limit=0;
        if(S.TryGetNumberField(TEXT("max_distance"),Limit))for(auto& Map:Lod.PointWeightMaps)if(Map.CurrentTarget==uint8(EWeightMapTargetCommon::MaxDistance))for(int32 I=0;I<Map.Num();++I)Map[I]=FMath::Min(Map[I],float(Limit));
        double Radius,Distance;
        if(S.TryGetNumberField(TEXT("backstop_radius"),Radius)&&S.TryGetNumberField(TEXT("backstop_distance"),Distance))
        {
            for(auto Target:{EWeightMapTargetCommon::BackstopRadius,EWeightMapTargetCommon::BackstopDistance})
            {
                FPointWeightMap Map(Lod.PhysicalMeshData.Vertices.Num());Map.Name=Target==EWeightMapTargetCommon::BackstopRadius?TEXT("SkirtBackstopRadius"):TEXT("SkirtBackstopDistance");Map.bEnabled=true;Map.CurrentTarget=uint8(Target);
                for(int32 I=0;I<Map.Num();++I)Map[I]=float(Target==EWeightMapTargetCommon::BackstopRadius?Radius:Distance);
                Lod.PointWeightMaps.Add(MoveTemp(Map));
            }
        }
        bool Feet=false;
        if(S.TryGetBoolField(TEXT("fitted_feet"),Feet)&&Feet)
        {
            const auto& R=Mesh->GetRefSkeleton();TArray<FTransform> Frames=R.GetRefBonePose();for(int32 I=0;I<Frames.Num();++I)if(R.GetParentIndex(I)>=0)Frames[I]*=Frames[R.GetParentIndex(I)];
            const float Scale=FVector::Distance(Frames[R.FindBoneIndex(TEXT("thigh_l"))].GetLocation(),Frames[R.FindBoneIndex(TEXT("calf_l"))].GetLocation())/39.1f;
            auto* Physics=Cloth->PhysicsAsset.Get();
            for(const TCHAR* Side:{TEXT("l"),TEXT("r")})
            {
                const FName FootName(*(FString(TEXT("foot_"))+Side)),ToeName(*(FString(TEXT("ball_"))+Side));const int32 F=R.FindBoneIndex(FootName),T=R.FindBoneIndex(ToeName);
                const FVector A=Frames[F].GetLocation(),Ball=Frames[T].GetLocation(),Forward=(Ball-A).GetSafeNormal2D(),Lateral=FVector::CrossProduct(Forward,FVector::UpVector);
                USkeletalBodySetup* Foot=nullptr;for(USkeletalBodySetup* B:Physics->SkeletalBodySetups)if(B->BoneName==FootName)Foot=B;
                if(!Foot)continue;Foot->AggGeom.SphylElems.Reset();const float BoneScale=Frames[F].GetScale3D().GetAbsMax();
                for(float Sign:{-1.f,1.f})
                {
                    const FVector Start=A+Scale*(-3.1f*Forward+Sign*2.3f*Lateral-FVector(0,0,6.6f)),End=A+Scale*(19.6f*Forward+Sign*2.3f*Lateral-FVector(0,0,6.6f));
                    FKSphylElem Shape;Shape.Center=Frames[F].InverseTransformPosition((Start+End)*.5);Shape.Rotation=FRotationMatrix::MakeFromZ(Frames[F].InverseTransformVectorNoScale(End-Start)).Rotator();Shape.Length=FVector::Distance(Start,End)/BoneScale;Shape.Radius=6.65f*Scale/BoneScale;Foot->AggGeom.SphylElems.Add(Shape);
                }
                auto* Toes=NewObject<USkeletalBodySetup>(Physics);Toes->BoneName=ToeName;FKSphereElem Tip;Tip.Center=Frames[T].InverseTransformPosition(Ball+Scale*(Forward*3.f+FVector(0,0,.5f)));Tip.Radius=5.5f*Scale/Frames[T].GetScale3D().GetAbsMax();Toes->AggGeom.SphereElems.Add(Tip);Physics->SkeletalBodySetups.Add(Toes);
            }
            Physics->UpdateBodySetupIndexMap();
        }
        bool Guide=false;
        if(S.TryGetBoolField(TEXT("leg_guide"),Guide)&&Guide)
        {
            auto& Phys=Cloth->LodData[0].PhysicalMeshData;const auto& R=Mesh->GetRefSkeleton();TArray<FTransform> Ref=R.GetRefBonePose();for(int32 I=0;I<Ref.Num();++I)if(R.GetParentIndex(I)>=0)Ref[I]*=Ref[R.GetParentIndex(I)];
            int32 Map[5];const FName Names[5]={TEXT("pelvis"),TEXT("thigh_l"),TEXT("thigh_r"),TEXT("calf_l"),TEXT("calf_r")};
            for(int32 J=0;J<5;++J){Map[J]=Cloth->UsedBoneNames.IndexOfByKey(Names[J]);if(Map[J]==INDEX_NONE){Map[J]=Cloth->UsedBoneNames.Add(Names[J]);Cloth->UsedBoneIndices.Add(R.FindBoneIndex(Names[J]));}}
            float Top=-MAX_flt;for(const auto& P:Phys.Vertices)Top=FMath::Max(Top,P.Z);
            const float Knee=Ref[R.FindBoneIndex(TEXT("calf_l"))].GetLocation().Z,Ankle=Ref[R.FindBoneIndex(TEXT("foot_l"))].GetLocation().Z;
            const float HalfSpan=FMath::Abs(Ref[R.FindBoneIndex(TEXT("thigh_l"))].GetLocation().X);
            for(int32 I=0;I<Phys.Vertices.Num();++I)
            {
                const auto P=Phys.Vertices[I];const float Drop=Top-P.Z;if(Drop<14.f)continue;
                const float Alpha=FMath::Clamp((Drop-14.f)/44.f,0.f,1.f);const float Leg=.75f*Alpha*Alpha*(3.f-2.f*Alpha);
                const float Left=FMath::Clamp(.5f+P.X/(2.f*HalfSpan),0.f,1.f),Calf=FMath::Clamp((Knee-P.Z)/(Knee-Ankle),0.f,1.f);
                const float Weights[5]={1-Leg,Leg*Left*(1-Calf),Leg*(1-Left)*(1-Calf),Leg*Left*Calf,Leg*(1-Left)*Calf};
                auto& B=Phys.BoneData[I];B.NumInfluences=0;
                for(int32 J=0;J<5;++J)if(Weights[J]>0){B.BoneIndices[B.NumInfluences]=Map[J];B.BoneWeights[B.NumInfluences]=Weights[J];++B.NumInfluences;}
            }
        }
        double Pleat=0;
        if(S.TryGetNumberField(TEXT("pleat_depth"),Pleat)&&Pleat>0)
        {
            auto& Phys=Cloth->LodData[0].PhysicalMeshData;float Top=-MAX_flt,Bottom=MAX_flt;
            for(const auto& P:Phys.Vertices){Top=FMath::Max(Top,P.Z);Bottom=FMath::Min(Bottom,P.Z);}
            const auto Old=Phys.Vertices;float NormalSign=1.f;
            if(Phys.Indices.Num()>=3){const auto A=Phys.Indices[0],B=Phys.Indices[1],C=Phys.Indices[2];NormalSign=FVector3f::CrossProduct(Old[B]-Old[A],Old[C]-Old[A]).Dot(Phys.Normals[A])<0?-1.f:1.f;}
            for(auto& P:Phys.Vertices)
            {
                const float T=FMath::Clamp((Top-P.Z-24.f)/(Top-Bottom-24.f),0.f,1.f),Fade=T*T*(3.f-2.f*T);
                const float A=FMath::Atan2(P.X,-(P.Y-1.f)),Front=FMath::Abs(A),Back=FMath::Abs(PI-FMath::Abs(A));
                auto Fold=[](float D){return -FMath::Exp(-FMath::Square(D/.10f))+.85f*FMath::Exp(-FMath::Square((D-.20f)/.08f));};
                const FVector2f Rad=FVector2f(P.X,P.Y-1.f).GetSafeNormal();const float Offset=float(Pleat)*Fade*(Fold(Front)+Fold(Back));
                P.X+=Rad.X*Offset;P.Y=1.f+(P.Y-1.f)*(1.f+.12f*Fade)+Rad.Y*Offset;
            }
            Phys.Normals.Init(FVector3f::ZeroVector,Phys.Vertices.Num());
            for(int32 I=0;I<Phys.Indices.Num();I+=3){const auto A=Phys.Indices[I],B=Phys.Indices[I+1],C=Phys.Indices[I+2];FVector3f N=NormalSign*FVector3f::CrossProduct(Phys.Vertices[B]-Phys.Vertices[A],Phys.Vertices[C]-Phys.Vertices[A]);Phys.Normals[A]+=N;Phys.Normals[B]+=N;Phys.Normals[C]+=N;}
            for(auto& N:Phys.Normals)N.Normalize();
        }
        Cloth->ApplyParameterMasks(true);Cloth->InvalidateAllCachedData();
    }
    const auto& DebugPhysical=Cloth->LodData[0].PhysicalMeshData;float LargestDistance=0.f;int32 Inward=0;
    if(const auto* Map=DebugPhysical.FindWeightMap(EWeightMapTargetCommon::MaxDistance))for(int32 I=0;I<Map->Num();++I)LargestDistance=FMath::Max(LargestDistance,(*Map)[I]);
    for(int32 I=0;I<DebugPhysical.Vertices.Num();++I)if(FVector3f(DebugPhysical.Vertices[I].X,DebugPhysical.Vertices[I].Y-1.f,0).Dot(DebugPhysical.Normals[I])<0)++Inward;
    UE_LOG(LogTemp,Display,TEXT("ROBE_OFFLINE_MAPS masks=%d max_distance=%.3f inward_normals=%d particles=%d"),Cloth->LodData[0].PointWeightMaps.Num(),LargestDistance,Inward,DebugPhysical.Vertices.Num());
    FAssetCompilingManager::Get().FinishAllCompilation();
    const auto Settings=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(false).RequiresHitProxies(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    auto* World=UWorld::CreateWorld(EWorldType::EditorPreview,false,TEXT("RobeStairDiagnosis"),nullptr,true,ERHIFeatureLevel::Num,&Settings);
    auto* Actor=World->SpawnActor<AActor>();auto* Part=NewObject<USkeletalMeshComponent>(Actor,NAME_None,RF_Transient);Actor->AddInstanceComponent(Part);
    Part->SetSkeletalMeshAsset(Mesh);Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);Part->SetDisablePostProcessBlueprint(true);
    Part->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    Part->RegisterComponentWithWorld(World);Part->SetComponentSpaceTransformsDoubleBuffering(false);Part->SetForcedLOD(1);Part->RefreshBoneTransforms();
    const auto& Ref=Mesh->GetRefSkeleton();TArray<FTransform> Rest=Ref.GetRefBonePose();
    for(int32 I=0;I<Rest.Num();++I)if(Ref.GetParentIndex(I)>=0)Rest[I]*=Rest[Ref.GetParentIndex(I)];
    const auto& Physical=Cloth->LodData[0].PhysicalMeshData;TArray<TSharedPtr<FJsonValue>> Samples,RestJson,Indices;
    for(const auto& P:Physical.Vertices)RestJson.Add(Vector(FVector(P)));for(auto I:Physical.Indices)Indices.Add(MakeShared<FJsonValueNumber>(I));
    auto Parse=[](const TSharedPtr<FJsonObject>& B)
    {
        const auto& P=B->GetArrayField(TEXT("p"));const auto& Q=B->GetArrayField(TEXT("q"));const auto& S=B->GetArrayField(TEXT("s"));
        return FTransform(FQuat(Q[0]->AsNumber(),Q[1]->AsNumber(),Q[2]->AsNumber(),Q[3]->AsNumber()),FVector(P[0]->AsNumber(),P[1]->AsNumber(),P[2]->AsNumber()),FVector(S[0]->AsNumber(),S[1]->AsNumber(),S[2]->AsNumber()));
    };
    const auto& Inputs=Request->GetArrayField(TEXT("poses"));const int32 Frames=Request->GetIntegerField(TEXT("frames"));
    const float Lift=Request->GetNumberField(TEXT("lift_cm"));double Cycle=1.;Request->TryGetNumberField(TEXT("cycle_seconds"),Cycle);
    auto Apply=[&](int32 Frame)
    {
        const double Phase=FMath::Max(0,Frame-90)/60.;const double Alpha=FMath::Fmod(Phase/Cycle,1.)*(Inputs.Num()-1);const int32 A=FMath::FloorToInt(Alpha),B=FMath::Min(A+1,Inputs.Num()-1);
        auto PoseA=Inputs[A]->AsObject();auto PoseB=Inputs[B]->AsObject();auto& CS=Part->GetEditableComponentSpaceTransforms();CS.SetNum(Rest.Num());
        for(int32 I=0;I<CS.Num();++I)
        {
            const FString Name=Ref.GetBoneName(I).ToString();
            if(PoseA->HasField(Name)){CS[I].Blend(Parse(PoseA->GetObjectField(Name)),Parse(PoseB->GetObjectField(Name)),Alpha-A);}
            else{CS[I]=Ref.GetRefBonePose()[I];if(Ref.GetParentIndex(I)>=0)CS[I]*=CS[Ref.GetParentIndex(I)];}
        }
        TArray<FTransform> Original=CS;
        for(int32 Side=0;Side<2;++Side)
        {
            const FString S=Side==0?TEXT("l"):TEXT("r");const int32 H=Ref.FindBoneIndex(FName(*(TEXT("thigh_")+S))),K=Ref.FindBoneIndex(FName(*(TEXT("calf_")+S))),F=Ref.FindBoneIndex(FName(*(TEXT("foot_")+S)));
            if(H<0||K<0||F<0)continue;
            const float Height=Frame<90?0.f:Lift*FMath::Max(0.,FMath::Sin(Phase*PI+(Side?PI:0.)));
            const FVector HK=CS[K].GetLocation()-CS[H].GetLocation(),HF=CS[F].GetLocation()-CS[H].GetLocation();
            FVector Bend=(HK-HF.GetSafeNormal()*HK.Dot(HF.GetSafeNormal())).GetSafeNormal();if(Bend.IsNearlyZero())Bend=FVector(0,-1,0);
            AnimationCore::SolveTwoBoneIK(CS[H],CS[K],CS[F],CS[K].GetLocation()+Bend*30.,CS[F].GetLocation()+FVector(0,0,Height),false,1.,1.);
            for(int32 I=H+1;I<CS.Num();++I)if(I!=K&&I!=F)
            {
                int32 Ancestor=Ref.GetParentIndex(I);while(Ancestor>=0&&Ancestor!=H)Ancestor=Ref.GetParentIndex(Ancestor);
                if(Ancestor==H){const int32 Parent=Ref.GetParentIndex(I);CS[I]=Original[I].GetRelativeTransform(Original[Parent])*CS[Parent];}
            }
        }
        Part->FinalizeBoneTransform();
    };
    Apply(0);
    {
        FClothingSimulationInstance::FFactoryAssetGroup Group(UClothingSimulationFactory::GetClothingSimulationFactory(Cloth),1);Group.AddClothingAsset(Cloth,0);
        auto& Instances=Part->GetClothingSimulationInstances();
        Instances.Reserve(1);auto& Simulation=Instances.Emplace_GetRef(Part,Group);
        for(int32 Frame=0;Frame<Frames;++Frame)
        {
            Apply(Frame);Part->ResetClothTeleportMode();Simulation.FillContextAndPrepareTick(Part,1.f/60.f,false);Simulation.Simulate();
            if(Frame%10!=0&&Frame!=Frames-1)continue;
            TMap<int32,FClothSimulData> Data;Simulation.AppendSimulationData(Data,Part,nullptr);
            if(!Data.Contains(0)){UE_LOG(LogTemp,Error,TEXT("ROBE_OFFLINE_NO_SIMULATION frame=%d lod=%d"),Frame,Part->GetPredictedLODLevel());break;}
            const auto& D=Data[0];TArray<TSharedPtr<FJsonValue>> Points,Skin,Bones;const auto& CS=Part->GetComponentSpaceTransforms();
            for(const auto& P:D.Positions)Points.Add(Vector(D.ComponentRelativeTransform.TransformPosition(FVector(P))));
            for(int32 V=0;V<Physical.Vertices.Num();++V)
            {
                FVector P(0);const auto& W=Physical.BoneData[V];
                for(int32 J=0;J<W.NumInfluences;++J){const int32 Bone=Cloth->UsedBoneIndices[W.BoneIndices[J]];P+=CS[Bone].TransformPosition(Rest[Bone].InverseTransformPosition(FVector(Physical.Vertices[V])))*W.BoneWeights[J];}
                Skin.Add(Vector(P));
            }
            for(int32 I=0;I<CS.Num();++I)
            {
                auto B=MakeShared<FJsonObject>();B->SetStringField(TEXT("name"),Ref.GetBoneName(I).ToString());B->SetField(TEXT("p"),Vector(CS[I].GetLocation()));
                const FQuat Q=CS[I].GetRotation();B->SetArrayField(TEXT("q"),{MakeShared<FJsonValueNumber>(Q.X),MakeShared<FJsonValueNumber>(Q.Y),MakeShared<FJsonValueNumber>(Q.Z),MakeShared<FJsonValueNumber>(Q.W)});B->SetField(TEXT("s"),Vector(CS[I].GetScale3D()));Bones.Add(MakeShared<FJsonValueObject>(B));
            }
            auto Sample=MakeShared<FJsonObject>();Sample->SetNumberField(TEXT("frame"),Frame);Sample->SetArrayField(TEXT("particles"),Points);Sample->SetArrayField(TEXT("skin"),Skin);Sample->SetArrayField(TEXT("bones"),Bones);Samples.Add(MakeShared<FJsonValueObject>(Sample));
        }
    }
    auto Report=MakeShared<FJsonObject>();Report->SetStringField(TEXT("mesh"),Mesh->GetPathName());Report->SetStringField(TEXT("scope"),TEXT("Isolated Chaos solve with authored gait and two-bone 24cm stair lift; no game movement or rendered validation"));Report->SetArrayField(TEXT("rest"),RestJson);Report->SetArrayField(TEXT("indices"),Indices);Report->SetArrayField(TEXT("samples"),Samples);
    FString Output;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Output));
    const FString Label=FPaths::MakeValidFileName(Request->GetStringField(TEXT("label")));FFileHelper::SaveStringToFile(Output,*(Dir/(TEXT("simulation-")+Label+TEXT(".json"))));
    Part->DestroyComponent();World->DestroyWorld(false);UE_LOG(LogTemp,Display,TEXT("ROBE_OFFLINE_COMPLETE %s samples=%d"),*Label,Samples.Num());
}
FAutoConsoleCommand OfflineCommand(TEXT("fps.Robe.SimulateStairs"),TEXT("Explicit isolated cloth/raised-foot solve from the scoped request file."),FConsoleCommandWithArgsDelegate::CreateStatic(&Offline));

}
#endif
