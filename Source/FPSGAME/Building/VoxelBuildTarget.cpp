#include "VoxelBuildComponent.h"
#include "../Dungeons/DungeonRoomSubsystem.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "VoxelBuildDebug.h"
#include "Camera/CameraTypes.h"
#include "Camera/PlayerCameraManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "VoxelCollapseFragment.h"
#include "VoxelBuildWorld.h"
#include "VoxelBuildPalette.h"
#include "VoxelBuildPrefabActor.h"
#include "VoxelBuildGrounding.h"
#include "VillageBuildDefense.h"
#include "VillageDefenseFootprint.h"
#include "VillageGateReplacement.h"
#include "VoxelBuildWidget.h"
#include "VoxelJointStrength.h"
#include "../FPSGAMECharacter.h"
#include "../Development/DevelopmentTuningSubsystem.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelWorldInteraction.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "../WorldGeneration/HighVillageDefense.h"
#include "Components/StaticMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Engine/StaticMesh.h"
#include "Engine/GameInstance.h"
#include "Engine/Engine.h"
#include "EngineUtils.h"
#include "InputKeyEventArgs.h"
#include "InputCoreTypes.h"
#include "Kismet/GameplayStatics.h"

#include "VoxelBuildPlacementPrivate.h"
using namespace VoxelBuildPlacementPrivate;

namespace VoxelBuildPlacementPrivate
{
    // 瞄准／辅助射线的多命中暂存（文件级复用、每帧 Reset）：稳态不分配是本文件的硬要求。
    TArray<FHitResult> AimScratch;
    TArray<FHitResult> ProbeScratch;
    using FRoofSites=TArray<FIntVector,TInlineAllocator<8>>;

    FRoofSites SiegeRoofSites(FName Id,const VillageDefenseFootprint::FShape& Deck,const FTransform& Frame,
        FVector Impact,int32 Yaw,FIntVector Footprint,FIntVector Original)
    {
        FRoofSites Sites;
        const FVector Aim=Frame.InverseTransformPosition(Impact);
        const double RoofZ=Deck.Bounds.Max.Z;
        if(Aim.Z<RoofZ-28. || Aim.Z>RoofZ+150.)return Sites;
        const bool Large=Id==VillageBuildDefense::Trebuchet;
        const FBox2D Outer(FVector2D(Deck.Bounds.Min),FVector2D(Deck.Bounds.Max));
        TArray<FBox2D,TInlineAllocator<4>> Regions;
        FBox2D Opening;
        if(Large && VillageDefenseFootprint::RoofOpening(Deck,Opening))
        {
            // A long chassis may stand on the joint between two slabs beside the stairwell.
            Regions.Emplace(Outer.Min,FVector2D(Opening.Min.X,Outer.Max.Y));
            Regions.Emplace(FVector2D(Opening.Max.X,Outer.Min.Y),Outer.Max);
            Regions.Emplace(Outer.Min,FVector2D(Outer.Max.X,Opening.Min.Y));
            Regions.Emplace(FVector2D(Outer.Min.X,Opening.Max.Y),Outer.Max);
        }
        else for(const FBox& Slab:Deck.Boxes)Regions.Emplace(FVector2D(Slab.Min),FVector2D(Slab.Max));

        const FRotator Facing(0,Yaw,0);
        auto Project=[&](FBox2D Local)
        {
            const FVector2D X(Frame.InverseTransformVector(Facing.Vector()));
            const FVector2D Y(Frame.InverseTransformVector(Facing.RotateVector(FVector::RightVector)));
            const FVector2D Centre=X*Local.GetCenter().X+Y*Local.GetCenter().Y;
            const FVector2D Half=X.GetAbs()*Local.GetExtent().X+Y.GetAbs()*Local.GetExtent().Y;
            return FBox2D(Centre-Half,Centre+Half);
        };
        const FBox2D Base=Project(VillageDefenseFootprint::SiegeBase(Id));
        auto GridCentre=[&](FIntVector Site){return FVector(Site)*20.+FVector(Footprint.X*10.,Footprint.Y*10.,0.);};
        auto Offer=[&](FVector2D Min,FVector2D Max)
        {
            if(Min.X>Max.X || Min.Y>Max.Y)return;
            const FVector P=Frame.TransformPosition(FVector(FMath::Clamp(Aim.X,Min.X,Max.X),FMath::Clamp(Aim.Y,Min.Y,Max.Y),RoofZ));
            const FIntVector Site(FMath::RoundToInt(P.X/20.-Footprint.X*.5),FMath::RoundToInt(P.Y/20.-Footprint.Y*.5),
                FMath::CeilToInt((P.Z-.05)/20.));
            if(Site!=Original && FVector::DistSquared2D(GridCentre(Site),Impact)<=FMath::Square(Large?360.:200.))
                Sites.AddUnique(Site);
        };
        const FBox& Envelope=VillageDefenseFootprint::Siege(Id).Bounds;
        const FBox2D Swing=Project(FBox2D(FVector2D(Envelope.Min),FVector2D(Envelope.Max)));
        for(const FBox2D& Region:Regions)
        {
            // Keep the chassis inside the coping and off the stair lip. The server checks actual solids.
            const FVector2D NearMargin(Large && Region.Min.X>Outer.Min.X+.1?20.:48.,Large && Region.Min.Y>Outer.Min.Y+.1?20.:48.);
            const FVector2D FarMargin(Large && Region.Max.X<Outer.Max.X-.1?20.:48.,Large && Region.Max.Y<Outer.Max.Y-.1?20.:48.);
            const FVector2D Min=Region.Min+NearMargin-Base.Min,Max=Region.Max-FarMargin-Base.Max;
            Offer(Min,Max);
            if(Large)
            {
                const FVector2D InnerMin=Outer.Min+FVector2D(48.)-Swing.Min,InnerMax=Outer.Max-FVector2D(48.)-Swing.Max;
                Offer(FVector2D::Max(Min,InnerMin),FVector2D::Min(Max,InnerMax));
            }
        }
        Sites.Sort([&](const FIntVector& A,const FIntVector& B)
            {return FVector::DistSquared2D(GridCentre(A),Impact)<FVector::DistSquared2D(GridCentre(B),Impact);});
        return Sites;
    }

