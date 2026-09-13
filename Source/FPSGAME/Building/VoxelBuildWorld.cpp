#include "VoxelBuildWorld.h"
#include "VoxelBuildPalette.h"
#include "VoxelSurfaceMesher.h"
#include "VoxelSupportGraph.h"
#include "Components/DynamicMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include "Materials/MaterialInterface.h"
#include "GameFramework/Character.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/SecureHash.h"
#include "EngineUtils.h"

namespace VoxelGrid
{
    const FIntVector Neighbors[]={FIntVector(1,0,0),FIntVector(-1,0,0),FIntVector(0,1,0),FIntVector(0,-1,0),FIntVector(0,0,1),FIntVector(0,0,-1)};
    int32 FloorChunk(int32 N){return N>=0?N/16:-int32((-(int64)N+15)/16);}
}

AVoxelBuildWorld::AVoxelBuildWorld()
{
    PrimaryActorTick.bCanEverTick=false;
    SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("VoxelRoot")));
}
FIntVector AVoxelBuildWorld::ToCell(const FVector& P){return FIntVector(FMath::FloorToInt(P.X/CellSizeCm),FMath::FloorToInt(P.Y/CellSizeCm),FMath::FloorToInt(P.Z/CellSizeCm));}
FVector AVoxelBuildWorld::CellMin(FIntVector P){return FVector(P)*CellSizeCm;}
FVector AVoxelBuildWorld::CellCenter(FIntVector P){return CellMin(P)+FVector(CellSizeCm*.5);}
FIntVector AVoxelBuildWorld::ChunkFor(FIntVector P){return FIntVector(VoxelGrid::FloorChunk(P.X),VoxelGrid::FloorChunk(P.Y),VoxelGrid::FloorChunk(P.Z));}
FName AVoxelBuildWorld::MaterialAt(FIntVector P) const {const auto* Value=Cells.Find(P);return Value?*Value:NAME_None;}
bool AVoxelBuildWorld::OwnsSurface(const UPrimitiveComponent* C) const {return C&&C->GetOwner()==this;}

FName AVoxelBuildWorld::VolumeMaterialAt(FGuid Volume,FIntVector Cell) const
{
    if(!Volume.IsValid())return MaterialAt(Cell);
    const auto* Data=FreeVolumes.Find(Volume);const auto* Value=Data?Data->Cells.Find(Cell):nullptr;
    return Value?*Value:NAME_None;
}
FVector AVoxelBuildWorld::VolumeOrigin(FGuid Volume) const
{
    const auto* Data=FreeVolumes.Find(Volume);return Data?Data->Origin:FVector::ZeroVector;
}
int32 AVoxelBuildWorld::BlockCount() const
{
    int32 Count=Cells.Num();for(const auto& Entry:FreeVolumes)Count+=Entry.Value.Cells.Num();return Count;
}
int32 AVoxelBuildWorld::UnsupportedBlockCount() const
{
    if(!SupportGraph)return 0;
    int32 Count=0;for(int32 I=0;I<SupportGraph->Nodes.Num();++I)Count+=!SupportGraph->IsSupported(I);return Count;
}
bool AVoxelBuildWorld::ResolveHit(const FHitResult& Hit,FVoxelBuildKey& Key) const
{
    const auto* Volume=CollisionVolumes.Find(Hit.GetComponent());if(!Volume)return false;
    Key.Volume=*Volume;Key.Cell=ToCell(Hit.ImpactPoint-Hit.ImpactNormal*.5-VolumeOrigin(*Volume));
    return !VolumeMaterialAt(Key.Volume,Key.Cell).IsNone();
}

