#include "ForestVillageGrassCover.h"
#include "ForestVillageMap.h"
#include "ForestVillageMistComponent.h"
#include "ForestVillageRegion.h"
#include "TemperateHillsWorld.h"
#include "EngineUtils.h"
#include "Algo/AllOf.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/BoxComponent.h"
#include "Components/HierarchicalInstancedStaticMeshComponent.h"
#include "Data/PCGBasePointData.h"
#include "Engine/StaticMesh.h"
#include "Engine/LevelStreamingDynamic.h"
#include "GameFramework/Pawn.h"
#include "Materials/MaterialInterface.h"
#include "GameFramework/PlayerController.h"
#include "PCGComponent.h"
#include "PCGContext.h"
#include "PCGElement.h"
#include "PCGGraph.h"
#include "TimerManager.h"
#if WITH_EDITOR
#include "AssetRegistry/AssetRegistryModule.h"
#include "Editor.h"
#include "LevelEditorViewport.h"
#include "Elements/PCGMergeElement.h"
#include "Elements/PCGStaticMeshSpawner.h"
#include "MeshSelectors/PCGMeshSelectorWeighted.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"
#include "PCGNode.h"
#include "UObject/SavePackage.h"
#endif

namespace
{
// The authoring tool writes a byte per lattice site in cell-major order.
constexpr int32 Tiles = 64, Cols = 40, Rows = 46, PerTile = Cols*Rows;
constexpr double CellCm = 1600.;
const FName Forms[] = {TEXT("Low"), TEXT("Spreading"), TEXT("Tall")};
const FVector2D GrassCoverWorldOrigin(ForestVillageMap::West*100.,ForestVillageMap::South*100.);

uint32 SiteHash(uint32 Index)
{
    uint32 H = (Index+237855u)*0x9e3779b1u;
    H ^= H>>16; H *= 0x85ebca6bu; H ^= H>>13;
    return H;
}

class FNearGrassElement final : public IPCGElement
{
    virtual bool IsCacheable(const UPCGSettings*) const override { return false; }
    virtual bool CanExecuteOnlyOnMainThread(FPCGContext*) const override { return true; }
    virtual bool ExecuteInternal(FPCGContext* Context) const override
    {
        auto* Cell = Cast<AForestGrassCell>(Context->GetTargetActor(nullptr));
        auto* Region = IsValid(Cell) ? Cast<AForestVillageRegion>(Cell->GetOwner()) : nullptr;
        if (!IsValid(Region)) return true;
        Region->BuildNearGrassPoints(Cell->Cell,*Context);
        return true;
    }
};
}

AForestGrassCell::AForestGrassCell()
{
    auto* Bounds = CreateDefaultSubobject<UBoxComponent>(TEXT("GrassCellBounds"));
    Bounds->SetBoxExtent(FVector(CellCm*.5,CellCm*.5,5000.));
    Bounds->SetMobility(EComponentMobility::Static);
    Bounds->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Bounds->SetGenerateOverlapEvents(false);
    Bounds->SetCanEverAffectNavigation(false);
    SetRootComponent(Bounds);
    PCG = CreateDefaultSubobject<UPCGComponent>(TEXT("NearbyGrassPCG"));
    PCG->GenerationTrigger = EPCGComponentGenerationTrigger::GenerateOnDemand;
    PCG->SetIsPartitioned(false);
}

TArray<FPCGPinProperties> UForestGrassSitesSettings::OutputPinProperties() const
{
    TArray<FPCGPinProperties> Pins;
    for (FName Name : Forms) Pins.Emplace(Name,EPCGDataType::Point);
    return Pins;
}

FPCGElementPtr UForestGrassSitesSettings::CreateElement() const
{
    return MakeShared<FNearGrassElement>();
}

