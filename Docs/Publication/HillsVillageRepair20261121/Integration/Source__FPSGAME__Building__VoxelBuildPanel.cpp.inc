// Source/FPSGAME/Building/VoxelBuildPanel.cpp
// Merge each excerpt at the named target and scope. Line numbers locate the 2026-11-21 production source.

// Lines 67-67 | void UVoxelBuildComponent::SetPanelOpen(bool Open)
    if(Open)RefreshVillageConstructionAccess();

// Lines 152-159 | void UVoxelBuildComponent::SelectComponent(FName Id)
    if(VillageBuildDefense::IsVillageRecipe(Id)&&!CanBuildVillagePieces())
    {
        Feedback=TEXT("请先在丘陵村庄的修女处解锁「村庄修建」");
        FeedbackTime=2.5f;
        bFeedbackValid=false;
        RefreshVillageConstructionAccess();
        return;
    }

// Lines 164-164 | void UVoxelBuildComponent::SelectComponent(FName Id)
    ComponentYaw=PrefabPlanYaw=GroundYawDegrees=0;DefenseDockPose.Reset();DefenseDockTarget.Reset();AimedPrefab=nullptr;bPrefabValid=false;

// Lines 170-187 | bool UVoxelBuildComponent::CanBuildVillagePieces() const
bool UVoxelBuildComponent::CanBuildVillagePieces() const
{
    const auto* Hills=VillageWorld.Get();
    return Hills&&Hills->IsVillagePlanUnlocked(TEXT("village_construction"));
}

void UVoxelBuildComponent::RefreshVillageConstructionAccess()
{
    const bool bUnlocked=CanBuildVillagePieces();
    if(Widget)Widget->SetVillageConstructionUnlocked(bUnlocked);
    if(bUnlocked||!VillageBuildDefense::IsVillageRecipe(SelectedComponent))return;
    SelectedComponent=NAME_None;
    ComponentYaw=0;
    AimedPrefab=nullptr;
    bPrefabValid=false;
    TargetUpdateAt=PlacementCheckAt=0;
    if(Widget)Widget->SetSelection(SelectedMaterial,SelectedComponent,Brush);
    if(bActive&&!bPanelOpen)SetPanelOpen(true);

// Lines 291-299 | void UVoxelBuildComponent::PushPanelContent()
        const bool bVillage=VillageBuildDefense::IsVillageRecipe(Entry.Id);
        const bool bWallStairs=Entry.Id==VillageWallStairs::Id;
        Card.Rows.Add({TEXT("归属构造"),bVillage?FString(TEXT("村庄建筑")):
            Group?(Group->DisplayName.IsEmpty()?Group->Id.ToString():Group->DisplayName.ToString()):FString(TEXT("其他（未归类）"))});
        Card.Rows.Add({TEXT("占格尺寸"),Card.Detail});
        Card.Rows.Add({TEXT("20 cm 占格"),FString::Printf(TEXT("%d × %d × %d"),Entry.Footprint.X,Entry.Footprint.Y,Entry.Footprint.Z)});
        Card.Rows.Add({TEXT("放置方式"),bWallStairs?TEXT("地面放置或对接高墙步道"):
            (Entry.Id==VillageBuildDefense::HighWall||Entry.Id==VillageBuildDefense::StoneGate)?TEXT("落地或吸附至城防接口"):
            bWall?TEXT("壁挂 · 朝向跟随墙面"):TEXT("表面放置 · 可切换吸附")});

// Lines 303-331 | void UVoxelBuildComponent::PushPanelContent()
        if(bVillage)
        {
            Card.Rows.Add({TEXT("解锁条件"),TEXT("修女 · 村庄修建")});
            if(bWallStairs)
            {
                Card.Subtitle=TEXT("村庄城防 · 折返石阶");
                Card.Note=TEXT("沿平台折返登上 3.6 米步道。地面滚轮每格旋转 1°。瞄准完好高墙内侧时，用滚轮选择平台的对接边。");
            }
            else if(Entry.Id==VillageBuildDefense::HighWall)
            {
                Card.Subtitle=TEXT("村庄城防 · 带城垛的石墙");
                Card.Note=TEXT("地面滚轮每格旋转 1°。将墙端接到高墙或石城门侧面，滚轮切换接法。步道朝村内，可接城墙石阶。");
            }
            else if(Entry.Id==VillageBuildDefense::StoneGate)
            {
                Card.Subtitle=TEXT("村庄城防 · 石拱门与升降铁闸");
                Card.Note=TEXT("门洞净宽 6.6 米，按 E 升降铁闸。二层守卫平台连通两侧墙顶，城墙石阶可另接在内侧。");
            }
            else if(Entry.Id==VillageBuildDefense::WoodGate)
            {
                Card.Subtitle=TEXT("村庄城防 · 双扇木门");
                Card.Note=TEXT("地面滚轮每格旋转 1°。两扇木门向两侧开启，放置时请留足摆动空间。");
            }
            else
            {
                Card.Subtitle=TEXT("村庄城防 · 砌石墙段");
                Card.Note=TEXT("地面滚轮每格旋转 1°。沿边界连续放置墙段，留出大门的通行位置。");
            }
        }

// Lines 364-367 | void UVoxelBuildComponent::UpdateWidget()
    const bool bDocked=!SelectedComponent.IsNone()&&DefenseDockPose.IsSet();
    const int32 GroundYaw=PlannedGroundYaw();
    const int32 ShownYaw=bDocked?FMath::RoundToInt(FRotator::ClampAxis(DefenseDockPose->Rotator().Yaw))%360:
        (GroundYaw!=INDEX_NONE?GroundYaw:PrefabPlanYaw*90);

// Lines 372-372 | void UVoxelBuildComponent::UpdateWidget()
        |(uint64)(PrefabPlanYaw&3)<<26|(uint64)(SelectedPrefab()?1:0)<<28

// Lines 385-387 | void UVoxelBuildComponent::UpdateWidget()
        |(JointBits<<40)|(SignalBits<<52);
    const uint64 LayoutKey=CheapKey^GetTypeHash(SelectedComponent)^(uint64(ShownYaw)<<46);
    if(LayoutKey==LastWidgetCheapKey&&Revision==LastWidgetRevision)

// Lines 392-392 | void UVoxelBuildComponent::UpdateWidget()
    LastWidgetCheapKey=LayoutKey;LastWidgetRevision=Revision;

// Lines 413-413 | void UVoxelBuildComponent::UpdateWidget()
        const FIntVector Footprint=AVoxelBuildPrefabActor::RotatedFootprint(Prefab->Footprint,PrefabPlanYaw);

// Lines 415-416 | void UVoxelBuildComponent::UpdateWidget()
            bDocked?FString::Printf(TEXT("%s · %d° · 滚轮调向"),SelectedComponent==VillageWallStairs::Id?TEXT("平台已对齐步道"):TEXT("城防接口已对齐"),ShownYaw):
                FString::Printf(TEXT("构件 · %d × %d × %d cm · %d°"),Footprint.X*20,Footprint.Y*20,Footprint.Z*20,ShownYaw),
