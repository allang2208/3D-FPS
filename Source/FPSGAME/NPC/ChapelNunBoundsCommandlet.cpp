#include "ChapelNunBoundsCommandlet.h"
#include "ChapelNun.h"
#include "Components/SkeletalMeshComponent.h"
#include "Containers/Ticker.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/ScopeExit.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/UObjectGlobals.h"

int32 UChapelNunBoundsCommandlet::Main(const FString& Params)
{
    const auto Settings=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(true)
        .RequiresHitProxies(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    UWorld* World=UWorld::CreateWorld(EWorldType::GamePreview,false,TEXT("NunFaceBounds"),nullptr,true,ERHIFeatureLevel::Num,&Settings);
    if(!World)return 2;
    ON_SCOPE_EXIT {World->DestroyWorld(false);};
    auto* Delay=IConsoleManager::Get().FindConsoleVariable(TEXT("s.StreamableDelegateDelayFrames"));
    const int32 PreviousDelay=Delay?Delay->GetInt():1;
    if(Delay)Delay->Set(0,ECVF_SetByCode);
    ON_SCOPE_EXIT {if(Delay)Delay->Set(PreviousDelay,ECVF_SetByCode);};
    auto* Nun=World->SpawnActor<AChapelNun>();
    if(!Nun)return 3;
    Nun->DispatchBeginPlay();
    FlushAsyncLoading();
    FTSTicker::GetCoreTicker().Tick(.01f);
    USkeletalMeshComponent* Head=nullptr;
    USkeletalMeshComponent* Body=nullptr;
    TInlineComponentArray<USkeletalMeshComponent*> Parts(Nun);
    for(auto* Part:Parts)
    {
        if(Part->GetFName()==TEXT("NunHead"))Head=Part;
        if(Part->GetFName()==TEXT("KaitlinBody"))Body=Part;
    }
    if(!Head||!Body||!Head->GetSkeletalMeshAsset()||!Head->IsVisible())return 4;
    auto* Physics=Head->GetPhysicsAsset();
    if(!Physics||Physics->GetFName()!=TEXT("NunHairHeadCollision"))return 5;
    Body->TickAnimation(.1f,false);Body->RefreshBoneTransforms();
    Head->TickAnimation(.1f,false);Head->RefreshBoneTransforms();
    // Reproduce the former cache omission only on this actor's transient collision asset.
    const auto BoundBodies=Physics->BoundsBodies;
    const bool Fixed=Head->bComponentUseFixedSkelBounds;
    Physics->BoundsBodies.Reset();Head->bComponentUseFixedSkelBounds=false;
    Head->InvalidateCachedBounds();
    const FBoxSphereBounds Broken=Head->CalcBounds(FTransform::Identity);
    Physics->BoundsBodies=BoundBodies;Head->bComponentUseFixedSkelBounds=Fixed;
    Head->InvalidateCachedBounds();
    const FBoxSphereBounds Corrected=Head->CalcBounds(FTransform::Identity);
    auto Report=MakeShared<FJsonObject>();
    Report->SetStringField(TEXT("old_origin_cm"),Broken.Origin.ToString());
    Report->SetStringField(TEXT("old_extent_cm"),Broken.BoxExtent.ToString());
    Report->SetStringField(TEXT("corrected_origin_cm"),Corrected.Origin.ToString());
    Report->SetStringField(TEXT("corrected_extent_cm"),Corrected.BoxExtent.ToString());
    Report->SetNumberField(TEXT("collision_bounds_bodies"),BoundBodies.Num());
    Report->SetBoolField(TEXT("uses_authored_head_bounds"),Fixed);
    const auto* Render=Head->GetSkeletalMeshAsset()->GetResourceForRendering();
    if(!Render||Render->LODRenderData.IsEmpty())return 6;
    TArray<TSharedPtr<FJsonValue>> Lods;
    bool Valid=BoundBodies.Num()==2&&Fixed&&Corrected.Origin.Z>120.&&Corrected.BoxExtent.Z>10.;
    for(int32 L=0;L<Render->LODRenderData.Num();++L)
    {
        const auto& Lod=Render->LODRenderData[L];
        auto* Weights=Head->GetSkinWeightBuffer(L);
        if(!Weights){Valid=false;continue;}
        TArray<FMatrix44f> Matrices;Head->GetCurrentRefToLocalMatrices(Matrices,L);
        FBox Geometry(ForceInit);
        for(uint32 I=0;I<Lod.GetNumVertices();++I)
            Geometry+=FVector(USkinnedMeshComponent::GetSkinnedVertexPosition(Head,I,Lod,*Weights,Matrices));
        auto Row=MakeShared<FJsonObject>();
        Row->SetNumberField(TEXT("lod"),L);Row->SetNumberField(TEXT("vertices"),Lod.GetNumVertices());
        Row->SetStringField(TEXT("posed_geometry_min_cm"),Geometry.Min.ToString());
        Row->SetStringField(TEXT("posed_geometry_max_cm"),Geometry.Max.ToString());
        const bool PoseValid=Geometry.IsValid&&!Geometry.Min.ContainsNaN()&&!Geometry.Max.ContainsNaN()
            &&Geometry.Max.Z>150.&&Geometry.Max.Z<185.&&Geometry.GetCenter().Z>120.;
        const bool Inside=Corrected.GetBox().IsInsideOrOn(Geometry.Min)&&Corrected.GetBox().IsInsideOrOn(Geometry.Max);
        Row->SetBoolField(TEXT("pose_valid"),PoseValid);
        Row->SetBoolField(TEXT("posed_geometry_inside_bounds"),Inside);Valid&=PoseValid&&Inside;
        Lods.Add(MakeShared<FJsonValueObject>(Row));
    }
    Report->SetArrayField(TEXT("head_lods"),Lods);
    Report->SetBoolField(TEXT("passed"),Valid);
    Report->SetBoolField(TEXT("gameplay_or_visual_acceptance_run"),false);
    FString Json;auto Writer=TJsonWriterFactory<>::Create(&Json);FJsonSerializer::Serialize(Report,Writer);
    const FString Path=FPaths::ProjectDir()/TEXT("SourceAssets/ChapelNun20261115/FaceHairFixR1/bounds_diagnosis.json");
    if(!FFileHelper::SaveStringToFile(Json,*Path))return 7;
    UE_LOG(LogTemp,Display,TEXT("NUN_FACE_BOUNDS %s old=%s fixed=%s"),Valid?TEXT("PASS"):TEXT("FAIL"),*Broken.Origin.ToString(),*Corrected.Origin.ToString());
    return Valid?0:8;
}
