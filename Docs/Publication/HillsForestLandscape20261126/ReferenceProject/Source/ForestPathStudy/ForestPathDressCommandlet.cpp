#include "ForestPathDressCommandlet.h"
#include "ActorFactories/ActorFactory.h"
#include "AssetCompilingManager.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "Builders/CubeBuilder.h"
#include "CineCameraActor.h"
#include "CineCameraComponent.h"
#include "Components/DecalComponent.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/SplineComponent.h"
#include "Elements/PCGDensityFilter.h"
#include "Elements/PCGMergeElement.h"
#include "Elements/PCGProjectionElement.h"
#include "Elements/PCGSpawnActor.h"
#include "Elements/PCGSplineSampler.h"
#include "Elements/PCGTypedGetter.h"
#include "Elements/PCGPointExtentsModifier.h"
#include "Elements/PCGStaticMeshSpawner.h"
#include "Elements/PCGSurfaceSampler.h"
#include "Elements/PCGTransformPoints.h"
#include "Engine/DecalActor.h"
#include "Engine/DirectionalLight.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "EngineUtils.h"
#include "FileHelpers.h"
#include "Landscape.h"
#include "Materials/MaterialInterface.h"
#include "MeshSelectors/PCGMeshSelectorWeighted.h"
#include "Misc/PackageName.h"
#include "PCGComponent.h"
#include "PCGGraph.h"
#include "PCGNode.h"
#include "PCGVolume.h"
#include "Subsystems/EditorAssetSubsystem.h"
#include "WorldPartition/WorldPartitionHelpers.h"

