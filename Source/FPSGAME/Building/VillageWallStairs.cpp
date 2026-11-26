#include "VillageWallStairs.h"
#include "VillageBuildDefense.h"
#include "VillageGateReplacement.h"
#include "VoxelBuildPrefabActor.h"
#include "VoxelBuildGrounding.h"
#include "VoxelBuildWorld.h"
#include "../WorldGeneration/HighVillageDefense.h"
#include "../WorldGeneration/VillageDefenseStairs.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/OverlapResult.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"

namespace VillageWallStairs
{
    namespace
    {
        const FIntVector StairFootprint(16,28,18);
        // Native art coordinates in centimetres. Both joins touch a 360 cm walking surface.
        const FVector WallWalk(0.,100.,360.);
        const FVector StairExit(80.,-280.,360.);
        const FVector StairSide(160.,-200.,360.);
        constexpr double WallHalfLength=150.;
        constexpr double WallHalfDepth=100.;
        constexpr double EastGateHalfWidth=VillageGateReplacement::PlacedPortalHalfWidth;
        constexpr double WestGateHalfWidth=534.;
        // Keep the original wall centreline and saved edge addresses. The new
        // portal gallery opens across the full wall-walk width at each pier.
        constexpr double GateWallLineY=VillageGateReplacement::PlacedPortalWallY;

        enum class EPiece { Wall, Gate, Tower, Stairs };
        // 0..7 are the original wall-end addresses. The two extra addresses mate
        // either tower doorway to the open, courtyard-facing edge of a wall walk.
        constexpr int32 WalkEdgeSocket=8;
        constexpr int32 SocketCount=WalkEdgeSocket+2;
        struct FSite
        {
            EPiece Piece;
            double HalfWidth;
        };

        FSite NewSite(FName PieceId)
        {
            if(PieceId==VillageBuildDefense::StoneGate)return {EPiece::Gate,EastGateHalfWidth};
            if(PieceId==VillageBuildDefense::HighTower)return {EPiece::Tower,460.};
            if(PieceId==Id)return {EPiece::Stairs,160.};
            return {EPiece::Wall,WallHalfLength};
        }

        FSite ExistingSite(const AVillageDefenseSection& Section)
        {
            if(const auto* Holder=Cast<AVoxelBuildPrefabActor>(Section.GetAttachParentActor());
                Holder && Holder->PrefabId()==VillageBuildDefense::HighTower)return NewSite(Holder->PrefabId());
            if(const auto* Gate=Cast<AHighVillageGate>(&Section))
            {
                const UStaticMesh* Frame=Gate->GetStonePortal()->GetStaticMesh();
                static const FName WestFrame(TEXT("SM_HighPortalGalleryWest"));
                const bool bWest=Frame?Frame->GetFName()==WestFrame:Gate->GetSectionId()==50000;
                return {EPiece::Gate,bWest?WestGateHalfWidth:EastGateHalfWidth};
            }
            return NewSite(Section.IsA<AVillageDefenseStairs>()?Id:VillageBuildDefense::HighWall);
        }

        int32 Wrap(int32 Turns,int32 Count)
        {
            return (Turns%Count+Count)%Count;
        }

        FIntVector CenterOffset(FIntVector Footprint,int32 QuarterTurns)
        {
            const FIntVector Size=AVoxelBuildPrefabActor::RotatedFootprint(Footprint,QuarterTurns);
            return FIntVector(Size.X/2,Size.Y/2,0);
        }

        FVector LocalGridCenter(FSite Site,FIntVector Footprint)
        {
            // The asymmetrical east gate's origin is the sill, not the middle of its
            // bounding footprint. Derive the offset from the same free-placement rule.
            if(Site.Piece!=EPiece::Gate)return FVector::ZeroVector;
            const FVector Center(Footprint.X*10.,Footprint.Y*10.,0.);
            return Center-VillageBuildDefense::Placement(VillageBuildDefense::StoneGate,
                FIntVector::ZeroValue,Footprint,0).GetLocation();
        }

        struct FSocket
        {
            FVector Point;
            int32 Facing; // Quarter turns from local +X, pointing out of this walkable surface.
        };

