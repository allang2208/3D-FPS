#include "Super90LoaderArmAuditCommandlet.h"
#include "FPSGunplayAnimInstance.h"
#include "RifleHipFraming.h"
#include "Super90WeaponAssets.h"
#include "WeaponActionCameraComponent.h"
#include "WeaponGripProfile.h"
#include "Animation/AnimSequence.h"
#include "Camera/CameraComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#if WITH_EDITOR
#include "AssetCompilingManager.h"
#include "PreviewScene.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "Rendering/SkeletalMeshLODRenderData.h"
#include "Rendering/SkinWeightVertexBuffer.h"
#include "StaticMeshResources.h"
#endif

namespace Super90ArmAudit
{
using JV=TSharedPtr<FJsonValue>;
JV Numbers(std::initializer_list<double> Values)
{
    TArray<JV> Out;for(double V:Values)Out.Add(MakeShared<FJsonValueNumber>(V));
    return MakeShared<FJsonValueArray>(Out);
}
JV Pose(const FTransform& T)
{
    const auto P=T.GetLocation();const auto Q=T.GetRotation();const auto S=T.GetScale3D();
    return Numbers({P.X,P.Y,P.Z,Q.X,Q.Y,Q.Z,Q.W,S.X,S.Y,S.Z});
}
bool Save(const TSharedRef<FJsonObject>& Object,const FString& Path)
{
    FString Text;FJsonSerializer::Serialize(Object,TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&Text));
    return FFileHelper::SaveStringToFile(Text,*Path);
}
#if WITH_EDITOR
TSharedRef<FJsonObject> StaticGeometry(UStaticMesh* Asset)
{
    auto Out=MakeShared<FJsonObject>();Out->SetStringField(TEXT("asset"),Asset->GetPathName());
    const auto& LOD=Asset->GetRenderData()->LODResources[0];TArray<JV> Positions,Triangles;
    for(uint32 I=0;I<LOD.VertexBuffers.PositionVertexBuffer.GetNumVertices();++I)
    {const auto P=LOD.VertexBuffers.PositionVertexBuffer.VertexPosition(I);Positions.Add(Numbers({P.X,P.Y,P.Z}));}
    for(int32 I=0;I<LOD.IndexBuffer.GetNumIndices();I+=3)
        Triangles.Add(Numbers({double(LOD.IndexBuffer.GetIndex(I)),double(LOD.IndexBuffer.GetIndex(I+1)),double(LOD.IndexBuffer.GetIndex(I+2))}));
    Out->SetArrayField(TEXT("positions"),Positions);Out->SetArrayField(TEXT("triangles"),Triangles);return Out;
}
#endif
}

int32 USuper90LoaderArmAuditCommandlet::Main(const FString& Params)
{
    FString Directory;FParse::Value(*Params,TEXT("Output="),Directory);
    return Directory.IsEmpty()||!Capture(Directory)?1:0;
}

