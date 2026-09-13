#include "VoxelBuildWorld.h"
#include "VoxelBuildPalette.h"
#include "VoxelSurfaceMesher.h"
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
        if(!Data||Data->Version!=1||Data->CellSizeCm!=CellSizeCm||Data->WorldKey!=WorldKey)
        {Message=TEXT("建筑存档版本不兼容，已保留原档");return false;}
        for(const auto& Cell:Data->Cells)
        {
            if(!MaterialSlots.Contains(Cell.Material)){Message=TEXT("建筑存档缺少材料定义，已保留原档");return false;}
            Cells.Add(Cell.Position,Cell.Material);
        }
    }
    TSet<FIntVector> Keys;
    for(const auto& Entry:Cells)
        for(int32 Z=-1;Z<=1;++Z)for(int32 Y=-1;Y<=1;++Y)for(int32 X=-1;X<=1;++X)
            Keys.Add(ChunkFor(Entry.Key+FIntVector(X,Y,Z)));
    for(const auto& Key:Keys)RebuildChunk(Key);
    bReady=true;Message=TEXT("自由建造 · 材料不限量");return true;
}

bool AVoxelBuildWorld::Save()
{
    if(!bReady||GetNetMode()!=NM_Standalone)return false;
    auto* Data=Cast<UVoxelBuildSave>(UGameplayStatics::CreateSaveGameObject(UVoxelBuildSave::StaticClass()));
    Data->WorldKey=WorldKey;Data->Cells.Reserve(Cells.Num());
    for(const auto& Entry:Cells){auto& Cell=Data->Cells.AddDefaulted_GetRef();Cell.Position=Entry.Key;Cell.Material=Entry.Value;}
    if(!UGameplayStatics::SaveGameToSlot(Data,SaveSlot,0)){Message=TEXT("建筑保存失败，本次操作未生效");return false;}
    return true;
}

bool AVoxelBuildWorld::CanPlace(const TArray<FIntVector>& Positions,FName Material,FString& Reason) const
{
    if(!bReady){Reason=Message;return false;}
    if(!MaterialSlots.Contains(Material)||Positions.IsEmpty()){Reason=TEXT("请选择建筑材料");return false;}
    bool Supported=false;
    FCollisionQueryParams SupportQuery(SCENE_QUERY_STAT(VoxelSupport),true,this);
    for(TActorIterator<APawn> It(GetWorld());It;++It)SupportQuery.AddIgnoredActor(*It);
    for(const auto& Cell:Positions)
    {
        if(!MaterialAt(Cell).IsNone()){Reason=TEXT("该位置已有方块");return false;}
        const FVector Min=CellMin(Cell),Center=CellCenter(Cell);
        const FBox Box(Min+FVector(.25),Min+FVector(CellSizeCm-.25));
        for(TActorIterator<ACharacter> It(GetWorld());It;++It)
        {
            if(auto* Capsule=It->GetCapsuleComponent();Capsule&&Capsule->IsCollisionEnabled()&&Box.Intersect(Capsule->Bounds.GetBox()))
            {Reason=TEXT("位置被角色占用");return false;}
        }
        FHitResult Ground;
        const FVector Foot(Center.X,Center.Y,Min.Z);
        // A grid cell may partly enter the ground. This keeps 20 cm snapping
        // continuous on uneven terrain instead of hovering above every slope.
        const bool GroundSupport=GetWorld()->LineTraceSingleByChannel(Ground,Foot+FVector(0,0,CellSizeCm+1),Foot-FVector(0,0,2),ECC_Visibility,SupportQuery)&&Ground.ImpactNormal.Z>.5f;
        Supported|=GroundSupport;
        // Scene geometry above the support surface remains an obstruction.
        FCollisionQueryParams SolidQuery(SCENE_QUERY_STAT(VoxelObstruction),true,this);
        FHitResult Obstacle;
        const FVector Samples[]={FVector(1,0,0),FVector(0,1,0),FVector(0,0,1)};
        for(const auto& Axis:Samples)
            if(GetWorld()->LineTraceSingleByChannel(Obstacle,Center-Axis*8,Center+Axis*8,ECC_Visibility,SolidQuery)
                &&!(GroundSupport&&Obstacle.GetComponent()==Ground.GetComponent()&&Obstacle.ImpactPoint.Z<=Ground.ImpactPoint.Z+1))
            {Reason=TEXT("位置与场景障碍重叠");return false;}
        for(const auto& N:VoxelGrid::Neighbors)Supported|=!MaterialAt(Cell+N).IsNone();
    }
    if(!Supported){Reason=TEXT("需要地面或已有方块作为支撑");return false;}
    Reason=FString::Printf(TEXT("可放置 %d 个方块"),Positions.Num());return true;
}

bool AVoxelBuildWorld::EditCells(const TArray<FIntVector>& Positions,FName Material)
{
    if(!bReady||GetNetMode()!=NM_Standalone)return false;
    if(!Material.IsNone()&&!CanPlace(Positions,Material,Message))return false;
    TArray<FVoxelEditCell> Edit;TSet<FIntVector> Seen;
    for(const auto& P:Positions)
    {
        if(Seen.Contains(P))continue;Seen.Add(P);
        const FName Before=MaterialAt(P);if(Before!=Material)Edit.Add({P,Before,Material});
    }
    if(Edit.IsEmpty()){Message=TEXT("没有可拆除的体素方块");return false;}
    return Commit(Edit,true);
}