        FSocket CourtyardSocket(double HalfWidth,int32 Side)
        {
            return {FVector(Side*(HalfWidth-52.),264.,360.),1};
        }

        FSocket WalkSocket(FSite Site,int32 Side)
        {
            if(Site.Piece==EPiece::Tower)return {FVector(Side*Site.HalfWidth,0.,360.),Side>0?0:2};
            if(Site.Piece==EPiece::Wall)return {WallWalk,1};
            // Retain the cantilevered landing's original socket for existing
            // player builds. The opposite pier opens onto the courtyard.
            if(Side>0)return {FVector(Site.HalfWidth+145.,87.5,360.),0};
            return CourtyardSocket(Site.HalfWidth,-1);
        }

        FSocket StairSocket(int32 Choice)
        {
            // Across the third edge the switchback extends back through the host's footprint.
            return Choice==0?FSocket{StairExit,3}:FSocket{StairSide,0};
        }

        FTransform Mate(const FTransform& Host,const FSocket& Fixed,const FSocket& Moving)
        {
            const double Yaw=Host.Rotator().Yaw+90.*(Fixed.Facing+2-Moving.Facing);
            const FQuat Rot=FRotator(0.,Yaw,0.).Quaternion();
            return FTransform(Rot,Host.TransformPosition(Fixed.Point)-Rot.RotateVector(Moving.Point));
        }

        FTransform EndJoint(const FTransform& Host,FSite Fixed,FSite Moving,int32 Side,int32 Turn)
        {
            const double LineY=Fixed.Piece==EPiece::Gate?GateWallLineY:0.;
            const FVector End=Host.TransformPosition(FVector(Side*Fixed.HalfWidth,LineY,0.));
            const double HostYaw=Host.Rotator().Yaw;
            const FQuat HostRot=FRotator(0.,HostYaw,0.).Quaternion();
            const bool bCorner=Turn%2!=0;
            const FQuat Rot=FRotator(0.,HostYaw+90.*Turn,0.).Quaternion();
            if(bCorner)
            {
                // Butt the short end to the perpendicular module's side. Meeting axis
                // centrelines instead would interpenetrate both walls by half their thickness.
                const double InnerDepth=WallHalfDepth*FMath::Abs(Host.GetScale3D().Y);
                const bool bNewWalkFacesJoint=(Turn==1)==(Side==1);
                // Meet one end against the open walking side of the other section.
                // Connecting an end directly to the crenellated side blocks the walkway.
                const FVector Offset=bNewWalkFacesJoint
                    ? FVector(Side*WallHalfDepth,Moving.HalfWidth-InnerDepth,0.)
                    : FVector(-Side*WallHalfDepth,InnerDepth+Moving.HalfWidth,0.);
                return FTransform(Rot,End+HostRot.RotateVector(Offset));
            }
            const double MovingLineY=Moving.Piece==EPiece::Gate?GateWallLineY:0.;
            const int32 MatingEnd=(Turn==0?-Side:Side);
            return FTransform(Rot,End-Rot.RotateVector(FVector(MatingEnd*Moving.HalfWidth,MovingLineY,0.)));
        }

