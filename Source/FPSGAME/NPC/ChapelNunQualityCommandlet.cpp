#include "ChapelNunQualityCommandlet.h"
#if WITH_EDITOR
#include "ChapelNun.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "../Characters/FPSOutfitStairVisibility.h"
#include "Containers/Ticker.h"
#include "AssetCompilingManager.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SkyLightComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/TextureCube.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/World.h"
#include "FXSystem.h"
#include "GroomAsset.h"
#include "GroomBindingAsset.h"
#include "GroomComponent.h"
#include "HAL/IConsoleManager.h"
#include "ImageUtils.h"
#include "Materials/MaterialInterface.h"
#include "Misc/FileHelper.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "NiagaraComponent.h"
#include "RenderingThread.h"
#include "SceneView.h"
#include "SceneViewExtension.h"
#include "Serialization/JsonSerializer.h"
#include "ContentStreaming.h"

int32 RepairChapelNunBack(const FString& OutputDirectory);
int32 FinalizeChapelNunBackMaterials(const FString& OutputDirectory);

// Scene captures normally skip guide interpolation / GPU particles. This isolated
// commandlet has no main viewport to perform those updates, so its inspection view
// must drive them itself. Scope the override to this temporary render world.
class FNunInspectionViewExtension final : public FSceneViewExtensionBase
{
public:
    FNunInspectionViewExtension(const FAutoRegister& AutoRegister, const FSceneInterface* InScene)
        : FSceneViewExtensionBase(AutoRegister), InspectionScene(InScene) {}
    virtual void SetupViewFamily(FSceneViewFamily& Family) override {}
    virtual void SetupView(FSceneViewFamily& Family, FSceneView& View) override
    {
        if(Family.Scene==InspectionScene)View.bIsSceneCapture=false;
    }
    virtual void BeginRenderViewFamily(FSceneViewFamily& Family) override {}
private:
    const FSceneInterface* InspectionScene;
};
#endif

bool UChapelNunQualityCommandlet::ApplyRefinedRootUV()
{
#if WITH_EDITOR
    FString Revision=TEXT("RefinementR4");FParse::Value(FCommandLine::Get(),TEXT("NunHairRevision="),Revision);
    if(Revision!=TEXT("RefinementR4")&&Revision!=TEXT("HairReferenceR5"))return false;
    const bool ReferenceHair=Revision==TEXT("HairReferenceR5");
    const FString Folder=FPaths::ProjectDir()/TEXT("SourceAssets/ChapelNun20261115")/Revision/TEXT("Authored");
    for(const TCHAR* Kind:{TEXT("Core"),TEXT("Loose")})
    {
        const FString Name=FString(TEXT("Nun_LowBun_"))+Kind+(ReferenceHair?TEXT("_R5"):TEXT("_R4"));
        auto* Groom=LoadObject<UGroomAsset>(nullptr,*(TEXT("/Game/Characters/ChapelNun20261115/")+Revision+TEXT("/Grooms/")+Name));
        if(!Groom)return false;
        TArray<uint8> Data;if(!FFileHelper::LoadFileToArray(Data,*(Folder/(Name+TEXT("_rootuv.bin")))))return false;
        FHairDescription Description=Groom->GetHairDescription();
        if(Data.Num()!=Description.GetNumStrands()*sizeof(FVector2f))return false;
        const FVector2f* UV=reinterpret_cast<const FVector2f*>(Data.GetData());
        for(int32 I=0;I<Description.GetNumStrands();++I)
            SetHairStrandAttribute(Description,FStrandID(I),HairAttribute::Strand::RootUV,UV[I]);
        Groom->CommitHairDescription(MoveTemp(Description),EHairDescriptionType::Source);
        if(!Groom->CacheDerivedDatas())return false;
        Groom->MarkPackageDirty();
    }
    return true;
#else
    return false;
#endif
}

