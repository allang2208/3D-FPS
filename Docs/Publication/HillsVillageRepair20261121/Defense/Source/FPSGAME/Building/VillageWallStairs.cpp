#include "VillageWallStairs.h"
#include "VillageBuildDefense.h"
#include "VoxelBuildPrefabActor.h"
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
        constexpr double EastGateHalfWidth=434.;
        constexpr double WestGateHalfWidth=534.;
        // Keep the original wall centreline and saved edge addresses. The new
        // portal gallery opens across the full wall-walk width at each pier.
        constexpr double GateWallLineY=63.-WallHalfDepth;

        enum class EPiece { Wall, Gate, Stairs };
        struct FSite
        {
            EPiece Piece;
            double HalfWidth;
        };

        FSite NewSite(FName PieceId)
        {
            if(PieceId==VillageBuildDefense::StoneGate)return {EPiece::Gate,EastGateHalfWidth};
            if(PieceId==Id)return {EPiece::Stairs,160.};
            return {EPiece::Wall,WallHalfLength};
        }

        FSite ExistingSite(const AVillageDefenseSection& Section)
        {
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

        bool MatchAddress(AVillageDefenseSection* Target,FName PieceId,FIntVector Footprint,FIntVector Anchor,int32 Yaw,FDock& Out)
        {
            if(!Target || Target->IsActorBeingDestroyed() || Target->GetHealth()<=0.f)return false;
            const FSite Host=ExistingSite(*Target),Moving=NewSite(PieceId);
            for(int32 Side:{-1,1})for(int32 Turn=0;Turn<4;++Turn)
            {
                FDock Dock;
                if(Candidate(*Target,Host,Moving,Side,Turn,Footprint,Dock)&&Dock.Anchor==Anchor && Dock.Yaw==Yaw)
                {
                    Dock.Target=Target;
                    Out=Dock;
                    return true;
                }
            }
            return false;
        }
    }

    bool CanDock(FName PieceId)
    {
        return PieceId==Id || PieceId==VillageBuildDefense::HighWall || PieceId==VillageBuildDefense::StoneGate;
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
                if(const auto* Wrapper=Cast<AVoxelBuildPrefabActor>(Node->GetAttachParentActor());Wrapper&&Wrapper->IsFalling())
                    return nullptr;
                if(Section->IsA<AHighVillageWall>() || Section->IsA<AHighVillageGate>() || Section->IsA<AVillageDefenseStairs>())
                    return Section;
            }
            if(const auto* Wrapper=Cast<AVoxelBuildPrefabActor>(Node))
            {
                if(!Wrapper->IsFalling() && CanDock(Wrapper->PrefabId()))
                    return Cast<AVillageDefenseSection>(Wrapper->Logic());
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
        if(!CanDock(PieceId)||Socket<0||Socket>=8||!Target||Target->IsActorBeingDestroyed()||Target->GetHealth()<=0.f)return false;
        if(!Candidate(*Target,ExistingSite(*Target),NewSite(PieceId),Socket<4?-1:1,Socket%4,Footprint,Out))return false;
        Out.Target=Target;
        return true;
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
        const double SearchRadius=Moving.Piece==EPiece::Gate?820.:510.;
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