        bool Candidate(const AVillageDefenseSection& Section,FSite Host,FSite Moving,int32 Side,int32 Turns,
            FIntVector Footprint,FDock& Out)
        {
            const FTransform& Frame=Section.GetActorTransform();
            if(Host.Piece==EPiece::Stairs && Moving.Piece==EPiece::Stairs)return false;
            if(Moving.Piece==EPiece::Stairs)
                Out.Pose=Mate(Frame,WalkSocket(Host,Side),StairSocket(Wrap(Turns,2)));
            else if(Host.Piece==EPiece::Stairs)
                Out.Pose=Mate(Frame,StairSocket(Wrap(Turns,2)),WalkSocket(Moving,Side));
            else if(Host.Piece==EPiece::Tower || Moving.Piece==EPiece::Tower)
            {
                // Match actual walking surfaces, including a generated wall's scale and yaw.
                const auto EndSocket=[](FSite Site,int32 End)
                {
                    if(Site.Piece==EPiece::Gate && End>0)return WalkSocket(Site,End);
                    const double Y=Site.Piece==EPiece::Gate?GateWallLineY:0.;
                    return FSocket{FVector(End*Site.HalfWidth,Y,360.),End>0?0:2};
                };
                const int32 MatingEnd=Wrap(Turns,2)==0?-Side:Side;
                Out.Pose=Mate(Frame,EndSocket(Host,Side),EndSocket(Moving,MatingEnd));
            }
            else
            {
                const int32 Rotation=Host.Piece==EPiece::Wall && Moving.Piece==EPiece::Wall
                    ? Wrap(Turns,4) : Wrap(Turns,2)*2;
                const bool bUseLookout=Side>0 && Rotation==2 &&
                    ((Host.Piece==EPiece::Gate && Moving.Piece==EPiece::Wall) ||
                     (Moving.Piece==EPiece::Gate && Host.Piece==EPiece::Wall));
                Out.Pose=bUseLookout?Mate(Frame,WalkSocket(Host,Side),WalkSocket(Moving,Side))
                    :EndJoint(Frame,Host,Moving,Side,Rotation);
            }
            Out.Yaw=Wrap(FMath::RoundToInt(Out.Pose.Rotator().Yaw/90.),4);
            const FVector GridCenter=Out.Pose.TransformPosition(LocalGridCenter(Moving,Footprint));
            Out.Anchor=AVoxelBuildWorld::ToCell(GridCenter)-CenterOffset(Footprint,Out.Yaw);
            Out.Socket=(Side>0?4:0)+Wrap(Turns,4);
            return true;
        }

        bool IsTowerWallPair(FSite Host,FSite Moving)
        {
            return (Host.Piece==EPiece::Wall && Moving.Piece==EPiece::Tower)
                || (Host.Piece==EPiece::Tower && Moving.Piece==EPiece::Wall);
        }

        bool SocketCandidate(AVillageDefenseSection& Target,FSite Host,FSite Moving,FIntVector Footprint,int32 Socket,FDock& Out)
        {
            if(Socket<0 || Socket>=SocketCount)return false;
            if(Socket<WalkEdgeSocket)
            {
                if(!Candidate(Target,Host,Moving,Socket<4?-1:1,Socket%4,Footprint,Out))return false;
            }
            else
            {
                if(!IsTowerWallPair(Host,Moving))return false;
                const int32 DoorSide=Socket==WalkEdgeSocket?-1:1;
                Out.Pose=Mate(Target.GetActorTransform(),WalkSocket(Host,DoorSide),WalkSocket(Moving,DoorSide));
                Out.Yaw=Wrap(FMath::RoundToInt(Out.Pose.Rotator().Yaw/90.),4);
                Out.Anchor=AVoxelBuildWorld::ToCell(Out.Pose.GetLocation())-CenterOffset(Footprint,Out.Yaw);
                Out.Socket=Socket;
            }
            Out.Target=&Target;
            return true;
        }

        bool MatchAddress(AVillageDefenseSection* Target,FName PieceId,FIntVector Footprint,FIntVector Anchor,int32 Yaw,FDock& Out)
        {
            if(!Target || Target->IsActorBeingDestroyed() || Target->GetHealth()<=0.f)return false;
            const FSite Host=ExistingSite(*Target),Moving=NewSite(PieceId);
            for(int32 Socket=0;Socket<SocketCount;++Socket)
            {
                FDock Dock;
                if(SocketCandidate(*Target,Host,Moving,Footprint,Socket,Dock)&&Dock.Anchor==Anchor && Dock.Yaw==Yaw)
                {
                    Out=Dock;
                    return true;
                }
            }
            return false;
        }
    }

    bool CanDock(FName PieceId)
    {
        return PieceId==Id || PieceId==VillageBuildDefense::HighTower || PieceId==VillageBuildDefense::HighWall || PieceId==VillageBuildDefense::StoneGate;
    }

