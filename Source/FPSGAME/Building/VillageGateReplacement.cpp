#include "VillageGateReplacement.h"
#include "VillageBuildDefense.h"
#include "VoxelBuildPrefabActor.h"
#include "VoxelBuildWorld.h"
#include "../WorldGeneration/HighVillageDefense.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "../WorldGeneration/TemperateVillageSite.h"
#include "EngineUtils.h"
#include "Engine/StaticMesh.h"
#include "Components/StaticMeshComponent.h"

namespace VillageGateReplacement
{
    AVillageDefenseSection* WallFor(FName Gate,const AActor* Actor)
    {
        if(Gate!=VillageBuildDefense::StoneGate && Gate!=VillageBuildDefense::WoodGate)return nullptr;
        const auto* Holder=Cast<AVoxelBuildPrefabActor>(Actor);
        auto* Wall=Cast<AVillageDefenseSection>(Holder?Holder->Logic():const_cast<AActor*>(Actor));
        if(Holder && Holder->IsFalling())return nullptr;
        if(!IsValid(Wall)||Wall->IsActorBeingDestroyed()||Wall->IsGateCut())return nullptr;
        if(Gate==VillageBuildDefense::StoneGate)return Cast<AHighVillageWall>(Wall);
        return Wall->IsRepairedCurtain()?Wall:nullptr;
    }

    bool Layout(FName Gate,const AActor* Target,FIntVector Footprint,FTransform& Pose,FIntVector& Anchor,int32& Yaw)
    {
        const auto* Wall=WallFor(Gate,Target);
        if(!Wall || Wall->GetHealth()<=0.f)return false;
        const FTransform Frame=Wall->GetActorTransform();
        // The generated high curtain is 67 cm inside the gate sill. Its +Y faces the village.
        const double Setback=Gate==VillageBuildDefense::StoneGate?(Wall->GetPlacedId().IsValid()?PlacedPortalWallY:67.):0.;
        Pose=FTransform(Frame.GetRotation(),Frame.TransformPosition(FVector(0.,-Setback,0.)));
        Yaw=(FMath::RoundToInt(Pose.Rotator().Yaw/90.)+4)%4;
        const FIntVector Size=AVoxelBuildPrefabActor::RotatedFootprint(Footprint,Yaw);
        // Use the same grid reference as a free gate, even when its threshold is off-centre.
        const FVector LocalOffset=FVector(Footprint.X*10.,Footprint.Y*10.,0.)-
            VillageBuildDefense::Placement(Gate,FIntVector::ZeroValue,Footprint,0).GetLocation();
        Anchor=AVoxelBuildWorld::ToCell(Pose.TransformPosition(LocalOffset))-FIntVector(Size.X/2,Size.Y/2,0);
        return true;
    }

    uint32 WallSelection(TConstArrayView<FVillageGateCut> Cuts)
    {
        // Cuts are ordered along the clicked wall. Compare identities, independent
        // of the small pose quantization difference between client and authority.
        uint32 Key=Cuts.Num();
        for(const auto& Cut:Cuts)
        {
            if(Cut.PlacedId.IsValid())
            {
                for(uint32 Word:{Cut.PlacedId.A,Cut.PlacedId.B,Cut.PlacedId.C,Cut.PlacedId.D})
                    Key=HashCombineFast(Key,Word);
            }
            else Key=HashCombineFast(Key,uint32(Cut.Section));
        }
        return Key;
    }

    static FVector2D OutsideOpening(double Mid,double Scale,double Gap)
    {
        const double Half=150.*FMath::Abs(Scale), Lo=Mid-Half, Hi=Mid+Half;
        if(Lo>=-Gap && Hi<=Gap)return FVector2D::ZeroVector;
        const bool Left=Lo < -Gap;
        const double A=((Left?Lo:Gap)-Mid)/Scale, B=((Left?-Gap:Hi)-Mid)/Scale;
        return {FMath::Clamp(FMath::Min(A,B),-150.,150.),FMath::Clamp(FMath::Max(A,B),-150.,150.)};
    }

    static const FVillageGateCut* CutFor(const AVillageDefenseSection& Wall,TConstArrayView<FVillageGateCut> Cuts)
    {
        const FGuid Id=Wall.GetPlacedId();
        for(const auto& Cut:Cuts)
            if(Id.IsValid()?Cut.PlacedId==Id:(!Cut.PlacedId.IsValid() && Cut.Section==Wall.GetSectionId()))return &Cut;
        return nullptr;
    }

    bool IntervalFor(const AVillageDefenseSection& Wall,const FVoxelBuildPrefabInstance& Gate,FVector2D& Remaining)
    {
        if(const auto* Cut=CutFor(Wall,Gate.GateCuts)){Remaining=Cut->Remaining;return true;}
        // Upgrading the village rebuilds the entire curtain, renumbers its stations and
        // moves its centreline inward. Keep a timber opening on the same outer wall line.
        if(Gate.Id!=VillageBuildDefense::WoodGate || !Gate.WallDockPose.IsSet() || Wall.GetPlacedId().IsValid() ||
            !Wall.IsA<AHighVillageWall>() || !Gate.GateCuts.ContainsByPredicate([](const auto& Cut){return !Cut.PlacedId.IsValid();}))return false;
        const FTransform& GatePose=Gate.WallDockPose.GetValue();
        const FVector Offset=GatePose.InverseTransformPosition(Wall.GetActorLocation());
        const double Axis=GatePose.GetUnitAxis(EAxis::X).Dot(Wall.GetActorForwardVector());
        if(Axis<.9999 || FMath::Abs(Offset.Y-67.)>3. || FMath::Abs(Offset.Z)>60.)return false;
        const double Scale=Axis*Wall.GetActorScale3D().X, Half=150.*Scale;
        const double Gap=AVillageDefenseGate::PlacedPostTransform(true).GetLocation().X;
        if(Half<1. || Offset.X+Half<=-Gap || Offset.X-Half>=Gap)return false;
        Remaining=OutsideOpening(Offset.X,Scale,Gap);
        return true;
    }

