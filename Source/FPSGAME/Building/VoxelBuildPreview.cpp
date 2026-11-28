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
#include "VillageBuildDefense.h"
#include "../WorldGeneration/HighVillageDefense.h"
#include "../WorldGeneration/VillageDefenseSection.h"
#include "VoxelBuildWidget.h"
#include "VoxelJointStrength.h"
#include "../FPSGAMECharacter.h"
#include "../Development/DevelopmentTuningSubsystem.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelWorldInteraction.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "Components/StaticMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/DecalComponent.h"
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

namespace
{
    // TEMPORARY diagnostics for the 2026-09-16 "cannot build above 2 m" report.
    FString LastPreviewReject;

    const TCHAR* EntranceMeshName(FName Recipe)
    {
        if(Recipe==VillageBuildDefense::HighTower)return TEXT("SM_TowerEntrances");
        if(Recipe==VillageBuildDefense::StoneGate)return TEXT("SM_StoneGateEntrances");
        if(Recipe==VillageBuildDefense::WoodGate)return TEXT("SM_WoodGateExterior");
        if(Recipe==VillageWallStairs::Id)return TEXT("SM_StairEntrances");
        return nullptr;
    }

    void TintPreviewMesh(UStaticMeshComponent& Part,UMaterialInterface* Material)
    {
        if(!Material||!Part.GetStaticMesh())return;
        for(int32 Slot=0;Slot<Part.GetStaticMesh()->GetStaticMaterials().Num();++Slot)
            Part.SetMaterial(Slot,Material);
    }
}

void UVoxelBuildComponent::UpdateEntrancePreview(FName Recipe,bool bValid)
{
    if(Recipe!=EntrancePreviewRecipe)
    {
        EntrancePreviewRecipe=Recipe;
        UStaticMesh* Mark=nullptr;
        if(const TCHAR* Name=EntranceMeshName(Recipe))
        {
            const FString Path=FString::Printf(TEXT("/Game/WorldGeneration/TemperateHills/HighVillageDefense/PlacementPreview/%s.%s"),Name,Name);
            Mark=LoadObject<UStaticMesh>(nullptr,*Path);
        }
        if(Mark && !EntrancePreview)
        {
            EntrancePreview=NewObject<UStaticMeshComponent>(PreviewActor.Get(),NAME_None,RF_Transient);
            PreviewActor->AddInstanceComponent(EntrancePreview);
            EntrancePreview->SetupAttachment(Preview);
            EntrancePreview->SetMobility(EComponentMobility::Movable);
            EntrancePreview->SetCollisionEnabled(ECollisionEnabled::NoCollision);
            EntrancePreview->SetGenerateOverlapEvents(false);
            EntrancePreview->SetCanEverAffectNavigation(false);
            EntrancePreview->SetCastShadow(false);
            EntrancePreview->SetTranslucentSortPriority(2);
            EntrancePreview->RegisterComponent();
        }
        if(EntrancePreview)
        {
            EntrancePreview->SetStaticMesh(Mark);
            // The wooden gate's preview parent is the left leaf's hinge.
            const double CenterX=Recipe==VillageBuildDefense::WoodGate?AVillageDefenseGate::NarrowHingeOffset:0.;
            EntrancePreview->SetRelativeLocation(FVector(CenterX,0.,0.));
        }
    }
    if(EntrancePreview)EntrancePreview->SetVisibility(bValid && EntrancePreview->GetStaticMesh());
}