    FTransform GatehouseFlight(const FTransform& Gate,bool bWest,bool bRightPier)
    {
        // At the right pier the flight runs parallel to the wall, away from the arch.
        // The low approach opens toward the road, five metres inside the courtyard.
        const double Width=bWest?WestGateHalfWidth:EastGateHalfWidth;
        return Mate(Gate,CourtyardSocket(Width,bRightPier?1:-1),StairSocket(bRightPier?1:0));
    }

    FBox EntranceBounds()
    {
        // The first riser is at (-80,-120). Leave a person-wide approach on grade;
        // the upper landing occupies the other lane, at positive X.
        return FBox::BuildAABB(FVector(-80.,-190.,107.),FVector(34.,69.,86.));
    }

    bool HasClearStairEntrance(UWorld& World,const FTransform& Stair)
    {
        const FBox Entry=EntranceBounds();
        TArray<FOverlapResult> Hits;
        World.OverlapMultiByChannel(Hits,Stair.TransformPosition(Entry.GetCenter()),
            Stair.GetRotation(),ECC_Pawn,FCollisionShape::MakeBox(Entry.GetExtent()),
            FCollisionQueryParams(SCENE_QUERY_STAT(VillageStairEntrance),false));
        for(const FOverlapResult& Hit:Hits)
            if(Hit.bBlockingHit && (!Cast<APawn>(Hit.GetActor()) || Cast<AVillageDefenseSection>(Hit.GetActor())))
                return false;
        return true;
    }

    AVillageDefenseSection* ResolveTarget(const AActor* Actor)
    {
        for(auto* Node=const_cast<AActor*>(Actor);IsValid(Node);Node=Node->GetAttachParentActor())
        {
            if(auto* Section=Cast<AVillageDefenseSection>(Node))
            {
                if(Section->IsGateCut())return nullptr;
                if(const auto* Wrapper=Cast<AVoxelBuildPrefabActor>(Node->GetAttachParentActor()))
                {
                    if(Wrapper->IsFalling())return nullptr;
                    if(Wrapper->PrefabId()==VillageBuildDefense::HighTower)return Section;
                }
                if(Section->IsA<AHighVillageWall>() || Section->IsA<AHighVillageGate>() || Section->IsA<AVillageDefenseStairs>())
                    return Section;
            }
            if(const auto* Wrapper=Cast<AVoxelBuildPrefabActor>(Node))
            {
                if(!Wrapper->IsFalling() && CanDock(Wrapper->PrefabId()))
                    {
                        auto* Part=Cast<AVillageDefenseSection>(Wrapper->Logic());
                        return Part && !Part->IsGateCut()?Part:nullptr;
                    }
                return nullptr;
            }
        }
        return nullptr;
    }

    bool MakeDock(FName PieceId,FIntVector Footprint,const AActor* Actor,const FVector& AimPoint,int32 WheelTurns,FDock& Out)
    {
        auto* Target=ResolveTarget(Actor);
        if(!Target)return false;
        const FVector Local=Target->GetActorTransform().InverseTransformPosition(AimPoint);
        return MakeDockAtSocket(PieceId,Footprint,Target,(Local.X<0.?0:4)+Wrap(WheelTurns,4),Out);
    }

    bool MakeDockAtSocket(FName PieceId,FIntVector Footprint,const AActor* Actor,int32 Socket,FDock& Out)
    {
        auto* Target=ResolveTarget(Actor);
        if(!CanDock(PieceId)||!Target||Target->IsActorBeingDestroyed()||Target->GetHealth()<=0.f)return false;
        return SocketCandidate(*Target,ExistingSite(*Target),NewSite(PieceId),Footprint,Socket,Out);
    }