void AForestVillageRegion::BuildNearGrassPoints(FIntPoint Cell,FPCGContext& Context) const
{
    if (GrassRestZ.Num()!=3 || Cell.X<0 || Cell.X>=Tiles || Cell.Y<0 || Cell.Y>=Tiles ||
        NearGrassMask.Num()!=Tiles*Tiles*PerTile) return;
    const int32 Start = (Cell.Y*Tiles+Cell.X)*PerTile;
    int32 Counts[4]={};
    for (int32 I=Start;I<Start+PerTile;++I) ++Counts[NearGrassMask[I]&3];

    FPCGPointTransform::ValueRange Transforms[3];
    FPCGPointSeed::ValueRange Seeds[3];
    int32 Next[3]={};
    for (int32 Form=0;Form<3;++Form)
    {
        if (!Counts[Form+1]) continue;
        auto* Data=FPCGContext::NewPointData_AnyThread(&Context);
        Data->SetNumPoints(Counts[Form+1],true);
        Data->AllocateProperties(EPCGPointNativeProperties::Transform | EPCGPointNativeProperties::Seed);
        Transforms[Form]=Data->GetTransformValueRange(false);
        Seeds[Form]=Data->GetSeedValueRange(false);
        auto& Out=Context.OutputData.TaggedData.Emplace_GetRef();
        Out.Pin=Forms[Form];
        Out.Data=Data;
    }
    // The foundation is built by the settlement. Use its actual triangles for grass in the wall collar.
    const FVector2D CellMin=GrassCoverWorldOrigin+FVector2D(Cell.X,Cell.Y)*CellCm;
    const FVector2D SiteMin=FVector2D(GetSettlementMinM())*100.;
    const FBox2D Site(SiteMin,SiteMin+FVector2D(11800.,14500.));
    const auto* Settlement=Site.Intersect(FBox2D(CellMin-FVector2D(35.),CellMin+FVector2D(CellCm+35.)))
        ? GrassSettlement.Get() : nullptr;
    const auto GrassHeight=[this,Settlement,&Site](double X,double Y)
    {
        return Settlement && Site.IsInsideOrOn(FVector2D(X,Y)) ? Settlement->Height(X,Y) : GroundHeight(X,Y);
    };
    for (int32 Row=0; Row<Rows; ++Row)
        for (int32 Col=0; Col<Cols; ++Col)
        {
            const int32 Index = Start+Row*Cols+Col;
            const uint8 Value = NearGrassMask[Index];
            if (!Value) continue;
            const int32 Form = (Value&3)-1;
            const uint32 H = SiteHash(Index);
            const double Jx = (double(H&255)/255.-.5)*.20;
            const double Jy = (double((H>>8)&255)/255.-.5)*.20;
            const double X = GrassCoverWorldOrigin.X+Cell.X*CellCm+(Col+.25+.5*(Row&1)+Jx)*CellCm/Cols;
            const double Y = GrassCoverWorldOrigin.Y+Cell.Y*CellCm+(Row+.5+Jy)*CellCm/Rows;
            const FVector Normal(GrassHeight(X-35,Y)-GrassHeight(X+35,Y),GrassHeight(X,Y-35)-GrassHeight(X,Y+35),70.);
            const FVector Up = FMath::Lerp(FVector::UpVector,Normal.GetSafeNormal(),.68).GetSafeNormal();
            const double Scale = (Value>>2)/GrassRestZ[Form].Y;
            const FVector Root(X,Y,GrassHeight(X,Y)-1.0);
            const FQuat Rot = FQuat(Up,double(H>>16)*(2.0*PI/65536.))*FQuat::FindBetweenNormals(FVector::UpVector,Up);
            const int32 Dest=Next[Form]++;
            Transforms[Form][Dest]=FTransform(Rot,Root-Up*GrassRestZ[Form].X*Scale,FVector(Scale));
            Seeds[Form][Dest]=int32(H);
        }
}

void AForestVillageRegion::BeginPlay()
{
    Super::BeginPlay();
#if WITH_EDITOR
    SetActorTickEnabled(false); // Game worlds use the same camera timer in PIE and in cooked builds.
#endif
    if(GetNetMode()!=NM_DedicatedServer && HasGround() && ForestVillageMap::Is(GetWorld()))
        NewObject<UForestVillageMistComponent>(this,NAME_None,RF_Transient)->RegisterComponent();
    if (!QuarryLevel.IsNull())
        GetWorldTimerManager().SetTimer(QuarryTimer,this,&AForestVillageRegion::UpdateQuarryStreaming,.5f,true,.01f);
    if (GetNetMode()!=NM_DedicatedServer && NearGrassGraph && HasGround() && OccupiedGrassTiles.Num()==Tiles*Tiles)
        GetWorldTimerManager().SetTimer(GrassTimer,this,&AForestVillageRegion::UpdateGrassCells,.075f,true,.01f);
}