    /**
     * Cone aim assist for snap mode: the centre ray rarely lands exactly on a voxel face once the
     * player drifts a little, which used to drop the ghost into the air. Probe a small cone
     * (8 directions x 1.5 deg / 3 deg) and return the first voxel hit so the ghost stays glued to a
     * surface until there really is nothing snappable in view.
     */
    bool TrySnapAssist(UWorld* World,AVoxelBuildWorld* BuildWorld,const FVector& Start,const FVector& Direction,
        const FCollisionQueryParams& Query,FHitResult& OutHit,FVoxelBuildKey& OutCell,
        const FVoxelBuildPrefab* Defense,int32 SocketTurns,double Reach)
    {
        if(!World||!BuildWorld)return false;
        const FQuat Basis=FRotationMatrix::MakeFromX(Direction).ToQuat();
        for(const float Angle:{1.5f,3.f})
        {
            const float Spread=FMath::Tan(FMath::DegreesToRadians(Angle));
            for(int32 Index=0;Index<8;++Index)
            {
                const float Theta=2.f*PI*float(Index)/8.f;
                const FVector Offset=Basis.RotateVector(FVector(0.f,FMath::Cos(Theta),FMath::Sin(Theta))*Spread);
                const FVector ProbeDirection=(Direction+Offset).GetSafeNormal();
                // 2026-09-20：辅助射线同样多命中取"第一个可解析面"。摆开到占格之外的门／窗扇解析不出
                // 格子，单命中时代 16 条辅助射线会全部白打在它身上原路返回——锥内有墙也"失灵"。
                ProbeScratch.Reset();
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
            }
        }
        return false;
    }
    // Cells dropped from the current plan because the local player's body is there (see
    // ClipLocalPlayerCells). File scope keeps the fix hot-patchable; there is one local builder.
    int32 ClippedPlayerCells=0;
}