    bool PickNearbyWallDock(const AVoxelBuildWorld& Builder,FName PieceId,FIntVector Footprint,const FHitResult& Hit,
        int32 WheelTurns,FDock& Out,bool& bCanPlace,FString& Reason)
    {
        const bool Tower=PieceId==VillageBuildDefense::HighTower;
        const bool Stair=PieceId==Id;
        if(!Tower && !Stair && PieceId!=VillageBuildDefense::HighWall)return false;
        const FSite Moving=NewSite(PieceId);
        AVillageDefenseSection* Direct=ResolveTarget(Hit.GetActor());
        TArray<AVillageDefenseSection*,TInlineAllocator<12>> Hosts;
        if(Direct)Hosts.Add(Direct);
        else
        {
            const bool VoxelFloor=Hit.GetActor()==&Builder && Hit.bBlockingHit && Hit.ImpactNormal.Z>=VoxelGrounding::MinimumNormalZ;
            if(!VoxelFloor && !VoxelGrounding::IsSurface(Hit))return false;
            // The cursor normally sits under the middle of the ghost. At first contact
            // the tower's door is already 4.60 m away from that point.
            FCollisionObjectQueryParams Types(ECC_WorldStatic);
            Types.AddObjectTypesToQuery(ECC_WorldDynamic);
            Types.AddObjectTypesToQuery(ECC_Pawn);
            TArray<FOverlapResult> Nearby;
            Builder.GetWorld()->OverlapMultiByObjectType(Nearby,Hit.ImpactPoint+FVector(0.,0.,100.),FQuat::Identity,Types,
                FCollisionShape::MakeSphere((Stair?280.:Moving.HalfWidth)+200.),FCollisionQueryParams(SCENE_QUERY_STAT(TowerWallSnap)));
            for(const FOverlapResult& Entry:Nearby)
                if(auto* Target=ResolveTarget(Entry.GetActor()))Hosts.AddUnique(Target);
        }

        struct FChoice { FDock Dock; double Score; };
        TArray<FChoice,TInlineAllocator<12>> Choices;
        for(auto* HostActor:Hosts)
        {
            const FSite Host=ExistingSite(*HostActor);
            if(!(IsTowerWallPair(Host,Moving) || (Stair && Host.Piece==EPiece::Wall)) || HostActor->GetHealth()<=0.f || HostActor->IsActorBeingDestroyed())continue;
            const FTransform& Frame=HostActor->GetActorTransform();
            auto Offer=[&](int32 Socket,const FVector& LocalJoint,double Priority)
            {
                FDock Dock;
                if(!SocketCandidate(*HostActor,Host,Moving,Footprint,Socket,Dock))return;
                const FVector Base=Dock.Pose.GetLocation();
                if(!Direct && FMath::Abs(Hit.ImpactPoint.Z-Base.Z)>180.)return;
                const FVector2D Joint(Frame.TransformPosition(LocalJoint)),Center(Base),Aim(Hit.ImpactPoint);
                const FVector2D Along=Center-Joint;
                const double T=FMath::Clamp(FVector2D::DotProduct(Aim-Joint,Along)/Along.SizeSquared(),0.,1.);
                const double Gap=(Aim-(Joint+T*Along)).Size();
                if(!Direct && Gap>150.)return;
                // Distance to the doorway-to-centre segment works both when pointing at
                // the seam and when bringing the ghost to it from open ground.
                Choices.Add({Dock,Gap+(Aim-Center).Size()*.05+Priority});
            };
            if(Stair)
            {
                const int32 Preferred=(WheelTurns&1)?0:1;
                Offer(Preferred,WallWalk,0.);
                Offer(1-Preferred,WallWalk,Direct?10000.:36.);
                continue;
            }
            for(int32 Side:{-1,1})
            {
                if(Direct && !Tower && Side!=(Frame.InverseTransformPosition(Hit.ImpactPoint).X<0.?-1:1))continue;
                const int32 EndTurn=Tower?WheelTurns:WheelTurns/2;
                const FVector End(Side*Host.HalfWidth,0.,360.);
                // A new wall can extend the doorway or run across it with its walk open to the tower.
                Offer((Side>0?4:0)+Wrap(EndTurn,4),End,!Tower && (WheelTurns&1)?50.:0.);
                if(!Tower)Offer(WalkEdgeSocket+(Side>0?1:0),End,(WheelTurns&1)?0.:50.);
            }
            if(Tower)Offer(WalkEdgeSocket+Wrap(WheelTurns,2),WallWalk,0.);
        }
        Choices.Sort([](const FChoice& A,const FChoice& B)
        {
            if(A.Score!=B.Score)return A.Score<B.Score;
            if(A.Dock.Target!=B.Dock.Target)return A.Dock.Target->GetSectionId()<B.Dock.Target->GetSectionId();
            return A.Dock.Socket<B.Dock.Socket;
        });
        for(int32 I=0;I<Choices.Num();++I)
        {
            const auto& Dock=Choices[I].Dock;
            FString Message;
            const bool Valid=Builder.CanPlacePrefab(PieceId,Dock.Anchor,Dock.Yaw,Message,false,true,Dock.Target);
            if(Valid || I==0)
            {
                Out=Dock;
                bCanPlace=Valid;
                Reason=Valid && Stair?TEXT("石阶上平台已对齐城墙步道 · 滚轮换向 · 左键放置"):Valid?(Dock.Socket>=WalkEdgeSocket?TEXT("塔门已对齐城墙内侧步道 · 左键放置"):TEXT("塔门已对齐城墙端部 · 左键放置")):MoveTemp(Message);
            }
            if(Valid)break;
        }
        return !Choices.IsEmpty();
    }