bool AVoxelBuildWorld::Initialize(const FString& InWorldKey, UVoxelBuildPalette* InPalette)
{
    if(GetNetMode()!=NM_Standalone||bReady||!InPalette)return false;
    Palette=InPalette;WorldKey=InWorldKey;
    FTCHARToUTF8 KeyBytes(*WorldKey);FMD5 KeyHash;uint8 Digest[16];
    KeyHash.Update(reinterpret_cast<const uint8*>(KeyBytes.Get()),KeyBytes.Length());KeyHash.Final(Digest);
    SaveSlot=TEXT("Voxel20_")+BytesToHex(Digest,16);
    for(const auto& Entry:Palette->Materials)
    {
        UMaterialInterface* Surface=Entry.Surface.LoadSynchronous();
        if(Entry.Id.IsNone()||!Surface||MaterialSlots.Contains(Entry.Id)){Message=TEXT("建造材质未准备完成");return false;}
        MaterialSlots.Add(Entry.Id,SurfaceMaterials.Add(Surface));
    }
    if(SurfaceMaterials.IsEmpty()){Message=TEXT("没有可用的建造材质");return false;}
    if(UGameplayStatics::DoesSaveGameExist(SaveSlot,0))
    {
        auto* Data=Cast<UVoxelBuildSave>(UGameplayStatics::LoadGameFromSlot(SaveSlot,0));
        if(!Data||(Data->Version!=1&&Data->Version!=2)||Data->CellSizeCm!=CellSizeCm||Data->WorldKey!=WorldKey)
        {Message=TEXT("建筑存档版本不兼容，已保留原档");return false;}
        for(const auto& Cell:Data->Cells)
        {
            if(!MaterialSlots.Contains(Cell.Material)){Message=TEXT("建筑存档缺少材料定义，已保留原档");return false;}
            Cells.Add(Cell.Position,Cell.Material);
        }
        for(const auto& Volume:Data->FreeVolumes)
        {
            if(!Volume.Id.IsValid()||Volume.Origin.ContainsNaN()||FreeVolumes.Contains(Volume.Id))
            {Message=TEXT("自由建筑存档无效，已保留原档");return false;}
            for(const auto& Cell:Volume.Cells)if(!MaterialSlots.Contains(Cell.Value))
            {Message=TEXT("自由建筑存档缺少材料定义，已保留原档");return false;}
            FreeVolumes.Add(Volume.Id,Volume);
        }
    }
    RefreshSupportGraph();
    TArray<FVoxelEditCell> Loaded;for(const auto& Entry:Cells)Loaded.Add({Entry.Key,NAME_None,Entry.Value,{}});
    for(const auto& Volume:FreeVolumes)for(const auto& Entry:Volume.Value.Cells)Loaded.Add({Entry.Key,NAME_None,Entry.Value,Volume.Key});
    RebuildAffected(Loaded);
    // Preserve older unsupported buildings; never delete player work on load.
    const int32 Unsupported=UnsupportedBlockCount();
    bReady=true;Message=Unsupported?FString::Printf(TEXT("建筑已载入 · %d 格需要补充支撑"),Unsupported):TEXT("自由建造 · 材料不限量");return true;
}

bool AVoxelBuildWorld::Save()
{
    if(!bReady||GetNetMode()!=NM_Standalone)return false;
    auto* Data=Cast<UVoxelBuildSave>(UGameplayStatics::CreateSaveGameObject(UVoxelBuildSave::StaticClass()));
    Data->WorldKey=WorldKey;Data->Cells.Reserve(Cells.Num());
    for(const auto& Entry:Cells){auto& Cell=Data->Cells.AddDefaulted_GetRef();Cell.Position=Entry.Key;Cell.Material=Entry.Value;}
    for(const auto& Entry:FreeVolumes)if(!Entry.Value.Cells.IsEmpty())Data->FreeVolumes.Add(Entry.Value);
    if(!UGameplayStatics::SaveGameToSlot(Data,SaveSlot,0)){Message=TEXT("建筑保存失败，本次操作未生效");return false;}
    return true;
}

bool AVoxelBuildWorld::CanPlace(const TArray<FIntVector>& Positions,FName Material,FString& Reason) const
{
    return CanPlaceInVolume({},Positions,Material,Reason);
}

bool AVoxelBuildWorld::EditCells(const TArray<FIntVector>& Positions,FName Material)
{
    return EditVolumeCells({},Positions,Material);
}

bool AVoxelBuildWorld::CanPlaceInVolume(FGuid Volume,const TArray<FIntVector>& Positions,FName Material,FString& Reason) const
{
    if(Volume.IsValid()&&!FreeVolumes.Contains(Volume)){Reason=TEXT("目标建筑已改变");return false;}
    for(const auto& Cell:Positions)if(!VolumeMaterialAt(Volume,Cell).IsNone()){Reason=TEXT("该位置已有方块");return false;}
    return CanPlaceAt(VolumeOrigin(Volume),Positions,Material,Reason);
}
bool AVoxelBuildWorld::CanPlaceFree(FVector Origin,const TArray<FIntVector>& Positions,FName Material,FString& Reason) const
{
    return CanPlaceAt(Origin,Positions,Material,Reason);
}