void AForestVillageRegion::EndPlay(const EEndPlayReason::Type Reason)
{
    GetWorldTimerManager().ClearTimer(QuarryTimer);
    if(QuarryStreaming) QuarryStreaming->SetIsRequestingUnloadAndRemoval(true);
    GetWorldTimerManager().ClearTimer(GrassTimer);
    ReleaseGrassCells();
    Super::EndPlay(Reason);
}

void AForestVillageRegion::UpdateQuarryStreaming()
{
    const double Radius=QuarryStreaming && QuarryStreaming->ShouldBeLoaded()?39000.:35000.;
    bool Needed=false;
    for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)
    {
        const auto* PC=It->Get();
        if(!PC) continue;
        if(const APawn* Pawn=PC->GetPawn())
            Needed|=FVector::DistSquared2D(Pawn->GetActorLocation(),QuarryOrigin)<=FMath::Square(Radius);
        if(PC->IsLocalController() && PC->PlayerCameraManager)
            Needed|=FVector::DistSquared2D(PC->PlayerCameraManager->GetCameraLocation(),QuarryOrigin)<=FMath::Square(Radius);
    }
    if(QuarryStreaming)
    {
        QuarryStreaming->SetShouldBeLoaded(Needed);
        QuarryStreaming->SetShouldBeVisible(Needed);
    }
    else if(Needed)
    {
        bool Success=false;
        QuarryStreaming=ULevelStreamingDynamic::LoadLevelInstanceBySoftObjectPtr(this,QuarryLevel,QuarryOrigin,
            FRotator(0.,90.,0.),Success,TEXT("ForestVillageWhiteCliffs"));
    }
}

void AForestVillageRegion::ReleaseGrassCells()
{
    for (auto& Pair : GrassCells)
        if (auto* Cell=Pair.Value.Get()) Cell->Destroy();
    GrassCells.Reset();
    SettledGrassViews.Reset();
}

#if WITH_EDITOR
bool AForestVillageRegion::ShouldTickIfViewportsOnly() const
{
    return !IsRunningCommandlet() && NearGrassGraph && GetWorld() && GetWorld()->WorldType==EWorldType::Editor;
}

void AForestVillageRegion::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (ShouldTickIfViewportsOnly()) UpdateGrassCells();
}

void AForestVillageRegion::Destroyed()
{
    ReleaseGrassCells();
    Super::Destroyed();
}
#endif

