#if WITH_EDITOR
// Explicitly requested visual diagnosis. Transient preview world; no asset/profile writes.
#include "FPSPlayerBodyAnimInstance.h"
#include "FPSBodyStaffGrip.h"
#include "../Weapons/Staff/StaffGripPose.h"
#include "../Weapons/Unarmed/FPSUnarmedHandPose.h"
#include "Animation/AnimSequence.h"
#include "AssetCompilingManager.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "Serialization/JsonSerializer.h"
#include "StaticMeshResources.h"

namespace FPSStaffPoseDiagnosis
{
static TSharedPtr<FJsonObject> Read(const FString& Path)
{
    FString Text;TSharedPtr<FJsonObject> O;
    if(FFileHelper::LoadFileToString(Text,*Path))FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),O);
    return O;
}
static void Write(const TSharedPtr<FJsonObject>& O,const FString& Path)
{
    FString Text;FJsonSerializer::Serialize(O.ToSharedRef(),TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&Text));
    FFileHelper::SaveStringToFile(Text,*Path,FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
}
static TSharedPtr<FJsonValue> Transform(const FTransform& T)
{
    const auto P=T.GetLocation();const auto Q=T.GetRotation();const auto S=T.GetScale3D();
    TArray<TSharedPtr<FJsonValue>> A;
    for(double V:{P.X,P.Y,P.Z,Q.X,Q.Y,Q.Z,Q.W,S.X,S.Y,S.Z})A.Add(MakeShared<FJsonValueNumber>(V));
    return MakeShared<FJsonValueArray>(A);
}
template<class T> static void Binary(const TArray<T>& Data,const FString& Path)
{
    TUniquePtr<FArchive> File(IFileManager::Get().CreateFileWriter(*Path));
    if(File)File->Serialize(const_cast<T*>(Data.GetData()),Data.Num()*sizeof(T));
}
static void Run(const TArray<FString>& Args)
{
    if(Args.IsEmpty())return;
    const FString Out=Args[0];IFileManager::Get().MakeDirectory(*Out,true);
    const auto Config=Read(FPaths::ProjectContentDir()/TEXT("ColdSteelData/player_body.json"));
    const auto Outfit=Read(FPaths::ProjectContentDir()/TEXT("ColdSteelData/modular_outfits.json"));
    if(!Config||!Outfit)return;
    auto* Asset=LoadObject<USkeletalMesh>(nullptr,*Config->GetStringField(TEXT("body_mesh")));
    auto* Native=LoadObject<USkeletalMesh>(nullptr,TEXT("/Game/Characters/ModularOutfit20260924/BarePalmV7/M4/SK_M4_BareArmsV7"));
    if(!Asset||!Native)return;
    const auto Settings=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(false)
        .RequiresHitProxies(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    auto* World=UWorld::CreateWorld(EWorldType::EditorPreview,false,TEXT("StaffPoseDiagnosis"),nullptr,true,ERHIFeatureLevel::Num,&Settings);
    auto* Actor=World->SpawnActor<AActor>();
    const auto MakeMesh=[&](USkeletalMesh* Mesh)
    {
        auto* C=NewObject<USkeletalMeshComponent>(Actor,NAME_None,RF_Transient);Actor->AddInstanceComponent(C);
        C->SetSkeletalMeshAsset(Mesh);C->SetDisablePostProcessBlueprint(true);C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        C->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
        C->RegisterComponentWithWorld(World);return C;
    };
    auto* Body=MakeMesh(Asset);Body->SetAnimationMode(EAnimationMode::AnimationBlueprint);
    Body->SetAnimInstanceClass(UFPSPlayerBodyAnimInstance::StaticClass());
    auto* Anim=CastChecked<UFPSPlayerBodyAnimInstance>(Body->GetAnimInstance());
    for(const auto& Pair:Config->GetObjectField(TEXT("clips"))->Values)
        if(auto* Clip=LoadObject<UAnimSequence>(nullptr,*Pair.Value->AsString()))Anim->Clips.Add(*Pair.Key,Clip);
    const auto& Scale=Config->GetArrayField(TEXT("pose_scale"));Anim->PoseScale=FVector(Scale[0]->AsNumber(),Scale[1]->AsNumber(),Scale[2]->AsNumber());
    TMap<FString,USkeletalMeshComponent*> Meshes;Meshes.Add(TEXT("body"),Body);
    for(const TCHAR* Id:{TEXT("ue_chainmail_shirt"),TEXT("ue_steel_gauntlets")})
    {
        const FString Path=Outfit->GetObjectField(TEXT("items"))->GetObjectField(Id)->GetObjectField(TEXT("rig_meshes"))->GetStringField(TEXT("Jason"));
        if(auto* M=LoadObject<USkeletalMesh>(nullptr,*Path))
        {auto* C=MakeMesh(M);C->SetLeaderPoseComponent(Body);Meshes.Add(Id,C);}
    }
    FAssetCompilingManager::Get().FinishAllCompilation();
    auto Report=MakeShared<FJsonObject>();auto MeshInfo=MakeShared<FJsonObject>();
    for(const auto& Pair:Meshes)
    {
        const auto& LOD=Pair.Value->GetSkeletalMeshAsset()->GetResourceForRendering()->LODRenderData[0];
        TArray<uint32> Indices;LOD.MultiSizeIndexContainer.GetIndexBuffer(Indices);Binary(Indices,Out/(Pair.Key+TEXT(".indices")));
        TArray<uint32> Materials;Materials.Init(0,Indices.Num()/3);
        for(const auto& S:LOD.RenderSections)for(uint32 T=S.BaseIndex/3;T<S.BaseIndex/3+S.NumTriangles;++T)Materials[T]=S.MaterialIndex;
        Binary(Materials,Out/(Pair.Key+TEXT(".materials")));
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("asset"),Pair.Value->GetSkeletalMeshAsset()->GetPathName());
        Row->SetNumberField(TEXT("vertices"),LOD.GetNumVertices());Row->SetNumberField(TEXT("triangles"),Indices.Num()/3);MeshInfo->SetObjectField(Pair.Key,Row);
    }
    Report->SetObjectField(TEXT("meshes"),MeshInfo);
    const auto& Ref=Native->GetRefSkeleton();auto Bind=Ref.GetRefBonePose();
    for(int32 I=0;I<Bind.Num();++I)if(Ref.GetParentIndex(I)>=0)Bind[I]=Bind[I]*Bind[Ref.GetParentIndex(I)];
    const auto& Hold=StaffGripPose::Get(Native,Bind,0);auto Pose=Hold.Local[0];
    for(int32 I=0;I<Pose.Num();++I)if(Ref.GetParentIndex(I)>=0)Pose[I]=Pose[I]*Pose[Ref.GetParentIndex(I)];
    FFPSBodyGripRig Grip,Left;Grip.Initialize(Ref,Asset->GetRefSkeleton(),TEXT("hand_r"),TEXT("hand_r"));
    FPSBodyStaffGrip::AdaptMount(Grip,0);
    Left.Initialize(Ref,Asset->GetRefSkeleton(),TEXT("hand_l"),TEXT("hand_l"));
    FPSBodyStaffGrip::Transfer(Grip,Ref,Pose,Anim->EquipmentFingers);
    const FTransform Mount=FTransform(-StaffGripPose::HoldPoint())*Hold.HandInGrip.Inverse()*Grip.Mount;
    Anim->StaffHandRotation=(Grip.Mount.Inverse()*Pose[Grip.SourceHand]*FTransform(FRotator(0,90,0))).GetRotation();
    FPSUnarmedHandPose::Build(Ref,TEXT("hand_l"),Pose);FPSBodyStaffGrip::Transfer(Left,Ref,Pose,Anim->EquipmentFingers);
    Anim->EquipmentGripHands=3;
    auto* Staff=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/Weapons/ApprenticeStaff20260927/Meshes/SM_Staff_Body"));
    auto* Lining=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/Weapons/ApprenticeStaff20260927/Meshes/SM_Staff_grip_lining_false"));
    FAssetCompilingManager::Get().FinishAllCompilation();
    if(Staff)
    {
        TArray<FVector3f> V;TArray<uint32> I;
        for(auto* Part:{Staff,Lining})if(Part)
        {
            const auto& LOD=Part->GetRenderData()->LODResources[0];const uint32 Base=V.Num();
            for(uint32 N=0;N<LOD.VertexBuffers.PositionVertexBuffer.GetNumVertices();++N)V.Add(LOD.VertexBuffers.PositionVertexBuffer.VertexPosition(N));
            for(int32 N=0;N<LOD.IndexBuffer.GetNumIndices();++N)I.Add(Base+LOD.IndexBuffer.GetIndex(N));
        }
        Binary(V,Out/TEXT("staff.vertices"));Binary(I,Out/TEXT("staff.indices"));
    }
    TArray<TSharedPtr<FJsonValue>> Samples;
    const auto Snapshot=[&](const FString& Label)
    {
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("label"),Label);
        auto Bones=MakeShared<FJsonObject>();const auto& Skeleton=Asset->GetRefSkeleton();const auto& Final=Body->GetComponentSpaceTransforms();
        for(int32 I=0;I<Final.Num();++I)Bones->SetField(Skeleton.GetBoneName(I).ToString(),Transform(Final[I]));
        Row->SetObjectField(TEXT("bones"),Bones);Row->SetField(TEXT("staff"),Transform(Mount*Final[Grip.TargetHand]));
        for(const auto& Pair:Meshes)
        {
            auto* C=Pair.Value;TArray<FMatrix44f> Matrices;C->GetCurrentRefToLocalMatrices(Matrices,0);
            TArray<FVector3f> V;const auto& LOD=C->GetSkeletalMeshAsset()->GetResourceForRendering()->LODRenderData[0];
            USkinnedMeshComponent::ComputeSkinnedPositions(C,V,Matrices,LOD,*C->GetSkinWeightBuffer(0));Binary(V,Out/(Label+TEXT(".")+Pair.Key+TEXT(".vertices")));
        }
        Samples.Add(MakeShared<FJsonValueObject>(Row));
    };
    const auto Tick=[&](float Delta){Anim->Clock+=Delta;Body->TickAnimation(Delta,false);Body->RefreshBoneTransforms();};
    Anim->BodyState.Family=TEXT("Staff");Anim->BodyState.Weapon=TEXT("ue_apprentice_staff");
    for(int32 I=0;I<30;++I)Tick(1.f/60.f);Snapshot(TEXT("idle"));
    Anim->Speed=450.f;for(int32 I=0;I<90;++I){Tick(1.f/60.f);if(I%15==14)Snapshot(FString::Printf(TEXT("walk_%02d"),I));}
    Anim->Speed=700.f;Anim->BodyState.bSprinting=true;for(int32 I=0;I<90;++I){Tick(1.f/60.f);if(I%15==14)Snapshot(FString::Printf(TEXT("run_%02d"),I));}
    Anim->Speed=0.f;Anim->BodyState.bSprinting=false;Anim->BodyState.bCrouched=true;
    for(int32 I=0;I<45;++I)Tick(1.f/60.f);Snapshot(TEXT("crouch"));
    Anim->BodyState.bCrouched=false;for(int32 I=0;I<45;++I)Tick(1.f/60.f);
    Anim->BodyState.bHasActionProgress=true;Anim->BodyState.ActionDuration=1.f;
    for(const TCHAR* Phase:{TEXT("Gather"),TEXT("Ready"),TEXT("Release"),TEXT("Recover")})
    {
        Anim->BodyState.Action=EFPSBodyAction::Cast;Anim->BodyState.ActionVariant=Phase;Anim->BodyState.Contacts.Channel=TEXT("StaffCast");
        for(int32 I=0;I<30;++I){Anim->BodyState.ActionProgress=I/29.f;Tick(1.f/60.f);if(I==14||I==29)Snapshot(FString::Printf(TEXT("cast_%s_%02d"),Phase,I));}
    }
    Anim->BodyState.Action=EFPSBodyAction::Strike;Anim->BodyState.ActionVariant=NAME_None;Anim->BodyState.Contacts.Channel=NAME_None;
    for(int32 I=0;I<45;++I){Anim->BodyState.ActionProgress=I/44.f;Tick(1.f/60.f);if(I%9==8)Snapshot(FString::Printf(TEXT("strike_%02d"),I));}
    Report->SetArrayField(TEXT("samples"),Samples);Report->SetStringField(TEXT("scope"),TEXT("Native animation proxy and CPU skinned saved meshes; isolated preview world, no gameplay input/physics"));
    Write(Report,Out/TEXT("poses.json"));World->DestroyWorld(false);
    UE_LOG(LogTemp,Display,TEXT("STAFF_POSE_DIAGNOSIS_SAVED %d samples %s"),Samples.Num(),*Out);
}
static FAutoConsoleCommand Command(TEXT("fps.body.DiagnoseStaffPose"),TEXT("Explicit staff hand/arm visual diagnosis to an output directory."),FConsoleCommandWithArgsDelegate::CreateStatic(&Run));
}
#endif