void UVoxelBuildComponent::UpdateWallCutPreview()
{
    if(WallCutBars.IsEmpty())
    {
        if(WallCutPreview)WallCutPreview->SetVisibility(false);
        return;
    }
    if(!WallCutPreview)
    {
        auto* Surface=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Building/Voxels/Rounded/M_VoxelAimEdge.M_VoxelAimEdge"));
        if(!GhostMesh || !Surface)return;
        WallCutPreview=NewObject<UInstancedStaticMeshComponent>(PreviewActor.Get(),NAME_None,RF_Transient);
        PreviewActor->AddInstanceComponent(WallCutPreview);
        WallCutPreview->SetupAttachment(Preview);
        WallCutPreview->SetAbsolute(true,true,true);
        WallCutPreview->SetMobility(EComponentMobility::Movable);
        WallCutPreview->SetStaticMesh(GhostMesh);
        WallCutPreview->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        WallCutPreview->SetCanEverAffectNavigation(false);
        WallCutPreview->SetCastShadow(false);
        WallCutPreview->SetTranslucentSortPriority(3);
        auto* Gold=UMaterialInstanceDynamic::Create(Surface,WallCutPreview);
        Gold->SetVectorParameterValue(TEXT("Tint"),FLinearColor(2.5f,1.1f,.06f));
        WallCutPreview->SetMaterial(0,Gold);
        WallCutPreview->RegisterComponent();
    }
    bool Changed=WallCutBars.Num()!=DisplayedWallCutBars.Num();
    for(int32 I=0;!Changed && I<WallCutBars.Num();++I)
        Changed=!WallCutBars[I].Equals(DisplayedWallCutBars[I],.01);
    if(Changed)
    {
        WallCutPreview->ClearInstances();
        WallCutPreview->AddInstances(WallCutBars,false,true,false);
        DisplayedWallCutBars=WallCutBars;
    }
    WallCutPreview->SetVisibility(true);
}

void UVoxelBuildComponent::HideSiegeRangePreview()
{
    if(SiegeRangeDecal && !SiegeRangeDecal->bHiddenInGame)
    {
        SiegeRangeDecal->SetHiddenInGame(true);
        SiegeRangeDecal->SetVisibility(false);
    }
}

