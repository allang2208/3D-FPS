// 冶炼面板视觉审计（先例：ColdSteelInventoryVisualAudit.cpp）。
// 独立进程启动（见 Tools/UI/run_smelting_visual_acceptance.ps1）：-game 地图 DayNight_Lighting，
// -SmeltingVisualAudit 触发，-ColdSteelProfile=SmeltingVisualAudit_* 把角色档与体素世界档一并隔离
// （WorldKey＝ProfileSlot＋"|"＋地图），绝不读写用户世界。放一台高炉→配料→起炉，
// 依次截「冶炼中／停炉／完成／空闲选料」四态到 Saved/SmeltingVisual，供人工读图与像素测量。
#include "ColdSteelHUDWidget.h"
#include "ColdSteelSmeltingWidget.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelInventoryTypes.h"
#include "../Building/SmeltingSystem.h"
#include "../Building/VoxelBuildWorld.h"
#include "../Building/VoxelBuildPrefabActor.h"
#include "Blueprint/WidgetTree.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "Engine/GameInstance.h"
#include "EngineUtils.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "TimerManager.h"
#include "UObject/GarbageCollection.h"
#include "UnrealClient.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "HAL/FileManager.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"

void UColdSteelHUDWidget::RunSmeltingVisualAudit()
{
    auto* Model=GetGameInstance()?GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
    auto* System=GetGameInstance()?GetGameInstance()->GetSubsystem<UColdSteelSmeltingSystem>():nullptr;
    if(!Model||!System||!Model->IsAudit())return;   // 只允许跑在隔离的 Audit 档上
    struct FRun{int32 Phase=0,Tries=0,Checks=0,Failures=0;bool bDone=false;FTimerHandle Timer;
        TWeakObjectPtr<AVoxelBuildWorld> W;TWeakObjectPtr<AVoxelBuildPrefabActor> Piece;
        FIntVector Cell;FName Recipe;double Fuel0=0.0;bool bFuelChecked=false;
        FString FuelTxt0;bool bFuelMoved=false;double Idle0=0.0;};
    auto R=MakeShared<FRun>();
    auto Check=[R](bool Pass,const FString& Name)
    {   ++R->Checks;if(!Pass)++R->Failures;
        UE_LOG(LogTemp,Display,TEXT("SmeltingVisualAudit: %s %s"),Pass?TEXT("PASS"):TEXT("FAIL"),*Name);};
    auto Finish=[this,R](const TCHAR* Tail)
    {   if(R->bDone)return;R->bDone=true;
        UE_LOG(LogTemp,Display,TEXT("SmeltingVisualAudit: %s checks=%d failures=%d"),Tail,R->Checks,R->Failures);
        GetOwningPlayer()->ConsoleCommand(TEXT("quit"));};
    auto Cleanup=[R](){if(auto* W=R->W.Get())if(R->Piece.IsValid())W->RemovePrefab(R->Piece.Get());};
    auto Shot=[this](const TCHAR* Name)
    {   const FString Dir=FPaths::ProjectSavedDir()/TEXT("SmeltingVisual");
        IFileManager::Get().MakeDirectory(*Dir,true);
        FScreenshotRequest::RequestScreenshot(Dir/FString::Printf(TEXT("%s-%d.png"),Name,
            FMath::RoundToInt32(UWidgetLayoutLibrary::GetViewportSize(this).X)),true,false);};
    // 实时消耗闸门（重试版）：首载卡顿时相邻两拍可能被挤进同一帧，单次采样不可信；
    // T=10/11 重试、T=12 终判（≥0.9s 挂钟窗口），通过即计一次，不重复计数。
    // 双证据：底层 FuelAt 必须下降 ＋ 面板读数行文案必须逐秒变化（2026-09-24 用户"一直显示 10 秒"）。
    auto FuelCheck=[this,R,Check](bool bFinal)
    {   if(R->bFuelChecked&&R->bFuelMoved)return;
        auto* W=R->W.Get();if(!W||R->Fuel0<=0.0)return;
        const double NowF=W->FuelAt(R->Cell);
        const FString Msg=FString::Printf(TEXT("fuel burns in real time (%.1fs -> %.1fs)"),R->Fuel0,NowF);
        if(!R->bFuelChecked)
        {   if(NowF<R->Fuel0-0.15){R->bFuelChecked=true;Check(true,Msg);}
            else if(bFinal){R->bFuelChecked=true;Check(false,Msg);}   }
        if(auto* P=SmeltingWidget.Get())
        {   if(!R->bFuelMoved&&P->DebugFuelLineText()!=R->FuelTxt0){R->bFuelMoved=true;Check(true,TEXT("fuel countdown text ticks"));}
            else if(!R->bFuelMoved&&bFinal)Check(false,FString::Printf(TEXT("fuel countdown text ticks (stuck at '%s')"),*R->FuelTxt0));   }
    };
    GetWorld()->GetTimerManager().SetTimer(R->Timer,FTimerDelegate::CreateWeakLambda(this,[this,Model,System,R,Check,Finish,Cleanup,Shot,FuelCheck]()
    {
        if(R->bDone)return;
        // —— 相位机：每 0.3s 一步；状态改变后留 3 拍让面板 0.1s 节流刷新与截图异步落盘。——
        const int32 T=R->Phase++;
        if(T>60){Cleanup();Finish(TEXT("TIMEOUT"));return;}
        switch(T)
        {
        case 0:   // 等体素世界生成并初始化（组件在 PlayerController BeginPlay 后自建）
        {
            for(TActorIterator<AVoxelBuildWorld> It(GetWorld());It;++It){R->W=*It;break;}
            AVoxelBuildWorld* W=R->W.Get();
            if(!W||!W->IsReady()){R->Phase=0;if(++R->Tries>60){Finish(TEXT("ABORT"));return;}}
            return;
        }
        case 1:   // 玩家前／右／更前方三列探针放高炉（PlacePrefab 自带支撑校验，逐格上下试）
        {
            auto* W=R->W.Get();auto* Pawn=GetOwningPlayerPawn();
            if(!W||!Pawn){R->Phase=0;return;}
            const FVector Loc=Pawn->GetActorLocation();
            const TArray<FVector> Probes={Loc+Pawn->GetActorForwardVector()*300.f,
                Loc+Pawn->GetActorRightVector()*250.f,Loc+Pawn->GetActorForwardVector()*450.f};
            bool bPlaced=false;
            for(const FVector& Pr:Probes)for(int32 dz=-6;dz<=6&&!bPlaced;++dz)
            {
                const FIntVector C=AVoxelBuildWorld::ToCell(Pr+FVector(0.f,0.f,20.f*dz));
                if(W->PlacePrefab(VoxelSmeltingFurnaceId,C,0)){R->Cell=C;bPlaced=true;}
            }
            Check(bPlaced,bPlaced?FString::Printf(TEXT("furnace placed @cell(%d,%d,%d)"),R->Cell.X,R->Cell.Y,R->Cell.Z)
                :FString::Printf(TEXT("furnace placement: %s"),*W->ResultMessage()));
            if(!bPlaced){Finish(TEXT("ABORT"));return;}
            for(TActorIterator<AVoxelBuildPrefabActor> It(GetWorld());It;++It)
                if((*It)->PrefabId()==VoxelSmeltingFurnaceId&&(*It)->AnchorCell()==R->Cell&&!(*It)->IsFalling()){R->Piece=*It;break;}
            Check(R->Piece.IsValid(),TEXT("furnace piece actor found"));
            return;
        }
        case 2:   // 配料：目录内每种输入 5 块＋木材 30——摆格走种子同一 Insert API（自带占格与 Footprint 校验）
        {
            auto State=Model->Snapshot();
            auto Give=[&](const FString& Def,int64 Count)
            {   auto I=Model->CreateItem(Def,Count);if(I.Data.IsEmpty())return false;
                return ColdSteelInventory::Insert(State.Items,I);};
            bool All=true;
            for(const FColdSteelSmeltingRecipe& Rec:System->Catalog())All&=Give(Rec.Input,5);
            All&=Give(System->FuelConfig().Item,30);
            All&=Give(TEXT("ironIngot"),32);   // 升级测试货币（v9 三轴：速度/燃料仓/批量各花 10，共 30，留 2 验"铁锭不足"）
            const bool bCommitted=All&&Model->CommitState(State);
            Check(bCommitted,FString::Printf(TEXT("ore and wood fixture committed (%s)"),*Model->ResultMessage()));
            if(!bCommitted){Cleanup();Finish(TEXT("ABORT"));return;}
            return;
        }
        case 3:   // 加燃 3 件（＝180 秒）起炉：挑目录里耗时最长的配方——首载帧率低、世界时间跳得快，
                  // 8 秒配方会在两个相位之间直接烧完（2026-09-23 实测"burning"拍成了"完成"）。
        {
            auto* W=R->W.Get();
            FString Reason;
            const bool bFueled=System->AddFuel(W,R->Cell,Reason)&&System->AddFuel(W,R->Cell,Reason)&&System->AddFuel(W,R->Cell,Reason);
            Check(bFueled,FString::Printf(TEXT("add fuel x3 (%s)"),*Reason));
            const FColdSteelSmeltingRecipe* Longest=&System->Catalog()[0];
            for(const FColdSteelSmeltingRecipe& Rec:System->Catalog())if(Rec.Seconds>Longest->Seconds)Longest=&Rec;
            R->Recipe=Longest->Id;
            const bool bBegan=bFueled&&System->BeginSmelting(W,R->Cell,R->Recipe,Reason);
            Check(bBegan,FString::Printf(TEXT("begin smelting (%s)"),*Reason));
            if(!bBegan){Cleanup();Finish(TEXT("ABORT"));return;}
            if(auto* J=W->FindSmeltingMutable(R->Cell))
            {   const int64 Back=FMath::RoundToInt64(Longest->Seconds*.5*ETimespan::TicksPerSecond);
                J->BurnStartTicks=FDateTime::UtcNow().GetTicks()-Back;W->MarkSmeltingDirty();}
            OpenSmelting(R->Piece.Get());
            Check(bSmeltingOpen,TEXT("panel open via E-equivalent entry"));
            return;
        }
        case 8: return;   // 接力动画预留：抽屉 0.25s 到位后面板再滑出 0.25s（2026-09-24 用户定稿）
        case 9:   // 开面板 0.6s 后：冶炼中（脉冲条＋火星燃料条），面板已落位；记存料与文案基准
            if(T==9){Shot(TEXT("burning"));R->bFuelChecked=false;R->bFuelMoved=false;
                if(auto* W=R->W.Get())R->Fuel0=W->FuelAt(R->Cell);
                if(auto* P=SmeltingWidget.Get())R->FuelTxt0=P->DebugFuelLineText();}return;
        case 10: case 11:   // 实时消耗闸门重试窗口
            FuelCheck(false);return;
        case 12:  // 闸门终判（≥0.9s 挂钟）；再抽干存料并把燃烧起点拨回现在 → "任务中＋零燃料"停炉态
        {
            FuelCheck(true);
            auto* W=R->W.Get();W->SetFuel(R->Cell,0.0);
            if(auto* J=W->FindSmeltingMutable(R->Cell))
            {   J->ProgressSeconds=0;J->BurnStartTicks=FDateTime::UtcNow().GetTicks();W->MarkSmeltingDirty();}
            return;
        }
        case 13:
            if(T==13){Shot(TEXT("starved"));}return;
        case 14:   // 强制到完成态（取出按钮＋Success 标题），燃料仍 0
        {
            auto* W=R->W.Get();
            if(auto* J=W->FindSmeltingMutable(R->Cell))
            {   J->ProgressSeconds=System->Find(R->Recipe)->Seconds;J->BurnStartTicks=0;W->MarkSmeltingDirty();}
            return;
        }
        case 15:
            // 强制完成后 0.3s 抓拍：正好落在 0.55s 扫条闪光的中段（B2 验证）。
            if(T==15){Shot(TEXT("done"));}return;
        case 18:   // 取出产物 → 空炉选料态（矿石行列表与图标是本次审计重点）
        {
            auto* W=R->W.Get();FString Reason;
            Check(System->CollectSmelting(W,R->Cell,Reason),FString::Printf(TEXT("collect ingot (%s)"),*Reason));
            return;
        }
        case 19:   // 批量步进（2026-09-24 批量冶炼）：选铁矿（持有 5 → 最多 5），+ 两拍 → ×3
            if(auto* P=SmeltingWidget.Get())
            {   P->SelectRecipe(System->Catalog()[0].Id);P->HandleBatchPlus();P->HandleBatchPlus();}
            return;
        case 20:
            if(T==20){Shot(TEXT("batch"));}return;
        case 21:   // 升级页签：独立页展开（v10 三页签 Lv.1，详情带默认速度轴）
        {
            if(auto* P=SmeltingWidget.Get())P->HandleUpgradeToggled();
            // v10c 回归（2026-09-24 用户"升级栏下方子选项不可切换"）：先强制 GC（复刻代理被
            // RefreshRows 重清收走的环境），再经真实 OnClicked 委托链点击——断链则下面即红。
            CollectGarbage(RF_NoFlags);
            if(auto* P=SmeltingWidget.Get())
            {   P->DebugClickUpgradeTab(VoxelFurnaceAxisFuelCapacity);
                Check(P->DebugUpgradeSel()==VoxelFurnaceAxisFuelCapacity,TEXT("tab click switches to fuel axis"));
                P->DebugClickUpgradeTab(VoxelFurnaceAxisBatch);
                Check(P->DebugUpgradeSel()==VoxelFurnaceAxisBatch,TEXT("tab click switches to batch axis"));
                P->DebugClickUpgradeTab(VoxelFurnaceAxisSpeed);
                Check(P->DebugUpgradeSel()==VoxelFurnaceAxisSpeed,TEXT("tab click switches back to speed"));   }
            return;
        }
        case 22:
            if(T==22){Shot(TEXT("upgrade-lv1"));}return;
        case 23:   // v9 三轴升级：速度（10）→ 燃料仓（10）→ 每次投料（10），铁锭 32→2
            if(auto* P=SmeltingWidget.Get())P->HandleUpgradeClicked();
            return;
        case 24:
            if(auto* P=SmeltingWidget.Get())P->HandleUpgradeFuelClicked();
            return;
        case 25:
            if(auto* P=SmeltingWidget.Get())P->HandleUpgradeBatchClicked();
            return;
        case 26:
            if(T==26){Shot(TEXT("upgrade-lv2"));}return;   // 三卡同屏：Lv.2/Lv.2/Lv.2 · 持有 2 → 按钮"铁锭不足"
        case 27:   // 关弹层回常规空闲态；三轴等级落账核验必须在拆炉之前（拆炉连记录一起清）
        {
            if(auto* P=SmeltingWidget.Get())P->HandleUpgradeClose();
            if(auto* W=R->W.Get())
            {   Check(W->FurnaceUpgradeLevel(R->Cell,VoxelFurnaceAxisSpeed)==2,TEXT("speed axis Lv.2"));
                Check(W->FurnaceUpgradeLevel(R->Cell,VoxelFurnaceAxisFuelCapacity)==2,TEXT("fuel-capacity axis Lv.2"));
                Check(W->FurnaceUpgradeLevel(R->Cell,VoxelFurnaceAxisBatch)==2,TEXT("batch axis Lv.2"));   }
            return;
        }
        case 28:   // 空闲燃烧（v8 语义，2026-09-24 用户"存料 10 秒挂机不动"定稿）：无任务添料两拍
        {
            auto* W=R->W.Get();FString Reason;
            System->AddFuel(W,R->Cell,Reason);System->AddFuel(W,R->Cell,Reason);
            R->Idle0=W->FuelAt(R->Cell);
            return;
        }
        case 29:
            if(T==29){Shot(TEXT("idle-rows"));}return;
        case 30:   // 0.6s 后：没矿也必须在烧——存料读数要真实下降
        {
            auto* W=R->W.Get();
            if(W)Check(W->FuelAt(R->Cell)<R->Idle0-0.2,
                FString::Printf(TEXT("fuel burns while idle (%.1fs -> %.1fs)"),R->Idle0,W->FuelAt(R->Cell)));
            return;
        }
        case 31:   // 收场：关面板、拆炉（隔离档随之作废）、汇报并退出
        {
            CloseSmelting();Cleanup();
            if(auto* W=R->W.Get())Check(W->PrefabCount()==0,FString::Printf(TEXT("furnace removed (prefabs=%d)"),W->PrefabCount()));
            // 2026-09-24 回头审查的两个回归点：拆炉必须连等级记录一起清（同格重建不白捡旧等级）；
            // 燃料仓轴 Lv5→6 的成本必须按曲线是 50 锭（曾被写死的五档封顶算成 0 锭免费）。
            if(auto* W=R->W.Get())Check(W->FurnaceUpgradeLevel(R->Cell,VoxelFurnaceAxisFuelCapacity)==1,TEXT("levels erased with the furnace"));
            Check(UColdSteelSmeltingSystem::UpgradeCostFor(5)==50,TEXT("fuel Lv5 upgrade costs 50"));
            Finish(TEXT("COMPLETE"));
            return;
        }
        default:return;
        }
    }),.3f,true);
}
