#include "WoodworkingSystem.h"
#include "../Multiplayer/ColdSteelStationNetwork.h"
#include "WoodworkingQuality.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/GameStateBase.h"
#include "Serialization/MemoryWriter.h"
#include "HAL/PlatformTime.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"

void UWoodworkingSystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);Collection.InitializeDependency<UColdSteelStatusModel>();
    Collection.InitializeDependency<UColdSteelCraftingSystem>();Load();
}
void UWoodworkingSystem::Deinitialize(){Close();Super::Deinitialize();}
void UWoodworkingSystem::Load()
{
    ConfigError=TEXT("木工配置缺失或格式无效，无法开始");
    FString Raw;TSharedPtr<FJsonObject> Root;
    if(!FFileHelper::LoadFileToString(Raw,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/woodworking.json")))
        ||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Raw),Root)||!Root)return;
    double Version=0;if(!Root->TryGetNumberField(TEXT("version"),Version)||Version!=1)return;
    const TSharedPtr<FJsonObject>* Options=nullptr;if(!Root->TryGetObjectField(TEXT("settings"),Options)||!Options||!Options->IsValid())return;
    auto Number=[&](const TCHAR* Key,double& Out,double Min,double Max)
    {double Value=0;if(!(*Options)->TryGetNumberField(Key,Value)||!FMath::IsFinite(Value)||Value<Min||Value>Max)return false;Out=Value;return true;};
    auto Integer=[&](const TCHAR* Key,int32& Out,int32 Min,int32 Max)
    {double Value=0;if(!Number(Key,Value,Min,Max)||FMath::FloorToDouble(Value)!=Value)return false;Out=int32(Value);return true;};
    if(!Integer(TEXT("maskWidth"),Rules.Width,64,768)||!Integer(TEXT("maskHeight"),Rules.Height,64,512)
        ||!Integer(TEXT("undoCount"),Rules.UndoLimit,0,10)||!Integer(TEXT("edgeBandPixels"),Rules.EdgeBandPixels,1,16)
        ||!Number(TEXT("timeSeconds"),Rules.Seconds,5,600)||!Number(TEXT("requiredClearance"),Rules.RequiredClearance,.5,1)
        ||!Number(TEXT("maximumDamage"),Rules.MaximumDamage,0,.5)
        ||!Number(TEXT("integrityWeight"),Rules.IntegrityWeight,0,1)||!Number(TEXT("edgeWeight"),Rules.EdgeWeight,0,1)
        ||!Number(TEXT("clearanceWeight"),Rules.ClearanceWeight,0,1)||!Number(TEXT("speedWeight"),Rules.SpeedWeight,0,.1)
        ||Rules.IntegrityWeight+Rules.EdgeWeight+Rules.ClearanceWeight<=0
        ||!(*Options)->TryGetBoolField(TEXT("autoPeel"),Rules.bAutoPeel)||!(*Options)->TryGetBoolField(TEXT("checkConnections"),Rules.bCheckConnections))return;
    const TArray<TSharedPtr<FJsonValue>>* Patterns=nullptr;
    if(!Root->TryGetArrayField(TEXT("patterns"),Patterns)||Patterns->IsEmpty()||Patterns->Num()>16)return;
    TArray<FWoodworkingPattern> Parsed;
    auto Points=[](const FJsonObject& O,const TCHAR* Key,TArray<FVector2D>& Out)
    {
        const TArray<TSharedPtr<FJsonValue>>* Values=nullptr;if(!O.TryGetArrayField(Key,Values)||Values->Num()>128)return false;
        for(const auto& V:*Values)
        {
            const TArray<TSharedPtr<FJsonValue>>* XY=nullptr;double X=0,Y=0;
            if(!V->TryGetArray(XY)||XY->Num()!=2||!(*XY)[0]->TryGetNumber(X)||!(*XY)[1]->TryGetNumber(Y)||!FMath::IsFinite(X)||!FMath::IsFinite(Y))return false;
            Out.Add(FVector2D(X,Y));
        }return true;
    };
    for(const auto& V:*Patterns)
    {
        const TSharedPtr<FJsonObject>* O=nullptr;FWoodworkingPattern P;FString Id,Recipe;
        if(!V->TryGetObject(O)||!O||!O->IsValid()||!(*O)->TryGetStringField(TEXT("id"),Id)||Id.IsEmpty()
            ||!(*O)->TryGetStringField(TEXT("name"),P.Name)||P.Name.IsEmpty()||!(*O)->TryGetStringField(TEXT("craftRecipe"),Recipe)
            ||!Points(**O,TEXT("outline"),P.Outline)||!Points(**O,TEXT("connections"),P.Connections))return;
        P.Id=FName(*Id);P.CraftRecipe=FName(*Recipe);
        (*O)->TryGetStringField(TEXT("description"),P.Description);
        (*O)->TryGetStringField(TEXT("instructions"),P.Instructions);
        (*O)->TryGetStringField(TEXT("difficulty"),P.Difficulty);
        P.Seconds=Rules.Seconds;P.RequiredClearance=Rules.RequiredClearance;P.MaximumDamage=Rules.MaximumDamage;
        (*O)->TryGetNumberField(TEXT("timeSeconds"),P.Seconds);
        (*O)->TryGetNumberField(TEXT("requiredClearance"),P.RequiredClearance);
        (*O)->TryGetNumberField(TEXT("maximumDamage"),P.MaximumDamage);
        if(!FMath::IsFinite(P.Seconds)||P.Seconds<5||P.Seconds>600||!FMath::IsFinite(P.RequiredClearance)||P.RequiredClearance<.5||P.RequiredClearance>1||!FMath::IsFinite(P.MaximumDamage)||P.MaximumDamage<0||P.MaximumDamage>.5)return;
        if(Parsed.ContainsByPredicate([&](const auto& Existing){return Existing.Id==P.Id;}))return;
        ColdSteelWoodworking::FMask Candidate;FString Why;if(!Candidate.Initialize(Rules,P.Outline,P.Connections,Why)){ConfigError=Why+TEXT("：")+P.Name;return;}
        // Only registered production recipes belong in the workbench's selectable catalog.
        if(!P.CraftRecipe.IsNone()&&GetGameInstance()->GetSubsystem<UColdSteelCraftingSystem>()->Find(P.CraftRecipe))Parsed.Add(MoveTemp(P));
    }
    if(Parsed.IsEmpty()){ConfigError=TEXT("暂无已配置的木工制作配方");return;}
    // Optional game-only device parameters. They do not alter scoring or inventory rules.
    const TSharedPtr<FJsonObject>* Saw=nullptr;
    if(Root->TryGetObjectField(TEXT("saw"),Saw)&&Saw&&Saw->IsValid())
    {
        auto ReadSaw=[&](const TCHAR* Key,double& Value,double Min,double Max)
        {double N;if((*Saw)->TryGetNumberField(Key,N)&&FMath::IsFinite(N))Value=FMath::Clamp(N,Min,Max);};
        ReadSaw(TEXT("kerfPixels"),SawRules.Kerf,1,6);
        ReadSaw(TEXT("centimetersPerPixel"),SawRules.CentimetersPerPixel,.1,.5);
        ReadSaw(TEXT("rotationStepDegrees"),SawRules.RotationStep,1,15);
        ReadSaw(TEXT("maximumFeedStepPixels"),SawRules.MaximumFeedStep,8,96);
    }
    using Device=ColdSteelWoodworking::FDeviceGeometry;
    const double Height=Device::StockBottom+Device::StockThickness-Device::SawHeight;
    SawRules.ContactLength=2*FMath::Sqrt(Device::BladeRadius*Device::BladeRadius-Height*Height)/SawRules.CentimetersPerPixel;
    Catalog=MoveTemp(Parsed);ConfigError.Reset();Selected=Catalog[0].Id;
}
const FWoodworkingPattern* UWoodworkingSystem::Pattern() const
{return Catalog.FindByPredicate([this](const auto& P){return P.Id==Selected;});}
bool UWoodworkingSystem::Open(bool PracticeOnly)
{
    if(PracticeOnly){Notice=TEXT("请使用木工工作台进行正式制作");return false;}
    ColdSteelStationNet::FInputScope NetworkScope;
    if(NetworkScope.Root)ColdSteelStationNet::Input(this,TEXT("wood"),0,NAME_None,0);
    if(!Close())return false;bPracticeOnly=false;bOpen=true;
    if(HasPendingJob())return RestoreJob();
    if(!ConfigError.IsEmpty()){Notice=ConfigError;return false;}
    return Select(Selected.IsNone()?Catalog[0].Id:Selected);
}
bool UWoodworkingSystem::Close()
{
    ColdSteelStationNet::FInputScope Scope;if(Scope.Root)ColdSteelStationNet::Input(this,TEXT("wood"),11);
    const bool Saved=!bOpen||Suspend();
    bMotorOn=bFeeding=false;bOpen=false;
    if(!HasPendingJob()){Phase=EWoodworkingPhase::Abandoned;AcceptedRecipe={};}
    return Saved;
}
bool UWoodworkingSystem::Select(FName Id)
{
    ColdSteelStationNet::FInputScope NetworkScope;
    if(NetworkScope.Root)ColdSteelStationNet::Input(this,TEXT("wood"),1,Id);
    if(!CanSelect())return false;
    const auto* P=Catalog.FindByPredicate([Id](const auto& Entry){return Entry.Id==Id;});if(!P)return false;
    Rules.Seconds=P->Seconds;Rules.RequiredClearance=P->RequiredClearance;Rules.MaximumDamage=P->MaximumDamage;
    FString Why;if(!Board.Initialize(Rules,P->Outline,P->Connections,Why)){Notice=Why;return false;}
    Selected=Id;Phase=EWoodworkingPhase::Preview;FrozenElapsed=0;AcceptedRecipe={};bPractice=false;
    SessionMode=EWoodworkingMode::Craft;ResetBoardPose();bCheckpointReady=true;
    Notice=TEXT("调整方向 · 锯片已降下，可自由拖动和转向。虚线是落刀位置，按空格进入切割。");return true;
}
bool UWoodworkingSystem::CanStart(bool Practice,FString& Reason) const
{
    if(!bOpen||!Pattern()||!ConfigError.IsEmpty()){Reason=ConfigError.IsEmpty()?TEXT("木工面板未就绪"):ConfigError;return false;}
    if(Phase!=EWoodworkingPhase::Preview){Reason=TEXT("请先选择或重新准备工件");return false;}
    if(HasPendingJob()||bClaiming){Reason=TEXT("先领取或废弃上一件工件");return false;}
    if(!GetWorld()){Reason=TEXT("木工制作未就绪");return false;}
    if(Practice||bPracticeOnly){Reason=TEXT("木工台仅提供正式制作");return false;}
    auto* Craft=GetGameInstance()->GetSubsystem<UColdSteelCraftingSystem>();
    const auto* Recipe=Craft?Craft->Find(Pattern()->CraftRecipe):nullptr;
    if(!Recipe){Reason=TEXT("制作配方未配置，暂不消耗材料或发放成品");return false;}
    const auto* M=Model();if(!M||M->CreateItem(Recipe->Output,Recipe->OutputCount).Data.IsEmpty())return false;
    for(const auto& Input:Recipe->Inputs)if(M->CountMaterial(Input.Item)<Input.Count)
    {Reason=FString::Printf(TEXT("缺少 %lld 个%s"),Input.Count-M->CountMaterial(Input.Item),*ColdSteelInventory::Text(M->CreateItem(Input.Item),TEXT("name")));return false;}
    Reason=TEXT("材料充足 · 开始加工时投入材料");return true;
}
bool UWoodworkingSystem::Start(bool Practice)
{return StartMode(Practice?EWoodworkingMode::Practice:EWoodworkingMode::Craft);}
bool UWoodworkingSystem::CanStartMode(EWoodworkingMode Mode,FString& Reason) const
{return CanStart(Mode!=EWoodworkingMode::Craft,Reason);}
bool UWoodworkingSystem::StartMode(EWoodworkingMode Mode)
{
    if(Mode!=EWoodworkingMode::Craft){Notice=TEXT("木工台仅提供正式制作");return false;}
    if(!CanStart(false,Notice))return false;
    if(ColdSteelStationNet::IsClient(this))
    {
        if(!ColdSteelStationNet::Request(this,TEXT("wood.start"),Selected))return false;
        bClaiming=true;Notice=TEXT("等待服务器投入材料");return true;
    }
    if(!PayForJob())return false;
    BeginPaidRun();return Phase==EWoodworkingPhase::Running;
}
bool UWoodworkingSystem::Restart()
{if(!bOpen||HasPendingJob()||bClaiming||Phase==EWoodworkingPhase::Running)return false;return Select(Selected);}
double UWoodworkingSystem::Elapsed() const
{
    const double Value=FrozenElapsed+(MotorRunning()?FMath::Max(0.0,FPlatformTime::Seconds()-StartedAt):0.0);
    return IsTimed()?FMath::Clamp(Value,0.0,Rules.Seconds):Value;
}
double UWoodworkingSystem::Remaining() const {return FMath::Max(0.0,Rules.Seconds-Elapsed());}
void UWoodworkingSystem::Tick(float)
{
    AdvanceClock();
    if(Phase==EWoodworkingPhase::Running&&HasPendingJob()&&!ColdSteelStationNet::IsClient(this)&&FPlatformTime::Seconds()>=NextCheckpointAt)
    {NextCheckpointAt=FPlatformTime::Seconds()+5;SaveCheckpoint();}
}
void UWoodworkingSystem::AdvanceClock()
{
    if(MotorRunning()&&IsTimed()&&Elapsed()>=Rules.Seconds)
    {Board.EndStroke();bFeeding=false;Evaluate(true);}
}
void UWoodworkingSystem::ResetBoardPose()
{
    BoardPose={};BoardPose.Offset=FVector2D(0,Rules.Height*.5+SawRules.ContactLength*.5+24);
    StrokePose=UndoPose=BoardPose;bMotorOn=bFeeding=bUndoPose=false;
}
void UWoodworkingSystem::SawInBoard(const ColdSteelWoodworking::FBoardPose& At,FVector2D& A,FVector2D& B) const
{
    A=At.ToBoard(FVector2D(0,-SawRules.ContactLength*.5),BoardCenter());
    B=At.ToBoard(FVector2D(0,SawRules.ContactLength*.5),BoardCenter());
}
bool UWoodworkingSystem::BeginFeed()
{
    ColdSteelStationNet::FInputScope NetworkScope;
    if(NetworkScope.Root)ColdSteelStationNet::Input(this,TEXT("wood"),3);
    AdvanceClock();if((Phase!=EWoodworkingPhase::Running&&Phase!=EWoodworkingPhase::Preview)||bFeeding)return false;
    StrokePose=BoardPose;StrokeRevision=Board.Revision();bFeeding=true;return true;
}
bool UWoodworkingSystem::MoveBoard(FVector2D WorkDelta)
{
    ColdSteelStationNet::FInputScope NetworkScope;
    if(NetworkScope.Root)ColdSteelStationNet::Input(this,TEXT("wood"),4,NAME_None,0,WorkDelta);
    AdvanceClock();if((Phase!=EWoodworkingPhase::Running&&Phase!=EWoodworkingPhase::Preview)||!bFeeding||!FMath::IsFinite(WorkDelta.X)||!FMath::IsFinite(WorkDelta.Y))return false;
    const FVector2D Target(FMath::Clamp(BoardPose.Offset.X+WorkDelta.X,-double(Rules.Width),double(Rules.Width)),FMath::Clamp(BoardPose.Offset.Y+WorkDelta.Y,-double(Rules.Height)*2,double(Rules.Height)*2));
    WorkDelta=Target-BoardPose.Offset;
    // Consume the full bounded gesture now. Nothing remains queued after mouse release.
    const int32 Steps=FMath::Clamp(FMath::CeilToInt(WorkDelta.Size()/FMath::Min(8.0,SawRules.MaximumFeedStep)),1,512);
    const FVector2D Step=WorkDelta/Steps;bool Moved=false;
    for(int32 I=0;I<Steps;++I)
    {
        if(!MoveBoardStep(Step))break;Moved=true;
        if(Phase!=EWoodworkingPhase::Preview&&Phase!=EWoodworkingPhase::Running)break;
    }
    return Moved;
}
bool UWoodworkingSystem::MoveBoardStep(FVector2D WorkDelta)
{
    ColdSteelWoodworking::FBoardPose Next=BoardPose;Next.Offset+=WorkDelta;
    Next.Offset.X=FMath::Clamp(Next.Offset.X,-double(Rules.Width),double(Rules.Width));
    Next.Offset.Y=FMath::Clamp(Next.Offset.Y,-double(Rules.Height)*2,double(Rules.Height)*2);
    FVector2D A0,B0,A1,B1;SawInBoard(BoardPose,A0,B0);SawInBoard(Next,A1,B1);
    // Adjustment lowers the blade clear of the board. Powered motion cuts the full sweep.
    BoardPose=Next;
    if(bMotorOn&&Board.SawTouches(A0,B0,A1,B1,SawRules.Kerf*.5))
    {Board.BeginStroke();Board.CutSawSweep(A0,B0,A1,B1,SawRules.Kerf*.5);}
    CheckDamage();return true;
}
bool UWoodworkingSystem::RotateBoard(int32 Direction,bool Fine)
{
    ColdSteelStationNet::FInputScope NetworkScope;
    if(NetworkScope.Root)ColdSteelStationNet::Input(this,TEXT("wood"),5,NAME_None,Direction,FVector2D(Fine?1:0,0));
    AdvanceClock();if((Phase!=EWoodworkingPhase::Running&&Phase!=EWoodworkingPhase::Preview)||Direction==0)return false;
    const double Angle=FMath::DegreesToRadians(SawRules.RotationStep)*(Fine?.25:1.0)*(Direction>0?1:-1);
    const bool OwnFeed=!bFeeding;if(OwnFeed&&!BeginFeed())return false;
    // Sub-pixel angular sweeps keep fine turns responsive without skipping damage.
    const int32 Steps=FMath::Clamp(FMath::CeilToInt(FMath::Abs(Angle)*BoardCenter().Size()*2),1,512);
    bool Moved=false;
    for(int32 I=0;I<Steps;++I)
    {
        auto Candidate=BoardPose;Candidate.Angle=FMath::UnwindRadians(Candidate.Angle+Angle/Steps);
        FVector2D A0,B0,A1,B1;SawInBoard(BoardPose,A0,B0);SawInBoard(Candidate,A1,B1);
        BoardPose=Candidate;Moved=true;
        if(bMotorOn&&Board.SawTouches(A0,B0,A1,B1,SawRules.Kerf*.5))
        {Board.BeginStroke();Board.CutSawSweep(A0,B0,A1,B1,SawRules.Kerf*.5);}
        CheckDamage();
        if(Phase!=EWoodworkingPhase::Preview&&Phase!=EWoodworkingPhase::Running)break;
    }
    if(OwnFeed)EndStroke();
    if(Phase==EWoodworkingPhase::Preview||Phase==EWoodworkingPhase::Running)
        Notice=bMotorOn?TEXT("切割中转向同样计入切削 · 空格切回自由调整 · Shift + Q / E 每次 0.25°"):
            TEXT("自由调整 · Q / E 每次 1°，Shift + Q / E 每次 0.25° · 对准虚线后按空格进入切割");
    return Moved;
}
bool UWoodworkingSystem::ToggleMotor()
{
    ColdSteelStationNet::FInputScope NetworkScope;
    if(NetworkScope.Root)ColdSteelStationNet::Input(this,TEXT("wood"),6);
    AdvanceClock();EndStroke();if(Phase!=EWoodworkingPhase::Running)return false;
    if(bMotorOn)
    {
        FrozenElapsed=Elapsed();bMotorOn=false;
        Notice=TEXT("调整方向 · 锯片已降下，计时暂停，可自由移动和转向；切口与损伤保留。");
    }
    else
    {
        StartedAt=FPlatformTime::Seconds();bMotorOn=true;
        Notice=TEXT("继续切割 · 已从当前位置落刀；按空格可再次调整方向，计时不会重置。");
        if(BeginFeed()){MoveBoardStep(FVector2D::ZeroVector);EndStroke();}
    }
    return true;
}
void UWoodworkingSystem::EndStroke()
{
    ColdSteelStationNet::FInputScope NetworkScope;
    if(NetworkScope.Root)ColdSteelStationNet::Input(this,TEXT("wood"),7);
    AdvanceClock();const bool HadFeed=bFeeding;bFeeding=false;
    if(Phase!=EWoodworkingPhase::Running){Board.EndStroke();return;}
    Board.EndStroke();
    if(HadFeed&&Board.Revision()!=StrokeRevision){UndoPose=StrokePose;bUndoPose=true;}
    CheckDamage();
    if(Phase==EWoodworkingPhase::Running&&HadFeed&&Board.Revision()!=StrokeRevision&&Rules.bCheckConnections&&!Board.ConnectionsIntact())
    {FrozenElapsed=Elapsed();Phase=EWoodworkingPhase::Failed;bMotorOn=false;Notice=TEXT("关键连接已切断 · 返回工作面板处理失败品");SaveResult();}
}
void UWoodworkingSystem::CheckDamage()
{
    if(Phase==EWoodworkingPhase::Running&&Board.DamageExceeded())
    {Board.EndStroke();FrozenElapsed=Elapsed();bFeeding=false;bMotorOn=false;Phase=EWoodworkingPhase::Failed;Notice=TEXT("主体损伤超过限度 · 返回工作面板处理失败品");SaveResult();}
}
bool UWoodworkingSystem::Undo()
{
    ColdSteelStationNet::FInputScope NetworkScope;
    if(NetworkScope.Root)ColdSteelStationNet::Input(this,TEXT("wood"),8);
    AdvanceClock();if(Phase!=EWoodworkingPhase::Running)return false;
    if(!Board.Undo()){Notice=TEXT("只能撤销上一笔，或撤销次数已用尽");return false;}
    if(bUndoPose)BoardPose=UndoPose;bUndoPose=false;
    Notice=TEXT("已还原上一笔及木板位置 · 时间不会返还");return true;
}
void UWoodworkingSystem::Evaluate(bool TimedOut)
{
    FrozenElapsed=Elapsed();bMotorOn=false;bFeeding=false;
    const bool Qualified=Board.Metrics().Clearance>=Rules.RequiredClearance&&!Board.DamageExceeded()&&(!Rules.bCheckConnections||Board.ConnectionsIntact());
    Phase=Qualified?EWoodworkingPhase::Complete:EWoodworkingPhase::Failed;
    if(!Qualified)Notice=TimedOut?TEXT("时间到 · 工件未达标，可废弃返还一半材料"):TEXT("工件未达标，可废弃返还一半材料");
    else Notice=TEXT("加工达标 · 返回工作面板领取成品或废弃返还一半材料");
    SaveResult();
}
bool UWoodworkingSystem::Finish()
{
    ColdSteelStationNet::FInputScope NetworkScope;
    if(NetworkScope.Root)ColdSteelStationNet::Input(this,TEXT("wood"),9);
    AdvanceClock();if(Phase!=EWoodworkingPhase::Running)return false;EndStroke();if(Phase!=EWoodworkingPhase::Running)return false;
    if(Board.Metrics().Clearance<Rules.RequiredClearance){Notice=TEXT("外围木料尚未清除到要求，请继续加工");return false;}
    Evaluate(false);return Phase==EWoodworkingPhase::Complete;
}
bool UWoodworkingSystem::Claim()
{
    if(!bOpen||!HasPendingJob()||!Job().bFinished||!Job().bPassed||bClaiming)return false;
    if(ColdSteelStationNet::IsClient(this))
    {if(!ColdSteelStationNet::Request(this,TEXT("wood.claim")))return false;bClaiming=true;Notice=TEXT("等待服务器结算");return false;}
    TGuardValue<bool> Guard(bClaiming,true);
    auto* M=Model();if(!M)return false;M->SyncRuntime();auto Next=M->Snapshot();
    // Apply from the authoritative saved score, including an older unclaimed finished job.
    // Replacing quality metadata never multiplies the stored base stats a second time.
    if(!ColdSteelWoodQuality::Apply(Next.WoodworkingJob.Item,Next.WoodworkingJob.Quality))
    {Notice=TEXT("成品工艺属性不可读，工件保留待领");return false;}
    if(!ColdSteelInventory::Insert(Next.Items,Next.WoodworkingJob.Item)){Notice=TEXT("背包空间不足，成品保留待领");return false;}
    Next.WoodworkingJob={};
    if(!M->CommitState(MoveTemp(Next))){Notice=M->ResultMessage();return false;}
    Phase=EWoodworkingPhase::Delivered;Notice=TEXT("成品已放入背包 · 本次制作已结算");return true;
}
void UWoodworkingSystem::Abandon()
{
    ColdSteelStationNet::FInputScope NetworkScope;
    if(NetworkScope.Root)ColdSteelStationNet::Input(this,TEXT("wood"),10);
    if(HasPendingJob()){Settle();return;}
    Board.EndStroke();FrozenElapsed=Elapsed();bMotorOn=bFeeding=false;Phase=EWoodworkingPhase::Abandoned;AcceptedRecipe={};
    Notice=TEXT("准备已取消，未投入材料");
}