namespace
{
struct FForestLayer
{
    FString Name;
    TArray<FSoftObjectPath> Meshes;
    float Density, Spacing, MinScale, MaxScale, Z, Setback;
    int32 SeedOffset;
    bool bUpright;
};

TArray<FSoftObjectPath> Trees(const FString& Pack, const TArray<FString>& Variants)
{
    TArray<FSoftObjectPath> Result;
    for (const FString& Variant : Variants)
    {
        FString Name = TEXT("SM_") + Pack + TEXT("_") + Variant;
        Result.Emplace(TEXT("/Game/") + Pack + TEXT("/Geometry/SimpleWind/") + Name + TEXT(".") + Name);
    }
    return Result;
}

TArray<FSoftObjectPath> Scans(const TArray<FString>& Keys)
{
    IAssetRegistry& Registry = FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry").Get();
    TArray<FSoftObjectPath> Result;
    for (const FString& Key : Keys)
    {
        FString Dir = TEXT("/Game/ForestPathStudy/Scans/") + Key;
        Registry.ScanPathsSynchronous({Dir});
        TArray<FAssetData> Found;
        Registry.GetAssetsByPath(*Dir, Found, true);
        for (const FAssetData& Data : Found)
            if (Data.AssetClassPath == UStaticMesh::StaticClass()->GetClassPathName()
                && !Data.AssetName.ToString().Contains(TEXT("_LOD"))
                && !Data.PackageName.ToString().Contains(TEXT("_nonUE/")))
                Result.Add(Data.GetSoftObjectPath());
    }
    Result.Sort([](const FSoftObjectPath& A,const FSoftObjectPath& B) { return A.ToString() < B.ToString(); });
    return Result;
}

UPCGGraph* MakeGraph(const FForestLayer& Layer)
{
    if (Layer.Meshes.IsEmpty()) return nullptr;
    UEditorAssetSubsystem* Library = GEditor->GetEditorSubsystem<UEditorAssetSubsystem>();
    FString Dir = TEXT("/Game/ForestPathStudy/PCG/PCG_ForestPath");
    FString Path = Dir + Layer.Name;
    if (Library->DoesAssetExist(Path)) return Cast<UPCGGraph>(Library->LoadAsset(Path));
    UPCGGraph* Graph = Cast<UPCGGraph>(Library->DuplicateAsset(Dir + TEXT("CanopyPoints"), Path));
    if (!Graph) return nullptr;
    UPCGNode* Transform = nullptr;
    for (UPCGNode* Node : Graph->GetNodes())
    {
        auto* Settings = Node->GetSettings();
        if (auto* Surface = Cast<UPCGSurfaceSamplerSettings>(Settings))
        {
            // Keep the full tutorial point recipe in CanopyPoints. Limit secondary detail to the photographed clearing.
            Surface->bUnbounded = false;
            Surface->PointExtents = FVector(Layer.Spacing);
            Surface->Seed += Layer.SeedOffset;
        }
        if (auto* Filter = Cast<UPCGDensityFilterSettings>(Settings)) Filter->LowerBound = Layer.Density;
        if (auto* Extents = Cast<UPCGPointExtentsModifierSettings>(Settings)) Extents->Extents = FVector(1., Layer.Setback, Layer.Setback);
        if (auto* Pose = Cast<UPCGTransformPointsSettings>(Settings))
        {
            Transform = Node;
            Pose->OffsetMin = Pose->OffsetMax = FVector(0.,0.,Layer.Z);
            Pose->ScaleMin = FVector(Layer.MinScale);
            Pose->ScaleMax = FVector(Layer.MaxScale);
            Pose->bAbsoluteRotation = Layer.bUpright;
        }
    }
    if (!Transform) return nullptr;
    UPCGStaticMeshSpawnerSettings* Spawn = nullptr;
    UPCGNode* SpawnNode = Graph->AddNodeOfType(Spawn);
    SpawnNode->SetNodePosition(1940, 0);
    Graph->GetOutputNode()->SetNodePosition(2240, 0);
    Spawn->SetMeshSelectorType(UPCGMeshSelectorWeighted::StaticClass());
    auto* Selector = CastChecked<UPCGMeshSelectorWeighted>(Spawn->MeshSelectorParameters);
    Selector->MeshEntries.Reset();
    for (const FSoftObjectPath& Mesh : Layer.Meshes)
        Selector->MeshEntries.Emplace(TSoftObjectPtr<UStaticMesh>(Mesh), 1);
    Graph->RemoveEdge(Transform, TEXT("Out"), Graph->GetOutputNode(), TEXT("Out"));
    Graph->AddEdge(Transform, TEXT("Out"), SpawnNode, TEXT("In"));
    Graph->AddEdge(SpawnNode, TEXT("Out"), Graph->GetOutputNode(), TEXT("Out"));
    return Library->SaveLoadedAsset(Graph, false) ? Graph : nullptr;
}

bool GenerateLayer(UWorld* World, const FForestLayer& Layer)
{
    UPCGGraph* Graph = MakeGraph(Layer);
    if (!Graph) return false;
    const bool Full = Layer.Name == TEXT("Canopy");
    FVector Centre = Full ? FVector::ZeroVector : FVector(-9000.,20100.,0.);
    APCGVolume* Volume = World->SpawnActor<APCGVolume>();
    Volume->SetActorLabel(TEXT("Forest path - ") + Layer.Name);
    auto* Cube = NewObject<UCubeBuilder>();
    Cube->X = Full ? 50400.f : 19500.f;
    Cube->Y = Full ? 50400.f : 10200.f;
    Cube->Z = 18000.f;
    UActorFactory::CreateBrushForVolumeActor(Volume,Cube);
    Volume->SetActorLocation(Centre);
    UPCGComponent* PCG = Volume->PCGComponent;
    PCG->GenerationTrigger = EPCGComponentGenerationTrigger::GenerateOnDemand;
    PCG->SetIsPartitioned(false);
    PCG->SetEditingMode(EPCGEditorDirtyMode::Normal, EPCGEditorDirtyMode::Normal);
    PCG->SetGraph(Graph);
    FWorldPartitionHelpers::FakeEngineTick(World);
    if (PCG->GenerateLocalGetTaskId(true) == InvalidPCGTaskId) return false;
    double Deadline = FPlatformTime::Seconds() + 900.;
    while (PCG->IsGenerating() && FPlatformTime::Seconds() < Deadline)
    {
        FWorldPartitionHelpers::FakeEngineTick(World);
        FPlatformProcess::Sleep(0.005f);
    }
    TInlineComponentArray<UInstancedStaticMeshComponent*> Instances(Volume);
    int32 Total = 0;
    for (const auto* Component : Instances) Total += Component->GetInstanceCount();
    UE_LOG(LogTemp, Display, TEXT("Forest layer %s authored %d instances."), *Layer.Name, Total);
    return !PCG->IsGenerating() && Total > 0;
}

UPCGGraph* MakeRoadDecalGraph()
{
    UEditorAssetSubsystem* Lib = GEditor->GetEditorSubsystem<UEditorAssetSubsystem>();
    FString Base = TEXT("/Game/ForestPathStudy/PCG/PCG_ForestPath");
    FString Path = Base + TEXT("RoadDecals");
    if (Lib->DoesAssetExist(Path)) return Cast<UPCGGraph>(Lib->LoadAsset(Path));
    UPCGGraph* Graph = Cast<UPCGGraph>(Lib->DuplicateAsset(Base + TEXT("CanopyPoints"), Path));
    if (!Graph) return nullptr;
    TArray<UPCGNode*> Remove;
    UPCGNode* SplineNode = nullptr;
    for (UPCGNode* Node : Graph->GetNodes())
    {
        auto* Settings = Node->GetSettings();
        if (auto* Spline = Cast<UPCGSplineSamplerSettings>(Settings))
        {
            SplineNode = Node;
            Spline->SamplerParams.Mode = EPCGSplineSamplingMode::Distance;
            Spline->SamplerParams.DistanceIncrement = 350.f;
        }
        else if (!Settings->IsA<UPCGGetLandscapeSettings>() && !Settings->IsA<UPCGGetSplineSettings>()
                && !Settings->IsA<UPCGProjectionSettings>())
            Remove.Add(Node);
    }
    if (!SplineNode) return nullptr;
    Graph->RemoveNodes(Remove);
    UPCGMergeSettings* Join = nullptr;
    UPCGNode* Merge = Graph->AddNodeOfType(Join);
    Merge->SetNodePosition(1170, 300);
    Graph->GetOutputNode()->SetNodePosition(1450, 300);
    Graph->AddEdge(Merge,TEXT("Out"),Graph->GetOutputNode(),TEXT("Out"));
    int32 Row = 0;
    for (const FString& Key : {FString("slqlwtd"),FString("tdipmjh")})
    {
        const FString Name = TEXT("M_") + Key + TEXT("_Decal");
        const FString Ref = TEXT("/Game/ForestPathStudy/Scans/") + Key + TEXT("/") + Name + TEXT(".") + Name;
        UMaterialInterface* Mat = LoadObject<UMaterialInterface>(nullptr,*Ref);
        if (!Mat) return nullptr;
        UPCGTransformPointsSettings* Pose = nullptr;
        UPCGNode* Transform = Graph->AddNodeOfType(Pose);
        Transform->SetNodePosition(570,Row*230 + 160);
        Pose->Seed = 132944 + Row*9613;
        Pose->bAbsoluteRotation = true;
        Pose->OffsetMin = FVector(-70.,-130.,4.);
        Pose->OffsetMax = FVector(70.,130.,4.);
        Pose->RotationMin = FRotator(-90.,-360.,0.);
        Pose->RotationMax = FRotator(-90.,360.,0.);
        Pose->ScaleMin = FVector(.2); Pose->ScaleMax = FVector(.5);
        Graph->AddEdge(SplineNode,TEXT("Out"),Transform,TEXT("In"));
        UPCGSpawnActorSettings* Spawn = nullptr;
        UPCGNode* Node = Graph->AddNodeOfType(Spawn);
        Node->SetNodePosition(850,Row*230 + 160);
        Spawn->Option = EPCGSpawnActorOption::NoMerging;
        Spawn->SetTemplateActorClass(ADecalActor::StaticClass());
        Spawn->SetAllowTemplateActorEditing(true);
        ADecalActor* Model = Cast<ADecalActor>(Spawn->TemplateActor.Get());
        if (!Model) return nullptr;
        Model->GetDecal()->SetDecalMaterial(Mat);
        Model->GetDecal()->DecalSize = FVector(100., Row ? 100. : 170., Row ? 100. : 170.);
        Spawn->ActorLabel = TEXT("Road decal - ") + Key;
        Graph->AddEdge(Transform,TEXT("Out"),Node,TEXT("In"));
        Graph->AddEdge(Node,TEXT("Out"),Merge,TEXT("In"));
        ++Row;
    }
    return Lib->SaveLoadedAsset(Graph,false) ? Graph : nullptr;
}

bool GenerateRoadDecals(UWorld* World, AActor* Road)
{
    UPCGGraph* Graph = MakeRoadDecalGraph();
    if (!Graph) return false;
    auto* PCG = NewObject<UPCGComponent>(Road,TEXT("RoadDecalPCG"),RF_Transactional);
    Road->AddInstanceComponent(PCG);
    PCG->GenerationTrigger = EPCGComponentGenerationTrigger::GenerateOnDemand;
    PCG->RegisterComponent();
    PCG->SetIsPartitioned(false);
    PCG->SetEditingMode(EPCGEditorDirtyMode::Normal,EPCGEditorDirtyMode::Normal);
    PCG->SetGraph(Graph);
    FWorldPartitionHelpers::FakeEngineTick(World);
    if (PCG->GenerateLocalGetTaskId(true) == InvalidPCGTaskId) return false;
    double Deadline = FPlatformTime::Seconds() + 180.;
    while (PCG->IsGenerating() && FPlatformTime::Seconds() < Deadline)
    {
        FWorldPartitionHelpers::FakeEngineTick(World);
        FPlatformProcess::Sleep(.005f);
    }
    int32 Count = 0;
    for (TActorIterator<ADecalActor> It(World); It; ++It) ++Count;
    UE_LOG(LogTemp,Display,TEXT("Forest road authored %d decal actors."),Count);
    return !PCG->IsGenerating() && Count > 0;
}

bool DecorateRoad(UWorld* World, ALandscape* Land, USplineComponent* Path)
{
    auto Height = [Land](FVector P, float Offset, FVector& Out)
    {
        TOptional<float> Value = Land->GetHeightAtLocation(P);
        if (!Value.IsSet()) return false;
        Out = FVector(P.X, P.Y, Value.GetValue() + Offset);
        return true;
    };
    if (!GenerateRoadDecals(World,Path->GetOwner())) return false;
    const FVector ViewPos(-10502.60,23732.50,-404.63);
    const FRotator ViewAngle(-3.474998,-77.725024,0.);
    ACineCameraActor* Camera = World->SpawnActor<ACineCameraActor>(ViewPos,ViewAngle);
    Camera->SetActorLabel(TEXT("Forest path - 15mm trail camera"));
    UCineCameraComponent* Lens = Camera->GetCineCameraComponent();
    Lens->SetFilmbackPresetByName(TEXT("16:9 DSLR"));
    Lens->SetCurrentFocalLength(15.f);
    Lens->SetCurrentAperture(1.67222f);
    auto Focus = Lens->FocusSettings;
    Focus.ManualFocusDistance = 580.5357f;
    Lens->SetFocusSettings(Focus);
    Lens->PostProcessSettings.bOverride_AutoExposureMethod = true;
    Lens->PostProcessSettings.AutoExposureMethod = AEM_Manual;
    Lens->PostProcessSettings.bOverride_AutoExposureBias = true;
    Lens->PostProcessSettings.AutoExposureBias = 10.f;
    if (World->EditorViews.IsValidIndex(LVT_Perspective))
    {
        World->EditorViews[LVT_Perspective].CamPosition = ViewPos;
        World->EditorViews[LVT_Perspective].CamRotation = ViewAngle;
    }
    TArray<FSoftObjectPath> Boulder = Scans({TEXT("wc1kedt")});
    if (!Boulder.IsEmpty())
    {
        float D = 3000.f;
        FVector P = Path->GetLocationAtDistanceAlongSpline(D, ESplineCoordinateSpace::World)
            + 430.f * Path->GetRightVectorAtDistanceAlongSpline(D, ESplineCoordinateSpace::World);
        FVector Location;
        if (Height(P,-22.f,Location))
        {
            AStaticMeshActor* Rock = World->SpawnActor<AStaticMeshActor>(Location,FRotator(0.,37.,0.));
            Rock->GetStaticMeshComponent()->SetStaticMesh(Cast<UStaticMesh>(Boulder[0].TryLoad()));
            Rock->SetActorLabel(TEXT("Mossy forest boulder - camera verge"));
        }
    }
    for (TActorIterator<ADirectionalLight> Sun(World); Sun; ++Sun)
        Sun->SetActorRotation(FRotator(-15.,ViewAngle.Yaw+156.,0.));
    return true;
}
}