void UVoxelBuildComponent::UpdateSiegeRangePreview(FName Recipe,const FVector& SiteWorld,bool bValid)
{
    if(!VillageBuildDefense::IsSiegeEngine(Recipe) || !PreviewActor)
    {
        HideSiegeRangePreview();
        return;
    }
    if(!VillageWorld.IsValid())
        for(TActorIterator<ATemperateHillsWorld> It(GetWorld());It;++It){VillageWorld=*It;break;}
    const VillageSiegeUpgrades::FRanks Ranks=VillageWorld.IsValid()?VillageWorld->GetAllSiegeRanks():VillageSiegeUpgrades::FRanks{};

    if((Recipe==VillageBuildDefense::Ballista || Recipe==VillageBuildDefense::SmartTurret) && FVector::DistSquared2D(SiteWorld,SiegeGroundSampleXY)>1600.)
    {
        SiegeGroundSampleXY=SiteWorld;
        SiegeGroundElevCm=0.;
        FHitResult GroundHit;
        FCollisionQueryParams Q(SCENE_QUERY_STAT(SiegeRangeGround),false,PreviewActor.Get());
        if(GetWorld()->LineTraceSingleByChannel(GroundHit,SiteWorld+FVector(0.,0.,40.),SiteWorld-FVector(0.,0.,4000.),ECC_WorldStatic,Q) &&
           GroundHit.IsValidBlockingHit())
            SiegeGroundElevCm=FMath::Max(0.,SiteWorld.Z-GroundHit.ImpactPoint.Z);
    }
    const double Elev=(Recipe==VillageBuildDefense::Ballista || Recipe==VillageBuildDefense::SmartTurret)?SiegeGroundElevCm:0.;

    VillageBuildDefense::FVillageSiegeRangeSpec Spec;
    if(!VillageBuildDefense::ComputeSiegeRange(Recipe,Ranks,Elev,Spec)){HideSiegeRangePreview();return;}

    if(!SiegeRangeMaterial)
        SiegeRangeMaterial=LoadObject<UMaterialInterface>(nullptr,
            TEXT("/Game/WorldGeneration/TemperateHills/HighVillageDefense/PlacementPreview/M_SiegeRangeIndicator.M_SiegeRangeIndicator"));
    if(!SiegeRangeMaterial){HideSiegeRangePreview();return;}

    const bool bCreate=!SiegeRangeDecal;
    if(bCreate)
    {
        SiegeRangeDecal=NewObject<UDecalComponent>(PreviewActor.Get(),TEXT("SiegePlacementRangeDecal"),RF_Transient);
        PreviewActor->AddInstanceComponent(SiegeRangeDecal);
        SiegeRangeDecal->SetupAttachment(PreviewActor->GetRootComponent());
        SiegeRangeDecal->SetAbsolute(true,true,true);
        SiegeRangeDecal->SetWorldRotation(FRotator(-90.f,0.f,0.f));
        SiegeRangeDecal->SetFadeScreenSize(0.f);
        SiegeRangeDecal->SortOrder=2;
        SiegeRangeDecal->SetDecalMaterial(SiegeRangeMaterial);
        SiegeRangeDecal->RegisterComponent();
        SiegeRangeMID=SiegeRangeDecal->CreateDynamicMaterialInstance();
    }
    if(!SiegeRangeDecal)return;

    const FVector DecalLoc(SiteWorld.X,SiteWorld.Y,SiteWorld.Z-700.);
    if(bCreate || !SiegeRangeCenter.Equals(SiteWorld,1.))
    {
        SiegeRangeCenter=SiteWorld;
        SiegeRangeDecal->SetWorldLocation(DecalLoc);
        if(SiegeRangeMID)SiegeRangeMID->SetVectorParameterValue(TEXT("Center"),FLinearColor(DecalLoc));
    }

    if(bCreate || SiegeRangeRecipe!=Recipe || SiegeRangeRanks!=Ranks.Low || SiegeRangeExtraRanks!=Ranks.High || bSiegeRangeValid!=bValid ||
       !FMath::IsNearlyEqual(SiegeRangeOuter,Spec.OuterRadiusCm,1.) ||
       !FMath::IsNearlyEqual(SiegeRangeInner,Spec.InnerRadiusCm,1.))
    {
        SiegeRangeRecipe=Recipe;
        SiegeRangeRanks=Ranks.Low;
        SiegeRangeExtraRanks=Ranks.High;
        SiegeRangeOuter=Spec.OuterRadiusCm;
        SiegeRangeInner=Spec.InnerRadiusCm;
        bSiegeRangeValid=bValid;

        const FVector Box(3600.,Spec.OuterRadiusCm+120.,Spec.OuterRadiusCm+120.);
        if(!SiegeRangeDecal->DecalSize.Equals(Box,1.f))
        {
            SiegeRangeDecal->DecalSize=Box;
            SiegeRangeDecal->MarkRenderStateDirty();
        }
        if(SiegeRangeMID)
        {
            const FLinearColor Ring=bValid?Spec.RingColor:FLinearColor(.94f,.34f,.30f);
            const FLinearColor Fill=bValid?Spec.FillColor:FLinearColor(.72f,.22f,.18f);
            SiegeRangeMID->SetVectorParameterValue(TEXT("RingColor"),Ring);
            SiegeRangeMID->SetVectorParameterValue(TEXT("FillColor"),Fill);
            SiegeRangeMID->SetScalarParameterValue(TEXT("OuterRadius"),float(Spec.OuterRadiusCm));
            SiegeRangeMID->SetScalarParameterValue(TEXT("InnerRadius"),float(Spec.InnerRadiusCm));
            SiegeRangeMID->SetScalarParameterValue(TEXT("FillInner"),Spec.bFillInner?1.f:0.f);
            SiegeRangeMID->SetScalarParameterValue(TEXT("VerticalSpan"),3500.f);
            SiegeRangeMID->SetScalarParameterValue(TEXT("OpacityScale"),bValid?1.f:.62f);
        }
    }
    if(SiegeRangeDecal->bHiddenInGame || !SiegeRangeDecal->IsVisible())
    {
        SiegeRangeDecal->SetHiddenInGame(false);
        SiegeRangeDecal->SetVisibility(true);
    }
}

