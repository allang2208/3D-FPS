#include "TemperateVillagePerimeter.h"
#include "VillageMasonry.h"
#include "TemperateHillsWorld.h"
#include "VillageDefenseSection.h"
#include "VillageDefenseStairs.h"
#include "HighVillageDefense.h"
#include "VillageDefenseState.h"
#include "../Building/VillageDefenseFootprint.h"
#include "../Building/VillageWallStairs.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "TimerManager.h"
#include "PhysicsEngine/BodySetup.h"
#include "Kismet/GameplayStatics.h"

namespace TemperateVillagePerimeter
{
const TCHAR* const Roles[]={TEXT("RepairedA"),TEXT("RepairedB"),TEXT("RuinedA"),TEXT("RuinedB"),
    TEXT("RuinedC"),TEXT("RuinedD"),TEXT("PierRepaired"),TEXT("PierRuined"),TEXT("RubbleA"),TEXT("RubbleB")};
FSoftObjectPath MeshPath(const TCHAR* Role)
{
    const FString Name=FString(TEXT("SM_VillageWall")) + Role;
    return FCString::Strncmp(Role,TEXT("Rubble"),6)==0 ? VillageMasonry::Mesh(Name) : VillageMasonry::CastleMesh(Name);
}
void AddMeshPaths(TArray<FSoftObjectPath>& Paths)
{
    for(const auto* Role:Roles)Paths.AddUnique(MeshPath(Role));
    AVillageDefenseSection::AddAssetPaths(Paths);
    AHighVillageWall::AddHighAssetPaths(Paths);
    Paths.AddUnique(AVillageDefenseStairs::StairMeshPath());
}

struct FPiece
{
    const TCHAR* Role;
    FVector2D At;
    double Yaw,Length;
    bool Pier=false,Rubble=false;
    int32 WallStation=INDEX_NONE;
};
TArray<FPiece> Layout(const FTemperateVillageSite& V,int32 Seed,bool Repaired,bool High=false)
{
    TArray<FPiece> Pieces;
    // Keep the entire perimeter on the graded crown, with at least 4 m to its edge.
    const FVector2D Wall=V.WallHalfSize();
    const double X=Wall.X,Y=Wall.Y,Bevel=FTemperateVillageSite::WallCornerCut;
    const TArray<FVector2D> Corners={{-X,-Y+Bevel},{-X+Bevel,-Y},{X-Bevel,-Y},{X,-Y+Bevel},
        {X,Y-Bevel},{X-Bevel,Y},{-X+Bevel,Y},{-X,Y-Bevel}};
    FRandomStream Random(int32(uint32(Seed)^0x3C75A29Bu));
    int32 Station=0;
    auto Run=[&](FVector2D A,FVector2D B,bool StartCorner=true,bool EndCorner=true)
    {
        const FVector2D D=(B-A).GetSafeNormal(),Out(D.Y,-D.X);
        if(High)
        {
            // The outside face stays on the old stone line. Let the square ends
            // meet at its bevel vertex so the wider wall walk also joins inside.
            const FVector2D Inset=-Out*67.;
            const double EndReturn=33.*FMath::Tan(PI/8.);
            A+=Inset-(StartCorner?D*EndReturn:FVector2D::ZeroVector);
            B+=Inset+(EndCorner?D*EndReturn:FVector2D::ZeroVector);
        }
        const double Length=(B-A).Size(),Yaw=FMath::RadiansToDegrees(FMath::Atan2(D.Y,D.X));
        const int32 Count=FMath::Max(1,FMath::CeilToInt(Length/300.));
        const double Span=Length/Count;
        for(int32 I=0;I<Count;++I,++Station)
        {
            const auto P=A+D*((I+.5)*Span);
            // Shared seeded stations keep both styles on the exact same footprint.
            // Keep the upper random bits: full-range float scaling erased variant bits,
            // while the low bits of this generator have a short repeating pattern.
            const uint32 Key=Random.GetUnsignedInt()>>8;
            if(Repaired)Pieces.Add({Roles[Key%2],P,Yaw,Span+1.5,false,false,Station});
            else
            {
                // Two adjacent open bays create proper breaches, not a repeated tiny crack.
                const bool Breach=Station%17==6||Station%17==7||Station%23==14;
                if(!Breach)Pieces.Add({Roles[2+Key%4],P,Yaw,Span+1.5,false,false,Station});
                if(Breach||Station%3==0)
                    Pieces.Add({Roles[8+Key%2],P+Out*(Breach?90.:115.),Yaw+double(Key%61)-30.,300.,false,true});
            }
        }
    };
    auto Pier=[&](const FVector2D& P){if(!High)Pieces.Add({Roles[Repaired?6:7],P,0.,300.,true,false});};
    for(int32 I=0;I<Corners.Num();++I)
    {
        const auto A=Corners[I],B=Corners[(I+1)%Corners.Num()];
        const bool West=FMath::IsNearlyEqual(A.X,-X)&&FMath::IsNearlyEqual(B.X,-X);
        const bool East=FMath::IsNearlyEqual(A.X,X)&&FMath::IsNearlyEqual(B.X,X);
        if(West||East)
        {
            // Match VillageSite::Approach: west y=0, east y=500 cm.
            const double GateY=V.GateY(A.X),HalfGap=V.GateHalfGap(A.X);
            const FVector2D D=(B-A).GetSafeNormal();
            const FVector2D Near(A.X,GateY-D.Y*HalfGap),Far(A.X,GateY+D.Y*HalfGap);
            Run(A,Near,true,false);Run(Far,B,false,true);Pier(Near);Pier(Far);
        }
        else Run(A,B);
        Pier(A);
    }
    return Pieces;
}
FTransform Placement(const FPiece& Piece,const ATemperateHillsWorld& Hills,bool High=false)
{
    const auto& V=Hills.GetVillageSite();const auto P=V.World(Piece.At.X,Piece.At.Y);
    const double Yaw=FMath::RadiansToDegrees(FMath::Atan2(V.Axis.Y,V.Axis.X))+Piece.Yaw;
    return FTransform(FRotator(0.,Yaw,0.),FVector(P,Hills.Height(P.X,P.Y)),FVector(Piece.Length/300.,1.,!High&&FCString::Strstr(Piece.Role,TEXT("Repaired"))?1.25:1.));
}
FTransform GatePlacement(const ATemperateHillsWorld& Hills,int32 Side)
{
    const auto& Site=Hills.GetVillageSite();
    const double X=Side*Site.WallHalfSize().X,Y=Site.GateY(Side),HalfGap=Site.GateHalfGap(Side);
    const auto P=Site.World(X,Y),A=Site.World(X,Y-HalfGap),B=Site.World(X,Y+HalfGap);
    const double Z=FMath::Max3(Hills.Height(P.X,P.Y),Hills.Height(A.X,A.Y),Hills.Height(B.X,B.Y));
    const double Yaw=FMath::RadiansToDegrees(FMath::Atan2(Site.Axis.Y,Site.Axis.X))+Side*90.;
    return FTransform(FRotator(0,Yaw,0),FVector(P,Z));
}

using FStairShape=VillageDefenseFootprint::FShape;

const FStairShape& StairShape()
{
    return VillageDefenseFootprint::Get(VillageWallStairs::Id,Cast<UStaticMesh>(AVillageDefenseStairs::StairMeshPath().ResolveObject()));
}

bool OverlapsStair(const FStairShape& Shape,const FTransform& Fixed,const FTransform& Placed)
{
    // All installed flights are upright. Projecting onto both sets of local axes
    // tests the two oriented boxes exactly, including angled player construction.
    const FTransform ToFixed=Placed.GetRelativeTransform(Fixed);
    if(!Shape.Bounds.Intersect(Shape.Bounds.TransformBy(ToFixed)))return false;
    const FTransform ToPlaced=Fixed.GetRelativeTransform(Placed);
    const FBox Entry=VillageWallStairs::EntranceBounds();
    const FBox EntryInPlaced=Entry.TransformBy(ToPlaced);
    for(const FBox& Tread:Shape.Boxes)
    {
        const FBox Inset=Tread.ExpandBy(-.5);
        const FBox InFixed=Inset.TransformBy(ToFixed);
        if(Entry.Intersect(InFixed) && Inset.Intersect(EntryInPlaced))return true;
        for(const FBox& Other:Shape.Boxes)
            if(Other.Intersect(InFixed) && Inset.Intersect(Other.TransformBy(ToPlaced)))
                return true;
    }
    return false;
}

bool HasPlacedStair(const ATemperateHillsWorld& Hills,const FTransform& Site,const FStairShape& Shape)
{
    // Destroyed masonry has no collision but its owner can still purchase a repair.
    for(TActorIterator<AVillageDefenseStairs> It(Hills.GetWorld());It;++It)
        if(It->GetOwner()==&Hills && It->IsPlayerBuilt() && !It->IsActorBeingDestroyed() &&
            !It->ActorHasTag(TEXT("VoxelDetached")) && OverlapsStair(Shape,Site,It->GetActorTransform()))
            return true;
    return false;
}

TOptional<FTransform> AvailableFlight(const ATemperateHillsWorld& Hills,const FTransform& Gate,bool bWest,
    const FStairShape& Shape,const AVillageDefenseStairs* Arriving=nullptr)
{
    for(bool bRightPier:{true,false})
    {
        const FTransform Site=VillageWallStairs::GatehouseFlight(Gate,bWest,bRightPier);
        if(Arriving && OverlapsStair(Shape,Site,Arriving->GetActorTransform()))continue;
        if(!HasPlacedStair(Hills,Site,Shape))return Site;
    }
    return {};
}

bool PawnInStair(UWorld& World,const FStairShape& Shape,const FTransform& Site)
{
    const auto Occupied=[&](const FBox& Box)
    {
        return World.OverlapAnyTestByObjectType(Site.TransformPosition(Box.GetCenter()),Site.GetRotation(),
            FCollisionObjectQueryParams(ECC_Pawn),FCollisionShape::MakeBox(Box.GetExtent()-FVector(.5)));
    };
    return Occupied(Shape.Bounds) && Shape.Boxes.ContainsByPredicate(Occupied);
}
}