double UWoodworkingSystem::Quality() const
{
    if(HasPendingJob()&&Job().bFinished)return Job().Quality;
    auto Scoring=Rules;if(!IsTimed())Scoring.SpeedWeight=0;
    return Board.Metrics().Quality(Scoring,Elapsed());
}
FString UWoodworkingSystem::RecipeSummary() const
{
    const auto* P=Pattern();const auto* Craft=GetGameInstance()->GetSubsystem<UColdSteelCraftingSystem>();
    const auto* Recipe=P&&Craft?Craft->Find(P->CraftRecipe):nullptr;
    const auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Recipe||!Model)return TEXT("正式制作配方暂不可用");
    FString Text=TEXT("材料来源 · 背包 + 主仓库\n");
    for(const auto& Input:Recipe->Inputs)
    {
        const FString Name=ColdSteelInventory::Text(Model->CreateItem(Input.Item),TEXT("name"));
        Text+=FString::Printf(TEXT("%s    %lld / %lld\n"),*Name,Model->CountMaterial(Input.Item),Input.Count);
    }
    Text+=FString::Printf(TEXT("产出 · %s × %lld\n开始加工时投入材料；完成后领取成品或废弃返还一半。"),*ColdSteelInventory::Text(Model->CreateItem(Recipe->Output),TEXT("name")),Recipe->OutputCount);
    return Text;
}
FString UWoodworkingSystem::ResultSummary() const
{
    if(HasPendingJob()&&Job().bFinished)return Job().Result;
    const auto M=Board.Metrics();FString Text;
    if(M.Clearance<Rules.RequiredClearance)Text+=FString::Printf(TEXT("仍有废料需要切除：清除 %.1f%%，要求 %.1f%%。\n"),M.Clearance*100,Rules.RequiredClearance*100);
    if(Board.DamageExceeded())Text+=FString::Printf(TEXT("主体损伤 %.1f%%，超过 %.1f%% 上限。\n"),(1-M.Integrity)*100,Rules.MaximumDamage*100);
    if(Rules.bCheckConnections&&!Board.ConnectionsIntact())Text+=TEXT("关键连接已经切断，查看木板上的红色缺损。\n");
    if(Text.IsEmpty())Text=TEXT("外围清除、主体完整和关键连接均已达标。\n");
    Text+=FString::Printf(TEXT("边缘贴合 %.1f%% · 总分由完整度、贴合度、清除率%s计算。"),M.EdgeFit*100,IsTimed()?TEXT("和用时"):TEXT(""));
    return Text;
}