bool AVoxelBuildWorld::Commit(const TArray<FVoxelEditCell>& Edit,bool bRemember)
{
    for(const auto& E:Edit){if(E.After.IsNone())Cells.Remove(E.Position);else Cells.Add(E.Position,E.After);}
    if(!Save())
    {
        for(const auto& E:Edit){if(E.Before.IsNone())Cells.Remove(E.Position);else Cells.Add(E.Position,E.Before);}
        return false;
    }
    RebuildAffected(Edit);
    if(bRemember){History.Add(Edit);if(History.Num()>32)History.RemoveAt(0);}
    Message=FString::Printf(TEXT("已保存 · 本次修改 %d 格"),Edit.Num());return true;
}

bool AVoxelBuildWorld::Undo()
{
    if(!bReady||History.IsEmpty()){Message=TEXT("没有可撤销的操作");return false;}
    TArray<FVoxelEditCell> Reverse;for(const auto& E:History.Last())Reverse.Add({E.Position,E.After,E.Before});
    if(!Commit(Reverse,false))return false;
    History.Pop();Message=TEXT("已撤销并保存");return true;
}

void AVoxelBuildWorld::RebuildAffected(const TArray<FVoxelEditCell>& Edit)
{
    TSet<FIntVector> Keys;
    // Rounded corners also depend on diagonal neighbors across chunk borders.
    for(const auto& E:Edit)
        for(int32 Z=-1;Z<=1;++Z)for(int32 Y=-1;Y<=1;++Y)for(int32 X=-1;X<=1;++X)
            Keys.Add(ChunkFor(E.Position+FIntVector(X,Y,Z)));
    for(const auto& Key:Keys)RebuildChunk(Key);
}

void AVoxelBuildWorld::RebuildChunk(FIntVector Key)
{
    using namespace UE::Geometry;
    FDynamicMesh3 Mesh;Mesh.EnableAttributes();Mesh.Attributes()->EnableMaterialID();
    auto* Normals=Mesh.Attributes()->PrimaryNormals();auto* UVs=Mesh.Attributes()->PrimaryUV();
    const FIntVector Origin=Key*ChunkSide;
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
                const int32* Slot=MaterialSlots.Find(MaterialAt(Cell));
                Mask[X+Y*ChunkSide]=Slot&&MaterialAt(Cell+Neighbor).IsNone()?*Slot+1:0;
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
                    const FVector3d World=FVector3d(CellMin(Origin))+Corners[I];
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
        if(auto* Existing=Chunks.Find(Key)){(*Existing)->DestroyComponent();Chunks.Remove(Key);}
    }
    else
    {
        // Keep the exact 20 cm collider for traces, stairs and build selection.
        // Rounded visual normals must not redirect the placement brush.
        UDynamicMeshComponent* Component=Chunks.FindRef(Key);
        if(!Component)
        {
            Component=NewObject<UDynamicMeshComponent>(this);AddInstanceComponent(Component);Component->SetupAttachment(RootComponent);
            Component->SetRelativeLocation(CellMin(Origin));Component->SetMobility(EComponentMobility::Movable);
            Component->SetCollisionProfileName(TEXT("BlockAll"));Component->SetComplexAsSimpleCollisionEnabled(true,false);
            Component->SetVisibility(false);Component->SetHiddenInGame(true);Component->SetCastShadow(false);
            Component->SetCanEverAffectNavigation(false);
            Component->RegisterComponent();Chunks.Add(Key,Component);
        }
        Component->SetMesh(MoveTemp(Mesh));Component->NotifyMeshUpdated();Component->UpdateBounds();Component->UpdateCollision(false);
    }
    FDynamicMesh3 Surface;
    VoxelSurface::Build(Surface,Origin,ChunkSide,Palette->EdgeRadiusCm,[this](FIntVector Cell)
    {const int32* Slot=MaterialSlots.Find(MaterialAt(Cell));return Slot?*Slot:INDEX_NONE;});
    if(Surface.TriangleCount()==0)
    {
        if(auto* Existing=RoundedChunks.Find(Key)){(*Existing)->DestroyComponent();RoundedChunks.Remove(Key);}return;
    }
    UDynamicMeshComponent* Visible=RoundedChunks.FindRef(Key);
    if(!Visible)
    {
        Visible=NewObject<UDynamicMeshComponent>(this);AddInstanceComponent(Visible);Visible->SetupAttachment(RootComponent);
        Visible->SetRelativeLocation(CellMin(Origin));Visible->SetMobility(EComponentMobility::Movable);
        Visible->SetTangentsType(EDynamicMeshComponentTangentsMode::AutoCalculated);
        Visible->SetCollisionEnabled(ECollisionEnabled::NoCollision);Visible->SetCanEverAffectNavigation(false);
        for(int32 I=0;I<SurfaceMaterials.Num();++I)Visible->SetMaterial(I,SurfaceMaterials[I]);
        Visible->RegisterComponent();RoundedChunks.Add(Key,Visible);
    }
    Visible->SetMesh(MoveTemp(Surface));Visible->NotifyMeshUpdated();Visible->UpdateBounds();
}