void ATemperateHillsWorld::ClearVillagePerimeter()
{
    GetWorldTimerManager().ClearTimer(VillageGateStairRetry);
    for(UInstancedStaticMeshComponent* Part:VillageWallParts)if(Part){RemoveInstanceComponent(Part);Part->DestroyComponent();}
    VillageWallParts.Reset();
    for(AVillageDefenseSection* Section:VillageDefenseParts)if(IsValid(Section))Section->Destroy();
    VillageDefenseParts.Reset();
}

void ATemperateHillsWorld::RefreshVillageGateStairs(const AVillageDefenseStairs* Arriving)
{
    using namespace TemperateVillagePerimeter;
    if(!HasAuthority() || IsActorBeingDestroyed() || !HasVillageHighWall() || VillageDefenseParts.IsEmpty())return;
    const FStairShape& Shape=StairShape();
    if(Shape.Boxes.IsEmpty())return;
    for(int32 Side:{-1,1})
    {
        const bool bWest=Side<0;
        const int32 Id=bWest?51000:51001;
        const FTransform Gate=GatePlacement(*this,Side);
        if(Arriving && !OverlapsStair(Shape,VillageWallStairs::GatehouseFlight(Gate,bWest,true),Arriving->GetActorTransform()) &&
            !OverlapsStair(Shape,VillageWallStairs::GatehouseFlight(Gate,bWest,false),Arriving->GetActorTransform()))continue;
        const TOptional<FTransform> Site=AvailableFlight(*this,Gate,bWest,Shape,Arriving);
        const int32 Index=VillageDefenseParts.IndexOfByPredicate([Id](const auto& Piece)
            {return IsValid(Piece) && Piece->GetSectionId()==Id;});
        if(Index!=INDEX_NONE)
        {
            auto* Existing=VillageDefenseParts[Index].Get();
            if(Site.IsSet() && Existing->GetActorTransform().Equals(Site.GetValue(),.01))continue;
            Existing->Destroy();
            VillageDefenseParts.RemoveAtSwap(Index);
        }
        // Player-built flights keep their GUID and health, even if broken. Use
        // the other pier if needed, and reserve both player sites when both are occupied.
        if(!Site.IsSet())continue;
        if(PawnInStair(*GetWorld(),Shape,Site.GetValue()) &&
            GetWorld()->GetSubsystem<UVillageDefenseState>()->Restore(WorldId,Id,1200.f)>0.f)
        {
            // A player may be standing inside a just dismantled or previously broken flight.
            if(!GetWorldTimerManager().IsTimerActive(VillageGateStairRetry))
                GetWorldTimerManager().SetTimer(VillageGateStairRetry,FTimerDelegate::CreateWeakLambda(this,
                    [this](){VillageGateStairRetry.Invalidate();RefreshVillageGateStairs();}),.5f,false);
            continue;
        }
        auto* Stair=GetWorld()->SpawnActorDeferred<AVillageDefenseStairs>(AVillageDefenseStairs::StaticClass(),
            Site.GetValue(),this,nullptr,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
        if(Stair)
        {
            Stair->Initialize(this,Id,AVillageDefenseStairs::StairMeshPath(),1200.f);
            Stair->FinishSpawning(Site.GetValue());
            VillageDefenseParts.Add(Stair);
        }
    }
}

void ATemperateHillsWorld::BuildVillagePerimeter()
{
    using namespace TemperateVillagePerimeter;
    RefreshVillageStreetLighting();
    if(!VillageSite.bPlaced||!VillageSite.bHilltop)return;
    const bool High=HasVillageHighWall();
    const auto Pieces=Layout(VillageSite,Seed,bVillageWallRepaired,High);
    TMap<FName,UStaticMesh*> Meshes;
    // Preloaded alongside chapel assets. Never synchronously load in a replication callback.
    if(!High)for(const auto& Piece:Pieces)
    {
        auto* Mesh=Cast<UStaticMesh>(MeshPath(Piece.Role).ResolveObject());
        if(!Mesh){UE_LOG(LogTemp,Warning,TEXT("HILLS_PERIMETER waiting for %s"),Piece.Role);return;}
        Meshes.Add(FName(Piece.Role),Mesh);
    }
    if(HasAuthority())
        SiegeRanks=GetWorld()->GetSubsystem<UVillageDefenseState>()->SelectGeneration(WorldId,VillageDefenseGeneration);
    ClearVillagePerimeter();
    TMap<FName,UInstancedStaticMeshComponent*> Groups;
    int32 SectionId=0;
    for(const auto& Piece:Pieces)
    {
        if(!Piece.Rubble)
        {
            if(HasAuthority())
            {
                const auto T=Placement(Piece,*this,High);
                UClass* Class=High?AHighVillageWall::StaticClass():AVillageDefenseSection::StaticClass();
                auto* Section=GetWorld()->SpawnActorDeferred<AVillageDefenseSection>(Class,T,this,nullptr,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
                // High-wall health belongs to this layout station across reloads.
                // These IDs retain the order already written by existing high-wall saves.
                if(High)CastChecked<AHighVillageWall>(Section)->InitializeHighWall(this,40000+Piece.WallStation);
                else Section->Initialize(this,SectionId+(bVillageWallRepaired?0:20000),MeshPath(Piece.Role),bVillageWallRepaired?(Piece.Pier?1600.f:1200.f):(Piece.Pier?500.f:350.f));
                UGameplayStatics::FinishSpawningActor(Section,T);VillageDefenseParts.Add(Section);
            }
            ++SectionId;continue;
        }
        auto*& Part=Groups.FindOrAdd(FName(Piece.Role));
        if(!Part)
        {
            Part=NewObject<UInstancedStaticMeshComponent>(this);
            AddInstanceComponent(Part);Part->SetupAttachment(RootComponent);
            Part->SetMobility(EComponentMobility::Movable);
            Part->SetStaticMesh(Meshes.FindChecked(FName(Piece.Role)));
            Part->SetCollisionProfileName(Piece.Rubble?TEXT("NoCollision"):TEXT("BlockAll"));
            Part->SetGenerateOverlapEvents(false);Part->SetCanEverAffectNavigation(!Piece.Rubble);
            Part->SetReceivesDecals(false);Part->ComponentTags.Add(TEXT("HillsVillagePerimeter"));
            Part->RegisterComponent();VillageWallParts.Add(Part);
        }
        Part->AddInstance(Placement(Piece,*this),true);
    }
    if(bVillageWallRepaired&&HasAuthority())for(int32 Side:{-1,1})
    {
        const FTransform T=GatePlacement(*this,Side);
        if(High)
        {
            auto* Gate=GetWorld()->SpawnActorDeferred<AHighVillageGate>(AHighVillageGate::StaticClass(),T,this,nullptr,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
            Gate->InitializeHighGate(this,Side<0?50000:50001,Side<0);
            UGameplayStatics::FinishSpawningActor(Gate,T);VillageDefenseParts.Add(Gate);
            continue;
        }
        auto* Gate=GetWorld()->SpawnActorDeferred<AVillageDefenseGate>(AVillageDefenseGate::StaticClass(),T,this,nullptr,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
        Gate->InitializeGate(this,Side<0?10000:10001,Side<0);
        UGameplayStatics::FinishSpawningActor(Gate,T);VillageDefenseParts.Add(Gate);
    }
    if(High && HasAuthority())RefreshVillageGateStairs();
    UE_LOG(LogTemp,Display,TEXT("HILLS_PERIMETER seed=%d repaired=%d instances=%d groups=%d"),Seed,bVillageWallRepaired,Pieces.Num(),Groups.Num());
}

void ATemperateHillsWorld::OnRep_VillageWall()
{BuildVillagePerimeter();}

bool ATemperateHillsWorld::CompleteVillageHighWallUpgrade(FText& FailureReason)
{
    FailureReason=FText::GetEmpty();
    if(!HasAuthority()||!WorldId.IsValid()||Slot.IsEmpty()||!VillageSite.bPlaced||!VillageSite.bHilltop||!IsVillageWallRepaired())
    {
        FailureReason=FText::FromString(TEXT("需要先修复村庄围墙。"));
        return false;
    }
    if(HasVillageHighWall())return true;

    using namespace TemperateVillagePerimeter;
    auto Occupied=[this](const FTransform& Pose,const FVector& Center,const FVector& Extent)
    {
        return GetWorld()->OverlapAnyTestByObjectType(Pose.TransformPositionNoScale(Center),Pose.GetRotation(),
            FCollisionObjectQueryParams(ECC_Pawn),FCollisionShape::MakeBox(Extent));
    };
    for(const FPiece& Piece:Layout(VillageSite,Seed,true,true))
    {
        if(Occupied(Placement(Piece,*this,true),FVector(0,0,240.),FVector(Piece.Length*.5,100.,240.)))
        {
            FailureReason=FText::FromString(TEXT("墙边有人或动物，请让开高墙施工位置。"));
            return false;
        }
    }
    for(int32 Side:{-1,1})
    {
        const FTransform Gate=GatePlacement(*this,Side);
        const FStairShape& Shape=StairShape();
        if(Shape.Boxes.IsEmpty())
        {
            FailureReason=FText::FromString(TEXT("门楼石阶正在加载，请稍后再升级。"));
            return false;
        }
        const TOptional<FTransform> Stair=AvailableFlight(*this,Gate,Side<0,Shape);
        if(Stair.IsSet() && (!VillageWallStairs::HasClearStairEntrance(*GetWorld(),Stair.GetValue()) ||
            !VillageDefenseFootprint::IsClear(*GetWorld(),Shape,Stair.GetValue(),nullptr)))
        {
            FailureReason=FText::FromString(TEXT("请腾出门楼内侧石阶和阶前通道，移开占位的构件、人员和动物。"));
            return false;
        }
        const auto* Portal=Cast<UStaticMesh>(AHighVillageGate::PlacedPortalMeshPath(Side<0).ResolveObject());
        const auto* Grille=Cast<UStaticMesh>(AHighVillageGate::PlacedGrilleMeshPath(Side<0).ResolveObject());
        const auto* Body=Portal ? Portal->GetBodySetup() : nullptr;
        if(!Grille || !Body || Body->AggGeom.BoxElems.IsEmpty())
        {
            FailureReason=FText::FromString(TEXT("门楼构件正在加载，请稍后再升级。"));
            return false;
        }
        // The new grille starts closed. Its opening and the gallery's actual collision
        // occupy separate volumes, leaving the yard beneath the gallery available.
        const FBox ClosedGrille=Grille->GetBoundingBox();
        bool bOccupied=Occupied(Gate,ClosedGrille.GetCenter(),ClosedGrille.GetExtent());
        const FBox Bounds=Portal->GetBoundingBox();
        if(!bOccupied && Occupied(Gate,Bounds.GetCenter(),Bounds.GetExtent()))
        {
            for(const FKBoxElem& Box:Body->AggGeom.BoxElems)
            {
                const FTransform Hull=Box.GetTransform()*Gate;
                if(Occupied(Hull,FVector::ZeroVector,FVector(Box.X,Box.Y,Box.Z)*.5))
                {
                    bOccupied=true;
                    break;
                }
            }
        }
        if(bOccupied)
        {
            FailureReason=FText::FromString(TEXT("请让人员和动物离开城门通道及门楼施工位置。"));
            return false;
        }
    }
    return CommitVillagePlanRepair(UTemperateHillsSave::HighWallPlan,7,TEXT("城防升级未能保存，请重试。"),FailureReason);
}

bool ATemperateHillsWorld::CompleteVillageWallRepair(FText& FailureReason)
{
    FailureReason=FText::GetEmpty();
    if(!HasAuthority()||Slot.IsEmpty()||!WorldId.IsValid()||!VillageSite.bPlaced||!VillageSite.bHilltop)
    {FailureReason=FText::FromString(TEXT("村庄尚未准备好修复围墙。"));return false;}
    if(bVillageWallRepaired)return true;
    using namespace TemperateVillagePerimeter;
    for(const auto& Piece:Layout(VillageSite,Seed,true))
    {
        const FTransform T=Placement(Piece,*this);
        const double HalfX=Piece.Pier?42.:Piece.Length*.5,HalfY=Piece.Pier?42.:33.;
        const FVector Center=T.GetLocation()+FVector(0,0,Piece.Pier?125.:104.);
        if(GetWorld()->OverlapAnyTestByObjectType(Center,T.GetRotation(),FCollisionObjectQueryParams(ECC_Pawn),
            FCollisionShape::MakeBox(FVector(HalfX,HalfY,Piece.Pier?125.:104.))))
        {FailureReason=FText::FromString(TEXT("围墙缺口处有人或动物，请让开后完成修复。"));return false;}
    }
    for(int32 Side:{-1,1})
    {
        const auto P=VillageSite.World(Side*VillageSite.WallHalfSize().X,VillageSite.GateY(Side));
        const double Yaw=FMath::RadiansToDegrees(FMath::Atan2(VillageSite.Axis.Y,VillageSite.Axis.X))+Side*90.;
        if(GetWorld()->OverlapAnyTestByObjectType(FVector(P,Height(P.X,P.Y)+115.),FRotator(0,Yaw,0).Quaternion(),
            FCollisionObjectQueryParams(ECC_Pawn),FCollisionShape::MakeBox(FVector(Side<0?435.:335.,25.,105.))))
        {FailureReason=FText::FromString(TEXT("村口有人或动物，请让开木门位置后完成修复。"));return false;}
    }
    auto* Save=Cast<UTemperateHillsSave>(UGameplayStatics::LoadGameFromSlot(Slot,0));
    if(!Save||Save->WorldId!=WorldId||Save->Seed!=Seed||Save->Version>6||Save->VillagePlanVersion>UTemperateHillsSave::CurrentVillagePlanVersion)
    {FailureReason=FText::FromString(TEXT("无法读取当前丘陵的修复存档。"));return false;}
    Save->Version=6;Save->bVillageWallRepaired=true;
    Save->VillagePlansUnlocked=Save->SavedVillagePlans()|1;
    Save->VillagePlanVersion=FMath::Max(2,Save->VillagePlanVersion);
    // Commit once before changing collision or publishing the quest's completion.
    if(!UGameplayStatics::SaveGameToSlot(Save,Slot,0))
    {FailureReason=FText::FromString(TEXT("围墙修复未能保存，请重试。"));return false;}
    VillagePlansUnlocked=Save->VillagePlansUnlocked;
    bVillageWallRepaired=true;BuildVillagePerimeter();ForceNetUpdate();
    return true;
}