bool AVoxelBuildWorld::IsGroundAnchor(FVector Min) const
{
    FCollisionQueryParams Query(SCENE_QUERY_STAT(VoxelGroundAnchor),true,this);
    for(TActorIterator<APawn> It(GetWorld());It;++It)Query.AddIgnoredActor(*It);
    // Four samples require a real base, not a single point on a cliff edge.
    // A bottom voxel may intersect sloping terrain, as in the original grid.
    for(double X:{2.,18.})for(double Y:{2.,18.})
    {
        const FVector Foot=Min+FVector(X,Y,0);FHitResult Hit;
        if(!GetWorld()->LineTraceSingleByChannel(Hit,Foot+FVector(0,0,20.5),Foot-FVector(0,0,.5),ECC_Visibility,Query)
            ||Hit.ImpactNormal.Z<.5||!Hit.GetComponent()||Hit.GetComponent()->IsSimulatingPhysics())return false;
    }
    return true;
}

bool AVoxelBuildWorld::ScenePlacementAllowed(FVector Min,FString& Reason) const
{
    const FVector Center=Min+FVector(10);const FBox Box(Min+FVector(.25),Min+FVector(19.75));
    for(TActorIterator<ACharacter> It(GetWorld());It;++It)
        if(auto* Capsule=It->GetCapsuleComponent();Capsule&&Capsule->IsCollisionEnabled()&&Box.Intersect(Capsule->Bounds.GetBox()))
        {Reason=TEXT("位置被角色占用");return false;}
    FCollisionQueryParams Query(SCENE_QUERY_STAT(VoxelObstruction),true,this);FHitResult Ground;
    const FVector Foot(Center.X,Center.Y,Min.Z);
    const bool GroundSupport=GetWorld()->LineTraceSingleByChannel(Ground,Foot+FVector(0,0,21),Foot-FVector(0,0,.5),ECC_Visibility,Query)&&Ground.ImpactNormal.Z>.5;
    for(const FVector Axis:{FVector(1,0,0),FVector(0,1,0),FVector(0,0,1)})
    {
        FHitResult Obstacle;
        if(GetWorld()->LineTraceSingleByChannel(Obstacle,Center-Axis*8,Center+Axis*8,ECC_Visibility,Query)
            &&!(GroundSupport&&Obstacle.GetComponent()==Ground.GetComponent()&&Obstacle.ImpactPoint.Z<=Ground.ImpactPoint.Z+1))
        {Reason=TEXT("位置与场景障碍重叠");return false;}
    }
    return true;
}

void AVoxelBuildWorld::RefreshSupportGraph()
{
    SupportGraph=MakeShared<FVoxelSupportGraph>();SupportGraph->MaxSpanCm=FMath::Max(0.f,Palette->MaxCantileverCm);
    auto Add=[&](FGuid Volume,FIntVector Cell,FName Material)
    {
        const FVoxelBuildKey Key{Volume,Cell};const FVector Min=VolumeOrigin(Volume)+CellMin(Cell);
        const bool* Cached=AnchorCache.Find(Key);const bool Anchor=Cached?*Cached:IsGroundAnchor(Min);AnchorCache.Add(Key,Anchor);
        const auto* Definition=Palette->Find(Material);
        SupportGraph->Add({Key,Min,Anchor,Definition&&Definition->bSupportsWeight});
    };
    for(const auto& Entry:Cells)Add({},Entry.Key,Entry.Value);
    for(const auto& Volume:FreeVolumes)for(const auto& Entry:Volume.Value.Cells)Add(Volume.Key,Entry.Key,Entry.Value);
    SupportGraph->Solve();
}

bool AVoxelBuildWorld::CanPlaceAt(FVector Origin,const TArray<FIntVector>& Positions,FName Material,FString& Reason) const
{
    if(!bReady||!SupportGraph){Reason=Message;return false;}
    const auto* Definition=Palette->Find(Material);
    if(!Definition||Positions.IsEmpty()||Origin.ContainsNaN()){Reason=TEXT("请选择有效的建筑位置和材料");return false;}
    FVoxelSupportGraph Trial=*SupportGraph;const int32 First=Trial.Nodes.Num();TSet<FIntVector> Seen;
    const FGuid Draft=FGuid::NewGuid();
    for(const auto& Cell:Positions)
    {
        if(Seen.Contains(Cell))continue;Seen.Add(Cell);
        const FVector Min=Origin+CellMin(Cell);
        if(Trial.Overlaps(Min)){Reason=TEXT("位置与已有建筑重叠");return false;}
        if(!ScenePlacementAllowed(Min,Reason))return false;
        Trial.Add({{Draft,Cell},Min,IsGroundAnchor(Min),Definition->bSupportsWeight});
    }
    Trial.Solve();float Span=0;
    for(int32 I=First;I<Trial.Nodes.Num();++I)
    {
        if(!Trial.IsSupported(I)){Reason=FString::Printf(TEXT("缺少承重路径，或横向悬挑超过 %.1f 米"),Trial.MaxSpanCm/100);return false;}
        Span=FMath::Max(Span,Trial.Cost[I]);
    }
    Reason=FString::Printf(TEXT("可放置 %d 格 · 支撑横距 %.1f / %.1f 米"),Seen.Num(),Span/100,Trial.MaxSpanCm/100);return true;
}