void UVoxelBuildComponent::UpdateTarget()
{
    PlacementMaterial=SelectedMaterial;bPlacementSnap=bSnapEnabled;bPlacementContinued=false;
    // The gold snapped-neighbour highlight is refreshed only by the snapped branch below. Only the
    // visibility is lowered here: the instance buffer and its signature cache stay, so the steady
    // state really is "rebuild only when the touching blocks change".
    if(auto* Edges=FindAimEdge(PreviewActor))Edges->SetVisibility(false);
    auto* PC=Cast<APlayerController>(GetOwner());
    if(!PC||!PC->PlayerCameraManager||!BuildWorld)return;
    FVector Start,Direction;
    const bool Survey=IsVillageCameraPlacing();
    if(Survey && bSnapEnabled && VillageBuildDefense::IsVillageRecipe(SelectedComponent))
    {
        // Bound the spatial search and compound clearance checks during edge scrolling.
        // Rotation, a new selection and a click already invalidate this timer.
        const double Now=GetWorld()->GetTimeSeconds();
        if(Now<TargetUpdateAt)return;
        TargetUpdateAt=Now+.04;
    }
    if(Survey)
    {
        if(!VillageCursorRay(Start,Direction))
        {
            Hit=FHitResult();AimedPrefab.Reset();Removal.Reset();
            UpdatePrefabTarget(false);UpdatePrefabPreview();return;
        }
    }
    else
    {
        FRotator AimRotation;
        ColdSteelWorldInteraction::GetReachViewPoint(PC,Start,AimRotation);
        Direction=AimRotation.Vector();
    }
    const FVector End=Start+Direction*(Survey?VillageBuildDefense::SurveyTraceLength:600.);const FIntVector Size=BrushSize();const FVector Half=FVector(Size)*10;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(VoxelAim),true,PC->GetPawn());
    // 2026-09-20：中心射线改多命中。摆开到占格之外的构件网格（开着的门扇、85° 开角的窗扇）解析不出
    // 格子，却挡在射线最前面——单命中时代它后面的墙整条不可见，吸附方案被瞬间清空落入贴地分支，
    // 手感上就是"吸附失灵"。现在沿射线取第一个"可解析建造面"（体素或构件占格）；全取不到时退而取
    // 第一个"非已放置构件"命中（门扇后面的地面，交给贴地分支）；再退回最前命中（拆除／贴地老口径）。
    AimScratch.Reset();
    GetWorld()->LineTraceMultiByChannel(AimScratch,Start,End,ECC_Visibility,Query);
    const FVoxelBuildPrefab* Prefab=SelectedPrefab();
    if(Prefab && VillageBuildDefense::IsSiegeEngine(Prefab->Id))
    {
        FCollisionQueryParams Structural=Query;
        Structural.bTraceComplex=false;
        FHitResult DeckHit;
        if(GetWorld()->LineTraceSingleByChannel(DeckHit,Start,End,ECC_Visibility,Structural)
            && VillageDefenseFootprint::SiegeRoof(DeckHit.GetComponent()))
        {
            // Use the walkable hull if the visible stone is its skin or the detailed trace missed it.
            // Keep any nearer foreground blocker, including a different building.
            const FHitResult* First=AimScratch.IsEmpty()?nullptr:&AimScratch.Last();
            if(!First || !First->bBlockingHit || DeckHit.Distance<=First->Distance ||
                (First->GetComponent()==DeckHit.GetComponent() && DeckHit.Distance<=First->Distance+24.))
            {
                AimScratch.Reset();
                AimScratch.Add(DeckHit);
            }
        }
    }
    bool HasHit=!AimScratch.IsEmpty();
    // 瞄准的构件引用必须**每帧**按当前命中重算（2026-09-19 排查顺带修复）：以前只在构件模式里刷新，
    // 切回体素模式后 AimedPrefab 留着上一帧的门——右键拆除按 AimedPrefab 优先，会拆到根本没瞄准的构件。
    // 拆除始终指**最前面**那件构件，与幽灵最终用哪个命中解算无关。
    AimedPrefab=nullptr;
    for(const FHitResult& RayHit:AimScratch)
    {
        for(AActor* Actor=RayHit.GetActor();Actor;Actor=Actor->GetAttachParentActor())
            if(auto* Piece=Cast<AVoxelBuildPrefabActor>(Actor)){AimedPrefab=Piece;break;}
        if(AimedPrefab.IsValid()||RayHit.bBlockingHit)break;
    }
    int32 AimIndex=INDEX_NONE;bool bVoxelSurface=false,bPrefabCellHit=false;
    const bool bDefense=Prefab&&VillageWallStairs::CanDock(Prefab->Id);
    if(HasHit)
    {
        // The surface under the crosshair chooses wall docking or ordinary floor placement.
        // A touch hit or a neighbouring assisted voxel must not change that choice.
        if((bDefense || (Prefab && VillageBuildDefense::IsSiegeEngine(Prefab->Id)) || (bSnapEnabled&&Prefab&&VillageGateReplacement::WallFor(Prefab->Id,AimScratch.Last().GetActor())))&&AimScratch.Last().bBlockingHit)AimIndex=AimScratch.Num()-1;
        for(int32 Index=0;AimIndex==INDEX_NONE&&Index<AimScratch.Num();++Index)
        {
            if(BuildWorld->ResolveHit(AimScratch[Index],HitCell)){AimIndex=Index;bVoxelSurface=true;break;}
            if(BuildWorld->ResolvePrefabSurfaceCell(AimScratch[Index],HitCell)){AimIndex=Index;bPrefabCellHit=true;break;}
        }
        if(AimIndex==INDEX_NONE)
            for(int32 Index=0;Index<AimScratch.Num();++Index)
                if(!BuildWorld->HitBelongsToPlacedPrefab(AimScratch[Index])){AimIndex=Index;break;}
        if(AimIndex==INDEX_NONE)AimIndex=0;
        Hit=AimScratch[AimIndex];
    }
    else Hit=FHitResult();
    bool BuildingHit=bVoxelSurface||bPrefabCellHit;
    LastAimWasAssisted=false;
    // Snap mode stays glued to a voxel surface inside a small cone: drifting the aim a little must
    // only switch which surface is snapped, not drop the ghost into the air. Only a real turn away
    // from every snappable surface falls through to the floating fallback below.
    // Never reach past a closer obstruction to capture a castle joint. A deliberate hit
    // on the floor keeps its grid placement, even when a wall is beside the crosshair.
    const bool bAimedAtWallMount=Prefab&&Prefab->Mount==EVoxelPrefabMount::Wall&&HasHit&&Cast<AVillageDefenseSection>(Hit.GetActor());
    const bool bTryAssist=bDefense
        ? (!HasHit || (!VillageWallStairs::ResolveTarget(Hit.GetActor()) && FMath::Abs(Hit.ImpactNormal.Z)<.5))
        : !BuildingHit&&!bAimedAtWallMount;
    const double AssistReach=bDefense&&HasHit?FMath::Min(600.,FVector::Distance(Start,Hit.ImpactPoint)+1.):600.;
    if(!Survey&&bSnapEnabled&&bTryAssist&&(!Prefab||!VillageGateReplacement::WallFor(Prefab->Id,Hit.GetActor()))&&TrySnapAssist(GetWorld(),BuildWorld,Start,Direction,Query,Hit,HitCell,
        bDefense?Prefab:nullptr,ComponentYaw,AssistReach))
    {
        HasHit=true;BuildingHit=true;LastAimWasAssisted=true;
        // 辅助射线可能命中的是构件面：重分辨一次，拆除笔刷只认真实体素。
        bVoxelSurface=BuildWorld->ResolveHit(Hit,HitCell);
    }
    // Removal is the only thing rebuilt every frame; the placement plan is only cleared by the
    // branch that actually recomputes it, so the throttled branches (terrain sampling, aim miss)
    // keep the previous plan and its validity instead of dropping the click.
    Removal.Reset();
    if(bVoxelSurface)FillBrush(HitCell.Cell,Removal);
    if(Prefab)
    {
        Placement.Reset();PlacementCuts.Reset();bCanPlace=false;UpdatePrefabTarget(HasHit);
        if(Survey && HasHit && !VillageBuildDefense::InSurveyRange(PC->GetPawn()->GetPawnViewLocation(),AVoxelBuildWorld::CellCenter(PrefabCell)))
        {
            bCanPlace=bPrefabValid=false;
            PrefabMessage=TargetMessage=TEXT("超出村庄施工范围 · 请在角色周围 120 米内选址");
        }
        UpdatePrefabPreview();return;
    }
    const double Now=GetWorld()->GetTimeSeconds();
    if(!HasHit)
    {
        // Momentary aim miss: keep the previous snapped ghost so it does not teleport away. Only in
        // snap mode - free placement (F) must follow the aim instead of holding a snapped plan.
        if(bSnapEnabled&&!Placement.IsEmpty()&&Now-LastSnapTime<.35)
        {bCanPlace=false;TargetMessage=TEXT("未命中可放置表面 · 瞄准 6 米内的地面或方块");UpdatePreview(Size);return;}
        Placement.Reset();PlacementCuts.Reset();bCanPlace=false;PlacementVolume={};HitCell={};
        PlacementOrigin=Start+Direction*250-Half;
        if(bSnapEnabled)PlacementOrigin=AVoxelBuildWorld::CellMin(AVoxelBuildWorld::ToCell(PlacementOrigin));
        FillBrush(FIntVector(Size.X/2,Size.Y/2,0),Placement,&PlacementCuts);
        TargetMessage=TEXT("未命中可放置表面 · 瞄准 6 米内的地面或方块");
        if(FoundationPreview){FoundationPreview->ClearInstances();FoundationPreview->SetVisibility(false);}
        for(UInstancedStaticMeshComponent* G:{CellGhost,CellCutGhost45,CellCutGhost26L,CellCutGhost26U,CellCutGhostTent})if(G){G->ClearInstances();G->SetVisibility(false);}
    }
    else if(!BuildingHit)
    {
        // 整条射线只剩已放置构件的网格（开着的门扇、背后是空的）：按"瞄空"同款 0.35 s 缓冲保住上一个
        // 吸附方案，别瞬间落进贴地分支——否则准星扫过一片扇面的瞬间幽灵就跳下墙，正是"吸附失灵"的手感。
        if(bSnapEnabled&&!Placement.IsEmpty()&&Now-LastSnapTime<.35
            &&BuildWorld->HitBelongsToPlacedPrefab(Hit))
        {bCanPlace=false;TargetMessage=TEXT("未命中可放置表面 · 瞄准 6 米内的地面或方块");UpdatePreview(Size);return;}
        // Terrain footprint sampling is expensive, so snap mode keeps the previous plan between
        // samples. Free placement must follow the aim continuously, so it is never throttled.
        if(bSnapEnabled&&Now<GroundSampleAt)return;
        GroundSampleAt=Now+1./20.;
        Placement.Reset();PlacementCuts.Reset();bCanPlace=false;PlacementVolume={};
        FString GroundingMessage;
        // 2026-10-15：坡刷（非 Box 形状）贴地放置也要按真实格子模板（实心三角）填充，
        // 不能落回 Size 整盒——否则地面放坡=砖墩。模板与切割同 FillBrush 一条真源。
        TArray<FIntVector> GroundTemplate;
        const TArray<FIntVector>* GroundTemplatePtr=nullptr;
        if(ShapeIsStaircase(Brush))
        {ShapeCells(Brush,BrushRotation,GroundTemplate);GroundTemplatePtr=&GroundTemplate;}
        if(BuildWorld->ResolveGroundPlacement(Hit,Size,bSnapEnabled,PlacementOrigin,Placement,GroundingMessage,GroundTemplatePtr))
        {
            if(GroundTemplatePtr)ShapeCuts(Brush,BrushRotation,GroundTemplate,PlacementCuts);
            ClippedPlayerCells=ClipLocalPlayerCells(Placement,PlacementOrigin,&PlacementCuts);
            GrowUpPlan=false;
            ValidatePlacement();
            if(bCanPlace)TargetMessage=GroundingMessage+TEXT("\n")+TargetMessage;
        }
        else TargetMessage=GroundingMessage;
    }
    else if(bSnapEnabled)
    {
        Placement.Reset();PlacementCuts.Reset();bCanPlace=false;
        PlacementVolume=BuildingHit?HitCell.Volume:FGuid();PlacementOrigin=BuildWorld->VolumeOrigin(PlacementVolume);
        FIntVector Base=AVoxelBuildWorld::ToCell(Hit.ImpactPoint+Hit.ImpactNormal*.5-PlacementOrigin);
        bool bGrowUp=false,bContinuePlane=false;
        if(BuildingHit)
        {
            // 2026-10-19 连续平面续坡：命中已放好的 45° 坡面顶格时，下一段从该坡最高端
            // 沿同一平面接上（低边抬升一格），新段首列的低边落在上一段最高格的顶面上。
            // 坡刷自身会补足新段下方的支撑实体，所以续接后每一列仍有实体承重；
            // 顶格楔形共面，20 cm 一节的坡刷拼出的是一整张连续斜面。
            const int32 Rise=ShapeSlopeRise(Brush);
            if(Rise==1&&!HitCell.Volume.IsValid())
            {
                const int32 RunDir=(BrushRotation&1)?((BrushRotation&2)?4:3):((BrushRotation&2)?2:1);
                const uint8 HitCut=BuildWorld->DebugCutAt(HitCell.Cell);
                if(HitCut&&VoxelCut::Pattern(HitCut)==0&&VoxelCut::Dir(HitCut)==uint8(RunDir))
                {
                    auto PlaneC=[RunDir](const FIntVector& C)
                    {
                        switch(RunDir){case 1:return C.Z-C.X;case 2:return C.Z+C.X+1;
                        case 3:return C.Z-C.Y;default:return C.Z+C.Y+1;}
                    };
                    const int32 Plane=PlaneC(HitCell.Cell);
                    const FIntVector Step=RunDir==1?FIntVector(1,0,0):RunDir==2?FIntVector(-1,0,0):
                        RunDir==3?FIntVector(0,1,0):FIntVector(0,-1,0);
                    // 从命中格沿坡向走到这一坡段的最高格（最多 64 格，防止异常数据长循环）。
                    FIntVector SlopeEnd=HitCell.Cell;
                    // 一层薄壳的坡面格是斜向排列：沿坡向前进必须是"水平一格 + 高度一格"。
                    // 2026-10-22 复核修复：旧循环只加水平 Step，查的是同一高度的空格，
                    // 第一步就停；命中坡面中段时 Base 落在已有格上（重叠），命中檐口时
                    // 又只前进一格，续坡自然接不上。这里用对角步进（正负坡向都适用：
                    // RunDir 的 Step 与"向上"一致，坡面高度始终 +1）。
                    const FIntVector SlopeStep=Step+FIntVector(0,0,1);
                    for(int32 I=0;I<64;++I)
                    {
                        const FIntVector Next=SlopeEnd+SlopeStep;const uint8 Cut=BuildWorld->DebugCutAt(Next);
                        if(!Cut||VoxelCut::Pattern(Cut)!=0||VoxelCut::Dir(Cut)!=uint8(RunDir)
                            ||PlaneC(Next)!=Plane)break;
                        SlopeEnd=Next;
                    }
                    Base=SlopeEnd+Step+FIntVector(0,0,1);
                    // 2026-10-22 复核修复：续坡的宽度轴必须与命中坡段对齐。原实现只按
                    // FillBrush 的居中口径重算，2 宽坡命中任意一侧时会整体错一格；两段
                    // 宽度错位后接缝只剩一条棱，用户看到的就是"拼接有明显间隙"。这里沿
                    // 宽度轴找同坡面/坡向的连续格，取最小格，让新段覆盖同一个宽度范围。
                    const int32 WidthAxis=RunDir<=2?1:0;const int32 WidthSize=WidthAxis==0?Size.X:Size.Y;
                    if(WidthSize>1)
                    {
                        auto SameWidthCell=[&](const FIntVector& C)
                        {
                            const uint8 Cut=BuildWorld->DebugCutAt(C);
                            return Cut&&VoxelCut::Pattern(Cut)==0&&VoxelCut::Dir(Cut)==uint8(RunDir)
                                &&PlaneC(C)==Plane;
                        };
                        // 宽度轴垂直于坡面：同 X/Z、只改宽度坐标就是同坡面邻格，
                        // 不需要再解坡面方程。
                        int32 WidthMin=HitCell.Cell[WidthAxis];
                        for(int32 S=-1;S<=1;S+=2)
                        {
                            FIntVector C=HitCell.Cell;
                            for(int32 I=0;I<64;++I)
                            {
                                C[WidthAxis]+=S;if(!SameWidthCell(C))break;
                                WidthMin=FMath::Min(WidthMin,C[WidthAxis]);
                            }
                        }
                        // FillBrush 会按笔刷宽度把宽度轴居中回退 WidthSize/2，所以这里传
                        // “最小格 + 半宽”，落位后的首格才是 WidthMin。
                        Base[WidthAxis]=WidthMin+WidthSize/2;
                    }
                    bContinuePlane=true;
                }
            }
            if(!bContinuePlane)
            {
                int32 Axis=0;const FVector N=Hit.ImpactNormal.GetAbs();if(N.Y>N.X)Axis=1;if(N.Z>N[Axis])Axis=2;
                Base=HitCell.Cell;
                if(Axis==2)Base.Z+=Hit.ImpactNormal.Z>0?1:-Size.Z;
                else if(ShapeIsSlope(Brush)&&(BrushRotation&1)==(Axis==1?1:0))
                    // 斜坡行进轴不居中（见 FillBrush）：檐口贴面外一格起坡；FillBrush 再按
                    // 正/负坡向把包围盒放到檐口的正确一侧（2026-10-19 四态统一锚点）。
                    Base[Axis]+=Hit.ImpactNormal[Axis]>0?1:-1;
                else Base[Axis]+=Hit.ImpactNormal[Axis]>0?1+Size[Axis]/2:-(Size[Axis]-Size[Axis]/2);
                // Looking up at a column's side means "put the next course on top of it". Once a wall is
                // taller than the player's eyes its top face is almost impossible to hit, which used to
                // make raising it impossible (2026-09-16 report: hit=0 above 2 m).
                if(Axis!=2&&Direction.Z>.05f)
                {
                    const FIntVector Above=HitCell.Cell+FIntVector(0,0,1);
                    // 2026-09-19：命中面可能是构件面（门框／窗框侧面），正上方那格若也被同一构件占着
                    // （框的竖直边柱），叠一层只会一直红——改试占格顶部之上：外廓整格时就是框顶上。
                    if(BuildWorld->VolumeMaterialAt(HitCell.Volume,Above).IsNone()
                        &&!BuildWorld->IsPrefabCell(FGuid(),Above))
                    {Base=Above;bGrowUp=true;}
                    else
                    {
                        FIntVector Top;
                        if(BuildWorld->PrefabColumnTop(HitCell.Cell,Top)
                            &&BuildWorld->VolumeMaterialAt(HitCell.Volume,Top).IsNone()
                            &&!BuildWorld->IsPrefabCell(FGuid(),Top))
                        {Base=Top;bGrowUp=true;}
                    }
                }
            }
        }
        FillBrush(Base,Placement,&PlacementCuts);
        // 2026-10-22 复核：一层薄壳续坡不填内部；接缝靠 20×20 共面坡棱承重，宽度轴
        // 已在上面与命中坡段对齐，新旧两段不会错一格。需要绝对无缝时用实心补结构
        // 或连续薄板构件，不在单层坡里偷偷塞承重格。
        bPlacementContinued=bContinuePlane;
        ClippedPlayerCells=ClipLocalPlayerCells(Placement,PlacementOrigin,&PlacementCuts);
        ValidatePlacement();
        GrowUpPlan=bGrowUp;
        LastSnapTime=Now;
        // Aim cursor on the hit face plus corner markers on the plan. The plan's faces can be hidden
        // inside existing blocks when stacking upward; corners and the cursor stay readable.
        if(FoundationPreview)
        {
            FBox Plan(ForceInit);
            for(const FIntVector& Cell:Placement)
            {
                const FVector Min=PlacementOrigin+AVoxelBuildWorld::CellMin(Cell);
                Plan+=FBox(Min,Min+FVector(20));
            }
            const FVector CursorPoint=Hit.ImpactPoint+Hit.ImpactNormal*1.5f;
            const FVector PlanMin=Plan.IsValid?Plan.Min:FVector::ZeroVector;
            const FVector PlanMax=Plan.IsValid?Plan.Max:FVector::ZeroVector;
            // Rebuild only when the cursor or the plan box actually moved: the steady state must not
            // allocate or touch the instance buffer every frame.
            const bool bCursorMoved=!LastCursorPoint.Equals(CursorPoint,.05f)||!LastCursorNormal.Equals(Hit.ImpactNormal,.01f);
            const bool bPlanMoved=!LastPlanMin.Equals(PlanMin,.05f)||!LastPlanMax.Equals(PlanMax,.05f);
            if(bCursorMoved||bPlanMoved)
            {
                LastCursorPoint=CursorPoint;LastCursorNormal=Hit.ImpactNormal;LastPlanMin=PlanMin;LastPlanMax=PlanMax;
                TArray<FTransform> Marks;
                Marks.Emplace(FRotationMatrix::MakeFromZ(Hit.ImpactNormal).ToQuat(),CursorPoint,FVector(.09f,.09f,.012f));
                if(Plan.IsValid)
                {
                    const FVector Extent=Plan.GetExtent()*2;
                    for(int32 Index=0;Index<8;++Index)
                    {
                        const FVector Corner(Plan.Min.X+((Index&1)?Extent.X:0),Plan.Min.Y+((Index&2)?Extent.Y:0),
                            Plan.Min.Z+((Index&4)?Extent.Z:0));
                        Marks.Emplace(FQuat::Identity,Corner,FVector(.03f,.03f,.03f));
                    }
                }
                if(FoundationPreview->GetInstanceCount()==Marks.Num())
                {
                    FoundationPreview->BatchUpdateInstancesTransforms(0,Marks,true,true,true);
                }
                else
                {
                    FoundationPreview->ClearInstances();FoundationPreview->AddInstances(Marks,false,true,false);
                }
                FoundationPreview->SetHiddenInGame(false);FoundationPreview->SetVisibility(true);
            }
        }
        // Gold edges on every existing block that touches the plan (blink is driven in TickComponent).
        if(auto* Edges=FindAimEdge(PreviewActor))
        {
            // 金色自发光比预览材质的世界网格更清楚；材质在 TryInitializeWorld 里一次性装好（缺材质时
            // 退回预览材质）。2026-09-16 清理：去掉了这里的函数 static 自愈逻辑与一次性日志。
            // Cheap signature pass (no allocation): only rebuild the instance buffer when the set of
            // touching blocks actually changes, so the steady state costs a handful of map lookups.
            static const FIntVector Directions[6]={{1,0,0},{-1,0,0},{0,1,0},{0,-1,0},{0,0,1},{0,0,-1}};
            uint32 Signature=0;int32 Count=0;
            for(const FIntVector& Cell:Placement)
            {
                for(const FIntVector& Dir:Directions)
                {
                    const FIntVector Neighbour=Cell+Dir;
                    if(BuildWorld->VolumeMaterialAt(HitCell.Volume,Neighbour).IsNone())continue;
                    Signature+=GetTypeHash(Neighbour);++Count;
                }
            }
            if(Signature!=AimEdgeSignature||Count!=AimEdgeCount||AimEdgeCell!=HitCell.Cell)
            {
                AimEdgeSignature=Signature;AimEdgeCount=Count;AimEdgeCell=HitCell.Cell;
                constexpr float Bar=.012f,Span=.21f;
                TArray<FTransform> Bars;
                auto Open=[&](FIntVector Cell,FIntVector Offset)
                {return BuildWorld->VolumeMaterialAt(HitCell.Volume,Cell+Offset).IsNone();};
                // One gold wireframe per touching block, drawing only edges that border open space:
                // edges buried against a neighbour sit inside that cell and would never be visible.
                auto AddBlockEdges=[&](FIntVector Cell)
                {
                    const FVector CellMin=BuildWorld->VolumeOrigin(HitCell.Volume)+AVoxelBuildWorld::CellMin(Cell);
                    const FVector Low=CellMin-FVector(.5f),High=CellMin+FVector(20.5f);
                    const FVector Center=(Low+High)*.5f;
                    for(int32 I=0;I<4;++I)
                    {
                        const int32 Sy=(I&1)?1:-1,Sz=(I&2)?1:-1;
                        if(!Open(Cell,FIntVector(0,Sy,0))&&!Open(Cell,FIntVector(0,0,Sz)))continue;
                        Bars.Emplace(FQuat::Identity,FVector(Center.X,(I&1)?High.Y:Low.Y,(I&2)?High.Z:Low.Z),FVector(Span,Bar,Bar));
                    }
                    for(int32 I=0;I<4;++I)
                    {
                        const int32 Sx=(I&1)?1:-1,Sz=(I&2)?1:-1;
                        if(!Open(Cell,FIntVector(Sx,0,0))&&!Open(Cell,FIntVector(0,0,Sz)))continue;
                        Bars.Emplace(FQuat::Identity,FVector((I&1)?High.X:Low.X,Center.Y,(I&2)?High.Z:Low.Z),FVector(Bar,Span,Bar));
                    }
                    for(int32 I=0;I<4;++I)
                    {
                        const int32 Sx=(I&1)?1:-1,Sy=(I&2)?1:-1;
                        if(!Open(Cell,FIntVector(Sx,0,0))&&!Open(Cell,FIntVector(0,Sy,0)))continue;
                        Bars.Emplace(FQuat::Identity,FVector((I&1)?High.X:Low.X,(I&2)?High.Y:Low.Y,Center.Z),FVector(Bar,Bar,Span));
                    }
                };
                for(const FIntVector& Cell:Placement)
                {
                    for(const FIntVector& Dir:Directions)
                    {
                        const FIntVector Neighbour=Cell+Dir;
                        if(BuildWorld->VolumeMaterialAt(HitCell.Volume,Neighbour).IsNone())continue;
                        AddBlockEdges(Neighbour);
                    }
                }
                if(Bars.IsEmpty())Edges->ClearInstances();
                else if(Edges->GetInstanceCount()==Bars.Num())Edges->BatchUpdateInstancesTransforms(0,Bars,true,true,true);
                else{Edges->ClearInstances();Edges->AddInstances(Bars,false,true,false);}
            }
            // Visibility comes from the cached touching count, outside the rebuild test, so a frame
            // that keeps the same neighbours still lights the outline up instead of leaving it hidden.
            Edges->SetHiddenInGame(false);Edges->SetVisibility(Count>0);
        }
    }
    else
    {
        Placement.Reset();PlacementCuts.Reset();bCanPlace=false;
        // Continuous world position: no floor/round/quantization in free mode.
        PlacementOrigin=Hit.ImpactPoint+Hit.ImpactNormal*FVector::DotProduct(Hit.ImpactNormal.GetAbs(),Half)-Half;
        FillBrush(FIntVector(Size.X/2,Size.Y/2,0),Placement,&PlacementCuts);
        ClippedPlayerCells=ClipLocalPlayerCells(Placement,PlacementOrigin,&PlacementCuts);
        GrowUpPlan=false;
        ValidatePlacement();
        if(FoundationPreview){FoundationPreview->ClearInstances();FoundationPreview->SetVisibility(false);}
        for(UInstancedStaticMeshComponent* G:{CellGhost,CellCutGhost45,CellCutGhost26L,CellCutGhost26U,CellCutGhostTent})if(G){G->ClearInstances();G->SetVisibility(false);}
    }
    UpdatePreview(Size);

    // TEMPORARY diagnostics for the 2026-09-16 "cannot build above 2 m" report: one line whenever
    // the aim or plan state changes, so a single reproduction in game tells where it stops.
    static FString LastAimSignature;
    const FString AimSignature=FString::Printf(TEXT("%d|%d|%d,%d,%d|%d|%d|%d|%d|%d"),HasHit?1:0,BuildingHit?1:0,
        HitCell.Cell.X,HitCell.Cell.Y,HitCell.Cell.Z,Placement.Num(),bCanPlace?1:0,GrowUpPlan?1:0,LastAimWasAssisted?1:0,
        bSnapEnabled?1:0);
    if(AimSignature!=LastAimSignature)
    {
        LastAimSignature=AimSignature;
    // 诊断日志默认关闭（fps.Building.DebugLog 1 打开），避免每帧刷屏与日志膨胀。
    if(!VoxelBuildDebug::Enabled())return;
    if(Now-LastAimLog<.5)return;
    LastAimLog=Now;
        // 2026-09-20 复盘加料：多命中时代光看 hit/building 分不清"谁挡的"——点名最前命中与
        // 实际选中命中的 Actor（含选中序号/命中总数），一次复现就能定位阻挡者或选错者。
        UE_LOG(LogTemp,Warning,TEXT("VOXEL_AIM hit=%d building=%d cell=%d,%d,%d plan=%d valid=%d grow=%d assist=%d snap=%d origin=%.1f,%.1f,%.1f message=%s hits=%d pick=%d first=%s chosen=%s"),
            HasHit?1:0,BuildingHit?1:0,HitCell.Cell.X,HitCell.Cell.Y,HitCell.Cell.Z,Placement.Num(),bCanPlace?1:0,GrowUpPlan?1:0,
            LastAimWasAssisted?1:0,bSnapEnabled?1:0,PlacementOrigin.X,PlacementOrigin.Y,PlacementOrigin.Z,*TargetMessage,
            AimScratch.Num(),AimIndex,*(AimScratch.IsEmpty()?FString(TEXT("")):GetNameSafe(AimScratch[0].GetActor())),
            *GetNameSafe(Hit.GetActor()));
    }
}

