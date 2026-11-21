// Source/FPSGAME/Building/VoxelBuildTarget.cpp
// Merge each excerpt at the named target and scope. Line numbers locate the 2026-11-21 production source.

// Lines 13-13 | file scope
#include "VoxelBuildGrounding.h"

// Lines 50-51 | file scope
        const FCollisionQueryParams& Query,FHitResult& OutHit,FVoxelBuildKey& OutCell,
        const FVoxelBuildPrefab* Defense,int32 SocketTurns,double Reach)

// Lines 66-78 | file scope
                if(!World->LineTraceMultiByChannel(ProbeScratch,Start,Start+ProbeDirection*Reach,ECC_Visibility,Query))continue;
                for(const FHitResult& Probe:ProbeScratch)
                {
                    if(Defense)
                    {
                        VillageWallStairs::FDock Socket;
                        if(!Probe.bBlockingHit||!VillageWallStairs::MakeDock(Defense->Id,Defense->Footprint,
                            Probe.GetActor(),Probe.ImpactPoint,SocketTurns,Socket))continue;
                    }
                    else if(!BuildWorld->ResolveHit(Probe,OutCell)&&!BuildWorld->ResolvePrefabSurfaceCell(Probe,OutCell))continue;
                    OutHit=Probe;
                    return true;
                }

// Lines 113-118 | void UVoxelBuildComponent::UpdateTarget()
    for(const FHitResult& RayHit:AimScratch)
    {
        for(AActor* Actor=RayHit.GetActor();Actor;Actor=Actor->GetAttachParentActor())
            if(auto* Piece=Cast<AVoxelBuildPrefabActor>(Actor)){AimedPrefab=Piece;break;}
        if(AimedPrefab.IsValid()||RayHit.bBlockingHit)break;
    }

// Lines 121-121 | void UVoxelBuildComponent::UpdateTarget()
    const bool bDefense=Prefab&&VillageWallStairs::CanDock(Prefab->Id);

// Lines 126-126 | void UVoxelBuildComponent::UpdateTarget()
        if(bDefense&&AimScratch.Last().bBlockingHit)AimIndex=AimScratch.Num()-1;

// Lines 144-152 | void UVoxelBuildComponent::UpdateTarget()
    // Never reach past a closer obstruction to capture a castle joint. A deliberate hit
    // on the floor keeps its grid placement, even when a wall is beside the crosshair.
    const bool bAimedAtWallMount=Prefab&&Prefab->Mount==EVoxelPrefabMount::Wall&&HasHit&&Cast<AVillageDefenseSection>(Hit.GetActor());
    const bool bTryAssist=bDefense
        ? (!HasHit || (!VillageWallStairs::ResolveTarget(Hit.GetActor()) && FMath::Abs(Hit.ImpactNormal.Z)<.5))
        : !BuildingHit&&!bAimedAtWallMount;
    const double AssistReach=bDefense&&HasHit?FMath::Min(600.,FVector::Distance(Start,Hit.ImpactPoint)+1.):600.;
    if(bSnapEnabled&&bTryAssist&&TrySnapAssist(GetWorld(),BuildWorld,Start,Direction,Query,Hit,HitCell,
        bDefense?Prefab:nullptr,ComponentYaw,AssistReach))

// Lines 473-478 | int32 UVoxelBuildComponent::PlannedGroundYaw() const
int32 UVoxelBuildComponent::PlannedGroundYaw() const
{
    return VillageBuildDefense::IsVillageRecipe(SelectedComponent)&&!DefenseDockPose.IsSet()?GroundYawDegrees:INDEX_NONE;
}

void UVoxelBuildComponent::UpdatePrefabTarget(bool bHit)

// Lines 481-482 | void UVoxelBuildComponent::UpdatePrefabTarget(bool bHit)
    DefenseDockTarget.Reset();
    DefenseDockPose.Reset();

// Lines 487-487 | void UVoxelBuildComponent::UpdatePrefabTarget(bool bHit)
    const FIntVector Footprint=AVoxelBuildPrefabActor::RotatedFootprint(Prefab->Footprint,PrefabPlanYaw);