bool AVoxelBuildWorld::EditVolumeCells(FGuid Volume,const TArray<FIntVector>& Positions,FName Material)
{
    if(!bReady||GetNetMode()!=NM_Standalone)return false;
    if(Volume.IsValid()&&!FreeVolumes.Contains(Volume)){Message=TEXT("目标建筑已改变");return false;}
    if(!Material.IsNone()&&!CanPlaceInVolume(Volume,Positions,Material,Message))return false;
    TArray<FVoxelEditCell> Edit;TSet<FIntVector> Seen;
    for(const auto& P:Positions)
    {
        if(Seen.Contains(P))continue;Seen.Add(P);
        const FName Before=VolumeMaterialAt(Volume,P);if(Before!=Material)Edit.Add({P,Before,Material,Volume});
    }
    if(Edit.IsEmpty()){Message=TEXT("没有可拆除的体素方块");return false;}
    return Commit(Edit,true);
}

bool AVoxelBuildWorld::PlaceFree(FVector Origin,const TArray<FIntVector>& Positions,FName Material)
{
    if(!bReady||GetNetMode()!=NM_Standalone)return false;
    if(!CanPlaceFree(Origin,Positions,Material,Message))return false;
    FVoxelFreeVolume Volume;Volume.Id=FGuid::NewGuid();Volume.Origin=Origin;FreeVolumes.Add(Volume.Id,Volume);
    if(!EditVolumeCells(Volume.Id,Positions,Material)){FreeVolumes.Remove(Volume.Id);return false;}
    return true;
}

bool AVoxelBuildWorld::CanCommit(const TArray<FVoxelEditCell>& Edit,FString& Reason) const
{
    TMap<FVoxelBuildKey,FName> Changes;
    for(const auto& E:Edit)
    {
        if(VolumeMaterialAt(E.Volume,E.Position)!=E.Before||(E.Volume.IsValid()&&!FreeVolumes.Contains(E.Volume)))
        {Reason=TEXT("建筑已改变，本次编辑未生效");return false;}
        Changes.Add({E.Volume,E.Position},E.After);
    }
    FVoxelSupportGraph Trial;Trial.MaxSpanCm=SupportGraph->MaxSpanCm;
    for(const auto& Node:SupportGraph->Nodes)if(!Changes.Contains(Node.Key))Trial.Add(Node);
    const int32 FirstNew=Trial.Nodes.Num();
    for(const auto& E:Edit)if(!E.After.IsNone())
    {
        const FVector Min=VolumeOrigin(E.Volume)+CellMin(E.Position);const auto* Definition=Palette->Find(E.After);
        if(!Definition||Trial.Overlaps(Min)){Reason=TEXT("编辑位置与已有建筑重叠");return false;}
        if(!ScenePlacementAllowed(Min,Reason))return false;
        Trial.Add({{E.Volume,E.Position},Min,IsGroundAnchor(Min),Definition->bSupportsWeight});
    }
    Trial.Solve();
    for(int32 I=FirstNew;I<Trial.Nodes.Num();++I)if(!Trial.IsSupported(I))
    {Reason=TEXT("编辑后的方块缺少承重支撑");return false;}
    for(int32 I=0;I<SupportGraph->Nodes.Num();++I)
    {
        const auto* Remaining=Trial.Indices.Find(SupportGraph->Nodes[I].Key);
        if(Remaining&&SupportGraph->IsSupported(I)&&!Trial.IsSupported(*Remaining))
        {Reason=TEXT("拆除会使结构失去支撑，请先拆上层或增加支柱");return false;}
    }
    return true;
}

void AVoxelBuildWorld::SetCell(const FVoxelEditCell& E,bool bAfter)
{
    const FName Material=bAfter?E.After:E.Before;
    auto& Target=E.Volume.IsValid()?FreeVolumes.FindChecked(E.Volume).Cells:Cells;
    if(Material.IsNone())Target.Remove(E.Position);else Target.Add(E.Position,Material);
}

