#include "ForestVillageRegion.h"
#if WITH_EDITOR
#include "ForestWoodDressing.h"
#include "ForestReferenceBoulders.h"
#include "ForestCourtyardShrubs.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "Components/DecalComponent.h"
#include "Components/HierarchicalInstancedStaticMeshComponent.h"
#include "Data/PCGPointArrayData.h"
#include "Elements/IO/PCGLoadAssetElement.h"
#include "Elements/PCGMergeElement.h"
#include "Elements/PCGGather.h"
#include "PCGSubgraph.h"
#include "UObject/MetaData.h"
#include "Elements/PCGSpawnActor.h"
#include "Elements/PCGStaticMeshSpawner.h"
#include "Engine/DecalActor.h"
#include "EngineUtils.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInterface.h"
#include "MeshSelectors/PCGMeshSelectorWeighted.h"
#include "Misc/PackageName.h"
#include "PCGComponent.h"
#include "PCGDataAsset.h"
#include "PCGGraph.h"
#include "PCGNode.h"
#include "UObject/SavePackage.h"
#include "WorldPartition/WorldPartitionHelpers.h"

namespace
{
bool SaveAsset(UObject* Asset)
{
    UPackage* Pkg=Asset->GetOutermost();
    FAssetRegistryModule::AssetCreated(Asset);
    Pkg->MarkPackageDirty();
    FSavePackageArgs Args; Args.TopLevelFlags=RF_Public|RF_Standalone;
    return UPackage::SavePackage(Pkg,Asset,*FPackageName::LongPackageNameToFilename(
        Pkg->GetName(),FPackageName::GetAssetPackageExtension()),Args);
}

template<class T>
T* RegionAsset(const FString& Relative)
{
    const FString Path=TEXT("/Game/ForestPathStudy/VillageRegion/")+Relative;
    UPackage* Package=CreatePackage(*Path);
    Package->FullyLoad();
    const FName Name(*FPackageName::GetShortName(Path));
    if(auto* Existing=FindObject<T>(Package,*Name.ToString()))return Existing;
    return NewObject<T>(Package,Name,RF_Public|RF_Standalone|RF_Transactional);
}

enum class ELayer : uint8 { Trees,Shrubs,Grass,Rocks,Deadwood,Floor,Wetland,Count };
struct FLayerInfo { const TCHAR* Key;const TCHAR* Title;const TCHAR* Note; };
constexpr FLayerInfo Layers[]={
    {TEXT("Trees"),TEXT("乔木树冠"),TEXT("烘焙的鹅耳枥树冠。可采伐黑杨、山毛榉由采伐系统持有。")},
    {TEXT("Shrubs"),TEXT("灌木"),TEXT("林下榛灌木；丘陵主题另加神像旁的九款灌木，沿实际林冠在适生草地上成簇生成。")},
    {TEXT("Grass"),TEXT("草类与草本"),TEXT("中景草与阔叶草本。近草流送及全图草皮使用各自的入口。")},
    {TEXT("Rocks"),TEXT("岩石与碎石"),TEXT("原林地石块、露岩岩架与坡脚堆积碎石。岩架沿岩面嵌入；小碎石沿下坡方向成簇沉积。")},
    {TEXT("Deadwood"),TEXT("枯木与松枝"),TEXT("树枝、倒木、苔木和树桩；沿用贴地支点与原有预算。")},
    {TEXT("Floor"),TEXT("林床装饰"),TEXT("林床组合网格、苔斑及泥土贴花。路肩落叶由地面材质绘制。")},
    {TEXT("Wetland"),TEXT("水坑与岸草"),TEXT("闭合水坑和岸边莎草。远岸莎草由同一岸线另外烘焙。")}
};
static_assert(UE_ARRAY_COUNT(Layers)==static_cast<int32>(ELayer::Count));
constexpr int32 PinsPerPage=24;
static_assert(PinsPerPage<=PCGPinIdHelpers::MaxOutputPins);

ELayer Classify(int32 Slot,const UStaticMesh* Mesh)
{
    // The first 16 slots are the existing binary planting contract, including three Actor spawners.
    static constexpr ELayer Base[]={ELayer::Trees,ELayer::Trees,ELayer::Shrubs,ELayer::Shrubs,
        ELayer::Rocks,ELayer::Rocks,ELayer::Deadwood,ELayer::Deadwood,ELayer::Grass,ELayer::Grass,
        ELayer::Floor,ELayer::Floor,ELayer::Grass,ELayer::Grass,ELayer::Grass,ELayer::Wetland};
    if(Slot<UE_ARRAY_COUNT(Base))return Base[Slot];
    if(!Mesh)return ELayer::Count;
    const FString& Tag=Mesh->GetPackage()->GetMetaData().GetValue(Mesh,TEXT("ForestEcologyLayer"));
    if(!Tag.IsEmpty())
    {
        for(int32 I=0;I<UE_ARRAY_COUNT(Layers);++I)
            if(Tag.Equals(Layers[I].Key,ESearchCase::IgnoreCase))return static_cast<ELayer>(I);
        UE_LOG(LogTemp,Error,TEXT("Invalid ForestEcologyLayer '%s' on %s"),*Tag,*Mesh->GetPathName());
        return ELayer::Count;
    }
    if(ForestWoodDressing::Kind(Mesh)!=ForestWoodDressing::EKind::None)return ELayer::Deadwood;
    if(ForestReferenceBoulders::IsReferenceMesh(Mesh))return ELayer::Rocks;
    if(ForestCourtyardShrubs::LeafOverride(Mesh))return ELayer::Shrubs;
    const FString Path=Mesh->GetOutermost()->GetName();
    if(Path.StartsWith(TEXT("/Game/ForestPathStudy/VillageRegion/Granite/")))return ELayer::Rocks;
    if(Mesh->GetFName()==TEXT("SM_RiverDense_grass_04_03_mesh"))return ELayer::Wetland;
    for(const TCHAR* Rock:{TEXT("/vikrdcnaw/"),TEXT("/vimrfjsaw/"),TEXT("/xiemca1/"),TEXT("/xisffer/"),TEXT("/xjijdiz/"),TEXT("/xjiifd1/")})
        if(Path.Contains(Rock))return ELayer::Rocks;
    if(Path.Contains(TEXT("/rbcuh/"))||Path.Contains(TEXT("/rbpir/")))return ELayer::Grass;
    if(Path.Contains(TEXT("/relu7/"))||Path.Contains(TEXT("/rioqm/")))return ELayer::Deadwood;
    // Includes the reference's Nordic Forest Cluster Medium and untagged general dressing.
    return ELayer::Floor;
}

void ResetGraph(UPCGGraph* Graph)
{
    TArray<UPCGNode*> Nodes;
    for(auto* Node:Graph->GetNodes())Nodes.Add(Node);
    Graph->RemoveNodes(Nodes);
    Graph->RemoveEdge(Graph->GetInputNode(),TEXT("In"),Graph->GetOutputNode(),TEXT("Out"));
}

UPCGNode* AddSpawner(UPCGGraph* Graph,int32 I,FName Pin,UStaticMesh* const* Meshes,UInstancedStaticMeshComponent* const* Templates)
{
    UPCGNode* Node=nullptr;
    if(I==15)
    {
        UPCGSpawnActorSettings* Spawn=nullptr;
        Node=Graph->AddNodeOfType(Spawn);
        Spawn->Option=EPCGSpawnActorOption::NoMerging;
        Spawn->SetTemplateActorClass(AForestVillagePoolSurface::StaticClass());
        Spawn->ActorLabel=TEXT("WoodlandPool");
    }
    else if(I!=10 && I!=11)
    {
        UPCGStaticMeshSpawnerSettings* Spawn=nullptr;
        Node=Graph->AddNodeOfType(Spawn);
        Spawn->SetMeshSelectorType(UPCGMeshSelectorWeighted::StaticClass());
        auto* Selector=CastChecked<UPCGMeshSelectorWeighted>(Spawn->MeshSelectorParameters);
        Selector->MeshEntries.Reset();
        auto& Entry=Selector->MeshEntries.Emplace_GetRef(TSoftObjectPtr<UStaticMesh>(Meshes[I]),1);
        auto& D=Entry.Descriptor;
        D.ComponentClass=UHierarchicalInstancedStaticMeshComponent::StaticClass();
        D.Mobility=EComponentMobility::Static;
        D.InstanceEndCullDistance=I>=16?10000:I>=12?(I==14?7600:6400):I<2?36000:I<4?16000:I<8?6500:5000;
        D.InstanceStartCullDistance=D.InstanceEndCullDistance*3/4;
        if(I<4) D.WorldPositionOffsetDisableDistance=I<2?8000:4000;
        D.bCanEverAffectNavigation=I<2;
        D.bVisibleInRayTracing=I<2;
        if(I>=12)
        {
            if(I<=14) if(auto* Mat=AForestVillageRegion::HillsGrassMaterial(Meshes[I])) D.OverrideMaterials.Add(Mat);
            D.bCastShadow=false; D.bAffectDistanceFieldLighting=false;
            D.bAffectDynamicIndirectLighting=false; D.bEnableDensityScaling=true;
        }
        const auto Wood=I>=16?ForestWoodDressing::Kind(Meshes[I]):ForestWoodDressing::EKind::None;
        if(Wood!=ForestWoodDressing::EKind::None)
        {
            D.InstanceEndCullDistance=ForestWoodDressing::CullEndCm(Wood);
            D.InstanceStartCullDistance=D.InstanceEndCullDistance*3/4;
            D.bCastShadow=Wood==ForestWoodDressing::EKind::Trunk || Wood==ForestWoodDressing::EKind::Large;
        }
        if(ForestReferenceBoulders::IsReferenceMesh(Meshes[I]))
        {
            D.bEnableDensityScaling=false;
            D.bCastShadow=true;
            D.InstanceStartCullDistance=11250;
            D.InstanceEndCullDistance=15000;
        }
        if (Pin==TEXT("TalusFine") || Pin==TEXT("TalusFragment"))
        {
            D.InstanceEndCullDistance=Pin==TEXT("TalusFine")?2800:4200;
            D.InstanceStartCullDistance=D.InstanceEndCullDistance*3/4;
        }
        D.bUseDefaultCollision=false;
        D.BodyInstance.SetCollisionProfileName(I<2?FName(TEXT("BlockAll")):FName(TEXT("NoCollision")));
        if(I<4)
            for(int32 M=0;M<Templates[I]->GetNumMaterials();++M) D.OverrideMaterials.Add(Templates[I]->GetMaterial(M));
        if(const TCHAR* Leaf=ForestCourtyardShrubs::LeafOverride(Meshes[I]))
        {
            const FString Path=FString::Printf(TEXT("/Game/WorldGeneration/TemperateHills/EcologyUpgrade/Materials/%s.%s"),Leaf,Leaf);
            auto* Material=LoadObject<UMaterialInterface>(nullptr,*Path);
            if(!Material){UE_LOG(LogTemp,Error,TEXT("Missing village shrub leaf material %s"),*Path);return nullptr;}
            D.OverrideMaterials.Add(Material);
            D.WorldPositionOffsetDisableDistance=2500;
        }
    }
    else
    {
        UPCGSpawnActorSettings* Spawn=nullptr;
        Node=Graph->AddNodeOfType(Spawn);
        Spawn->Option=EPCGSpawnActorOption::NoMerging;
        Spawn->SetTemplateActorClass(ADecalActor::StaticClass());
        Spawn->SetAllowTemplateActorEditing(true);
        auto* Decal=Cast<ADecalActor>(Spawn->TemplateActor.Get());
        const FString Name=I==10?TEXT("M_EastRoad_MossPatch"):TEXT("M_EastRoad_SoilPatch");
        const FString Path=TEXT("/Game/WorldGeneration/TemperateHills/EastRiverRoad/")+Name+TEXT(".")+Name;
        auto* Mat=LoadObject<UMaterialInterface>(nullptr,*Path);
        if(!Decal || !Mat) return nullptr;
        Decal->GetDecal()->SetDecalMaterial(Mat);
        Decal->GetDecal()->DecalSize=FVector(10.,80.,61.);
        Spawn->ActorLabel=Pin.ToString();
    }
    return Node;
}

FName SlotName(int32 I,UStaticMesh* const* Meshes,int32 FirstTalus)
{
    if(I>=FirstTalus && ForestCourtyardShrubs::LeafOverride(Meshes[I]))return Meshes[I]->GetFName();
    if (I>=FirstTalus) return I==FirstTalus?FName(TEXT("TalusFine")):FName(TEXT("TalusFragment"));
    static const TCHAR* const Fixed[]={TEXT("Hornbeam04"),TEXT("Hornbeam05"),TEXT("Hazel01"),TEXT("Hazel02"),
        TEXT("StoneA"),TEXT("StoneB"),TEXT("BranchA"),TEXT("BranchB"),TEXT("HerbsA"),TEXT("HerbsB"),
        TEXT("MossPatch"),TEXT("ForestSoil"),TEXT("LowGrass"),TEXT("SpreadingGrass"),TEXT("TallGrass"),TEXT("WoodlandPool")};
    return I<UE_ARRAY_COUNT(Fixed)?FName(Fixed[I]):FName(*FString::Printf(TEXT("Ref_%02d_%s"),I,*Meshes[I]->GetName()));
}

void AddPointSet(UPCGDataAsset* Page,FName Pin,const TArray<FTransform>& Group)
{
    auto* Data=NewObject<UPCGPointArrayData>(Page);
    Data->SetNumPoints(Group.Num(),false);
    Data->GetBoundsMinValueRange(false).Set(FVector(-25.));
    Data->GetBoundsMaxValueRange(false).Set(FVector(25.));
    auto Poses=Data->GetTransformValueRange();
    auto Seeds=Data->GetSeedValueRange();
    for(int32 J=0;J<Group.Num();++J)
    {
        Poses[J]=Group[J];
        Seeds[J]=int32(GetTypeHash(Group[J].GetLocation()));
    }
    auto& Tagged=Page->Data.TaggedData.Emplace_GetRef();
    Tagged.Pin=Pin;Tagged.Data=Data;
}

UPCGGraph* BakeLayer(bool Road,const FLayerInfo& Info,const TArray<int32>& Slots,const TArray<TArray<FTransform>>& Transforms,
                     UStaticMesh* const* Meshes,UInstancedStaticMeshComponent* const* Templates,int32 FirstTalus)
{
    const FString Folder=Road?TEXT("Themes/Road/"):TEXT("Themes/Hills/");
    const FString DataStem=(Road?FString(TEXT("Themes/Road/DA_Road")):FString(TEXT("Ecology/DA_Forest")))+Info.Key;
    auto* Graph=RegionAsset<UPCGGraph>(Folder+TEXT("PCG_")+Info.Key);
    const FString PagePrefix=FString(TEXT("/Game/ForestPathStudy/VillageRegion/"))+DataStem+TEXT("_");
    TSet<TSoftObjectPtr<UPCGDataAsset>> Superseded;
    for(const auto* Existing:Graph->GetNodes())
        if(const auto* Load=Cast<UPCGLoadDataAssetSettings>(Existing->GetSettings()))
        {
            const FString Path=Load->Asset.ToSoftObjectPath().GetLongPackageName();
            if(Path.StartsWith(PagePrefix)&&Path.RightChop(PagePrefix.Len()).IsNumeric())
                Superseded.Add(Load->Asset);
        }
    ResetGraph(Graph);
    UPCGGatherSettings* Gather=nullptr;
    auto* Join=Graph->AddNodeOfType(Gather);
    Join->SetNodeTitle(TEXT("汇集本层输出"));Join->NodeComment=TEXT("传递数据引用；最终点合并在主图执行。");
    const int32 PageCount=FMath::DivideAndRoundUp(Slots.Num(),PinsPerPage);
    Join->SetNodePosition(PageCount*950+150,0);
    Graph->GetOutputNode()->SetNodePosition(PageCount*950+570,0);
    if(!Graph->AddEdge(Join,TEXT("Out"),Graph->GetOutputNode(),TEXT("Out")))return nullptr;
    for(int32 PageId=0;PageId<PageCount;++PageId)
    {
        const int32 First=PageId*PinsPerPage,End=FMath::Min(First+PinsPerPage,Slots.Num());
        auto* Page=RegionAsset<UPCGDataAsset>(DataStem+FString::Printf(TEXT("_%02d"),PageId+1));
        Superseded.Remove(TSoftObjectPtr<UPCGDataAsset>(Page));
        Page->Data.TaggedData.Reset();
        for(int32 J=First;J<End;++J)
        {
            const int32 Slot=Slots[J];
            AddPointSet(Page,SlotName(Slot,Meshes,FirstTalus),Transforms[Slot]);
        }
        if(!SaveAsset(Page))return nullptr;
        UPCGLoadDataAssetSettings* Load=nullptr;
        auto* Source=Graph->AddNodeOfType(Load);
        Load->SetFromAsset(FAssetData(Page));
        Source->SetNodeTitle(FName(*FString::Printf(TEXT("%s 点集 %02d"),Info.Title,PageId+1)));
        Source->NodeComment=FString::Printf(TEXT("%d 路有效变体，每页最多 %d 路。"),End-First,PinsPerPage);
        Source->SetNodePosition(PageId*950,250);
        for(int32 J=First;J<End;++J)
        {
            const int32 Slot=Slots[J];const FName Pin=SlotName(Slot,Meshes,FirstTalus);
            auto* Spawner=AddSpawner(Graph,Slot,Pin,Meshes,Templates);
            if(!Spawner)return nullptr;
            Spawner->SetNodeTitle(Pin);
            if (Pin==TEXT("TalusFine") || Pin==TEXT("TalusFragment"))
            {
                Spawner->NodeComment=Pin==TEXT("TalusFine")?TEXT("坡脚细碎石；近景 28 米剔除。"):TEXT("坡脚断片；近景 42 米剔除。");
                Spawner->bCommentBubbleVisible=true;
            }
            Spawner->SetNodePosition(PageId*950+420,(J-First)*150+260);
            if(!Graph->AddEdge(Source,Pin,Spawner,TEXT("In"))||!Graph->AddEdge(Spawner,TEXT("Out"),Join,TEXT("In")))return nullptr;
        }
    }
    // A saved combination may still reference this child after its last site disappears.
    // Keep that asset current and release any point payload left over from a larger bake.
    for(const auto& Ref:Superseded)
        if(auto* OldPage=Ref.LoadSynchronous())
        {
            OldPage->Data.TaggedData.Reset();
            if(!SaveAsset(OldPage))return nullptr;
        }
    return SaveAsset(Graph)?Graph:nullptr;
}
bool LinkChild(UPCGGraph* Parent,UPCGGraph* Child,UPCGNode* Join,int32 Row,const TCHAR* Title,const TCHAR* Note)
{
    UPCGSubgraphSettings* Settings=nullptr;
    auto* N=Parent->AddNodeOfType(Settings);Settings->SetSubgraph(Child);
    N->SetNodeTitle(Title);N->NodeComment=Note;N->bCommentBubbleVisible=true;N->SetNodePosition(150,Row*235);
    return Parent->AddEdge(Parent->GetInputNode(),TEXT("In"),N,TEXT("In")) &&
           Parent->AddEdge(N,TEXT("Out"),Join,TEXT("In"));
}

// A theme owns its own component. The R30 ecological combinations reference the same child graphs.
UPCGNode* StartComposition(UPCGGraph* Graph,bool MergePoints)
{
    ResetGraph(Graph);
    UPCGNode* Join=nullptr;
    if(MergePoints){UPCGMergeSettings* S=nullptr;Join=Graph->AddNodeOfType(S);}
    else {UPCGGatherSettings* S=nullptr;Join=Graph->AddNodeOfType(S);}
    Join->SetNodePosition(900,500);Graph->GetInputNode()->SetNodePosition(-450,500);
    Graph->GetOutputNode()->SetNodePosition(1300,500);
    return Graph->AddEdge(Join,TEXT("Out"),Graph->GetOutputNode(),TEXT("Out"))?Join:nullptr;
}

bool GenerateTheme(AForestVillageRegion& Owner,UPCGComponent*& Component,FName Name,UPCGGraph* Graph)
{
    if(!Component)
    {
        Component=NewObject<UPCGComponent>(&Owner,Name,RF_Transactional);
        Owner.AddInstanceComponent(Component);
        Component->GenerationTrigger=EPCGComponentGenerationTrigger::GenerateOnDemand;
        Component->RegisterComponent();
    }
    Component->SetIsPartitioned(false);
    Component->SetEditingMode(EPCGEditorDirtyMode::Normal,EPCGEditorDirtyMode::Normal);
    Component->SetGraph(Graph);
    UWorld* World=Owner.GetWorld();
    FWorldPartitionHelpers::FakeEngineTick(World);
    if(Component->GenerateLocalGetTaskId(true)==InvalidPCGTaskId)return false;
    const double End=FPlatformTime::Seconds()+300.;
    while(Component->IsGenerating() && FPlatformTime::Seconds()<End)
    {FWorldPartitionHelpers::FakeEngineTick(World);FPlatformProcess::Sleep(.005f);}
    return !Component->IsGenerating();
}
}