void UVoxelBuildComponent::UpdatePrefabPreview()
{
    if(!Preview)return;
    if(FoundationPreview){FoundationPreview->ClearInstances();FoundationPreview->SetVisibility(false);}
    for(UInstancedStaticMeshComponent* G:{CellGhost,CellCutGhost45,CellCutGhost26L,CellCutGhost26U,CellCutGhostTent})if(G){G->ClearInstances();G->SetVisibility(false);}
    const FVoxelBuildPrefab* Prefab=SelectedPrefab();
    UStaticMesh* Mesh=Prefab?Prefab->Mesh.LoadSynchronous():nullptr;
    if(!Prefab||!Mesh||!bPrefabAimHit){Preview->SetVisibility(false,true);HideSiegeRangePreview();return;}
    const bool NewMesh=Preview->GetStaticMesh()!=Mesh;
    Preview->SetStaticMesh(Mesh);
    // 逻辑构件（门）与普通构件的摆放口径不同：前者锚点在占格底面中心、构件自己往上搭，
    // 后者网格包围盒居中于占格。预览必须与 AVoxelBuildWorld::SpawnPrefab 用同一口径，
    // 否则落地的门会比预览高一个半身高（2026-09-17 用户反馈）。
    FTransform Transform;
    const bool bWoodGate=Prefab->Id==VillageBuildDefense::WoodGate;
    const bool Gate=bWoodGate||Prefab->Id==VillageBuildDefense::StoneGate;
    UpdateEntrancePreview(Prefab->Id,bPrefabValid);
    UMaterialInterface* LeafMaterial=PreviewMID.Get();
    if(Gate && bPrefabValid && EntrancePreview && EntrancePreview->GetStaticMesh())
        LeafMaterial=EntrancePreview->GetMaterial(0);
    UMaterialInterface* BodyMaterial=bWoodGate?LeafMaterial:PreviewMID.Get();
    if(NewMesh || Preview->GetMaterial(0)!=BodyMaterial)TintPreviewMesh(*Preview,BodyMaterial);
    if(VillageBuildDefense::IsVillageRecipe(Prefab->Id))
    {
        const auto Size=AVoxelBuildPrefabActor::RotatedFootprint(Prefab->Footprint,PrefabPlanYaw);
        Transform=DefenseDockPose.IsSet()?DefenseDockPose.GetValue():
            VillageBuildDefense::Placement(Prefab->Id,PrefabCell,Size,PrefabPlanYaw,PlannedGroundYaw());
        if(VillageBuildDefense::IsSiegeEngine(Prefab->Id) && SiegeFloorPreview.IsSet())Transform=SiegeFloorPreview.GetValue();
        if(Gate)
        {
            const float Offset=bWoodGate?AVillageDefenseGate::NarrowHingeOffset:0.f;
            Transform.AddToTranslation(Transform.GetRotation().RotateVector(FVector(-Offset,0.,0.)));
            if(PreviewGateAssembly!=Prefab->Id)
            {
                for(UStaticMeshComponent* Old:VillageGatePreviewParts)Old->DestroyComponent();
                VillageGatePreviewParts.Reset();
                GatePreviewLeaf=nullptr;
                PreviewGateAssembly=Prefab->Id;
                const FSoftObjectPath RightLeaf(TEXT("/Game/WorldGeneration/TemperateHills/VillageDefenses/SM_GateNarrowRight.SM_GateNarrowRight"));
                const FSoftObjectPath LeftMount(TEXT("/Game/WorldGeneration/TemperateHills/VillageDefenses/SM_GateHingeMount.SM_GateHingeMount"));
                const FSoftObjectPath RightMount(TEXT("/Game/WorldGeneration/TemperateHills/VillageDefenses/SM_GateHingeMountRight.SM_GateHingeMountRight"));
                auto AddPart=[this,Offset](const FSoftObjectPath& Path,FTransform Relative)
                {
                    auto* Part=NewObject<UStaticMeshComponent>(PreviewActor.Get(),NAME_None,RF_Transient);
                    PreviewActor->AddInstanceComponent(Part);Part->SetupAttachment(Preview);
                    Relative.AddToTranslation(FVector(Offset,0.,0.));
                    Part->SetRelativeTransform(Relative);Part->SetMobility(EComponentMobility::Movable);
                    Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);
                    Part->SetCastShadow(false);Part->SetCanEverAffectNavigation(false);
                    if(auto* PartMesh=Cast<UStaticMesh>(Path.TryLoad()))
                    {
                        Part->SetStaticMesh(PartMesh);
                        TintPreviewMesh(*Part,PreviewMID);
                    }
                    Part->RegisterComponent();VillageGatePreviewParts.Add(Part);
                    return Part;
                };
                if(bWoodGate)
                {
                    GatePreviewLeaf=AddPart(RightLeaf,FTransform(FVector(Offset,0.,0.)));
                    AddPart(LeftMount,FTransform(FVector(-Offset,0.,0.)));
                    AddPart(RightMount,FTransform(FVector(Offset,0.,0.)));
                    AddPart(AVillageDefenseGate::PlacedPostMeshPath(),AVillageDefenseGate::PlacedPostTransform(false));
                    AddPart(AVillageDefenseGate::PlacedPostMeshPath(),AVillageDefenseGate::PlacedPostTransform(true));
                }
                else
                {
                    GatePreviewLeaf=AddPart(AHighVillageGate::PlacedGrilleMeshPath(),FTransform::Identity);
                    AddPart(AHighVillageGate::ReleaseMeshPath(),AHighVillageGate::ReleasePose(false));
                }
                GatePreviewLeaf->SetTranslucentSortPriority(1);
            }
            if(GatePreviewLeaf && GatePreviewLeaf->GetMaterial(0)!=LeafMaterial)
                TintPreviewMesh(*GatePreviewLeaf,LeafMaterial);
        }
    }
    else if(!Prefab->ActorClass.IsNull())
    {
        const FIntVector Size=AVoxelBuildPrefabActor::RotatedFootprint(Prefab->Footprint,PrefabPlanYaw);
        const FQuat Rotation(FRotator(0.f,PrefabPlanYaw*90.f,0.f));
        const FBoxSphereBounds Bounds=Mesh->GetBounds();
        const FVector Centre=FVector(PrefabCell)*20.+FVector(Size.X,Size.Y,0)*10.;
        // 网格包围盒底面贴占格底面，X／Y 居中于占格。
        Transform=FTransform(Rotation,Centre-Rotation.RotateVector(Bounds.Origin)
            +FVector(0,0,Bounds.BoxExtent.Z)+Prefab->PivotOffsetCm);
        // This assembly preserves the native campfire's authored ground-centre
        // origin; the asymmetric crank must not recenter the base or the rack.
        if(Prefab->Id==TEXT("campfire")&&Mesh->GetFName()==FName(TEXT("SM_Campfire_WithRack")))
            Transform=FTransform(Rotation,Centre+Rotation.RotateVector(Prefab->ActorOffsetCm));
    }
    else
    {
        Transform=AVoxelBuildPrefabActor::ComputeTransform(*Prefab,Mesh,PrefabCell,PrefabPlanYaw);
    }
    Preview->SetWorldLocationAndRotation(Transform.GetLocation(),Transform.GetRotation());
    Preview->SetWorldScale3D(Transform.GetScale3D());
    UpdateWallCutPreview();
    for(UStaticMeshComponent* Part:VillageGatePreviewParts)Part->SetVisibility(Gate);
    if(PreviewMID)
    {
        PreviewMID->SetVectorParameterValue(TEXT("Tint"),bPrefabValid?FLinearColor(.06f,1.f,.15f):FLinearColor(1.f,.035f,.02f));
        const FVector Min=FVector(PrefabCell)*20.;
        PreviewMID->SetVectorParameterValue(TEXT("PreviewOrigin"),FLinearColor(Min.X,Min.Y,Min.Z));
    }
    Preview->SetHiddenInGame(false);Preview->SetVisibility(true);
    UpdateSiegeRangePreview(Prefab->Id,Transform.GetLocation(),bPrefabValid);
}