bool AVoxelBuildWorld::Commit(const TArray<FVoxelEditCell>& Edit,bool bRemember)
{
    if(!CanCommit(Edit,Message))return false;
    for(const auto& E:Edit)SetCell(E,true);
    if(!Save())
    {
        for(const auto& E:Edit)SetCell(E,false);
        return false;
    }
    for(const auto& E:Edit)AnchorCache.Remove({E.Volume,E.Position});
    RefreshSupportGraph();RebuildAffected(Edit);
    if(bRemember){History.Add(Edit);if(History.Num()>32)History.RemoveAt(0);}
    Message=FString::Printf(TEXT("已保存 · 本次修改 %d 格"),Edit.Num());return true;
}

bool AVoxelBuildWorld::Undo()
{
    if(!bReady||History.IsEmpty()){Message=TEXT("没有可撤销的操作");return false;}
    TArray<FVoxelEditCell> Reverse;for(const auto& E:History.Last())Reverse.Add({E.Position,E.After,E.Before,E.Volume});
    if(!Commit(Reverse,false))return false;
    History.Pop();Message=TEXT("已撤销并保存");return true;
}

void AVoxelBuildWorld::RebuildAffected(const TArray<FVoxelEditCell>& Edit)
{
    TSet<FVoxelBuildKey> Keys;
    // Rounded corners also depend on diagonal neighbors across chunk borders.
    for(const auto& E:Edit)
        for(int32 Z=-1;Z<=1;++Z)for(int32 Y=-1;Y<=1;++Y)for(int32 X=-1;X<=1;++X)
            Keys.Add({E.Volume,ChunkFor(E.Position+FIntVector(X,Y,Z))});
    for(const auto& Key:Keys)RebuildChunk(Key);
}

