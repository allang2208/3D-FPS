#include "TemperateHillsWorld.h"
#include "HillsFixedTerrainCells.h"
#include "HillsNightRaidSubsystem.h"
#include "VT/RuntimeVirtualTexture.h"
#include "TemperateHillsChapel.h"
#include "TemperateHillsPCG.h"
#include "TemperateHillsVisibility.h"
#include "TemperateHillsSurface.h"
#include "TemperateForestHabitat.h"
#include "../FPSWeatherManager.h"
#include "../Production/ProductionOreRocks.h"
#include "TemperateHillsBackdrop.h"
#include "TemperateHillsGroundLayers.h"
#include "RiverPilotFXSubsystem.h"
#include "NiagaraSystem.h"
#include "../UI/TransitLoadingSubsystem.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Async/Async.h"
#include "Algo/AllOf.h"
#include "Components/DynamicMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/InstancedSkinnedMeshComponent.h"
#include "Animation/TransformProviderData.h"
#include "Components/CapsuleComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include "Engine/AssetManager.h"
#include "Engine/GameInstance.h"
#include "Engine/StreamableManager.h"
#include "Engine/LevelStreamingDynamic.h"
#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/Texture2D.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "MaterialShared.h"
#include "RHIGlobals.h"
#include "HAL/IConsoleManager.h"
#include "PCGGraph.h"
#include "PCGComponent.h"
#include "PCGWorldActor.h"
#include "RuntimeGen/PCGGenSourceManager.h"
#include "PCGGraphExecutionStateInterface.h"
#include "Subsystems/PCGSubsystem.h"
#include "ContentStreaming.h"
#include "RenderCommandFence.h"
#include "Misc/ScopeExit.h"