void UVoxelBuildComponent::UpdatePreview(FIntVector Size)
{
    HideSiegeRangePreview();
    if(EntrancePreview)EntrancePreview->SetVisibility(false);
    if(WallCutPreview)WallCutPreview->SetVisibility(false);
    for(UStaticMeshComponent* Part:VillageGatePreviewParts)Part->SetVisibility(false);
    // Component previews switch the ghost mesh; the voxel brush always uses the 20 cm cube.
    if(Preview&&GhostMesh&&Preview->GetStaticMesh()!=GhostMesh)
    {
        Preview->SetStaticMesh(GhostMesh);
        if(PreviewMID)Preview->SetMaterial(0,PreviewMID);
    }
    // 2026-10-14 修复：屋顶阶梯族（坡/山墙/金字塔）用逐格 ghost 表达真实排列——整体拉伸盒
    // 在斜坡包围盒上就是一整面墙，玩家看到的"预览与设计不符"正是它。逐格实例复用同一个
    // PreviewMID（红绿有效色/网格材质与整体盒一致）；FoundationPreview（贴地角标/地基柱）
    // 不抢占：贴地放置时地基格也在 Placement 里，逐格 ghost 自然带出。
    if(ShapeIsStaircase(Brush)&&!Placement.IsEmpty())
    {
        if(Preview)Preview->SetVisibility(false);
        if(CellGhost)
        {
            // 2026-10-15：楔形切割格走专属 ghost（pattern 分 45/26L/26U，方向带 yaw；+X=0°
            // +Y=90° -X=180° -Y=270°），网格缺资产时该格回落立方。立方格（山墙/金字塔/
            // 地基柱）仍在 CellGhost。
            TArray<FTransform> Cubes,P45,P26L,P26U,PTent;
            for(int32 I=0;I<Placement.Num();++I)
            {
                const FVector Min=PlacementOrigin+AVoxelBuildWorld::CellMin(Placement[I]);
                const uint8 Cut=I<PlacementCuts.Num()?PlacementCuts[I]:0;
                UInstancedStaticMeshComponent* Target=nullptr;
                if(Cut)
                {
                    switch(VoxelCut::Pattern(Cut))
                    {case 1:Target=CellCutGhost26L;break;case 2:Target=CellCutGhost26U;break;
                     case 3:Target=CellCutGhostTent;break;default:Target=CellCutGhost45;}
                }
                if(!Target)Cubes.Emplace(FQuat::Identity,Min+FVector(10),FVector(.2f,.2f,.2f));
                else if(Target==CellCutGhostTent)
                {
                    // 帐篷网格按脊沿 Y 烘制；Dir 3/4（脊沿 X）转 90°。
                    const double Yaw=VoxelCut::Dir(Cut)>=3?90.:0.;
                    const FTransform T(FQuat(FVector::UpVector,FMath::DegreesToRadians(Yaw)),Min+FVector(10));
                    PTent.Add(T);
                }
                else
                {
                    constexpr double YawByDir[5]={0.,0.,180.,90.,270.};   // 下标=VoxelCut::Dir(1..4)
                    const FTransform T(FQuat(FVector::UpVector,FMath::DegreesToRadians(YawByDir[VoxelCut::Dir(Cut)])),Min+FVector(10));
                    if(Target==CellCutGhost45)P45.Add(T);else if(Target==CellCutGhost26L)P26L.Add(T);else P26U.Add(T);
                }
            }
            auto Push=[&](UInstancedStaticMeshComponent* Comp,const TArray<FTransform>& T)
            {
                if(!Comp||T.IsEmpty()){if(Comp){Comp->ClearInstances();Comp->SetVisibility(false);}return;}
                if(Comp->GetInstanceCount()==T.Num())Comp->BatchUpdateInstancesTransforms(0,const_cast<TArray<FTransform>&>(T),true,true,true);
                else{Comp->ClearInstances();Comp->AddInstances(const_cast<TArray<FTransform>&>(T),false,true,false);}
                Comp->SetHiddenInGame(false);Comp->SetVisibility(true);
            };
            Push(CellGhost,Cubes);Push(CellCutGhost45,P45);Push(CellCutGhost26L,P26L);Push(CellCutGhost26U,P26U);Push(CellCutGhostTent,PTent);
            if(PreviewMID)
            {
                PreviewMID->SetVectorParameterValue(TEXT("Tint"),bCanPlace?FLinearColor(.06f,1.f,.15f):FLinearColor(1.f,.035f,.02f));
                const FVector Min=PlacementOrigin+AVoxelBuildWorld::CellMin(Placement[0]);
                PreviewMID->SetVectorParameterValue(TEXT("PreviewOrigin"),FLinearColor(Min.X,Min.Y,Min.Z));
            }
        }
        return;
    }
    for(UInstancedStaticMeshComponent* G:{CellGhost,CellCutGhost45,CellCutGhost26L,CellCutGhost26U,CellCutGhostTent})if(G)G->SetVisibility(false);
    if(Preview&&!Placement.IsEmpty())
    {
        const FVector Half=FVector(Size)*10;
        const FVector Min=PlacementOrigin+AVoxelBuildWorld::CellMin(Placement[0]);
        Preview->SetWorldLocation(Min+Half);
        // ~1.2 cm larger on every side (cube is 100 cm): the ghost stays visible when the next cell
        // touches or sits inside existing blocks, which is exactly the upward-building case.
        Preview->SetWorldScale3D(FVector(Size)*.2+FVector(.024));
        if(PreviewMID)
        {
            PreviewMID->SetVectorParameterValue(TEXT("Tint"),bCanPlace?FLinearColor(.06f,1.f,.15f):FLinearColor(1.f,.035f,.02f));
            PreviewMID->SetVectorParameterValue(TEXT("PreviewOrigin"),FLinearColor(Min.X,Min.Y,Min.Z));
        }
        Preview->SetHiddenInGame(false);
        Preview->SetVisibility(true);
        // One instanced box per foundation column, not an Actor per voxel.
        // All transforms use the same world-space plan that is committed.
        if(FoundationPreview)
        {
            TMap<FIntPoint,int32> Bottoms;
            const int32 MainCells=Size.X*Size.Y*Size.Z;
            for(int32 I=MainCells;I<Placement.Num();++I)
            {
                const auto Cell=Placement[I];const FIntPoint Column(Cell.X,Cell.Y);
                if(auto* Bottom=Bottoms.Find(Column))*Bottom=FMath::Min(*Bottom,Cell.Z);
                else Bottoms.Add(Column,Cell.Z);
            }
            TArray<FTransform> Transforms;
            for(const auto& Column:Bottoms)
            {
                const FVector Bottom=PlacementOrigin+AVoxelBuildWorld::CellMin(FIntVector(Column.Key.X,Column.Key.Y,Column.Value));
                const double Height=Min.Z-Bottom.Z;
                Transforms.Emplace(FQuat::Identity,Bottom+FVector(10,10,Height*.5),FVector(.2,.2,Height/100.));
            }
            if(FoundationPreview->GetInstanceCount()==Transforms.Num())
            {
                if(!Transforms.IsEmpty())FoundationPreview->BatchUpdateInstancesTransforms(0,Transforms,true,true,true);
            }
            else
            {
                FoundationPreview->ClearInstances();
                if(!Transforms.IsEmpty())FoundationPreview->AddInstances(Transforms,false,true,false);
            }
            FoundationPreview->SetHiddenInGame(false);FoundationPreview->SetVisibility(!Transforms.IsEmpty());
        }
    }
}