UWoodworkingSystem* UWoodworkingSystem::CreateNetworkSession(UColdSteelStatusModel* InModel)
{auto* S=NewObject<UWoodworkingSystem>(GetGameInstance());S->Rules=Rules;S->SawRules=SawRules;S->Catalog=Catalog;S->ConfigError=ConfigError;S->NetworkModel=InModel;return S;}
void UWoodworkingSystem::NetworkDelivered(bool Success)
{bClaiming=false;if(Success){Phase=EWoodworkingPhase::Delivered;Notice=TEXT("成品已放入背包");}else Notice=TEXT("服务器未完成结算，请查看加工状态后重试");}

UColdSteelWoodNetState* UWoodworkingSystem::NetworkState()
{
    auto* S=NewObject<UColdSteelWoodNetState>();S->Selected=Selected;S->Phase=uint8(Phase);S->Mode=uint8(SessionMode);
    S->Job=Job();if(const auto* M=Model())S->InventoryRevision=M->InventoryRevision();
    S->Open=bOpen;S->Motor=bMotorOn;S->Feeding=bFeeding;S->UndoPoseValid=bUndoPose;S->StrokeChanged=StrokeRevision!=Board.Revision();S->Elapsed=Elapsed();
    S->ServerTime=GetWorld()->GetGameState()?GetWorld()->GetGameState()->GetServerWorldTimeSeconds():GetWorld()->GetTimeSeconds();
    S->Offset=BoardPose.Offset;S->Angle=BoardPose.Angle;S->StrokeOffset=StrokePose.Offset;S->StrokeAngle=StrokePose.Angle;
    S->UndoOffset=UndoPose.Offset;S->UndoAngle=UndoPose.Angle;S->Notice=Notice;
    FMemoryWriter Writer(S->Mask);Board.SerializeNetwork(Writer);return S;
}