int32 UChapelNunQualityCommandlet::Main(const FString& Params)
{
#if WITH_EDITOR
    const bool Before=FParse::Param(*Params,TEXT("Before"));
    const bool Unlit=FParse::Param(*Params,TEXT("Unlit"));
    const bool OriginalFace=FParse::Param(*Params,TEXT("OriginalFace"));
    const bool Refined=FParse::Param(*Params,TEXT("Refined"));
    const bool ReferenceHair=FParse::Param(*Params,TEXT("ReferenceHair"));
    const bool NoShadows=FParse::Param(*Params,TEXT("NoShadows"));
    const bool RuntimePose=FParse::Param(*Params,TEXT("RuntimePose"));
    const bool CrossedIdleReview=FParse::Param(*Params,TEXT("CrossedIdleReview"));
    const bool RelaxedIdleReview=CrossedIdleReview||FParse::Param(*Params,TEXT("RelaxedIdleReview"));
    const bool IdleReview=RelaxedIdleReview||FParse::Param(*Params,TEXT("IdleReview"));
    const bool HideRobeHood=FParse::Param(*Params,TEXT("HideRobeHood"));
    if(FParse::Param(*Params,TEXT("RepairBackHood")))
        return RepairChapelNunBack(FPaths::ProjectDir()/TEXT("SourceAssets/ChapelNun20261115/IdleBackReviewR2"));
    if(FParse::Param(*Params,TEXT("FinalizeBackSlots")))
        return FinalizeChapelNunBackMaterials(FPaths::ProjectDir()/TEXT("SourceAssets/ChapelNun20261115/IdleBackReviewR2"));
    if(FParse::Param(*Params,TEXT("ExportNativeHair")))
    {
        const FString Folder=FPaths::ProjectDir()/TEXT("SourceAssets/ChapelNun20261115/RefinementR4/Inputs");
        IFileManager::Get().MakeDirectory(*Folder,true);
        auto* Native=LoadObject<UGroomAsset>(nullptr,TEXT("/Game/Characters/KaitlinPlayer20261023/Native/Kaitlin/Grooms/Hair_L_Straight.Hair_L_Straight"));
        if(!Native)return 6;
        auto Metadata=MakeShared<FJsonObject>();Metadata->SetStringField(TEXT("asset"),Native->GetPathName());
        TArray<TSharedPtr<FJsonValue>> Items;int32 Index=0;
        auto Bytes=[&](const FString& Name,const void* Data,int64 Count)
        {return FFileHelper::SaveArrayToFile(TArrayView<const uint8>(static_cast<const uint8*>(Data),Count),*(Folder/Name));};
        for(const auto& Group:Native->GetHairDescriptionGroups().HairGroups)
        {
            const auto& D=Group.Strands;const FString Prefix=FString::Printf(TEXT("native_hair_%d"),Index++);
            if(!Bytes(Prefix+TEXT("_points.bin"),D.StrandsPoints.PointsPosition.GetData(),D.StrandsPoints.PointsPosition.Num()*sizeof(FVector3f))||
               !Bytes(Prefix+TEXT("_counts.bin"),D.StrandsCurves.CurvesCount.GetData(),D.StrandsCurves.CurvesCount.Num()*sizeof(uint16))||
               !Bytes(Prefix+TEXT("_offsets.bin"),D.StrandsCurves.CurvesOffset.GetData(),D.StrandsCurves.CurvesOffset.Num()*sizeof(uint32)))return 7;
            Bytes(Prefix+TEXT("_rootuv.bin"),D.StrandsCurves.CurvesRootUV.GetData(),D.StrandsCurves.CurvesRootUV.Num()*sizeof(FVector2f));
            auto Item=MakeShared<FJsonObject>();Item->SetStringField(TEXT("prefix"),Prefix);Item->SetNumberField(TEXT("curves"),D.GetNumCurves());Item->SetNumberField(TEXT("points"),D.GetNumPoints());Items.Add(MakeShared<FJsonValueObject>(Item));
        }
        Metadata->SetArrayField(TEXT("groups"),Items);FString Json;auto Writer=TJsonWriterFactory<>::Create(&Json);FJsonSerializer::Serialize(Metadata,Writer);FFileHelper::SaveStringToFile(Json,*(Folder/TEXT("native_hair.json")));return 0;
    }
    // Standalone captures do not run the editor frame loop that drains delayed PSO proxies.
    IConsoleManager::Get().FindConsoleVariable(TEXT("r.PSOPrecache.ProxyCreationStrategy"))->Set(0,ECVF_SetByCode);
    const FString Base=TEXT("/Game/Characters/ChapelNun20261115/");
    const FString Root=Refined?Base+TEXT("RefinementR4/"):OriginalFace?Base+TEXT("OriginalMeshyFaceR3/"):Before?Base:Base+TEXT("HeadQualityR2/");
    const FString HairRoot=ReferenceHair?Base+TEXT("HairReferenceR5/"):Refined?Root:OriginalFace?Base+TEXT("HeadQualityR2/"):Root;
    const FString Suffix=Before?TEXT(""):TEXT("_R2");
    FString Out=FPaths::ProjectDir()/TEXT("SourceAssets/ChapelNun20261115")/(ReferenceHair?TEXT("HairReferenceR5"):Refined?TEXT("RefinementR4"):OriginalFace?TEXT("OriginalMeshyFaceR3"):TEXT("HeadQualityR2"))/(RuntimePose?TEXT("EngineRuntime"):NoShadows?TEXT("EngineNoShadows"):Before?TEXT("EngineBefore"):Unlit?TEXT("EngineUnlit"):TEXT("EngineAfter"));
    FParse::Value(*Params,TEXT("CaptureOut="),Out);
    IFileManager::Get().MakeDirectory(*Out,true);
    auto* Mesh=LoadObject<USkeletalMesh>(nullptr,*(Root+(Refined?TEXT("Meshes/SK_Nun_OriginalMeshyFace_Final"):OriginalFace?TEXT("Meshes/SK_Nun_OriginalMeshyFace"):Before?TEXT("Meshes/SK_Nun_Head"):TEXT("Meshes/SK_Nun_Head_R2_Final"))));
    if(!Mesh)return 2;
    const auto Settings=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(true)
        .RequiresHitProxies(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    auto* World=UWorld::CreateWorld(EWorldType::GamePreview,false,TEXT("NunHeadInspection"),nullptr,true,ERHIFeatureLevel::Num,&Settings);
    auto InspectionViewExtension=FSceneViewExtensions::NewExtension<FNunInspectionViewExtension>(World->Scene);
    World->FXSystem=FFXSystemInterface::Create(World->GetFeatureLevel(),World->Scene);
    World->Scene->SetFXSystem(World->FXSystem.Get());
    auto* Owner=World->SpawnActor<AActor>();
    auto* Head=NewObject<USkeletalMeshComponent>(Owner);Owner->AddInstanceComponent(Head);
    Head->SetSkeletalMeshAsset(Mesh);Head->SetForcedLOD(1);Head->bComponentUseFixedSkelBounds=true;Head->RegisterComponent();
    Head->RefreshBoneTransforms();Head->PrestreamTextures(30.f,true);
    auto Report=MakeShared<FJsonObject>();Report->SetStringField(TEXT("head"),Mesh->GetPathName());
    TArray<TSharedPtr<FJsonValue>> Materials;
    for(const auto& Slot:Mesh->GetMaterials())Materials.Add(MakeShared<FJsonValueString>(Slot.MaterialInterface?Slot.MaterialInterface->GetPathName():TEXT("Missing")));
    Report->SetArrayField(TEXT("materials"),Materials);
    Report->SetBoolField(TEXT("reference_pose_asset_inspection"),true);Report->SetBoolField(TEXT("gameplay_started"),false);
    Report->SetBoolField(TEXT("offscreen_hair_guide_updates"),true);
    TArray<TSharedPtr<FJsonValue>> OutfitAssets;
    FFPSRobeStairSections BodyInner,BootInner;
    if(OriginalFace)
    {
        for(const TCHAR* Name:{TEXT("SK_Nun_Body"),TEXT("SK_Nun_BlackRobe"),TEXT("SK_Nun_CollarCross"),TEXT("SK_Nun_Boots")})
        {
            const bool NewPart=Refined&&(FString(Name)==TEXT("SK_Nun_CollarCross")||FString(Name)==TEXT("SK_Nun_Boots"));
            const FString PartName=Refined&&FString(Name)==TEXT("SK_Nun_CollarCross")?TEXT("SK_Nun_CollarCross_Final"):Name;
            auto* OutfitMesh=LoadObject<USkeletalMesh>(nullptr,*((NewPart?Root:Base)+TEXT("Meshes/")+PartName));
            if(!OutfitMesh)return 5;
            auto* Part=NewObject<USkeletalMeshComponent>(Owner);Owner->AddInstanceComponent(Part);
            Part->SetSkeletalMeshAsset(OutfitMesh);Part->SetForcedLOD(1);Part->bComponentUseFixedSkelBounds=true;
            Part->bDisableClothSimulation=true;Part->RegisterComponent();Part->RefreshBoneTransforms();Part->PrestreamTextures(30.f,true);
            const FString Label(Name);
            if(Label==TEXT("SK_Nun_Body"))
            {
                BodyInner.Initialize(Part,{0,1,3,7,8,9,10,14});BodyInner.Apply(false);
                const auto& Slots=OutfitMesh->GetMaterials();
                for(int32 I=0;I<Slots.Num();++I)
                {
                    const FString Slot=Slots[I].MaterialSlotName.ToString();
                    if(Slot==TEXT("SkinBoots_12")||Slot==TEXT("SkinArmoredBoot_12")||Slot==TEXT("RobeStairHidden_12")||Slot==TEXT("RobeStairHidden_15")||Slot==TEXT("RobeStairHidden_16"))
                        for(int32 Lod=0;Lod<OutfitMesh->GetLODNum();++Lod)Part->ShowMaterialSection(I,INDEX_NONE,false,Lod);
                }
            }
            if(Label==TEXT("SK_Nun_Boots")){BootInner.Initialize(Part,{});BootInner.Apply(false);}
            OutfitAssets.Add(MakeShared<FJsonValueString>(OutfitMesh->GetPathName()));
        }
    }
    Report->SetArrayField(TEXT("outfit_assets"),OutfitAssets);
    TArray<TSharedPtr<FJsonValue>> Grooms;
    TArray<UGroomComponent*> HairComponents;
    for(const TCHAR* Kind:{TEXT("Core"),TEXT("Loose")})
    {
        const FString Name=FString(TEXT("Nun_LowBun_"))+Kind+(ReferenceHair?TEXT("_R5"):Refined?TEXT("_R4"):Suffix);
        auto* Asset=LoadObject<UGroomAsset>(nullptr,*(HairRoot+TEXT("Grooms/")+Name));
        const FString BindingName=ReferenceHair?Name+TEXT("_Binding"):OriginalFace?FString(TEXT("Nun_LowBun_"))+Kind+(Refined?TEXT("_Final_Binding"):TEXT("_OriginalFace_Binding")):Name+(Before?TEXT("_Binding"):TEXT("_Final_Binding"));
        auto* Binding=LoadObject<UGroomBindingAsset>(nullptr,*((ReferenceHair?HairRoot:Root)+TEXT("Grooms/")+BindingName));
        if(!Asset||!Binding)return 3;
        auto* Hair=NewObject<UGroomComponent>(Owner);Owner->AddInstanceComponent(Hair);Hair->SetupAttachment(Head);
        Hair->SetGroomAsset(Asset,Binding,false);Hair->SetForcedLOD(0);
        Hair->SetMaterial(0,LoadObject<UMaterialInterface>(nullptr,*((ReferenceHair?HairRoot:Refined?Root:Base)+TEXT("Materials/MI_Nun_Hair"))));Hair->RegisterComponent();
        HairComponents.Add(Hair);
        const auto& Groups=Asset->GetHairDescriptionGroups();
        auto Item=MakeShared<FJsonObject>();Item->SetStringField(TEXT("asset"),Asset->GetPathName());
        Item->SetStringField(TEXT("binding"),Binding->GetPathName());
        FBox Bounds(ForceInit);int32 Curves=0;
        for(const auto& Group:Groups.HairGroups)
        {
            Curves+=Group.Strands.GetNumCurves();
            for(const auto& Point:Group.Strands.StrandsPoints.PointsPosition)Bounds+=FVector(Point);
        }
        Item->SetNumberField(TEXT("curves"),Curves);Item->SetStringField(TEXT("bounds_min"),Bounds.Min.ToString());Item->SetStringField(TEXT("bounds_max"),Bounds.Max.ToString());
        Grooms.Add(MakeShared<FJsonValueObject>(Item));
    }
    Report->SetArrayField(TEXT("grooms"),Grooms);
    TArray<USkeletalMeshComponent*> RuntimeParts;
    FVector PoseOffset=FVector::ZeroVector;
    if(RuntimePose)
    {
        // Use the production actor's actual assembly and idle pose in the isolated render world.
        TInlineComponentArray<UPrimitiveComponent*> PreviewParts(Owner);
        for(auto* Part:PreviewParts)Part->SetVisibility(false);
        auto* Delay=IConsoleManager::Get().FindConsoleVariable(TEXT("s.StreamableDelegateDelayFrames"));
        const int32 PreviousDelay=Delay?Delay->GetInt():1;
        if(Delay)Delay->Set(0,ECVF_SetByCode);
        auto* Nun=World->SpawnActor<AChapelNun>(AChapelNun::StaticClass(),FVector(0,0,84),FRotator(0,90,0));
        Nun->DispatchBeginPlay();FlushAsyncLoading();FTSTicker::GetCoreTicker().Tick(.01f);
        if(Delay)Delay->Set(PreviousDelay,ECVF_SetByCode);
        TInlineComponentArray<USkeletalMeshComponent*> Parts(Nun);
        for(const TCHAR* Name:{TEXT("KaitlinBody"),TEXT("NunHead"),TEXT("BlackHabit"),TEXT("CollarAndCross"),TEXT("RobeBoots")})
            for(auto* Part:Parts)if(Part->GetFName()==Name)
            {
                if(!Part->GetSkeletalMeshAsset()||!Part->IsVisible())return 8;
                Part->SetForcedLOD(1);Part->TickAnimation(.7f,false);Part->RefreshBoneTransforms();Part->PrestreamTextures(30.f,true);
                RuntimeParts.Add(Part);if(Part->GetFName()==TEXT("NunHead"))Head=Part;
                if(HideRobeHood&&Part->GetFName()==TEXT("BlackHabit"))
                {
                    const auto& Slots=Part->GetSkeletalMeshAsset()->GetMaterials();
                    for(int32 Slot=0;Slot<Slots.Num();++Slot)
                        if(Slots[Slot].MaterialSlotName==TEXT("RobeHood"))
                            Part->ShowMaterialSection(Slot,INDEX_NONE,false,0);
                }
            }
        if(Head->GetSkeletalMeshAsset()!=Mesh)return 9;
        HairComponents.Reset();TInlineComponentArray<UGroomComponent*> NativeHair(Nun);
        for(auto* Hair:NativeHair){Hair->SetForcedLOD(0);Hair->SetVisibility(true);HairComponents.Add(Hair);}
        const int32 Bone=Mesh->GetRefSkeleton().FindBoneIndex(TEXT("head"));
        FTransform Reference=Mesh->GetRefSkeleton().GetRefBonePose()[Bone];
        for(int32 Parent=Mesh->GetRefSkeleton().GetParentIndex(Bone);Parent>=0;Parent=Mesh->GetRefSkeleton().GetParentIndex(Parent))
            Reference=Reference*Mesh->GetRefSkeleton().GetRefBonePose()[Parent];
        PoseOffset=Head->GetBoneTransform(Bone).TransformPosition(Reference.InverseTransformPosition(FVector(0,0,157)))-FVector(0,0,157);
        Report->SetBoolField(TEXT("reference_pose_asset_inspection"),false);
        Report->SetBoolField(TEXT("production_actor_assembly"),true);
        Report->SetBoolField(TEXT("idle_animation_sampled"),true);
        Report->SetStringField(TEXT("pose_camera_offset"),PoseOffset.ToString());
    }
    if(OriginalFace)
    {
        // Neutral inspection booth keeps black hair and cloth readable without asset edits.
        auto* Cube=LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube"));
        auto* Background=LoadObject<UMaterialInterface>(nullptr,TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"));
        const float BackdropDistance=RelaxedIdleReview?700.f:IdleReview?240.f:ReferenceHair?160.f:60.f;
        const FVector Locations[]={FVector(0,-BackdropDistance,100),FVector(-BackdropDistance,0,100),FVector(0,0,-8)};
        const FVector Scales[]={FVector(20,.1,20),FVector(.1,20,20),FVector(20,20,.1)};
        for(int32 I=0;I<3;++I)
        {
            auto* Panel=NewObject<UStaticMeshComponent>(Owner);Owner->AddInstanceComponent(Panel);
            Panel->SetStaticMesh(Cube);Panel->SetMaterial(0,Background);Panel->SetCastShadow(false);
            Panel->SetWorldLocation(Locations[I]);Panel->SetWorldScale3D(Scales[I]);Panel->RegisterComponent();
        }
    }
    auto Light=[&](FRotator Rotation,float Intensity,bool Shadows=true)
    {
        auto* C=NewObject<UDirectionalLightComponent>(Owner);Owner->AddInstanceComponent(C);C->SetIntensity(Intensity);
        C->SetWorldRotation(Rotation);C->SetCastShadows(Shadows&&!NoShadows);C->SetMobility(EComponentMobility::Movable);C->RegisterComponent();
    };
    Light(FRotator(-32,-60,0),4.5f);Light(FRotator(-15,130,0),1.4f);
    Light(FRotator(-5,-90,0),1.8f,false);
    auto* Sky=NewObject<USkyLightComponent>(Owner);Owner->AddInstanceComponent(Sky);Sky->SourceType=SLS_SpecifiedCubemap;
    Sky->SetCubemap(LoadObject<UTextureCube>(nullptr,TEXT("/Engine/MapTemplates/Sky/DaylightAmbientCubemap.DaylightAmbientCubemap")));
    Sky->SetIntensity(.4f);Sky->SetMobility(EComponentMobility::Movable);Sky->RegisterComponent();USkyLightComponent::UpdateSkyCaptureContents(World);
    auto* RT=NewObject<UTextureRenderTarget2D>();RT->AddToRoot();RT->ClearColor=FLinearColor(.035f,.035f,.035f,1.f);RT->RenderTargetFormat=RTF_RGBA8;RT->InitAutoFormat(960,960);RT->UpdateResourceImmediate(true);
    auto* Camera=NewObject<USceneCaptureComponent2D>(Owner);Owner->AddInstanceComponent(Camera);Camera->RegisterComponent();Camera->TextureTarget=RT;
    Camera->CaptureSource=SCS_FinalColorLDR;Camera->FOVAngle=22;Camera->bCaptureEveryFrame=Camera->bCaptureOnMovement=false;
    Camera->bAlwaysPersistRenderingState=true;Camera->ShowFlags.SetMotionBlur(false);Camera->ShowFlags.SetAtmosphere(false);Camera->ShowFlags.SetFog(false);
    Camera->ShowFlags.SetHair(true);
    if(Unlit){Camera->ShowFlags.SetLighting(false);Camera->ShowFlags.SetHair(false);}
    Camera->PostProcessSettings.bOverride_AutoExposureMethod=true;Camera->PostProcessSettings.AutoExposureMethod=AEM_Manual;
    Camera->PostProcessSettings.bOverride_AutoExposureApplyPhysicalCameraExposure=true;Camera->PostProcessSettings.AutoExposureApplyPhysicalCameraExposure=false;
    Camera->PostProcessSettings.bOverride_AutoExposureBias=true;Camera->PostProcessSettings.AutoExposureBias=1.f;
    Camera->PostProcessSettings.bOverride_BloomIntensity=true;Camera->PostProcessSettings.BloomIntensity=0;
    FAssetCompilingManager::Get().FinishAllCompilation();
    for(auto* Hair:HairComponents)Hair->MarkRenderStateDirty();
    World->SendAllEndOfFrameUpdates();FlushRenderingCommands();
    IStreamingManager::Get().StreamAllResources(30.f);
    const TArray<FVector> Eyes=CrossedIdleReview?
        TArray<FVector>{FVector(0,530,94),FVector(530,0,94),FVector(-530,0,94),FVector(0,320,108),FVector(0,135,95),FVector(95,110,95),FVector(150,0,96),FVector(-150,0,96),FVector(0,320,108),FVector(300,0,106)}:RelaxedIdleReview?
        TArray<FVector>{FVector(0,530,94),FVector(530,0,94),FVector(-530,0,94),FVector(0,320,108),FVector(62,106,84),FVector(-62,106,84),FVector(150,5,84),FVector(-150,5,84),FVector(0,320,108),FVector(300,0,106)}:IdleReview?
        TArray<FVector>{FVector(0,520,94),FVector(0,-160,149),FVector(120,-120,149),FVector(170,8,120),FVector(0,155,103),FVector(110,110,105),FVector(0,520,94),FVector(0,520,94),FVector(0,520,94),FVector(0,-160,149),FVector(120,-120,149)}:
        TArray<FVector>{FVector(0,85,161),FVector(57,65,172),FVector(0,28,242),FVector(85,0,160),FVector(0,520,94),FVector(0,-85,161)};
    const TArray<FString> Names=RelaxedIdleReview?
        TArray<FString>{TEXT("front"),TEXT("profile_left"),TEXT("profile_right"),TEXT("arms_front"),TEXT("hand_left"),TEXT("hand_right"),TEXT("hand_left_side"),TEXT("hand_right_side"),TEXT("breath_in_front"),TEXT("breath_out_side")}:IdleReview?
        TArray<FString>{TEXT("warmup_fullbody"),TEXT("back_upper"),TEXT("back_threequarter"),TEXT("profile_torso"),TEXT("hands_front"),TEXT("hands_side"),TEXT("breath_01"),TEXT("breath_025"),TEXT("fullbody"),TEXT("back_geometry"),TEXT("back_geometry_threequarter")}:
        TArray<FString>{TEXT("front"),TEXT("threequarter"),TEXT("crown"),TEXT("profile"),TEXT("fullbody"),TEXT("back")};
    const FVector ReviewTargets[]={FVector(0,0,86),FVector(0,-2,133),FVector(0,0,134),FVector(0,0,118),FVector(0,22,97),FVector(0,22,97),FVector(0,0,86),FVector(0,0,86),FVector(0,0,86),FVector(0,-2,133),FVector(0,0,134)};
    const FVector RelaxedTargets[]={FVector(0,0,86),FVector(0,0,86),FVector(0,0,86),FVector(0,0,104),FVector(24,4,78),FVector(-25,5,78),FVector(24,4,79),FVector(-25,5,79),FVector(0,0,104),FVector(0,0,103)};
    const FVector CrossedTargets[]={FVector(0,0,86),FVector(0,0,86),FVector(0,0,86),FVector(0,0,104),FVector(0,20,86),FVector(0,20,87),FVector(0,19,90),FVector(0,19,90),FVector(0,0,104),FVector(0,0,103)};
    const int32 ViewCount=IdleReview?Eyes.Num():ReferenceHair?6:OriginalFace?5:3;
    // Revisit the front after the other views have initialized the groom's
    // view-dependent render resources. This changes only the review capture.
    for(int32 Pass=0;Pass<ViewCount+(CrossedIdleReview?1:0);++Pass)
    {
        const int32 I=Pass==ViewCount?0:Pass;
        if(IdleReview)
        {
            // Geometry-only diagnostic, transient component override; no asset material edits.
            if(!RelaxedIdleReview&&I==9)
                for(auto* Part:RuntimeParts)if(Part->GetFName()==TEXT("BlackHabit"))
                    for(int32 Slot=0;Slot<Part->GetNumMaterials();++Slot)
                        Part->SetMaterial(Slot,LoadObject<UMaterialInterface>(nullptr,TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial")));
            for(auto* Part:RuntimeParts)
                if(Part->GetFName()==TEXT("KaitlinBody"))
                {
                    const float SampleTime=RelaxedIdleReview?(I==8?1.f:I==9?2.5f:0.f):(I==6?1.f:I==7?2.5f:0.f);
                    Part->SetPosition(SampleTime,false);
                    Part->bPauseAnims=true;
                    Part->TickAnimation(0.f,false);Part->RefreshBoneTransforms();
                    if(auto* Instance=Part->GetSingleNodeInstance())
                        if(auto* Animation=Instance->GetCurrentAsset())Report->SetStringField(TEXT("idle_asset"),Animation->GetPathName());
                }
        }
        const FVector Offset=IdleReview||I==4?FVector::ZeroVector:PoseOffset;
        const FVector Target=CrossedIdleReview?CrossedTargets[I]:RelaxedIdleReview?RelaxedTargets[I]:IdleReview?ReviewTargets[I]:FVector(0,0,I==4?86:I==2?162:157)+Offset;
        Camera->SetWorldLocationAndRotation(Eyes[I]+Offset,(Target-Eyes[I]-Offset).Rotation());
        // A newly imported groom can finish its render-resource initialization
        // after the initial close-up frames. Warm the actual first view before
        // saving it, just as the later views already benefit from earlier frames.
        const int32 CaptureFrames=I==0?120:20;
        for(int32 Frame=0;Frame<CaptureFrames;++Frame)
        {
            ++GFrameCounter;
            ENQUEUE_RENDER_COMMAND(NunInspectionFrame)([](FRHICommandListImmediate&){++GFrameNumberRenderThread;});
            World->Tick(LEVELTICK_All,1.f/60);
            for(auto* Part:RuntimeParts){Part->TickAnimation(0.f,false);Part->RefreshBoneTransforms();}
            for(auto* Hair:HairComponents)
            {
                // The isolated close-up world has no player camera for distance culling.
                if(RuntimePose){Hair->SetVisibility(true);Hair->SetComponentTickEnabled(true);if(auto* Solver=Hair->GetNiagaraComponent(0))Solver->SetPaused(false);}
                Hair->TickComponent(1.f/60,LEVELTICK_All,nullptr);
            }
            World->SendAllEndOfFrameUpdates();Camera->CaptureScene();FlushRenderingCommands();
        }
        TArray<FColor> Pixels;RT->GameThread_GetRenderTargetResource()->ReadPixels(Pixels);TArray64<uint8> PNG;
        FImageUtils::PNGCompressImageArray(960,960,Pixels,PNG);
        if(!FFileHelper::SaveArrayToFile(PNG,*(Out/(Names[I]+TEXT(".png")))))return 4;
    }
    for(int32 I=0;I<HairComponents.Num();++I)
    {
        const auto* Hair=HairComponents[I];
        auto Item=Grooms[I]->AsObject();
        Item->SetNumberField(TEXT("render_groups"),Hair->GetGroupCount());
        Item->SetBoolField(TEXT("scene_proxy"),Hair->GetSceneProxy()!=nullptr);
        Item->SetStringField(TEXT("component_bounds"),Hair->Bounds.ToString());
    }
    FString Json;auto Writer=TJsonWriterFactory<>::Create(&Json);FJsonSerializer::Serialize(Report,Writer);FFileHelper::SaveStringToFile(Json,*(Out/TEXT("assets.json")));
    RT->RemoveFromRoot();World->DestroyWorld(false);
    UE_LOG(LogTemp,Display,TEXT("NUN_HEAD_QUALITY_CAPTURED %s"),*Out);return 0;
#else
    return 1;
#endif
}
