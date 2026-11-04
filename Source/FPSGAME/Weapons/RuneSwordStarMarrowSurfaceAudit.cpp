#include "RuneSwordAuditCommandlet.h"
#include "RuneSwordComponent.h"
#include "RuneSwordMeshComponent.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Characters/FPSArmJointCorrectiveComponent.h"
#include "Animation/AnimSequence.h"
#include "Animation/MorphTarget.h"
#include "AssetCompilingManager.h"
#include "Camera/CameraComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "Rendering/SkeletalMeshLODRenderData.h"
#include "Rendering/SkinWeightVertexBuffer.h"
#include "StaticMeshResources.h"
#include "Serialization/JsonSerializer.h"

namespace
{
template<class T> void Binary(const TArray<T>& Values,const FString& Path)
{FFileHelper::SaveArrayToFile(TArrayView<const uint8>(reinterpret_cast<const uint8*>(Values.GetData()),Values.Num()*sizeof(T)),*Path);}
TArray<TSharedPtr<FJsonValue>> Vec(const FVector& V)
{return {MakeShared<FJsonValueNumber>(V.X),MakeShared<FJsonValueNumber>(V.Y),MakeShared<FJsonValueNumber>(V.Z)};}
TSharedPtr<FJsonObject> Transform(const FTransform& T)
{
    auto J=MakeShared<FJsonObject>();J->SetArrayField(TEXT("p"),Vec(T.GetLocation()));J->SetArrayField(TEXT("s"),Vec(T.GetScale3D()));
    const FQuat Q=T.GetRotation();J->SetArrayField(TEXT("q"),{MakeShared<FJsonValueNumber>(Q.X),MakeShared<FJsonValueNumber>(Q.Y),MakeShared<FJsonValueNumber>(Q.Z),MakeShared<FJsonValueNumber>(Q.W)});return J;
}
}