bool BakeForestRegionPCG(AForestVillageRegion& Owner,const TArray<TArray<FTransform>>& Hills,
    const TArray<TArray<FTransform>>& Road,FName OnlyTheme,UStaticMesh* const* Meshes,UInstancedStaticMeshComponent* const* Templates,int32 FirstTalus)
{
    const FName ComponentNames[]={TEXT("SurroundingForestPCG"),TEXT("RoadLandscapePCG")};
    UPCGComponent* Components[]={FindObject<UPCGComponent>(&Owner,*ComponentNames[0].ToString()),
        FindObject<UPCGComponent>(&Owner,*ComponentNames[1].ToString())};
    if(!Components[0])
        for(auto* Existing:TInlineComponentArray<UPCGComponent*>(&Owner))
            if(auto* Graph=Existing->GetGraph();Graph && (Graph->GetName()==TEXT("PCG_ForestVillageSurroundings") || Graph->GetName()==TEXT("PCG_HillsLandscape")))
            {Components[0]=Existing;break;}
    if(!OnlyTheme.IsNone() && (!Components[0] || !Components[1]))return false;
    const bool Requested[]={OnlyTheme.IsNone()||OnlyTheme==TEXT("HillsLandscape"),OnlyTheme.IsNone()||OnlyTheme==TEXT("RoadLandscape")};
    for(int32 T=0;T<2;++T)if(Requested[T] && Components[T])Components[T]->CleanupLocalImmediate(true);
    auto InstanceCount=[&Owner]()
    {
        int32 N=0;for(auto* Inst:TInlineComponentArray<UInstancedStaticMeshComponent*>(&Owner))N+=Inst->GetInstanceCount();
        return N;
    };
    auto PoolCount=[&Owner]()
    {
        int32 N=0;for(TActorIterator<AForestVillagePoolSurface> It(Owner.GetWorld());It;++It)if(It->GetLevel()==Owner.GetLevel())++N;
        return N;
    };
    int32 Expected=OnlyTheme.IsNone()?0:InstanceCount();
    int32 ExpectedPools=OnlyTheme.IsNone()?0:PoolCount();
    UPCGGraph* Children[2][UE_ARRAY_COUNT(Layers)]={};
    for(int32 T=0;T<2;++T)
    {
        if(!Requested[T])continue;
        const auto& Transforms=T?Road:Hills;
        TArray<int32> Members[UE_ARRAY_COUNT(Layers)];
        for(int32 I=0;I<Transforms.Num();++I)
        {
            if(Transforms[I].IsEmpty())continue;
            const ELayer Layer=Classify(I,I==15?nullptr:Meshes[I]);
            if(Layer==ELayer::Count)return false;
            Members[static_cast<int32>(Layer)].Add(I);
            if(I==15)ExpectedPools+=Transforms[I].Num();
            else if(I!=10 && I!=11)Expected+=Transforms[I].Num();
        }
        auto* Theme=RegionAsset<UPCGGraph>(T?TEXT("Themes/PCG_RoadLandscape"):TEXT("Themes/PCG_HillsLandscape"));
        auto* Join=StartComposition(Theme,true);if(!Join)return false;
        Join->SetNodeTitle(T?TEXT("道路景观"):TEXT("丘陵景观"));
        Join->NodeComment=T?TEXT("东门至河岸和采石场的道路、路肩布景。构建入口：道路景观。"):
            TEXT("丘陵林地、湿地与地形布景。构建入口：丘陵景观。");
        Join->bCommentBubbleVisible=true;
        for(int32 I=0;I<UE_ARRAY_COUNT(Layers);++I)
        {
            if(T==1 && I==static_cast<int32>(ELayer::Wetland))continue;
            auto* Child=BakeLayer(T==1,Layers[I],Members[I],Transforms,Meshes,Templates,FirstTalus);
            Children[T][I]=Child;
            if(!Child || (!Members[I].IsEmpty() && !LinkChild(Theme,Child,Join,I,Layers[I].Title,Layers[I].Note)))return false;
        }
        if(!SaveAsset(Theme) || !GenerateTheme(Owner,Components[T],ComponentNames[T],Theme))return false;
    }
    if(OnlyTheme.IsNone())
    {
        auto* Master=RegionAsset<UPCGGraph>(TEXT("PCG_ForestVillageSurroundings"));
        auto* Merge=StartComposition(Master,true);if(!Merge)return false;
        for(int32 I=0;I<UE_ARRAY_COUNT(Layers);++I)
        {
            auto* Layer=RegionAsset<UPCGGraph>(FString(TEXT("Ecology/PCG_Forest"))+Layers[I].Key);
            auto* Gather=StartComposition(Layer,false);if(!Gather)return false;
            if(!LinkChild(Layer,Children[0][I],Gather,0,TEXT("丘陵景观"),Layers[I].Note))return false;
            if(Children[1][I] && !LinkChild(Layer,Children[1][I],Gather,1,TEXT("道路景观"),Layers[I].Note))return false;
            if(!SaveAsset(Layer)||!LinkChild(Master,Layer,Merge,I,Layers[I].Title,Layers[I].Note))return false;
        }
        if(!SaveAsset(Master))return false;
    }
    const int32 Placed=InstanceCount(),Pools=PoolCount();
    UE_LOG(LogTemp,Display,TEXT("FOREST_THEMES %s meshes %d/%d; pools %d/%d"),*OnlyTheme.ToString(),Placed,Expected,Pools,ExpectedPools);
    return Placed==Expected && Pools==ExpectedPools;
}
#endif