    bool FindDock(UWorld* World,FName PieceId,FIntVector Footprint,FIntVector Anchor,int32 Yaw,FDock& Out,
        const AActor* ExpectedTarget)
    {
        if(!World || !CanDock(PieceId) || Yaw<0 || Yaw>3)return false;
        if(ExpectedTarget)
            return ExpectedTarget->GetWorld()==World && MatchAddress(ResolveTarget(ExpectedTarget),PieceId,Footprint,Anchor,Yaw,Out);

        // Include the gate's two elevated courtyard landings when replaying
        // a saved connection, even when the moving piece is a complete gate.
        const FSite Moving=NewSite(PieceId);
        const double SearchRadius=(Moving.Piece==EPiece::Gate || Moving.Piece==EPiece::Tower)?820.:510.;
        const FVector ApproxOffset=FRotator(0.,Yaw*90.,0.).RotateVector(LocalGridCenter(Moving,Footprint));
        const FVector Near=AVoxelBuildWorld::CellCenter(Anchor+CenterOffset(Footprint,Yaw))-ApproxOffset+FVector(0,0,150.);
        TArray<FOverlapResult> Hits;
        FCollisionObjectQueryParams Types(ECC_WorldStatic);
        Types.AddObjectTypesToQuery(ECC_WorldDynamic);
        Types.AddObjectTypesToQuery(ECC_Pawn);
        World->OverlapMultiByObjectType(Hits,Near,FQuat::Identity,Types,FCollisionShape::MakeSphere(SearchRadius),
            FCollisionQueryParams(SCENE_QUERY_STAT(VillageDefenseDock)));
        TArray<AVillageDefenseSection*,TInlineAllocator<16>> Seen;
        for(const FOverlapResult& Hit:Hits)
        {
            auto* Target=ResolveTarget(Hit.GetActor());
            if(Target && !Seen.Contains(Target))
            {
                Seen.Add(Target);
                if(MatchAddress(Target,PieceId,Footprint,Anchor,Yaw,Out))return true;
            }
        }
        return false;
    }

    FTransform Placement(const FVoxelBuildPrefabInstance& Instance)
    {
        if(Instance.WallDockPose.IsSet())return Instance.WallDockPose.GetValue();
        return VillageBuildDefense::Placement(Instance.Id,Instance.Cell,Instance.Footprint,Instance.Yaw);
    }

    bool MakeDock(const AHighVillageWall& Wall,FTransform& WorldPose,FIntVector& Anchor,int32& QuarterTurns)
    {
        FDock Dock;
        if(!MakeDock(Id,StairFootprint,&Wall,Wall.GetActorLocation(),0,Dock))return false;
        WorldPose=Dock.Pose;Anchor=Dock.Anchor;QuarterTurns=Dock.Yaw;
        return true;
    }

    AHighVillageWall* FindDock(UWorld* World,FIntVector Anchor,int32 QuarterTurns,FTransform& OutPose)
    {
        FDock Dock;
        if(!FindDock(World,Id,StairFootprint,Anchor,QuarterTurns,Dock))return nullptr;
        auto* Wall=Cast<AHighVillageWall>(Dock.Target);
        if(Wall)OutPose=Dock.Pose;
        return Wall;
    }
}