int32 UForestPathDressCommandlet::Main(const FString& Params)
{
    const FString Base = TEXT("/Game/ForestPathStudy/Maps/L_ForestPathCameraRoute");
    UWorld* World = UEditorLoadingAndSavingUtils::LoadMap(FPackageName::LongPackageNameToFilename(Base, FPackageName::GetMapPackageExtension()));
    if (!World) return 1;
    ALandscape* Land = nullptr;
    USplineComponent* Road = nullptr;
    for (TActorIterator<ALandscape> It(World); It; ++It) Land = *It;
    for (TActorIterator<AActor> It(World); It; ++It)
        if (It->GetClass()->GetName() == TEXT("BP_ForestPathSpline_C")) Road = It->FindComponentByClass<USplineComponent>();
    if (!Road || !Land || !DecorateRoad(World,Land,Road)) return 1;
    TArray<FForestLayer> Layers = {
        {TEXT("Canopy"),Trees(TEXT("EuropeanHornbeam"),{TEXT("Forest_05"),TEXT("Forest_04")}), .679997f,100,.8f,1.2f,-20,50,0,true},
        {TEXT("Hazel"),Trees(TEXT("CommonHazel"),{TEXT("Forest_01"),TEXT("Forest_02")}), .73f,75,.2f,.5f,-89,29,18522,true},
        {TEXT("Rocks"),Scans({TEXT("xjijdiz"),TEXT("xisffer"),TEXT("xiemca1"),TEXT("vikrdcnaw"),TEXT("vimrfjsaw")}), .89f,60,.35f,.78f,-3,15,78421,false},
        {TEXT("LeafyWeeds"),Scans({TEXT("rbpir"),TEXT("rbcuh")}), .54f,38,.65f,1.2f,-1,10,51805,false}
    };
    for (const FForestLayer& Layer : Layers)
    {
        if (!GenerateLayer(World,Layer))
        {
            UE_LOG(LogTemp,Error,TEXT("Unable to author %s."),*Layer.Name);
            return 1;
        }
    }
    FAssetCompilingManager::Get().FinishAllCompilation();
    const FString Name = TEXT("/Game/ForestPathStudy/Maps/L_ForestPathForest");
    if (!UEditorLoadingAndSavingUtils::SaveMap(World, Name)) return 1;
    UE_LOG(LogTemp,Display,TEXT("Saved dressed map %s"), *Name);
    return 0;
}