void AVoxelBuildWorld::RebuildChunk(FVoxelBuildKey Key)
{
    using namespace UE::Geometry;
    FDynamicMesh3 Mesh;Mesh.EnableAttributes();Mesh.Attributes()->EnableMaterialID();
    auto* Normals=Mesh.Attributes()->PrimaryNormals();auto* UVs=Mesh.Attributes()->PrimaryUV();
    const FIntVector Origin=Key.Cell*ChunkSide;const FVector Offset=VolumeOrigin(Key.Volume);
    for(int32 Axis=0;Axis<3;++Axis)for(int32 Sign:{-1,1})
    {
        const int32 U=Axis==0?1:0,V=Axis==2?1:2;
        FIntVector Neighbor=FIntVector::ZeroValue;Neighbor[Axis]=Sign;
        FVector3f Normal=FVector3f::ZeroVector;Normal[Axis]=float(Sign);
        for(int32 Layer=0;Layer<ChunkSide;++Layer)
        {
            int32 Mask[ChunkSide*ChunkSide];
            for(int32 Y=0;Y<ChunkSide;++Y)for(int32 X=0;X<ChunkSide;++X)
            {
                FIntVector Cell=Origin;Cell[Axis]+=Layer;Cell[U]+=X;Cell[V]+=Y;
                const int32* Slot=MaterialSlots.Find(VolumeMaterialAt(Key.Volume,Cell));
                Mask[X+Y*ChunkSide]=Slot&&VolumeMaterialAt(Key.Volume,Cell+Neighbor).IsNone()?*Slot+1:0;
            }
            for(int32 Y=0;Y<ChunkSide;++Y)for(int32 X=0;X<ChunkSide;)
            {
                const int32 Slot=Mask[X+Y*ChunkSide];if(!Slot){++X;continue;}
                int32 Width=1,Height=1;
                while(X+Width<ChunkSide&&Mask[X+Width+Y*ChunkSide]==Slot)++Width;
                bool Extend=true;
                while(Y+Height<ChunkSide&&Extend)
                {
                    for(int32 I=0;I<Width;++I)if(Mask[X+I+(Y+Height)*ChunkSide]!=Slot){Extend=false;break;}
                    if(Extend)++Height;
                }
                FVector3d P=FVector3d::ZeroVector;P[Axis]=(Layer+(Sign>0?1:0))*CellSizeCm;P[U]=X*CellSizeCm;P[V]=Y*CellSizeCm;
                FVector3d DU=FVector3d::ZeroVector,DV=FVector3d::ZeroVector;DU[U]=Width*CellSizeCm;DV[V]=Height*CellSizeCm;
                const FVector3d Corners[]={P,P+DU,P+DU+DV,P+DV};
                int32 Vertices[4],NIDs[4],UVIds[4];
                for(int32 I=0;I<4;++I)
                {
                    Vertices[I]=Mesh.AppendVertex(Corners[I]);NIDs[I]=Normals->AppendElement(Normal);
                    const FVector3d World=FVector3d(Offset+CellMin(Origin))+Corners[I];
                    UVIds[I]=UVs->AppendElement(FVector2f(World[U]/80.0,World[V]/80.0));
                }
                auto Triangle=[&](int32 A,int32 B,int32 C)
                {
                    const int32 T=Mesh.AppendTriangle(Vertices[A],Vertices[B],Vertices[C]);
                    Normals->SetTriangle(T,FIndex3i(NIDs[A],NIDs[B],NIDs[C]));
                    UVs->SetTriangle(T,FIndex3i(UVIds[A],UVIds[B],UVIds[C]));
                    Mesh.Attributes()->GetMaterialID()->SetValue(T,Slot-1);
                };
                // Unreal front faces wind clockwise when seen from the outside.
                const int32 CrossSign=Axis==1?-1:1;
                if(Sign==CrossSign){Triangle(0,2,1);Triangle(0,3,2);}else{Triangle(0,1,2);Triangle(0,2,3);}
                for(int32 J=0;J<Height;++J)for(int32 I=0;I<Width;++I)Mask[X+I+(Y+J)*ChunkSide]=0;
                X+=Width;
            }
        }
    }
    if(Mesh.TriangleCount()==0)
    {
        if(auto* Existing=Chunks.Find(Key)){CollisionVolumes.Remove(*Existing);(*Existing)->DestroyComponent();Chunks.Remove(Key);}
    }
    else
    {
        // Keep the exact 20 cm collider for traces, stairs and build selection.
        // Rounded visual normals must not redirect the placement brush.
        UDynamicMeshComponent* Component=Chunks.FindRef(Key);
        if(!Component)
        {
            Component=NewObject<UDynamicMeshComponent>(this);AddInstanceComponent(Component);Component->SetupAttachment(RootComponent);
            Component->SetRelativeLocation(Offset+CellMin(Origin));Component->SetMobility(EComponentMobility::Movable);
            Component->SetCollisionProfileName(TEXT("BlockAll"));Component->SetComplexAsSimpleCollisionEnabled(true,false);
            Component->SetVisibility(false);Component->SetHiddenInGame(true);Component->SetCastShadow(false);
            Component->SetCanEverAffectNavigation(false);
            Component->RegisterComponent();Chunks.Add(Key,Component);CollisionVolumes.Add(Component,Key.Volume);
        }
        Component->SetMesh(MoveTemp(Mesh));Component->NotifyMeshUpdated();Component->UpdateBounds();Component->UpdateCollision(false);
    }
    FDynamicMesh3 Surface;
    VoxelSurface::Build(Surface,Origin,ChunkSide,Palette->EdgeRadiusCm,[this,Key](FIntVector Cell)
    {const int32* Slot=MaterialSlots.Find(VolumeMaterialAt(Key.Volume,Cell));return Slot?*Slot:INDEX_NONE;});
    if(Surface.TriangleCount()==0)
    {
        if(auto* Existing=RoundedChunks.Find(Key)){(*Existing)->DestroyComponent();RoundedChunks.Remove(Key);}return;
    }
    UDynamicMeshComponent* Visible=RoundedChunks.FindRef(Key);
    if(!Visible)
    {
        Visible=NewObject<UDynamicMeshComponent>(this);AddInstanceComponent(Visible);Visible->SetupAttachment(RootComponent);
        Visible->SetRelativeLocation(Offset+CellMin(Origin));Visible->SetMobility(EComponentMobility::Movable);
        Visible->SetTangentsType(EDynamicMeshComponentTangentsMode::AutoCalculated);
        Visible->SetCollisionEnabled(ECollisionEnabled::NoCollision);Visible->SetCanEverAffectNavigation(false);
        for(int32 I=0;I<SurfaceMaterials.Num();++I)Visible->SetMaterial(I,SurfaceMaterials[I]);
        Visible->RegisterComponent();RoundedChunks.Add(Key,Visible);
    }
    Visible->SetMesh(MoveTemp(Surface));Visible->NotifyMeshUpdated();Visible->UpdateBounds();
}