#include "TemperateHillsStreamingPrivate.h"
namespace HillsStreaming
{
void SetCellMesh(UDynamicMeshComponent* Component,UE::Geometry::FDynamicMesh3&& Mesh,
    TConstArrayView<TObjectPtr<UPCGComponent>> VegetationLayers)
{
    TRACE_CPUPROFILER_EVENT_SCOPE(HillsSubmitTerrainMesh);
#if WITH_EDITOR
    // SetMesh broadcasts OnObjectPropertyChanged even in PIE. PCG tracks our
    // owning hills actor, so submitting a streamed ground/water mesh otherwise
    // dirties ALL vegetation layers, cancels their jobs and removes live cells.
    // These meshes are presentation of Height()/TerrainEdits, not PCG inputs.
    // Ignore only this component during the synchronous notification; preserve
    // normal mesh notifications, explicit edits and the distance scheduler.
    for(const auto& Layer:VegetationLayers)
        Layer->StartIgnoringChangeOriginDuringGeneration(Component);
    ON_SCOPE_EXIT
    {
        for(const auto& Layer:VegetationLayers)
            Layer->StopIgnoringChangeOriginDuringGeneration(Component);
    };
#endif
    Component->SetMesh(MoveTemp(Mesh));
}

double CellDistanceSquared(const FVector& Point,const FVector& Origin)
{
    const double DX=FMath::Max(0.,FMath::Abs(Point.X-Origin.X-CellSize*.5)-CellSize*.5);
    const double DY=FMath::Max(0.,FMath::Abs(Point.Y-Origin.Y-CellSize*.5)-CellSize*.5);
    return DX*DX+DY*DY;
}
// Edited cells are meshed at this multiple of the normal quad count. 1 disables the
// refinement (cheaper, faceted); 2 is the shipped default.
static TAutoConsoleVariable<int32> EditMeshBoost(
    TEXT("fps.Hills.EditMeshBoost"), 2,
    TEXT("Extra mesh resolution for cells touched by a crater or shovel edit (1..4)."));
static TSharedPtr<FMeshResult,ESPMode::ThreadSafe> GenerateCellGeometry(FIntPoint Key,bool Detailed,double Half,int32 Seed,TemperateRiver::FPlanPtr River,const TArray<TemperateHillsSurface::FTerrainEdit>& Edits,int32 Version,TemperateForestWater::FPlanPtr ForestWater,FTemperateChapelSite Chapel,FTemperateVillageSite Village,bool IncludeWater,int32 ReuseQuads=0,int32* OutQuads=nullptr)
{
    auto Result=MakeShared<FMeshResult,ESPMode::ThreadSafe>();Result->Key=Key;Result->Detailed=Detailed;
    auto& Mesh=Result->Mesh;Mesh.EnableAttributes();Mesh.Attributes()->EnablePrimaryColors();
    const double OX=-Half+Key.X*CellSize,OY=-Half+Key.Y*CellSize;
    const bool SlopeCell=River&&River->QuarryLakeSlope.IntersectsCell(OX,OY,CellSize);
    Mesh.Attributes()->SetNumUVLayers(SlopeCell?4:3);
    auto* Habitat=Mesh.Attributes()->GetUVLayer(1);
    auto* UplandCover=Mesh.Attributes()->GetUVLayer(2);
    auto* SlopeDrainage=SlopeCell?Mesh.Attributes()->GetUVLayer(3):nullptr;
    auto* Normals=Mesh.Attributes()->PrimaryNormals();auto* UVs=Mesh.Attributes()->PrimaryUV();
    auto* Colors=Mesh.Attributes()->PrimaryColors();
    const bool RiverCell=River&&River->IntersectsCell(OX,OY,CellSize);
    const bool PondCell=ForestWater&&ForestWater->IntersectsCell(OX,OY,CellSize);
    // Only the edits that can still reach this cell (plus the normal stencil) travel into the job.
    TArray<TemperateHillsSurface::FTerrainEdit> LocalEdits;
    if(!Edits.IsEmpty())for(const TemperateHillsSurface::FTerrainEdit& Edit:Edits)
    {
        const double Reach=TemperateHillsSurface::TerrainEditReach(Edit)+110;
        if(Edit.X>OX-Reach&&Edit.X<OX+CellSize+Reach&&Edit.Y>OY-Reach&&Edit.Y<OY+CellSize+Reach)LocalEdits.Add(Edit);
    }
    // Even distant river cells retain 2 m terrain spacing to avoid a coarse LOD
    // spanning across the shallow channel and covering its water surface.
    // Edited ground gets twice the resolution: a 3 m crater or a 20 cm shovel step
    // needs the extra vertices to avoid reading as a faceted polygon.
    const int32 Boost=!LocalEdits.IsEmpty()?FMath::Clamp(HillsStreaming::EditMeshBoost.GetValueOnAnyThread(),1,4):1;
    // Shallow forest shorelines retain a 1 m grid even in the distant LOD.
    const bool ChapelCell=Chapel.Near(OX+CellSize*.5,OY+CellSize*.5,CellSize*.5);
    const bool VillageCell=Village.Near(OX+CellSize*.5,OY+CellSize*.5,CellSize*.5);
    const bool CliffCell=River&&River->WhiteCliffs.Weight(OX+CellSize*.5,OY+CellSize*.5)>.01;
    // A distant 8 m quad spans an entire slope gully. Retain its 2 m grid
    // from the opposite shore and keep normal near-field density on approach.
    const int32 GroundQuads=Detailed||SlopeCell?32:8;
    const int32 RiverQuads=Detailed?SurfaceDetailQuads:32;
    const int32 Quads=(PondCell||ChapelCell||VillageCell?SurfaceDetailQuads:RiverCell||CliffCell?RiverQuads:GroundQuads)*Boost;
    if(OutQuads)*OutQuads=Quads;
    // Both LODs are identical for ponds and settlement pads (and some slope
    // cells). The authoring pass stores the first mesh once for both draws.
    if(Quads==ReuseQuads)return nullptr;
    const double Step=CellSize/Quads;
    for(int32 Y=0;Y<=Quads;++Y)for(int32 X=0;X<=Quads;++X)
    {
        const double WX=OX+X*Step,WY=OY+Y*Step;
        double Z=River?River->Height(WX,WY,Seed):TemperateHillsSurface::Height(WX,WY,Seed,Version);
        if(ForestWater)Z=ForestWater->ShapeGround(WX,WY,Z);
        if(VillageCell)Z=Village.Grade(WX,WY,Z,Seed);
        if(ChapelCell)Z=Chapel.Grade(WX,WY,Z);
        if(!LocalEdits.IsEmpty())Z+=TemperateHillsSurface::TerrainEditOffset(LocalEdits,WX,WY);
        Mesh.AppendVertex(FVector3d(X*Step,Y*Step,Z));
        FVector Normal=River?River->Normal(WX,WY,Seed):TemperateHillsSurface::Normal(WX,WY,Seed,Version);
        if((ChapelCell&&Chapel.Near(WX,WY))||(VillageCell&&Village.Near(WX,WY))||(ForestWater&&ForestWater->HasBasin(WX,WY))||(!LocalEdits.IsEmpty()&&TemperateHillsSurface::TerrainEditTouches(LocalEdits,WX,WY)))
            Normal=TemperateHillsSurface::NumericNormal([&](double PX,double PY)
            {
                double Base=River?River->Height(PX,PY,Seed):TemperateHillsSurface::Height(PX,PY,Seed,Version);
                if(ForestWater)Base=ForestWater->ShapeGround(PX,PY,Base);
                return Chapel.Grade(PX,PY,Village.Grade(PX,PY,Base,Seed))+TemperateHillsSurface::TerrainEditOffset(LocalEdits,PX,PY);
            },WX,WY);
        Normals->AppendElement(FVector3f(Normal));
        const auto Bank=River?River->Sample(WX,WY):TemperateRiver::FSample();
        const auto Layers=TemperateHillsGround::Layers(WX,WY,Z,Normal,Seed,Bank,River?River->RainforestWeight(WX,WY):0.,
            River ? River->Ecology : TemperateEcology::FProfile{},River&&River->bVillageRainforest,Village,River.Get());
        UVs->AppendElement(Layers.UV);
        Habitat->AppendElement(Layers.Habitat);
        UplandCover->AppendElement(Layers.Upland);
        if(SlopeDrainage)SlopeDrainage->AppendElement(Layers.SlopeDrainage);
        Colors->AppendElement(Layers.Color);
    }
    // Concavity is sampled from the existing grid, without extra height noise
    // queries per vertex. UV1 is an added contract; UV0 and RGBA keep their uses.
    auto NeighborZ=[&](int32 X,int32 Y)
    {
        if(X>=0&&Y>=0&&X<=Quads&&Y<=Quads)return Mesh.GetVertex(Y*(Quads+1)+X).Z;
        const double WX=OX+X*Step,WY=OY+Y*Step;
        double Z=River?River->Height(WX,WY,Seed):TemperateHillsSurface::Height(WX,WY,Seed,Version);
        if(ForestWater)Z=ForestWater->ShapeGround(WX,WY,Z);
        return Chapel.Grade(WX,WY,Village.Grade(WX,WY,Z,Seed))+TemperateHillsSurface::TerrainEditOffset(LocalEdits,WX,WY);
    };
    for(int32 Y=0;Y<=Quads;++Y)for(int32 X=0;X<=Quads;++X)
    {
        const int32 I=Y*(Quads+1)+X;const double Z=Mesh.GetVertex(I).Z;
        const double Mean=(NeighborZ(X-1,Y)+NeighborZ(X+1,Y)+NeighborZ(X,Y-1)+NeighborZ(X,Y+1))*.25;
        const auto Value=Habitat->GetElement(I);
        const float Moisture=TemperateHillsGround::SurfaceMoisture(Mean,Z,Step,Value.X,ForestWater,OX+X*Step,OY+Y*Step);
        Habitat->SetElement(I,FVector2f(Value.X,Moisture));
    }
    auto Tri=[&](int32 A,int32 B,int32 C)
    {
        const int32 ID=Mesh.AppendTriangle(A,B,C);
        const UE::Geometry::FIndex3i Indices(A,B,C);
        Normals->SetTriangle(ID,Indices);UVs->SetTriangle(ID,Indices);Colors->SetTriangle(ID,Indices);
        Habitat->SetTriangle(ID,Indices);UplandCover->SetTriangle(ID,Indices);
        if(SlopeDrainage)SlopeDrainage->SetTriangle(ID,Indices);
    };
    for(int32 Y=0;Y<Quads;++Y)for(int32 X=0;X<Quads;++X)
    {const int32 A=Y*(Quads+1)+X;Tri(A,A+Quads+2,A+1);Tri(A,A+Quads+1,A+Quads+2);}
    // Downward skirts cover the different edge subdivisions at the LOD boundary.
    TArray<int32> Edge;
    for(int32 X=0;X<=Quads;++X)Edge.Add(X);
    for(int32 Y=1;Y<=Quads;++Y)Edge.Add(Y*(Quads+1)+Quads);
    for(int32 X=Quads-1;X>=0;--X)Edge.Add(Quads*(Quads+1)+X);
    for(int32 Y=Quads-1;Y>0;--Y)Edge.Add(Y*(Quads+1));
    TArray<int32> Bottom;
    for(int32 Top:Edge)
    {
        const FVector3d P=Mesh.GetVertex(Top);
        const double Proxy=TemperateBackdrop::CoreTriangleHeight(OX+P.X,OY+P.Y,Half,Seed,River,Version,Village);
        Bottom.Add(Mesh.AppendVertex(FVector3d(P.X,P.Y,FMath::Min(P.Z-800,Proxy-50))));
        Normals->AppendElement(Normals->GetElement(Top));UVs->AppendElement(UVs->GetElement(Top));
        Colors->AppendElement(Colors->GetElement(Top));
        Habitat->AppendElement(FVector2f(0,0));
        UplandCover->AppendElement(UplandCover->GetElement(Top));
        if(SlopeDrainage)SlopeDrainage->AppendElement(SlopeDrainage->GetElement(Top));
    }
    for(int32 I=0;I<Edge.Num();++I){const int32 J=(I+1)%Edge.Num();Tri(Edge[I],Bottom[J],Bottom[I]);Tri(Edge[I],Edge[J],Bottom[J]);}
    if(IncludeWater&&RiverCell)River->BuildWaterMesh(OX,OY,CellSize,Result->Water);
    if(IncludeWater&&PondCell)ForestWater->BuildWaterMesh(OX,OY,CellSize,Result->Ponds);
    return Result;
}

TSharedPtr<FMeshResult,ESPMode::ThreadSafe> MakeMesh(FIntPoint Key,bool Detailed,double Half,int32 Seed,TemperateRiver::FPlanPtr River,const TArray<TemperateHillsSurface::FTerrainEdit>& Edits,int32 Version,TemperateForestWater::FPlanPtr ForestWater,FTemperateChapelSite Chapel,FTemperateVillageSite Village)
{
    return GenerateCellGeometry(Key,Detailed,Half,Seed,River,Edits,Version,ForestWater,Chapel,Village,true);
}
}

#if WITH_EDITOR
void HillsFixedTerrainCells::BuildBakeCell(FIntPoint Key,double Half,int32 Seed,int32 Version,
    TemperateRiver::FPlanPtr River,TemperateForestWater::FPlanPtr Water,FTemperateChapelSite Chapel,
    FTemperateVillageSite Village,FCellPtr& Near,FCellPtr& Far)
{
    int32 NearQuads=0;
    Near=HillsStreaming::GenerateCellGeometry(Key,true,Half,Seed,River,{},Version,Water,Chapel,Village,true,0,&NearQuads);
    Far=HillsStreaming::GenerateCellGeometry(Key,false,Half,Seed,River,{},Version,Water,Chapel,Village,false,NearQuads);
}
#endif