    FTransform Trim(const FTransform& Original,FVector2D Interval)
    {
        FTransform Part=Original;
        Part.SetLocation(Original.TransformPosition(FVector((Interval.X+Interval.Y)*.5,0,0)));
        Part.SetScale3D(Original.GetScale3D()*FVector((Interval.Y-Interval.X)/300.,1.,1.));
        return Part;
    }

    bool Collect(const AVoxelBuildWorld& Builder,const ATemperateHillsWorld& Hills,FName Gate,
        const AActor* Target,const FTransform& Pose,FOpening& Out,TArray<FTransform>* PreviewBars)
    {
        const auto* Centre=WallFor(Gate,Target);
        if(!Centre||Centre->GetOwner()!=&Hills)return false;
        const FTransform Line=Centre->GetActorTransform();
        const FVector Along=Pose.GetUnitAxis(EAxis::X), In=Line.GetUnitAxis(EAxis::Y);
        const bool Stone=Gate==VillageBuildDefense::StoneGate;
        const double StoneHalfSpan=Centre->GetPlacedId().IsValid()?PlacedPortalHalfWidth:FTemperateVillageSite::GateHalfGap(1.);
        const double Gap=Stone?StoneHalfSpan:AVillageDefenseGate::PlacedPostTransform(true).GetLocation().X;
        struct FBay { AVillageDefenseSection* Wall; AVoxelBuildPrefabActor* Holder; double Mid,Scale,Lo,Hi; };
        TArray<FBay,TInlineAllocator<8>> Bays;
        for(TActorIterator<AVillageDefenseSection> It(Builder.GetWorld());It;++It)
        {
            auto* Wall=*It;
            if(Wall->GetOwner()!=&Hills || WallFor(Gate,Wall)!=Wall)continue;
            const FVector Offset=Wall->GetActorLocation()-Line.GetLocation();
            if(FMath::Abs(Offset.Z)>23. || FMath::Abs(Offset.Dot(In))>3.)continue;
            const double Axis=Along.Dot(Wall->GetActorForwardVector());
            if(FMath::Abs(Axis)<.9999)continue;
            auto* Holder=Cast<AVoxelBuildPrefabActor>(Wall->GetAttachParentActor());
            if(Holder && (Holder->GetOwner()!=&Builder || Holder->IsFalling()))continue;
            const double Mid=Offset.Dot(Along),Scale=Axis*Wall->GetActorScale3D().X;
            const double Half=150.*FMath::Abs(Scale);
            if(2.*Half>2.*Gap || Half<1. || FMath::Abs(Mid)>Gap+Half+190.)continue;
            Bays.Add({Wall,Holder,Mid,Scale,Mid-Half,Mid+Half});
        }
        Bays.Sort([](const FBay& A,const FBay& B){return A.Mid<B.Mid;});
        int32 L=Bays.IndexOfByPredicate([Centre](const FBay& B){return B.Wall==Centre;});
        if(L==INDEX_NONE)return false;
        int32 R=L;
        // Only follow this continuous run; a separate wall behind a gap is still an obstacle.
        while(L>0 && FMath::Abs(Bays[L].Lo-Bays[L-1].Hi)<=4.)--L;
        while(R+1<Bays.Num() && FMath::Abs(Bays[R+1].Lo-Bays[R].Hi)<=4.)++R;
        for(int32 I=L;I<=R;++I)
        {
            const FBay& B=Bays[I];
            Out.Walls.Add(B.Wall);
            if(B.Holder){Out.Walls.Add(B.Holder);Out.WallAnchors.Add(B.Holder->AnchorCell());}
            if(B.Hi<=-Gap || B.Lo>=Gap)continue;
            FVillageGateCut Cut;
            Cut.PlacedId=B.Wall->GetPlacedId();
            Cut.Section=B.Wall->GetSectionId();
            Cut.Remaining=OutsideOpening(B.Mid,B.Scale,Gap);
            Out.Cuts.Add(Cut);
            if(PreviewBars && B.Wall->GetMasonry()->GetStaticMesh())
            {
                const FBox Bounds=B.Wall->GetMasonry()->GetStaticMesh()->GetBoundingBox();
                const double Lo=FMath::Max(-Gap,B.Lo), Hi=FMath::Min(Gap,B.Hi);
                const FVector Up=FVector::UpVector*(Bounds.Max.Z*B.Wall->GetActorScale3D().Z+9.);
                const FVector Base=B.Wall->GetActorLocation()+Up-Along*B.Mid;
                const FVector Scale((Hi-Lo)/100.,.23,.09);
                PreviewBars->Emplace(Pose.GetRotation(),Base+Along*((Lo+Hi)*.5),Scale);
                const FVector Cap(.09,FMath::Clamp(Bounds.GetSize().Y/100.,.32,1.1),.09);
                for(double End:{Lo,Hi})PreviewBars->Emplace(Pose.GetRotation(),Base+Along*End,Cap);
            }
        }
        return !Out.Cuts.IsEmpty() && Out.Cuts.Num()<=32;
    }
}