bool USuper90LoaderArmAuditCommandlet::Capture(const FString& Directory)
{
#if WITH_EDITOR
    using namespace Super90ArmAudit;
    IFileManager::Get().MakeDirectory(*Directory,true);
    auto* Asset=LoadObject<USkeletalMesh>(nullptr,Super90WeaponAssets::MeshPath);
    auto* Idle=LoadObject<UAnimSequence>(nullptr,*Super90WeaponAssets::AnimationPath(TEXT("idle")));
    if(!Asset||!Idle)return false;
    FAssetCompilingManager::Get().FinishAllCompilation();
    FPreviewScene Scene(FPreviewScene::ConstructionValues().SetEditor(false).SetCreatePhysicsScene(false).SetTransactional(false));
    auto* Mesh=NewObject<USkeletalMeshComponent>();Mesh->SetSkeletalMesh(Asset);
    Mesh->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    Mesh->bEnableUpdateRateOptimizations=false;Mesh->SetForcedLOD(1);
    Scene.AddComponent(Mesh,FTransform::Identity);
    Mesh->SetAnimInstanceClass(UFPSGunplayAnimInstance::StaticClass());Mesh->InitAnim(true);
    auto* Anim=Cast<UFPSGunplayAnimInstance>(Mesh->GetAnimInstance());if(!Anim)return false;
    Anim->IdleClip=Idle;Anim->AimClip=Idle;
    const auto& Ref=Asset->GetRefSkeleton();TArray<FTransform> Rest;
    TArray<JV> Names,Parents,RefPoses;
    for(int32 B=0;B<Ref.GetNum();++B)
    {
        const int32 Parent=Ref.GetParentIndex(B);FTransform T=Ref.GetRefBonePose()[B];if(Parent!=INDEX_NONE)T=T*Rest[Parent];
        Rest.Add(T);Names.Add(MakeShared<FJsonValueString>(Ref.GetBoneName(B).ToString()));Parents.Add(MakeShared<FJsonValueNumber>(Parent));RefPoses.Add(Pose(T));
    }
    const auto& LOD=Asset->GetResourceForRendering()->LODRenderData[0];const auto* Weights=Mesh->GetSkinWeightBuffer(0);
    auto Geometry=MakeShared<FJsonObject>();TArray<JV> Vertices,Triangles,Materials;
    Geometry->SetStringField(TEXT("asset"),Asset->GetPathName());Geometry->SetArrayField(TEXT("names"),Names);
    Geometry->SetArrayField(TEXT("parents"),Parents);Geometry->SetArrayField(TEXT("rest"),RefPoses);
    for(const auto& M:Asset->GetMaterials())Materials.Add(MakeShared<FJsonValueString>(M.MaterialSlotName.ToString()));
    Geometry->SetArrayField(TEXT("materials"),Materials);
    for(int32 SectionIndex=0;SectionIndex<LOD.RenderSections.Num();++SectionIndex)
    {
        const auto& Section=LOD.RenderSections[SectionIndex];
        for(uint32 V=Section.BaseVertexIndex;V<Section.BaseVertexIndex+Section.NumVertices;++V)
        {
            const auto P=LOD.StaticVertexBuffers.PositionVertexBuffer.VertexPosition(V);auto Item=MakeShared<FJsonObject>();TArray<JV> W;
            for(uint32 K=0;K<Weights->GetMaxBoneInfluences();++K)if(const auto Weight=Weights->GetBoneWeight(V,K))
                W.Add(Numbers({double(Section.BoneMap[Weights->GetBoneIndex(V,K)]),double(Weight)}));
            Item->SetField(TEXT("p"),Numbers({P.X,P.Y,P.Z}));Item->SetArrayField(TEXT("w"),W);Item->SetNumberField(TEXT("section"),SectionIndex);
            Item->SetNumberField(TEXT("index"),V);Item->SetNumberField(TEXT("material"),Section.MaterialIndex);Vertices.Add(MakeShared<FJsonValueObject>(Item));
        }
        auto* Indices=LOD.MultiSizeIndexContainer.GetIndexBuffer();
        for(uint32 I=Section.BaseIndex;I<Section.BaseIndex+Section.NumTriangles*3;I+=3)
            Triangles.Add(Numbers({double(Indices->Get(I)),double(Indices->Get(I+1)),double(Indices->Get(I+2)),double(Section.MaterialIndex)}));
    }
    Geometry->SetArrayField(TEXT("vertices"),Vertices);Geometry->SetArrayField(TEXT("triangles"),Triangles);
    if(!Save(Geometry,Directory/TEXT("geometry.json")))return false;
    auto* Camera=NewObject<UCameraComponent>();Scene.AddComponent(Camera,FTransform::Identity);
    auto* CameraMotion=NewObject<UWeaponActionCameraComponent>();TArray<float> Contacts;
    const TCHAR* Families[]={TEXT("base"),TEXT("vertical"),TEXT("canted"),TEXT("prism"),TEXT("angled")};
    const float HFOVs[]={FMath::RadiansToDegrees(2.f*FMath::Atan(FMath::Tan(FMath::DegreesToRadians(75.f)*.5f)*(16.f/9.f))),112.f};
    auto Manifest=MakeShared<FJsonObject>();TArray<JV> Cases;
    for(int32 Family=0;Family<5;++Family)
    {
        UWeaponGripProfile* Profile=nullptr;
        if(Family)
        {
            const FString Path=FString::Printf(TEXT("/Game/Weapons/Super90/Foregrips20261007/Profiles/DA_Super90_%s.DA_Super90_%s"),Families[Family],Families[Family]);
            Profile=LoadObject<UWeaponGripProfile>(nullptr,*Path);if(!Profile)return false;
            auto* Grip=LoadObject<UStaticMesh>(nullptr,*FString::Printf(TEXT("/Game/Weapons/Super90/Foregrips20261007/Meshes/SM_Super90_%s.SM_Super90_%s"),Families[Family],Families[Family]));
            if(!Grip)return false;FAssetCompilingManager::Get().FinishAllCompilation();
            if(!Save(StaticGeometry(Grip),Directory/(FString(Families[Family])+TEXT("_grip.json"))))return false;
        }
        Anim->GripProfile=Profile;
        FRifleHipFraming Framing;Framing.Initialize(TEXT("ue_super90"),Idle,FVector(0,7,-7),FRotator(0,90,0),FVector::OneVector,false);
        Framing.SelectIdle(Idle,Profile);if(!Framing.IsReady())return false;
        const FTransform MeshFrame(Framing.Rotation(FQuat::Identity),Framing.Location(FVector::ZeroVector));
        for(bool Empty:{false,true})for(int32 Count=1;Count<=7;++Count)
        {
            const FString Name=FString::Printf(TEXT("A_Super90_loader_%s%d"),Empty?TEXT("empty_"):TEXT("normal_"),Count);
            const FString Path=TEXT("/Game/Weapons/Super90/Speedloader20261007/Animations/")+Name+TEXT(".")+Name;
            auto* Clip=LoadObject<UAnimSequence>(nullptr,*Path);if(!Clip|| (Profile&&!Profile->Find(Clip)))return false;
            FAssetCompilingManager::Get().FinishAllCompilation();Anim->ActionClip=Clip;
            auto Case=MakeShared<FJsonObject>();TArray<JV> Samples;
            const FString Key=FString::Printf(TEXT("%s_%s%d"),Families[Family],Empty?TEXT("empty_"):TEXT("normal_"),Count);
            Case->SetStringField(TEXT("clip"),Path);Case->SetStringField(TEXT("family"),Families[Family]);Case->SetNumberField(TEXT("count"),Count);
            Case->SetBoolField(TEXT("empty"),Empty);Case->SetNumberField(TEXT("duration"),Clip->GetPlayLength());Case->SetField(TEXT("mesh_frame"),Pose(MeshFrame));
            // Half-source-frame steps catch interpolated poses; normal includes the idle handoff.
            for(int32 HalfFrame=216;HalfFrame<=(Empty?328:296);++HalfFrame)
            {
                const float Frame=HalfFrame*.5f,Time=Frame/60.f;
                Anim->ActionTime=FMath::Min(Time,Clip->GetPlayLength());
                Anim->ActionAlpha=FMath::Clamp((Clip->GetPlayLength()-Time)/.10f,0.f,1.f);
                Anim->BaseTime=(Time+.10f)/.85f;
                ++GFrameCounter;Mesh->TickAnimation(1.f/120.f,false);Mesh->RefreshBoneTransforms();
                const auto& Bones=Mesh->GetComponentSpaceTransforms();if(Bones.Num()!=Ref.GetNum())return false;
                auto Sample=MakeShared<FJsonObject>();TArray<JV> Poses,Cameras;
                for(const auto& Bone:Bones)Poses.Add(Pose(Bone));
                for(float FOV:HFOVs)
                {
                    Camera->SetFieldOfView(FOV);
                    CameraMotion->Apply(*Camera,Empty?EM4CameraAction::Super90LoaderEmpty:EM4CameraAction::Super90Loader,Anim->ActionTime,Clip->GetPlayLength(),Contacts,.45f);
                    FMinimalViewInfo View;Camera->GetCameraView(0.f,View);Cameras.Add(Pose(FTransform(View.Rotation,View.Location)));
                }
                Sample->SetNumberField(TEXT("frame"),Frame);Sample->SetNumberField(TEXT("alpha"),Anim->ActionAlpha);
                Sample->SetArrayField(TEXT("bones"),Poses);Sample->SetArrayField(TEXT("cameras"),Cameras);
                // One native CPU-skinned snapshot per case independently checks the external skinning.
                if(HalfFrame==288)
                {
                    TArray<FMatrix44f> Matrices;Mesh->GetCurrentRefToLocalMatrices(Matrices,0);TArray<FVector3f> Skinned;
                    USkinnedMeshComponent::ComputeSkinnedPositions(Mesh,Skinned,Matrices,LOD,*Weights);TArray<JV> Points;
                    for(const auto P:Skinned)Points.Add(Numbers({P.X,P.Y,P.Z}));Sample->SetArrayField(TEXT("native_skinned"),Points);
                }
                Samples.Add(MakeShared<FJsonValueObject>(Sample));
            }
            Case->SetArrayField(TEXT("samples"),Samples);if(!Save(Case,Directory/(Key+TEXT(".json"))))return false;
            Cases.Add(MakeShared<FJsonValueString>(Key));UE_LOG(LogTemp,Display,TEXT("SUPER90_ARM_CAPTURE %s poses=%d"),*Key,Samples.Num());
        }
    }
    Manifest->SetArrayField(TEXT("cases"),Cases);Manifest->SetStringField(TEXT("graph"),TEXT("UFPSGunplayAnimInstance including grip, action blend and Super90SupportArmNode"));
    Manifest->SetStringField(TEXT("camera"),TEXT("FRifleHipFraming + UWeaponActionCameraComponent defaults; standing hip reload"));
    Manifest->SetField(TEXT("horizontal_fovs"),Numbers({HFOVs[0],HFOVs[1]}));
    Manifest->SetBoolField(TEXT("assets_modified"),false);Manifest->SetBoolField(TEXT("game_begin_play"),false);
    return Save(Manifest,Directory/TEXT("capture_manifest.json"));
#else
    return false;
#endif
}