int32 UVoxelBuildComponent::PlannedGroundYaw() const
{
    return VillageBuildDefense::IsVillageRecipe(SelectedComponent)&&!DefenseDockPose.IsSet()?GroundYawDegrees:INDEX_NONE;
}

void UVoxelBuildComponent::UpdatePrefabTarget(bool bHit)
{
    bPrefabAimHit=bHit;bPrefabValid=false;bCanPlace=false;PrefabMessage=TEXT("");
    DefenseDockTarget.Reset();
    DefenseDockPose.Reset();
    SiegeFloorPreview.Reset();
    DefenseDockSocket=INDEX_NONE;
    WallCutBars.Reset();
    WallCutSelection=-1;
    PrefabPlanYaw=VillageBuildDefense::IsVillageRecipe(SelectedComponent)?0:ComponentYaw;
    const FVoxelBuildPrefab* Prefab=SelectedPrefab();
    if(!Prefab||!BuildWorld){TargetMessage=TEXT("构件定义已失效");PrefabMessage=TargetMessage;return;}
    const FIntVector Footprint=AVoxelBuildPrefabActor::RotatedFootprint(Prefab->Footprint,PrefabPlanYaw);
    // Removing voxels stays available while a component is selected: right click the aimed block.
    if(BuildWorld->ResolveHit(Hit,HitCell))FillBrush(HitCell.Cell,Removal);
    if(!bHit)
    {
        PrefabCell=AVoxelBuildWorld::ToCell(Hit.ImpactPoint);
        PrefabMessage=IsVillageCameraPlacing()?TEXT("移动鼠标，指向地面或城防接口"):TEXT("未命中可放置表面 · 瞄准 6 米内的地面或结构");
        TargetMessage=PrefabMessage;
        return;
    }
    FIntVector Cell;
    bool bSurfaceBacked=false;
    if(auto* Wall=bSnapEnabled?VillageGateReplacement::WallFor(Prefab->Id,Hit.GetActor()):nullptr)
    {
        // Keep the end-face socket for extending an exposed run. Its top and broad faces select a replacement.
        const bool EndFace=Prefab->Id==VillageBuildDefense::StoneGate &&
            FMath::Abs(Hit.ImpactNormal.Dot(Wall->GetActorForwardVector()))>.85 &&
            FMath::Abs(Wall->GetActorTransform().InverseTransformPosition(Hit.ImpactPoint).X)>140.;
        FTransform Pose;
        if(!EndFace && VillageGateReplacement::Layout(Prefab->Id,Wall,Prefab->Footprint,Pose,PrefabCell,PrefabPlanYaw))
        {
            DefenseDockPose=Pose;
            DefenseDockTarget=Wall;
            DefenseDockSocket=VillageGateReplacement::ReplacementSocket;
            TArray<FVillageGateCut> Cuts;
            bCanPlace=bPrefabValid=BuildWorld->CanPlacePrefab(Prefab->Id,PrefabCell,PrefabPlanYaw,PrefabMessage,false,true,Wall,nullptr,INDEX_NONE,true,&Cuts,&WallCutBars);
            if(bPrefabValid)WallCutSelection=VillageGateReplacement::WallSelection(Cuts);
            TargetMessage=PrefabMessage;
            return;
        }
    }
    const auto* Target=bSnapEnabled&&VillageWallStairs::CanDock(Prefab->Id)
        ? VillageWallStairs::ResolveTarget(Hit.GetActor()):nullptr;
    VillageWallStairs::FDock Dock;
    const bool NearbyJoin=bSnapEnabled && VillageWallStairs::PickNearbyWallDock(*BuildWorld,Prefab->Id,Prefab->Footprint,
        Hit,ComponentYaw,Dock,bPrefabValid,PrefabMessage);
    if(Target && !NearbyJoin)
    {
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
                if(bOtherValid && (!bPrefabValid || bWheelAlternate))
                {
                    Dock=Other;
                    PrefabMessage=MoveTemp(OtherMessage);
                    bPrefabValid=bOtherValid;
                }
            }
        }
    }
    if(Dock.Target)
    {
        PrefabCell=Dock.Anchor;
        PrefabPlanYaw=Dock.Yaw;
        DefenseDockPose=Dock.Pose;
        DefenseDockTarget=Dock.Target;
        DefenseDockSocket=Dock.Socket;
        bCanPlace=bPrefabValid;
        TargetMessage=PrefabMessage;
        return;
    }
    else if(Prefab->Mount==EVoxelPrefabMount::Wall)
    {
        // 壁挂构件（火把等）：只认竖直表面，朝向由表面外法线定（局部 +X 是伸出方向，四向吸附）。
        FHitResult Backing=Hit;
        if(!VoxelGrounding::ResolveMountingSurface(Backing))
        {
            // 红幽灵留在准星处，而不是上一帧的位置。
            PrefabCell=AVoxelBuildWorld::ToCell(Hit.ImpactPoint);
            PrefabMessage=TEXT("必须贴在墙面或结构表面 · 壁挂构件不能放在地面或天花板");
            TargetMessage=PrefabMessage;
            return;
        }
        const FVector Normal2D=Backing.ImpactNormal.GetSafeNormal2D();
        PrefabPlanYaw=((FMath::RoundToInt(FMath::Atan2(Normal2D.Y,Normal2D.X)/(PI/2))%4)+4)%4;
        const FIntVector Size=AVoxelBuildPrefabActor::RotatedFootprint(Prefab->Footprint,PrefabPlanYaw);
        // 占格贴着表面往外长：法线轴向最小面压在表面上，切向与竖直方向都以准星为中心。
        Cell=AVoxelBuildWorld::ToCell(Backing.ImpactPoint-FVector(Size)*10.);
        const int32 Axis=PrefabPlanYaw&1;
        const double Plane=Backing.ImpactPoint[Axis];
        // The two negative-facing sides seat the far face of the fixture on the wall.
        // Pick the same cardinal axis as the mesh, including on diagonal masonry.
        Cell[Axis]=PrefabPlanYaw<2?FMath::CeilToInt((Plane-.5)/20.):
            FMath::FloorToInt((Plane+.5)/20.)-Size[Axis];
        bSurfaceBacked=true;
    }
    else
    {
        // The 20 cm footprint is centred on the aimed column and always lands on lattice multiples.
        const FVector Base=Hit.ImpactPoint+Hit.ImpactNormal*.5;
        Cell=AVoxelBuildWorld::ToCell(Base);
        if(VillageBuildDefense::IsSiegeEngine(Prefab->Id))Cell.Z=FMath::CeilToInt((Hit.ImpactPoint.Z-.05)/20.);
        Cell.X-=Footprint.X/2;Cell.Y-=Footprint.Y/2;
    }
    PrefabCell=Cell;
    FTransform FloorPose;
    const bool Siege=VillageBuildDefense::IsSiegeEngine(Prefab->Id);
    bPrefabValid=BuildWorld->CanPlacePrefab(Prefab->Id,Cell,PrefabPlanYaw,PrefabMessage,bSurfaceBacked,
        DefenseDockPose.IsSet(),DefenseDockTarget.Get(),Siege?&FloorPose:nullptr,PlannedGroundYaw());
    if(!bPrefabValid && bSnapEnabled && Siege)
    {
        const auto* Surface=Hit.GetComponent();
        if(const auto* Deck=VillageDefenseFootprint::SiegeRoof(Surface))
        {
            const FTransform& Frame=Surface->GetComponentTransform();
            for(const FIntVector& Site:SiegeRoofSites(Prefab->Id,*Deck,Frame,Hit.ImpactPoint,GroundYawDegrees,Footprint,Cell))
            {
                FString SiteReason;
                if(!BuildWorld->CanPlacePrefab(Prefab->Id,Site,PrefabPlanYaw,SiteReason,false,false,nullptr,&FloorPose,PlannedGroundYaw()))continue;
                if(FMath::Abs(Frame.InverseTransformPosition(FloorPose.GetLocation()).Z-Deck->Bounds.Max.Z)>2.)continue;
                PrefabCell=Site;
                PrefabMessage=Prefab->Id==VillageBuildDefense::Trebuchet?TEXT("投石机已贴合附近的平台 · 滚轮旋转 · 左键建造"):
                    Prefab->Id==VillageBuildDefense::OilPot?TEXT("热油锅已贴合附近的平台 · 滚轮旋转 · 左键建造"):TEXT("弩炮已贴合附近的平台 · 滚轮旋转 · 左键建造");
                bPrefabValid=true;
                break;
            }
        }
    }
    if(Siege && bPrefabValid)SiegeFloorPreview=FloorPose;
    bCanPlace=bPrefabValid;TargetMessage=PrefabMessage;
}

