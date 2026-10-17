#include "Engine/SkeletalMesh.h"
#include "WitchRebuiltClothingAsset.h"

#if WITH_EDITOR
#include "Animation/AnimSequence.h"
#include "ClothingAssetFactory.h"
#include "ClothingAsset.h"
#include "ChaosCloth/ChaosClothConfig.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"
#include "Rendering/SkeletalMeshModel.h"
#include "Rendering/SkeletalMeshLODModel.h"
#include "HAL/IConsoleManager.h"
#include "Misc/FileHelper.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/StrongObjectPtr.h"

namespace NightWardenWaistAuthoring
{
FVector ReadVector(const TArray<TSharedPtr<FJsonValue>>& A)
{
    return FVector(A[0]->AsNumber(), A[1]->AsNumber(), A[2]->AsNumber());
}

int32 FindSection(USkeletalMesh* Mesh, const FString& Slot)
{
    const auto& Sections=Mesh->GetImportedModel()->LODModels[0].Sections;
    for(int32 I=0;I<Sections.Num();++I)
        if(Mesh->GetMaterials().IsValidIndex(Sections[I].MaterialIndex) &&
           Mesh->GetMaterials()[Sections[I].MaterialIndex].ImportedMaterialSlotName.ToString()==Slot)
            return I;
    return INDEX_NONE;
}

void Build(const TArray<FString>& Args)
{
    if(Args.Num()!=4){UE_LOG(LogTemp,Error,TEXT("NightWarden.BuildWaistCloth requires mesh, proxy, manifest, receipt"));return;}
    auto Receipt=MakeShared<FJsonObject>();Receipt->SetBoolField(TEXT("success"),false);
    auto Write=[&]()
    {
        FString Text;auto Writer=TJsonWriterFactory<>::Create(&Text);
        FJsonSerializer::Serialize(Receipt,Writer);FFileHelper::SaveStringToFile(Text,*Args[3]);
    };
    auto Fail=[&](const TCHAR* Message){Receipt->SetStringField(TEXT("error"),Message);Write();UE_LOG(LogTemp,Error,TEXT("NW7_CLOTH %s"),Message);};
    auto* Mesh=LoadObject<USkeletalMesh>(nullptr,*Args[0]);
    auto* Proxy=LoadObject<USkeletalMesh>(nullptr,*Args[1]);
    if(!Mesh||!Proxy||!(Mesh->GetPathName().StartsWith(TEXT("/Game/Monsters/NightWarden/V07WaistStride/"))||
       Mesh->GetPathName().StartsWith(TEXT("/Game/Monsters/NightWarden/V09Melee/")))||
       !Proxy->GetPathName().StartsWith(TEXT("/Game/Monsters/NightWarden/V07WaistStride/"))||
       !Mesh->GetImportedModel()||!Proxy->GetImportedModel()) {Fail(TEXT("Night Warden display and proxy required"));return;}
    FString Json;TSharedPtr<FJsonObject> Manifest;
    if(!FFileHelper::LoadFileToString(Json,*Args[2])||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Manifest))
        {Fail(TEXT("Cannot read waist cloth production manifest"));return;}
    const int32 SourceSection=FindSection(Proxy,Manifest->GetStringField(TEXT("proxy_slot")));
    const int32 RenderSection=FindSection(Mesh,Manifest->GetStringField(TEXT("render_slot")));
    if(SourceSection==INDEX_NONE||RenderSection==INDEX_NONE){Fail(TEXT("Waist cloth sections missing"));return;}
    auto* Witch=LoadObject<USkeletalMesh>(nullptr,TEXT("/Game/Monsters/WitchRebuilt/SK_WitchRebuilt.SK_WitchRebuilt"));
    UChaosClothConfig* TemplateConfig=nullptr;UChaosClothSharedSimConfig* TemplateShared=nullptr;
    if(Witch)for(const auto& Asset:Witch->GetMeshClothingAssets())
    {
        auto* Common=Cast<UClothingAssetCommon>(Asset);
        if(!Common||!Common->GetName().Contains(TEXT("Lower")))continue;
        for(const auto& Pair:Common->ClothConfigs)
        {
            if(auto* Config=Cast<UChaosClothConfig>(Pair.Value))TemplateConfig=Config;
            if(auto* Shared=Cast<UChaosClothSharedSimConfig>(Pair.Value))TemplateShared=Shared;
        }
        if(TemplateConfig&&TemplateShared)break;
    }
    if(!TemplateConfig||!TemplateShared){Fail(TEXT("Saved Witch lower cloth configuration unavailable"));return;}
    const auto& Ref=Mesh->GetRefSkeleton();TArray<FTransform> Frames=Ref.GetRefBonePose();
    for(int32 I=0;I<Frames.Num();++I)if(Ref.GetParentIndex(I)>=0)Frames[I]*=Frames[Ref.GetParentIndex(I)];
    auto* Collision=NewObject<UPhysicsAsset>(Mesh,MakeUniqueObjectName(Mesh,UPhysicsAsset::StaticClass(),TEXT("NW7_WaistBodyCollision")),RF_Transactional);
    for(const auto& Value:Manifest->GetArrayField(TEXT("capsules")))
    {
        const auto Shape=Value->AsObject();const FName Bone(*Shape->GetStringField(TEXT("bone")));
        const int32 Index=Ref.FindBoneIndex(Bone);
        if(Index==INDEX_NONE){Fail(TEXT("Cloth collider bone missing"));return;}
        const FVector A=ReadVector(Shape->GetArrayField(TEXT("a_cm"))),B=ReadVector(Shape->GetArrayField(TEXT("b_cm")));
        const double Scale=Frames[Index].GetScale3D().GetAbsMax();
        auto* Body=NewObject<USkeletalBodySetup>(Collision);Body->BoneName=Bone;Body->PhysicsType=PhysType_Kinematic;
        FKSphylElem Capsule;Capsule.Center=Frames[Index].InverseTransformPosition((A+B)*.5);
        Capsule.Rotation=FQuat::FindBetweenNormals(FVector::UpVector,Frames[Index].InverseTransformVectorNoScale(B-A).GetSafeNormal()).Rotator();
        Capsule.Radius=Shape->GetNumberField(TEXT("radius_cm"))/Scale;Capsule.Length=(B-A).Size()/Scale;
        Body->AggGeom.SphylElems.Add(Capsule);Collision->SkeletalBodySetups.Add(Body);
    }
    Collision->UpdateBodySetupIndexMap();Collision->SetPreviewMesh(Mesh,false);
    FSkeletalMeshClothBuildParams Params;Params.AssetName=TEXT("NW7_WaistProxyExtract");Params.LodIndex=0;Params.SourceSection=SourceSection;Params.bRemoveFromMesh=false;Params.PhysicsAsset=Collision;
    TStrongObjectPtr<UClothingAssetFactory> Factory(NewObject<UClothingAssetFactory>());
    TStrongObjectPtr<UClothingAssetCommon> Extracted(Cast<UClothingAssetCommon>(Factory->CreateFromSkeletalMesh(Proxy,Params)));
    if(!Extracted.IsValid()||Extracted->LodData.Num()!=1){Fail(TEXT("Waist simulation extraction failed"));return;}
    auto* Cloth=NewObject<UWitchRebuiltClothingAsset>(Mesh,MakeUniqueObjectName(Mesh,UWitchRebuiltClothingAsset::StaticClass(),TEXT("NW7_TatteredWaistDrape")),RF_Transactional);
    Cloth->InitializeSimulationFrom(Extracted.Get());Cloth->PhysicsAsset=Collision;
    auto& Lod=Cloth->LodData[0];Lod.bUseMultipleInfluences=false;Lod.bSmoothTransition=true;Lod.PointWeightMaps.Reset();
    const auto& Points=Manifest->GetArrayField(TEXT("vertices_cm"));const auto& Travel=Manifest->GetArrayField(TEXT("max_distance_cm"));
    if(Points.Num()!=Travel.Num()||Points.IsEmpty()){Fail(TEXT("Cloth mobility field missing"));return;}
    TArray<FVector> Authored;for(const auto& Point:Points)Authored.Add(ReadVector(Point->AsArray()));
    FPointWeightMap Distance(Lod.PhysicalMeshData.Vertices.Num());Distance.Name=TEXT("FixedWaist_FreeShortHem");Distance.bEnabled=true;Distance.CurrentTarget=static_cast<uint8>(EWeightMapTargetCommon::MaxDistance);
    int32 Pinned=0;float MaxTravel=0;
    for(int32 I=0;I<Distance.Num();++I)
    {
        double Best=TNumericLimits<double>::Max();int32 Nearest=INDEX_NONE;
        for(int32 J=0;J<Authored.Num();++J){const double D=FVector::DistSquared(FVector(Lod.PhysicalMeshData.Vertices[I]),Authored[J]);if(D<Best){Best=D;Nearest=J;}}
        if(Best>FMath::Square(.05)){Fail(TEXT("Proxy import units do not match authored centimeter mobility field"));return;}
        Distance[I]=Travel[Nearest]->AsNumber();Pinned+=Distance[I]==0;MaxTravel=FMath::Max(MaxTravel,Distance[I]);
    }
    Lod.PointWeightMaps.Add(MoveTemp(Distance));
    auto* Config=DuplicateObject<UChaosClothConfig>(TemplateConfig,Cloth);auto* Shared=DuplicateObject<UChaosClothSharedSimConfig>(TemplateShared,Cloth);
    Config->Density=.30f;Config->EdgeStiffnessWeighted={.98f,.98f};Config->AreaStiffnessWeighted={.96f,.96f};
    Config->BendingStiffnessWeighted={.045f,.045f};Config->BucklingStiffnessWeighted={.022f,.022f};
    Config->TetherScale={1.01f,1.01f};Config->TetherStiffness={1.f,1.f};Config->bUseGeodesicDistance=true;
    Config->AnimDriveStiffness={.025f,.025f};Config->AnimDriveDamping={.12f,.12f};
    Config->CollisionThickness=.6f;Config->FrictionCoefficient=.25f;Config->LocalDampingCoefficient=.18f;
    Config->bUseCCD=true;Config->bUseSelfCollisions=false;Config->bUseSelfCollisionSpheres=true;
    Config->SelfCollisionSphereRadius=.45f;Config->SelfCollisionSphereRadiusCullMultiplier=2.f;
    Config->LinearVelocityScale=FVector(.8);Config->AngularVelocityScale=.7f;
    Shared->IterationCount=4;Shared->MaxIterationCount=6;Shared->SubdivisionCount=1;
    Cloth->ClothConfigs.Add(Config->GetClass()->GetFName(),Config);Cloth->ClothConfigs.Add(Shared->GetClass()->GetFName(),Shared);
    Cloth->ApplyParameterMasks(true);Cloth->InvalidateAllCachedData();Cloth->RefreshBoneMapping(Mesh);Cloth->CalculateReferenceBoneIndex();
    FScopedSkeletalMeshPostEditChange Change(Mesh);Mesh->Modify();
    const auto Old=Mesh->GetMeshClothingAssets();for(const auto& Asset:Old)if(Asset)Asset->UnbindFromSkeletalMesh(Mesh,INDEX_NONE,INDEX_NONE);
    Mesh->SetMeshClothingAssets({Cloth});
    if(!Cloth->BindToSkeletalMesh(Mesh,0,RenderSection,0)){Fail(TEXT("Witch-style stable capture could not bind the waist display"));return;}
    auto& Section=Mesh->GetImportedModel()->LODModels[0].Sections[RenderSection];auto& User=Mesh->GetImportedModel()->LODModels[0].UserSectionsData.FindOrAdd(Section.OriginalDataSectionIndex);
    User.CorrespondClothAssetIndex=0;User.ClothingData=Section.ClothingData;User.bDisabled=Section.bDisabled=false;
    Mesh->InvalidateDeriveDataCacheGUID();Mesh->MarkPackageDirty();
    Receipt->SetBoolField(TEXT("success"),true);Receipt->SetBoolField(TEXT("saved"),false);
    Receipt->SetStringField(TEXT("cloth"),Cloth->GetPathName());Receipt->SetStringField(TEXT("template"),TemplateConfig->GetPathName());
    Receipt->SetNumberField(TEXT("proxy_vertices"),Lod.PhysicalMeshData.Vertices.Num());Receipt->SetNumberField(TEXT("pinned_vertices"),Pinned);Receipt->SetNumberField(TEXT("maximum_travel_cm"),MaxTravel);
    Receipt->SetNumberField(TEXT("collision_capsules"),Collision->SkeletalBodySetups.Num());Receipt->SetNumberField(TEXT("render_section"),RenderSection);Write();
    UE_LOG(LogTemp,Display,TEXT("NW7_CLOTH authored continuous waist wrap: %d particles, %d fixed"),Lod.PhysicalMeshData.Vertices.Num(),Pinned);
}
FAutoConsoleCommand Command(TEXT("NightWarden.BuildWaistCloth"),TEXT("Build Night Warden's waist cloth from its preserved mesh, proxy and mobility manifest; caller saves."),FConsoleCommandWithArgsDelegate::CreateStatic(&Build));
void FinishMotion(const TArray<FString>& Args)
{
    for(const FString& Path:Args)
    {
        if(!Path.StartsWith(TEXT("/Game/Monsters/NightWarden/V07WaistStride/")) &&
           !Path.StartsWith(TEXT("/Game/Monsters/NightWarden/V08AIMovement/")) &&
           !Path.StartsWith(TEXT("/Game/Monsters/NightWarden/V09Melee/")))continue;
        if(auto* Animation=LoadObject<UAnimSequence>(nullptr,*Path))
        {
            // A retarget/controller edit may already be compressing this hash.
            Animation->WaitOnExistingCompression(true);
            Animation->CacheDerivedDataForCurrentPlatform();
            Animation->WaitOnExistingCompression(true);
        }
    }
}
FAutoConsoleCommand FinishMotionCommand(TEXT("NightWarden.FinishMotion"),TEXT("Drain pending animation compression before requesting and saving Night Warden motion data."),FConsoleCommandWithArgsDelegate::CreateStatic(&FinishMotion));
}
#endif