// Lines 497-546 | void UVoxelBuildComponent::UpdatePrefabTarget(bool bHit)
    FIntVector Cell;
    bool bSurfaceBacked=false;
    const auto* Target=bSnapEnabled&&VillageWallStairs::CanDock(Prefab->Id)
        ? VillageWallStairs::ResolveTarget(Hit.GetActor()):nullptr;
    if(Target)
    {
        VillageWallStairs::FDock Dock;
        // The side joint opens the entrance along a wall or into the gate courtyard.
        const bool bStairs=Prefab->Id==VillageWallStairs::Id;
        const int32 FirstSocket=bStairs?1:ComponentYaw;
        if(!VillageWallStairs::MakeDock(Prefab->Id,Prefab->Footprint,Target,Hit.ImpactPoint,FirstSocket,Dock))
        {
            PrefabCell=AVoxelBuildWorld::ToCell(Hit.ImpactPoint)-FIntVector(Footprint.X/2,Footprint.Y/2,0);
            if(Target->GetHealth()<=0.f)PrefabMessage=TEXT("修复受损的城防后可吸附");
            else if(Prefab->Id==VillageWallStairs::Id&&Target->IsA<AHighVillageGate>())
                PrefabMessage=TEXT("请瞄准门楼内侧的平台入口");
            else PrefabMessage=TEXT("此处没有匹配的接口 · F 切换地面放置");
            TargetMessage=PrefabMessage;
            return;
        }
        auto CanUse=[&](const VillageWallStairs::FDock& Option,FString& Reason)
        {
            return BuildWorld->CanPlacePrefab(Prefab->Id,Option.Anchor,Option.Yaw,Reason,false,true,Option.Target);
        };
        bPrefabValid=CanUse(Dock,PrefabMessage);
        const bool bWheelAlternate=(ComponentYaw&1)!=0;
        if(bStairs && (!bPrefabValid || bWheelAlternate))
        {
            VillageWallStairs::FDock Other;
            if(VillageWallStairs::MakeDock(Prefab->Id,Prefab->Footprint,Target,Hit.ImpactPoint,0,Other))
            {
                FString OtherMessage;
                const bool bOtherValid=CanUse(Other,OtherMessage);
                const bool bPreferOther=!bPrefabValid && bOtherValid;
                if(bWheelAlternate!=bPreferOther)
                {
                    Dock=Other;
                    PrefabMessage=MoveTemp(OtherMessage);
                    bPrefabValid=bOtherValid;
                }
            }
        }
        PrefabCell=Dock.Anchor;
        PrefabPlanYaw=Dock.Yaw;
        DefenseDockPose=Dock.Pose;
        DefenseDockTarget=Dock.Target;
        DefenseDockSocket=Dock.Socket;
        bCanPlace=bPrefabValid;
        TargetMessage=PrefabMessage;
        return;

// Lines 551-552 | void UVoxelBuildComponent::UpdatePrefabTarget(bool bHit)
        FHitResult Backing=Hit;
        if(!VoxelGrounding::ResolveMountingSurface(Backing))

// Lines 557-562 | void UVoxelBuildComponent::UpdatePrefabTarget(bool bHit)
            TargetMessage=PrefabMessage;
            return;
        }
        const FVector Normal2D=Backing.ImpactNormal.GetSafeNormal2D();
        PrefabPlanYaw=((FMath::RoundToInt(FMath::Atan2(Normal2D.Y,Normal2D.X)/(PI/2))%4)+4)%4;
        const FIntVector Size=AVoxelBuildPrefabActor::RotatedFootprint(Prefab->Footprint,PrefabPlanYaw);

// Lines 564-570 | void UVoxelBuildComponent::UpdatePrefabTarget(bool bHit)
        Cell=AVoxelBuildWorld::ToCell(Backing.ImpactPoint-FVector(Size)*10.);
        const int32 Axis=PrefabPlanYaw&1;
        const double Plane=Backing.ImpactPoint[Axis];
        // The two negative-facing sides seat the far face of the fixture on the wall.
        // Pick the same cardinal axis as the mesh, including on diagonal masonry.
        Cell[Axis]=PrefabPlanYaw<2?FMath::CeilToInt((Plane-.5)/20.):
            FMath::FloorToInt((Plane+.5)/20.)-Size[Axis];

// Lines 581-582 | void UVoxelBuildComponent::UpdatePrefabTarget(bool bHit)
    bPrefabValid=BuildWorld->CanPlacePrefab(Prefab->Id,Cell,PrefabPlanYaw,PrefabMessage,bSurfaceBacked,
        DefenseDockPose.IsSet(),DefenseDockTarget.Get(),nullptr,PlannedGroundYaw());