int32 UVoxelBuildComponent::ClipLocalPlayerCells(TArray<FIntVector>& Cells,FVector Origin,TArray<uint8>* ParallelCuts) const
{
    // The world refuses any cell that intersects a character, and one refused cell rejects the whole
    // brush. Standing on your own wall therefore used to block the next 5-cell-high wall brush
    // entirely. Drop only the cells that really contain the local player; the rest is still built.
    auto* PC=Cast<APlayerController>(GetOwner());
    APawn* Pawn=PC?PC->GetPawn():nullptr;
    UCapsuleComponent* Capsule=Pawn?Pawn->FindComponentByClass<UCapsuleComponent>():nullptr;
    if(!Capsule||!Capsule->IsCollisionEnabled()||Cells.IsEmpty())return 0;
    // Runs every frame now, so bail out unless the plan's box actually overlaps the body box:
    // building away from yourself is the common case and must stay allocation free.
    FBox PlanBounds(ForceInit);
    for(const FIntVector& Cell:Cells)
    {
        const FVector Min=Origin+AVoxelBuildWorld::CellMin(Cell);
        PlanBounds+=FBox(Min,Min+FVector(20));
    }
    if(!PlanBounds.Intersect(Capsule->Bounds.GetBox()))return 0;
    const float Radius=Capsule->GetScaledCapsuleRadius();
    const float Half=Capsule->GetScaledCapsuleHalfHeight();
    const FVector Up=Capsule->GetUpVector();
    const FVector A=Capsule->GetComponentLocation()+Up*FMath::Max(0.f,Half-Radius);
    const FVector B=Capsule->GetComponentLocation()-Up*FMath::Max(0.f,Half-Radius);
    const TArray<FIntVector> Original=Cells;
    // 平行切割字节同步裁剪（2026-10-16 自检发现）：RemoveAll 移动元素后下标平移，
    // PlacementCuts 不跟着裁会让楔形切口落到错误的格上。
    TArray<uint8> OriginalCuts;
    if(ParallelCuts)OriginalCuts=*ParallelCuts;
    const int32 Removed=Cells.RemoveAll([&](const FIntVector& Cell)
    {
        const FVector Min=Origin+AVoxelBuildWorld::CellMin(Cell);
        const FBox Box(Min+FVector(.25),Min+FVector(19.75));
        const FVector Nearest=FMath::ClosestPointOnSegment(Box.GetCenter(),A,B);
        return FVector::DistSquared(Box.GetClosestPointTo(Nearest),Nearest)<double(Radius)*Radius;
    });
    if(ParallelCuts&&Removed>0)
    {
        // 幸存格保持原序，双指针按值配对重建（格子无重复，见上游去重）。
        TArray<uint8> Kept;Kept.Reserve(Cells.Num());
        int32 J=0;
        for(int32 I=0;I<Original.Num()&&J<Cells.Num();++I)
            if(Original[I]==Cells[J]){Kept.Add(I<OriginalCuts.Num()?OriginalCuts[I]:0);++J;}
        *ParallelCuts=MoveTemp(Kept);
    }
    if(Cells.IsEmpty())
    {
        // Nothing left to build: keep the original plan so the normal "位置被角色占用" message shows.
        Cells=Original;if(ParallelCuts)*ParallelCuts=MoveTemp(OriginalCuts);return 0;
    }
    return Removed;
}