void AForestVillageRegion::UpdateGrassCells()
{
    if (!NearGrassGraph || OccupiedGrassTiles.Num()!=Tiles*Tiles || !HasGround()) return;
    // The village surface is installed during streaming. Cells generated against the temporary
    // foundation would keep those first transforms until the camera left the area.
    if (GetWorld()->IsGameWorld() && VillageLoessDetail && ForestVillageMap::Is(GetWorld()))
    {
        if (!GrassSettlement.IsValid())
            for (TActorIterator<ATemperateHillsWorld> It(GetWorld());It;++It)
                if (It->IsForestVillage()) { GrassSettlement=*It; break; }
        if (!GrassSettlement.IsValid() || !GrassSettlement->bReady) return;
    }
    // Use local camera positions, including split screen. Distant network players do not cost local grass.
    TArray<FVector2D,TInlineAllocator<2>> Views;
#if WITH_EDITOR
    if (GetWorld()->WorldType==EWorldType::Editor)
    {
        if (GEditor && !GEditor->PlayWorld && GCurrentLevelEditingViewportClient &&
            GCurrentLevelEditingViewportClient->IsPerspective() && GCurrentLevelEditingViewportClient->GetWorld()==GetWorld())
            Views.Emplace(GCurrentLevelEditingViewportClient->GetViewLocation());
    }
    else
#endif
    {
        for (auto It=GetWorld()->GetPlayerControllerIterator(); It; ++It)
            if (auto* PC=It->Get(); PC && PC->IsLocalController() && PC->PlayerCameraManager)
                Views.Emplace(PC->PlayerCameraManager->GetCameraLocation());
    }

    // Revisit a stationary camera if an editor action or world teardown removed a patch.
    if (!Views.IsEmpty() && Views==SettledGrassViews &&
        Algo::AllOf(GrassCells,[](const auto& Pair){ return Pair.Value.IsValid(); })) return;
    SettledGrassViews.Reset();

    auto DistanceSq = [](FIntPoint Key,const FVector2D& View)
    {
        const FVector2D Low = GrassCoverWorldOrigin+FVector2D(Key.X,Key.Y)*CellCm;
        const FVector2D Closest(FMath::Clamp(View.X,Low.X,Low.X+CellCm),FMath::Clamp(View.Y,Low.Y,Low.Y+CellCm));
        return FVector2D::DistSquared(Closest,View);
    };
    int32 InFlight=0;
    for (auto It=GrassCells.CreateIterator(); It; ++It)
    {
        auto* Cell=It.Value().Get();
        if (!Cell || !Views.ContainsByPredicate([&](const FVector2D& V){return DistanceSq(It.Key(),V)<FMath::Square(5200.);}))
        {
            if (Cell) Cell->Destroy();
            It.RemoveCurrent();
        }
        else if (Cell->PCG->IsGenerating()) ++InFlight;
    }
    if (InFlight>=3) return;
    FIntPoint Best(-1,-1);
    double BestDist=FMath::Square(4000.);
    for (const auto& View : Views)
    {
        const int32 CX=FMath::FloorToInt((View.X-GrassCoverWorldOrigin.X)/CellCm), CY=FMath::FloorToInt((View.Y-GrassCoverWorldOrigin.Y)/CellCm);
        for (int32 Y=FMath::Max(0,CY-3);Y<=FMath::Min(Tiles-1,CY+3);++Y)
            for (int32 X=FMath::Max(0,CX-3);X<=FMath::Min(Tiles-1,CX+3);++X)
            {
                const FIntPoint Key(X,Y);
                if (!OccupiedGrassTiles[Y*Tiles+X] || GrassCells.Contains(Key)) continue;
                const double D=DistanceSq(Key,View);
                if (D<BestDist) { BestDist=D; Best=Key; }
            }
    }
    if (Best.X<0)
    {
        if (!InFlight) SettledGrassViews=Views;
        return;
    }
    const FVector2D Center=GrassCoverWorldOrigin+FVector2D(Best.X+.5,Best.Y+.5)*CellCm;
    FActorSpawnParameters P;
    P.Owner=this; P.OverrideLevel=GetLevel(); P.ObjectFlags=RF_Transient|RF_DuplicateTransient|RF_TextExportTransient;
#if WITH_EDITOR
    P.bHideFromSceneOutliner=true;
    P.bTemporaryEditorActor=GetWorld()->WorldType==EWorldType::Editor;
    P.bCreateActorPackage=false;
#endif
    P.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    auto* Cell=GetWorld()->SpawnActor<AForestGrassCell>(AForestGrassCell::StaticClass(),
        FVector(Center.X,Center.Y,GroundHeight(Center.X,Center.Y)),FRotator::ZeroRotator,P);
    if (!Cell) return;
    Cell->Cell=Best;
    Cell->PCG->SetGraph(NearGrassGraph);
    if (Cell->PCG->GenerateLocalGetTaskId(true)==InvalidPCGTaskId) { Cell->Destroy(); return; }
    GrassCells.Add(Best,Cell);
}