bool UWoodworkingSystem::ApplyNetworkState(const UColdSteelWoodNetState* S)
{
    if(!S||!ColdSteelStationNet::IsClient(this)||S->Phase>uint8(EWoodworkingPhase::Abandoned)||S->Mode>uint8(EWoodworkingMode::Craft))return false;
    if(bClaiming)return false;
    auto* M=Model();if(!M||S->InventoryRevision<M->InventoryRevision())return false;
    if(HasPendingJob()&&Job().bFinished&&Job().Id==S->Job.Id&&!S->Job.bFinished)return false;
    // A buffered board snapshot may finish after the inventory claim receipt.
    // A new local selection/open changes Phase and permits its own fresh state.
    if(Phase==EWoodworkingPhase::Delivered&&Selected==S->Selected&&S->Phase!=uint8(EWoodworkingPhase::Delivered))return false;
    if(S->Selected.IsNone()){bOpen=false;bMotorOn=bFeeding=false;Phase=EWoodworkingPhase::Abandoned;Notice=S->Notice;return true;}
    const auto* P=Catalog.FindByPredicate([&](const auto& Entry){return Entry.Id==S->Selected;});if(!P)return false;
    auto Settings=Rules;Settings.Seconds=P->Seconds;Settings.RequiredClearance=P->RequiredClearance;Settings.MaximumDamage=P->MaximumDamage;
    auto Next=Board;
    if(Selected!=S->Selected||Next.Wood().IsEmpty()){FString Error;if(!Next.Initialize(Settings,P->Outline,P->Connections,Error))return false;}
    if(!Next.RestoreNetwork(S->Mask))return false;
    const bool JobChanged=Job().Id!=S->Job.Id||Job().bFinished!=S->Job.bFinished||Job().Elapsed!=S->Job.Elapsed||Job().Mask!=S->Job.Mask
        ||Job().Quality!=S->Job.Quality||Job().Item.Data!=S->Job.Item.Data;
    if(JobChanged){auto Profile=M->Snapshot();Profile.WoodworkingJob=S->Job;M->AdoptNetMirror(Profile);}
    Rules=Settings;Selected=S->Selected;Board=MoveTemp(Next);Phase=EWoodworkingPhase(S->Phase);SessionMode=EWoodworkingMode(S->Mode);
    bCheckpointReady=true;
    bOpen=S->Open;bMotorOn=S->Motor;bFeeding=S->Feeding;bUndoPose=S->UndoPoseValid;bPractice=false;
    BoardPose.Offset=S->Offset;BoardPose.Angle=S->Angle;StrokePose.Offset=S->StrokeOffset;StrokePose.Angle=S->StrokeAngle;
    UndoPose.Offset=S->UndoOffset;UndoPose.Angle=S->UndoAngle;StrokeRevision=Board.Revision()-(S->StrokeChanged?1:0);
    const double Now=GetWorld()->GetGameState()?GetWorld()->GetGameState()->GetServerWorldTimeSeconds():GetWorld()->GetTimeSeconds();
    FrozenElapsed=S->Elapsed+(MotorRunning()?FMath::Max(0.,Now-S->ServerTime):0.);StartedAt=FPlatformTime::Seconds();Notice=S->Notice;
    if(JobChanged)M->NotifyChanged();return true;
}

void UWoodworkingSystem::NetworkUnavailable(const FString& Reason)
{Close();Notice=Reason;}