void UVoxelBuildComponent::ValidatePlacement()
{
    // 审计 C3：同文件其它入口（UpdateTarget:566、UpdatePrefabTarget:843）都检查了 BuildWorld，
    // 这里没有。当前调用链上 UpdateTarget 已提前返回所以不可达，但本函数是私有成员、
    // 将来可能被新路径调用，补上防御。
    if(!BuildWorld)return;
    const double Now=GetWorld()->GetTimeSeconds();
    const bool Changed=CheckedRevision!=BuildWorld->StructureRevision()||CheckedMaterial!=PlacementMaterial||
        bCheckedSnap!=bPlacementSnap||CheckedVolume!=PlacementVolume||CheckedOrigin!=PlacementOrigin||CheckedCells!=Placement||
        CheckedCuts!=PlacementCuts;
    if(Changed||Now>=PlacementCheckAt)
    {
        const TArray<uint8>* PlacementShapeBytes=PlacementCuts.Num()==Placement.Num()?&PlacementCuts:nullptr;
        bCheckedValid=bPlacementSnap?BuildWorld->CanPlaceInVolume(PlacementVolume,Placement,PlacementMaterial,CheckedMessage,PlacementShapeBytes):
            BuildWorld->CanPlaceFree(PlacementOrigin,Placement,PlacementMaterial,CheckedMessage,PlacementShapeBytes);
        // 诊断：默认关闭（fps.Building.DebugLog 1），只在拒绝原因变化时记一行。
        if(VoxelBuildDebug::Enabled()&&!bCheckedValid&&!LastPreviewReject.Equals(CheckedMessage))
        {
            LastPreviewReject=CheckedMessage;
            UE_LOG(LogTemp,Warning,TEXT("VOXEL_REJECT stage=preview origin=%.1f,%.1f,%.1f snap=%d cells=%d message=%s"),
                PlacementOrigin.X,PlacementOrigin.Y,PlacementOrigin.Z,bPlacementSnap?1:0,Placement.Num(),*CheckedMessage);
        }
        CheckedRevision=BuildWorld->StructureRevision();CheckedMaterial=PlacementMaterial;bCheckedSnap=bPlacementSnap;
        CheckedVolume=PlacementVolume;CheckedOrigin=PlacementOrigin;CheckedCells=Placement;CheckedCuts=PlacementCuts;
        PlacementCheckAt=Now+.1;
    }
    bCanPlace=bCheckedValid;TargetMessage=CheckedMessage;
}