bool AForestVillageRegion::InstallGrassCover(const FString& MaskFile, bool bMaskOnly)
{
#if WITH_EDITOR
    TArray<uint8> Mask;
    if (!FFileHelper::LoadFileToArray(Mask,*MaskFile) || Mask.Num()!=Tiles*Tiles*PerTile) return false;
    TArray<uint8> Occupied;
    Occupied.Init(0,Tiles*Tiles);
    for (int32 I=0;I<Mask.Num();++I)
    {
        if (!Mask[I]) continue;
        if ((Mask[I]&3)==0 || (Mask[I]>>2)==0) return false;
        Occupied[I/PerTile]=1;
    }
    if (bMaskOnly)
    {
        if (!NearGrassGraph || GrassRestZ.Num()!=3) return false;
        ReleaseGrassCells();
        Modify();
        NearGrassMask=MoveTemp(Mask);
        OccupiedGrassTiles=MoveTemp(Occupied);
        MarkPackageDirty();
        return true;
    }
    const FString Path=TEXT("/Game/ForestPathStudy/VillageRegion/GrassCover/PCG_ForestGrassNear");
    auto* Package=CreatePackage(*Path); Package->FullyLoad();
    auto* Graph=FindObject<UPCGGraph>(Package,TEXT("PCG_ForestGrassNear"));
    if (!Graph)
    {
        Graph=NewObject<UPCGGraph>(Package,TEXT("PCG_ForestGrassNear"),RF_Public|RF_Standalone|RF_Transactional);
        FAssetRegistryModule::AssetCreated(Graph);
    }
    TArray<UPCGNode*> Old;
    for (auto* N : Graph->GetNodes()) Old.Add(N);
    Graph->RemoveNodes(Old);
    Graph->RemoveEdge(Graph->GetInputNode(),TEXT("In"),Graph->GetOutputNode(),TEXT("Out"));
    UForestGrassSitesSettings* SourceSettings=nullptr;
    auto* Source=Graph->AddNodeOfType(SourceSettings);
    UPCGMergeSettings* MergeSettings=nullptr;
    auto* Merge=Graph->AddNodeOfType(MergeSettings);
    Merge->SetNodePosition(720,120); Graph->GetOutputNode()->SetNodePosition(990,120);
    if (!Graph->AddEdge(Merge,TEXT("Out"),Graph->GetOutputNode(),TEXT("Out"))) return false;
    TArray<FVector2f> Rest;
    for (int32 I=0;I<3;++I)
    {
        const FString Name=TEXT("SM_RainforestGrass")+Forms[I].ToString();
        const FString MeshPath=TEXT("/Game/WorldGeneration/TemperateHills/WetForest/CarpetGrass/")+Name+TEXT(".")+Name;
        auto* Mesh=LoadObject<UStaticMesh>(nullptr,*MeshPath);
        if (!Mesh) return false;
        const auto Box=Mesh->GetBoundingBox();
        const float Low=Box.Min.Z+Mesh->GetNegativeBoundsExtension().Z;
        Rest.Emplace(Low,FMath::Max(1.f,float(Box.Max.Z-Mesh->GetPositiveBoundsExtension().Z-Low)));
        UPCGStaticMeshSpawnerSettings* Spawn=nullptr;
        auto* Node=Graph->AddNodeOfType(Spawn);
        Spawn->SetMeshSelectorType(UPCGMeshSelectorWeighted::StaticClass());
        auto* Selector=CastChecked<UPCGMeshSelectorWeighted>(Spawn->MeshSelectorParameters);
        Selector->MeshEntries.Reset();
        auto& D=Selector->MeshEntries.Emplace_GetRef(TSoftObjectPtr<UStaticMesh>(Mesh),1).Descriptor;
        D.ComponentClass=UHierarchicalInstancedStaticMeshComponent::StaticClass();
        D.Mobility=EComponentMobility::Static;
        D.InstanceStartCullDistance=I==2?2450:2150; D.InstanceEndCullDistance=I==2?3300:2950;
        if(auto* Mat=HillsGrassMaterial(Mesh)) D.OverrideMaterials.Add(Mat);
        D.bUseDefaultCollision=false; D.BodyInstance.SetCollisionProfileName(TEXT("NoCollision"));
        D.bCanEverAffectNavigation=false; D.bCastShadow=false; D.bVisibleInRayTracing=false;
        D.bAffectDistanceFieldLighting=false; D.bAffectDynamicIndirectLighting=false; D.bEnableDensityScaling=true;
        Node->SetNodePosition(320,I*160); Node->SetNodeTitle(Forms[I]);
        if (!Graph->AddEdge(Source,Forms[I],Node,TEXT("In")) || !Graph->AddEdge(Node,TEXT("Out"),Merge,TEXT("In"))) return false;
    }
    Package->MarkPackageDirty();
    FSavePackageArgs Save; Save.TopLevelFlags=RF_Standalone|RF_Public;
    if (!UPackage::SavePackage(Package,Graph,*FPackageName::LongPackageNameToFilename(Path,FPackageName::GetAssetPackageExtension()),Save)) return false;
    ReleaseGrassCells();
    Modify(); NearGrassGraph=Graph; GrassRestZ=MoveTemp(Rest); NearGrassMask=MoveTemp(Mask);
    OccupiedGrassTiles=MoveTemp(Occupied);
    MarkPackageDirty();
    return true;
#else
    return false;
#endif
}