int32 URuneSwordAuditCommandlet::AuditStarMarrowSurface(const FString& Params)
{
    FString Out;if(!FParse::Value(*Params,TEXT("Out="),Out))return 2;
    int32 SampleRate=240;FParse::Value(*Params,TEXT("SampleRate="),SampleRate);SampleRate=FMath::Clamp(SampleRate,30,240);
    FString RequestedVariant;FParse::Value(*Params,TEXT("Variant="),RequestedVariant);
    FString CasesPath;FParse::Value(*Params,TEXT("SwordGripCases="),CasesPath);
    TArray<TSharedPtr<FJsonValue>> Cases;
    if(!CasesPath.IsEmpty())
    {
        FString Input;if(!FFileHelper::LoadFileToString(Input,*CasesPath)||
            !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Input),Cases))return 8;
    }
    else for(const FString Variant:{FString(TEXT("Standard")),FString(TEXT("LongGrip"))})
    {
        auto Case=MakeShared<FJsonObject>();Case->SetStringField(TEXT("id"),Variant);
        Case->SetStringField(TEXT("definition"),TEXT("ue_frost_crystal_sword"));
        Case->SetStringField(TEXT("role"),TEXT("StarMarrowCharge"));
        auto Parts=MakeShared<FJsonObject>();Parts->SetStringField(TEXT("blade_1"),TEXT("star_marrow"));
        if(Variant==TEXT("LongGrip"))Parts->SetStringField(TEXT("grip"),TEXT("long_twohand"));
        Case->SetObjectField(TEXT("parts"),Parts);Cases.Add(MakeShared<FJsonValueObject>(Case));
    }
    IFileManager::Get().MakeDirectory(*Out,true);
    const FString Original=FCommandLine::Get(),Slot=TEXT("SkillNetworkAudit_Surface_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FCommandLine::Set(*(TEXT("StarMarrowSurfaceAudit -ColdSteelProfile=")+Slot));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("StarMarrowSurfaceAudit"));
    auto* World=GI->GetWorld();auto* Model=GI->GetSubsystem<UColdSteelStatusModel>();
    if(!World||!Model||!Model->IsAudit()||Model->ProfileSlot()!=TEXT("ColdSteel_")+Slot)return 3;
    World->InitializeActorsForPlay(FURL());
    auto* Pawn=World->SpawnActor<AFPSGAMECharacter>();auto* PC=World->SpawnActor<APlayerController>();
    PC->SetAsLocalPlayerController();PC->bShowMouseCursor=false;PC->Possess(Pawn);
    Pawn->SetActorTickEnabled(false);for(auto* C:Pawn->GetComponents())C->SetComponentTickEnabled(false);
    auto* Sword=Pawn->FindComponentByClass<URuneSwordComponent>();Sword->Character=Pawn;Sword->Camera=Pawn->FindComponentByClass<UCameraComponent>();
    auto* Corrective=Pawn->FindComponentByClass<UFPSArmJointCorrectiveComponent>();if(!Corrective)return 4;
    for(const auto& CaseValue:Cases)
    {
        const auto Case=CaseValue->AsObject();if(!Case)return 9;
        const FString Variant=Case->GetStringField(TEXT("id")),Definition=Case->GetStringField(TEXT("definition")),Role=Case->GetStringField(TEXT("role"));
        if(!RequestedVariant.IsEmpty()&&RequestedVariant!=Variant)continue;
        const FString Folder=Out/Variant;IFileManager::Get().MakeDirectory(*Folder,true);
        auto State=Model->Snapshot();State.Items.Reset();State.ActiveWeaponSlot=6;State.ActiveProductionTool.Reset();State.Mana=100;State.Stamina=100;State.DungeonRun={};
        for(auto& Skill:State.Skills){Skill.Value.Level=1;Skill.Value.Experience=0;}
        auto Item=Model->CreateItem(Definition);Item.InstanceId=TEXT("surface-")+Variant;Item.Place=1;Item.Cell=6;
        TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data);if(!Data)Data=MakeShared<FJsonObject>();
        const auto Parts=Case->GetObjectField(TEXT("parts"));
        Data->SetObjectField(TEXT("gunsmith_parts"),Parts);Item.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Item.Data));State.Items={Item};Model->AdoptNetMirror(State);
        Sword->RefreshEquipment(Model);Sword->CancelAction();
        auto* Mesh=Cast<URuneSwordMeshComponent>(Sword->Viewmodel);if(!Mesh||!Sword->ModularSword)return 5;
        auto* Asset=Mesh->GetSkeletalMeshAsset();
        UAnimSequence* Clip=Sword->Animations.FindRef(FName(*Role));
        if(Role==TEXT("StarMarrowCharge"))
        {
            FString Grip;Parts->TryGetStringField(TEXT("grip"),Grip);
            Clip=LoadObject<UAnimSequence>(nullptr,*(TEXT("/Game/Weapons/FrostCrystalSword20260915/StarMarrowChargeMotion20261103/")+
                FString(Grip==TEXT("long_twohand")?TEXT("LongGrip"):TEXT("Standard"))+TEXT("/A_StarMarrow_Charge")));
        }
        if(!Clip)return 6;Sword->Animations.Add(FName(*Role),Clip);
        FAssetCompilingManager::Get().FinishAllCompilation();
        const auto& LOD=Asset->GetResourceForRendering()->LODRenderData[0];const auto* Weights=Mesh->GetSkinWeightBuffer(0);
        if(!Weights||!Weights->GetNeedsCPUAccess())return 7;
        const int32 Count=LOD.GetNumVertices();const auto& Ref=Asset->GetRefSkeleton();
        TArray<uint32> Indices;LOD.MultiSizeIndexContainer.GetIndexBuffer(Indices);Binary(Indices,Folder/TEXT("arms.indices"));
        TArray<FVector3f> Bind;TArray<uint16> BoneIndices;TArray<float> BoneWeights;TArray<uint16> MainBone;
        Bind.SetNum(Count);MainBone.SetNum(Count);const int32 Influences=Weights->GetMaxBoneInfluences();
        BoneIndices.SetNumZeroed(Count*Influences);BoneWeights.SetNumZeroed(Count*Influences);
        for(const auto& Section:LOD.RenderSections)for(uint32 I=Section.BaseVertexIndex;I<Section.BaseVertexIndex+Section.NumVertices;++I)
        {
            Bind[I]=LOD.StaticVertexBuffers.PositionVertexBuffer.VertexPosition(I);float Best=-1;
            for(int32 K=0;K<Influences;++K)
            {
                const int32 B=Section.BoneMap[Weights->GetBoneIndex(I,K)];const float W=float(Weights->GetBoneWeight(I,K))/65535.f;
                BoneIndices[I*Influences+K]=B;BoneWeights[I*Influences+K]=W;if(W>Best){Best=W;MainBone[I]=B;}
            }
        }
        Binary(Bind,Folder/TEXT("arms.bind"));Binary(MainBone,Folder/TEXT("arms.mainbone"));Binary(BoneIndices,Folder/TEXT("arms.bones"));Binary(BoneWeights,Folder/TEXT("arms.weights"));
        auto Metadata=MakeShared<FJsonObject>();Metadata->SetStringField(TEXT("mesh"),Asset->GetPathName());Metadata->SetStringField(TEXT("animation"),Clip->GetPathName());
        Metadata->SetNumberField(TEXT("vertex_count"),Count);Metadata->SetNumberField(TEXT("influences"),Influences);Metadata->SetNumberField(TEXT("fps"),SampleRate);
        TArray<TSharedPtr<FJsonValue>> Names,Rest;TArray<FTransform> RefPose=Ref.GetRefBonePose();
        for(int32 I=0;I<Ref.GetNum();++I){if(Ref.GetParentIndex(I)>=0)RefPose[I]=RefPose[I]*RefPose[Ref.GetParentIndex(I)];Names.Add(MakeShared<FJsonValueString>(Ref.GetBoneName(I).ToString()));Rest.Add(MakeShared<FJsonValueObject>(Transform(RefPose[I])));}
        Metadata->SetArrayField(TEXT("bone_names"),Names);Metadata->SetArrayField(TEXT("rest"),Rest);
        Metadata->SetNumberField(TEXT("morph_count"),Asset->GetMorphTargets().Num());
        Metadata->SetObjectField(TEXT("case"),Case);
        Sword->SetClip(TEXT("Idle"),true);Mesh->ClearWhirlwindEntry();Sword->SamplePose(0);
        TArray<TSharedPtr<FJsonValue>> PartRows;TArray<UStaticMeshComponent*> Static;Pawn->GetComponents(Static);int32 PartIndex=0;
        FTransform Root=Mesh->GetSocketTransform(TEXT("WPN_root"));Root.SetScale3D(FVector::OneVector);
        for(auto* Part:Static)if(Part->GetStaticMesh()&&(Part==Sword->ModularSword||Part->IsAttachedTo(Sword->ModularSword)))
        {
            const auto& L=Part->GetStaticMesh()->GetRenderData()->LODResources[0];TArray<FVector3f> V;TArray<uint32> I;
            for(uint32 J=0;J<L.VertexBuffers.PositionVertexBuffer.GetNumVertices();++J)
            {
                const FVector Local(L.VertexBuffers.PositionVertexBuffer.VertexPosition(J));
                V.Add(FVector3f(Root.InverseTransformPosition(Part->GetComponentTransform().TransformPosition(Local))));
            }
            for(int32 J=0;J<L.IndexBuffer.GetNumIndices();++J)I.Add(L.IndexBuffer.GetIndex(J));
            const FString Label=FString::Printf(TEXT("part%d"),PartIndex++);Binary(V,Folder/(Label+TEXT(".vertices")));Binary(I,Folder/(Label+TEXT(".indices")));
            auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("id"),Label);Row->SetStringField(TEXT("mesh"),Part->GetStaticMesh()->GetPathName());PartRows.Add(MakeShared<FJsonValueObject>(Row));
        }
        Metadata->SetArrayField(TEXT("parts"),PartRows);TArray<TSharedPtr<FJsonValue>> Frames;
        if(Role==TEXT("StarMarrowCharge"))Sword->BeginStarMarrowChargeMotion();
        else {Sword->SetClip(FName(*Role),false);Mesh->ClearWhirlwindEntry();}
        int32 SampleCount=0;Case->TryGetNumberField(TEXT("samples"),SampleCount);
        const int32 LastFrame=SampleCount>1?SampleCount-1:FMath::RoundToInt(Clip->GetPlayLength()*SampleRate);
        const float SampleDelta=SampleCount>1?Clip->GetPlayLength()/LastFrame:1.f/SampleRate;
        for(int32 Frame=0;Frame<=LastFrame;++Frame)
        {
            const float T=FMath::Min(Frame*SampleDelta,Clip->GetPlayLength());Sword->Elapsed=T;if(Frame)Mesh->AdvanceLocomotionEntry(SampleDelta);Sword->SamplePose(T);
            Corrective->TickComponent(SampleDelta,LEVELTICK_All,nullptr);
            // Evaluate the actual morph weights in bind space, then skin with the final runtime bone matrices.
            TArray<FVector3f> Morphed=Bind;int32 Active=0;
            for(const UMorphTarget* Morph:Asset->GetMorphTargets())
            {
                const float W=Mesh->GetMorphTarget(Morph->GetFName());if(FMath::Abs(W)<1e-6f)continue;++Active;
                for(auto Delta=Morph->GetDeltaIteratorForLOD(0);!Delta.AtEnd();++Delta)
                    if(Morphed.IsValidIndex(Delta->SourceIdx))Morphed[Delta->SourceIdx]+=Delta->PositionDelta*W;
            }
            TArray<FMatrix44f> Matrices;Mesh->GetCurrentRefToLocalMatrices(Matrices,0);TArray<FVector3f> V;V.SetNumZeroed(Count);
            for(int32 I=0;I<Count;++I)for(int32 K=0;K<Influences;++K)
                if(BoneWeights[I*Influences+K]>0)V[I]+=FVector3f(Matrices[BoneIndices[I*Influences+K]].TransformPosition(Morphed[I]))*BoneWeights[I*Influences+K];
            Binary(V,Folder/FString::Printf(TEXT("f%04d.vertices"),Frame));
            auto Row=MakeShared<FJsonObject>();Row->SetNumberField(TEXT("frame"),Frame);Row->SetNumberField(TEXT("seconds"),T);Row->SetNumberField(TEXT("active_correctives"),Active);
            FTransform W=Mesh->GetSocketTransform(TEXT("WPN_root"),RTS_Component);W.SetScale3D(FVector::OneVector);Row->SetObjectField(TEXT("weapon"),Transform(W));
            auto Bones=MakeShared<FJsonObject>();
            for(int32 B=0;B<Ref.GetNum();++B)
            {
                const FName Name=Ref.GetBoneName(B);
                Bones->SetObjectField(Name.ToString(),Transform(Mesh->GetSocketTransform(Name,RTS_Component)));
            }
            FVector CameraLocation=FVector::ZeroVector;FRotator CameraRotation=FRotator::ZeroRotator;
            Sword->GetCameraMotion(CameraLocation,CameraRotation);
            Row->SetArrayField(TEXT("camera_location_cm"),Vec(CameraLocation));
            Row->SetArrayField(TEXT("camera_rotation_pyr"),Vec(FVector(CameraRotation.Pitch,CameraRotation.Yaw,CameraRotation.Roll)));
            Row->SetObjectField(TEXT("bones"),Bones);Frames.Add(MakeShared<FJsonValueObject>(Row));
        }
        Metadata->SetArrayField(TEXT("frames"),Frames);FString Json;FJsonSerializer::Serialize(Metadata,TJsonWriterFactory<>::Create(&Json));FFileHelper::SaveStringToFile(Json,*(Folder/TEXT("surface.json")));
        UE_LOG(LogTemp,Display,TEXT("STAR_MARROW_SURFACE %s vertices=%d frames=%d morphs=%d parts=%d"),*Variant,Count,LastFrame+1,Asset->GetMorphTargets().Num(),PartIndex);
    }
    GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);return 0;
}
