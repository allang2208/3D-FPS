#include "GunAssemblySystem.h"
#include "../Development/DevelopmentTuningSubsystem.h"
#include "../FPSGAMECharacter.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../Multiplayer/ColdSteelStationNetwork.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

void UColdSteelStatusModel::StageGunCalibration(const FString& Id,float Held,float Time,float Error)
{
    auto& J=Current.GunAssemblyJob;if(J.Id!=Id||J.bFinished)return;
    J.CalibrationSeconds=Held;J.CalibrationTime=Time;J.CalibrationError=Error;bTrainingDirty=true;
}
UColdSteelStatusModel* UGunAssemblySystem::Model() const
{return NetworkModel?NetworkModel.Get():ColdSteelAuthority::Model(this);}
const FColdSteelGunAssemblyJob& UGunAssemblySystem::Job() const
{static const FColdSteelGunAssemblyJob Empty;return Model()?Model()->GunAssemblyJob():Empty;}
void UGunAssemblySystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);Collection.InitializeDependency<UColdSteelStatusModel>();Collection.InitializeDependency<UColdSteelForgingSystem>();
    FString Raw;TSharedPtr<FJsonObject> Root;
    if(!FFileHelper::LoadFileToString(Raw,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/gun-assembly.json")))
        ||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Raw),Root)||!Root)return;
    const TArray<TSharedPtr<FJsonValue>>* Entries=nullptr;
    TArray<TSharedPtr<FJsonValue>> Legacy;
    if(!Root->TryGetArrayField(TEXT("recipes"),Entries))
    {Legacy.Add(MakeShared<FJsonValueObject>(Root));Entries=&Legacy;}
    for(const auto& Value:*Entries)
    {
        const auto Entry=Value->AsObject();if(!Entry)continue;
        FGunAssemblyRecipe Data;
    Data.Id=FName(*Entry->GetStringField(TEXT("id")));Data.Output=Entry->GetStringField(TEXT("output"));
    Data.BodyMesh=Entry->GetStringField(TEXT("body_mesh"));
    auto Vec=[](const TArray<TSharedPtr<FJsonValue>>& A){return FVector(A[0]->AsNumber(),A[1]->AsNumber(),A[2]->AsNumber());};
    Data.BodyPosition=Vec(Entry->GetArrayField(TEXT("body_position")));
    Data.Camera=Vec(Entry->GetArrayField(TEXT("camera")));Data.LookAt=Vec(Entry->GetArrayField(TEXT("look_at")));
    Data.PositionTolerance=Entry->GetNumberField(TEXT("position_tolerance_cm"));
    Data.AngleTolerance=Entry->GetNumberField(TEXT("angle_tolerance_deg"));
    Data.CalibrationDuration=GunAssemblyCalibration::Duration;
    for(const auto& V:Entry->GetArrayField(TEXT("inputs")))
    {const auto O=V->AsObject();Data.Inputs.Add({O->GetStringField(TEXT("item")),int64(O->GetNumberField(TEXT("count")))});}
    double MetalCount=0;Entry->TryGetNumberField(TEXT("metal_count"),MetalCount);Data.MetalCount=FMath::Max<int64>(0,FMath::RoundToInt64(MetalCount));
    const TArray<TSharedPtr<FJsonValue>>* LegacyInputs=nullptr;
    if(Entry->TryGetArrayField(TEXT("legacy_inputs"),LegacyInputs))for(const auto& V:*LegacyInputs)
    {const auto O=V->AsObject();Data.LegacyInputs.Add({O->GetStringField(TEXT("item")),int64(O->GetNumberField(TEXT("count")))});}
    for(const auto& V:Entry->GetArrayField(TEXT("parts")))
    {
        const auto O=V->AsObject();FGunAssemblyPart P;
        P.Id=O->GetStringField(TEXT("id"));P.Name=O->GetStringField(TEXT("name"));P.Mesh=O->GetStringField(TEXT("mesh"));
        P.Target=Vec(O->GetArrayField(TEXT("target")));P.Loose=Vec(O->GetArrayField(TEXT("loose")));
        P.Extent=Vec(O->GetArrayField(TEXT("extent")));P.Angle=O->GetNumberField(TEXT("angle"));
        P.Radius=FMath::Max(3.5f,float(O->GetNumberField(TEXT("radius"))));Data.Parts.Add(P);
    }
        if(!Data.Id.IsNone()&&!Data.BodyMesh.IsEmpty()&&!Data.Output.IsEmpty()&&Data.Parts.Num()>0&&Data.Parts.Num()<=30
            &&Data.PositionTolerance>0&&Data.AngleTolerance>0&&Data.CalibrationDuration>0
            &&!Recipes.ContainsByPredicate([&](const auto& R){return R.Id==Data.Id;}))Recipes.Add(MoveTemp(Data));
    }
    if(!Recipes.IsEmpty())SelectedRecipe=Recipes[0].Id;
}
const FGunAssemblyRecipe& UGunAssemblySystem::Recipe() const
{
    const FName Id=Job().Id.IsEmpty()?SelectedRecipe:Job().Recipe;
    const auto* Found=Recipes.FindByPredicate([Id](const auto& R){return R.Id==Id;});
    static const FGunAssemblyRecipe Empty;return Found?*Found:Empty;
}
bool UGunAssemblySystem::SelectRecipe(FName Id)
{
    if(!Job().Id.IsEmpty()||!Recipes.ContainsByPredicate([Id](const auto& R){return R.Id==Id;}))return false;
    SelectedRecipe=Id;return true;
}
const TArray<FColdSteelForgeMetal>& UGunAssemblySystem::Metals() const
{return GetGameInstance()->GetSubsystem<UColdSteelForgingSystem>()->Metals();}
const FColdSteelForgeMetal* UGunAssemblySystem::FindMetal(FName Id) const
{return GetGameInstance()->GetSubsystem<UColdSteelForgingSystem>()->FindMetal(Id);}
bool UGunAssemblySystem::SelectMetal(FName Id)
{if(!Job().Id.IsEmpty()||!FindMetal(Id))return false;SelectedMetal=Id;return true;}
FName UGunAssemblySystem::Metal() const
{return Job().Id.IsEmpty()?SelectedMetal:Job().Metal;}
double UGunAssemblySystem::MaterialBonus() const
{if(!Job().Id.IsEmpty())return ColdSteelAssemblyQuality::MaterialBonus(Job());const auto* M=FindMetal(SelectedMetal);return M?M->Bonus:0.;}
bool UGunAssemblySystem::InputsFor(TArray<FColdSteelCraftingInput>& Inputs) const
{
    Inputs.Reset();const auto& R=Recipe();if(R.Id.IsNone()||R.MetalCount<=0||!FindMetal(Metal()))return false;
    Inputs=R.Inputs;Inputs.Add({Metal().ToString(),R.MetalCount});return true;
}
FString UGunAssemblySystem::ProductName() const
{
    if(!Model())return TEXT("枪械");
    return ColdSteelInventory::Text(Job().Id.IsEmpty()?Model()->CreateItem(Recipe().Output):Job().Item,TEXT("name"));
}
bool UGunAssemblySystem::CanStart(FString& Reason) const
{
    const auto& Data=Recipe();
    auto* M=Model();
    if(!M||Data.Id.IsNone()||Data.Parts.IsEmpty()||Data.Parts.Num()>30||Data.Inputs.IsEmpty()){Reason=TEXT("拼装配方未就绪");return false;}
    if(!GetWorld()){Reason=TEXT("拼装仅支持单人模式");return false;}
    if(!Job().Id.IsEmpty()){Reason=TEXT("已有工件，请继续拼装或领取成品");return false;}
    if(M->CreateItem(Data.Output).Data.IsEmpty()){Reason=TEXT("枪械目录未就绪");return false;}
    TArray<FColdSteelCraftingInput> Inputs;
    if(!InputsFor(Inputs)){Reason=TEXT("请选择一种可用金属锭");return false;}
    for(const auto& In:Inputs)if(M->CreateItem(In.Item).Data.IsEmpty())
    {Reason=TEXT("拼装材料未加入物品目录");return false;}
    const bool Free=UDevelopmentTuningSubsystem::IsFreeCrafting(M);
    if(!Free)for(const auto& In:Inputs)if(M->CountMaterial(In.Item)<In.Count)
    {Reason=FString::Printf(TEXT("缺少 %lld 个%s"),In.Count-M->CountMaterial(In.Item),*ColdSteelInventory::Text(M->CreateItem(In.Item),TEXT("name")));return false;}
    Reason=(Free?FString(TEXT("免材料制作 · 制作一把 ")):FString(TEXT("材料充足 · 制作一把 ")))+ProductName();return true;
}
bool UGunAssemblySystem::Start(FString& Reason)
{
    const auto& Data=Recipe();
    if(!CanStart(Reason))return false;
    if(ColdSteelStationNet::IsClient(this))return RequestTransaction(TEXT("assembly.start"),Reason);
    auto* M=Model();M->SyncRuntime();auto P=M->Snapshot();
    TArray<FColdSteelCraftingInput> Inputs;InputsFor(Inputs);
    const bool Free=UDevelopmentTuningSubsystem::IsFreeCrafting(M);
    if(!Free)for(const auto& In:Inputs)
    {
        int64 Left=In.Count;
        for(int32 Place:{0,5,4})for(int32 I=P.Items.Num()-1;I>=0&&Left>0;--I)
        {
            auto& Item=P.Items[I];if(Item.Definition!=In.Item||Item.Place!=Place||(Place==4&&!Item.Container.IsEmpty()))continue;
            const int64 N=FMath::Min(Left,Item.Count);Item.Count-=N;Left-=N;if(Item.Count==0)P.Items.RemoveAt(I);
        }
        if(Left>0){Reason=TEXT("材料已变化，未扣除材料");return false;}
    }
    auto& J=P.GunAssemblyJob;J={};J.Id=FGuid::NewGuid().ToString(EGuidFormats::Digits);J.Recipe=Data.Id;
    J.Item=M->CreateItem(Data.Output);J.Item.Magazine=0;J.Item.Reserve=0;J.Item.VirtualMagazineAmmo=0;
    J.PartCount=Data.Parts.Num();J.CalibrationDuration=GunAssemblyCalibration::Duration;
    J.CalibrationVersion=GunAssemblyCalibration::Version;
    J.Scores.Init(0,Data.Parts.Num());J.Misses.Init(0,Data.Parts.Num());
    J.bMaterialsWaived=Free;
    J.QualityVersion=ColdSteelAssemblyQuality::Version;J.Metal=SelectedMetal;J.MaterialBonus=FindMetal(SelectedMetal)->Bonus;
    J.MaterialName=ColdSteelInventory::Text(M->CreateItem(SelectedMetal.ToString()),TEXT("name"));
    if(!ColdSteelAssemblyQuality::Apply(J.Item,J)){Reason=TEXT("枪械工件数据不可读，未扣材料");return false;}
    if(!Free)for(const auto& In:Inputs)J.PaidMaterials.Add(In.Item,In.Count);
    if(!M->CommitState(MoveTemp(P))){Reason=M->ResultMessage();return false;}
    Reason=Free?TEXT("免材料制作 · 拿起组件开始拼装"):TEXT("材料已投入 · 拿起组件开始拼装");return true;
}
bool UGunAssemblySystem::RequestTransaction(const FString& Mode,FString& Reason)
{
    if(!BoundStation.IsValid()){Reason=TEXT("请重新打开枪械工作台");return false;}
    const bool Sent=ColdSteelStationNet::Request(this,Mode,SelectedRecipe,1,BoundStation.Get(),FIntVector::ZeroValue,SelectedMetal);
    Reason=Sent?TEXT("等待服务器确认…"):TEXT("当前操作尚未同步，请稍后重试");return Sent;
}
bool UGunAssemblySystem::CanResume(FString& Reason) const
{
    if(Job().Id.IsEmpty()||Job().bFinished){Reason=TEXT("没有可继续的工件");return false;}
    if(Recipe().Id.IsNone()||Job().PartCount!=Recipe().Parts.Num())
    {Reason=TEXT("工件配方已变化，可取消工件并按实付记录返还一半材料");return false;}
    return true;
}
bool UGunAssemblySystem::Resume(FString& Reason)
{
    if(!CanResume(Reason))return false;
    if(ColdSteelStationNet::IsClient(this))return RequestTransaction(TEXT("assembly.resume"),Reason);
    if(Job().CalibrationVersion<GunAssemblyCalibration::Version)
    {
        Model()->SyncRuntime();auto P=Model()->Snapshot();auto& J=P.GunAssemblyJob;
        if(J.CalibrationVersion>=GunAssemblyCalibration::FirstRoundsVersion)
            J.CalibrationTime=GunAssemblyCalibration::UpgradeElapsed(J.CalibrationTime,J.CalibrationVersion);
        else
        {
            const float Progress=FMath::Clamp(J.CalibrationSeconds/FMath::Max(.01f,J.CalibrationDuration),0.f,1.f);
            const float AverageError=J.CalibrationError/FMath::Max(.01f,J.CalibrationTime);
            // Preserve earned quality from the original hold-until-complete rules.
            J.CalibrationSeconds=Progress*GunAssemblyCalibration::ScoringSeconds;
            J.CalibrationTime=GunAssemblyCalibration::ElapsedForActive(J.CalibrationSeconds);
            J.CalibrationError=J.CalibrationSeconds*AverageError;
        }
        J.CalibrationDuration=GunAssemblyCalibration::Duration;J.CalibrationVersion=GunAssemblyCalibration::Version;
        if(!Model()->CommitState(MoveTemp(P))){Reason=Model()->ResultMessage();return false;}
    }
    Reason=TEXT("继续已有工件 · 不重复扣料");return true;
}
bool UGunAssemblySystem::Installed(int32 Part) const
{return Recipe().Parts.IsValidIndex(Part)&&(Job().InstalledMask&(1<<Part))!=0;}
int32 UGunAssemblySystem::InstalledCount() const
{int32 N=0;for(int32 I=0;I<FMath::Clamp(Job().PartCount,0,30);++I)if(Job().InstalledMask&(1<<I))++N;return N;}
bool UGunAssemblySystem::Assembled() const
{return !Job().Id.IsEmpty()&&!Recipe().Parts.IsEmpty()&&Job().PartCount==Recipe().Parts.Num()&&InstalledCount()==Recipe().Parts.Num();}
bool UGunAssemblySystem::Install(int32 Part,float Distance,float Angle,FString& Reason)
{
    if(ColdSteelStationNet::IsClient(this))
    {ColdSteelStationNet::Input(this,TEXT("assembly"),0,NAME_None,Part,FVector2D(Distance,Angle));Reason=TEXT("正在同步装配");return Distance<=Recipe().PositionTolerance&&FMath::Abs(Angle)<=Recipe().AngleTolerance;}
    const auto& Data=Recipe();
    if(!Model()||Job().Id.IsEmpty()||Job().bFinished||Job().PartCount!=Data.Parts.Num()||!Data.Parts.IsValidIndex(Part)||Installed(Part))return false;
    if(!FMath::IsFinite(Distance)||!FMath::IsFinite(Angle))return false;
    Model()->SyncRuntime();auto P=Model()->Snapshot();auto& J=P.GunAssemblyJob;
    const bool Accept=Distance<=Data.PositionTolerance&&FMath::Abs(Angle)<=Data.AngleTolerance;
    if(!Accept)
    {J.Misses[Part]=FMath::Min(10,J.Misses[Part]+1);Reason=Distance>Data.PositionTolerance?TEXT("位置未对准 · 零件已回到托位"):TEXT("朝向未对准 · 长按 Q / E 旋转，滚轮微调");}
    else
    {
        J.InstalledMask|=1<<Part;
        J.Scores[Part]=FMath::Clamp(100.f-18.f*Distance/Data.PositionTolerance-18.f*FMath::Abs(Angle)/Data.AngleTolerance-3.f*J.Misses[Part],40.f,100.f);
        Reason=FString::Printf(TEXT("%s已安装 · 对位 %.0f 分"),*Data.Parts[Part].Name,J.Scores[Part]);
    }
    if(!Model()->CommitState(MoveTemp(P))){Reason=Model()->ResultMessage();return false;}
    return Accept;
}
void UGunAssemblySystem::Calibrate(float DeltaTime,float Error,float HitFraction)
{
    const float Dt=FMath::Clamp(DeltaTime,0.f,.25f),E=FMath::Clamp(Error,0.f,2.f);
    const float Hit=HitFraction<0?(E<=1.f?1.f:0.f):FMath::Clamp(HitFraction,0.f,1.f);
    if(ColdSteelStationNet::IsClient(this))
    {
        auto* M=Model();if(!M||!M->RuntimePawn()||Job().Id.IsEmpty()||Job().bFinished)return;
        if(CalibrationPawn.Get()!=M->RuntimePawn()||CalibrationJob!=Job().Id)
        {NetworkSessionEnded();CalibrationPawn=M->RuntimePawn();CalibrationJob=Job().Id;}
        CalibrationAccum+=Dt;CalibrationErrorAccum+=Dt*E;CalibrationHitAccum+=Dt*Hit;
        if(CalibrationAccum>=.1f)
        {ColdSteelStationNet::Input(this,TEXT("assembly"),1,NAME_None,0,FVector2D(CalibrationAccum,CalibrationErrorAccum/CalibrationAccum),FVector2D(CalibrationHitAccum/CalibrationAccum,0));CalibrationAccum=CalibrationErrorAccum=CalibrationHitAccum=0.f;}
        return;
    }
    if(!Assembled()||Job().bFinished||!Model())return;
    const auto J=Job();
    if(J.CalibrationVersion>=GunAssemblyCalibration::FirstRoundsVersion)
    {
        if(GunAssemblyCalibration::Complete(J.CalibrationTime,J.CalibrationVersion))return;
        const float Time=FMath::Min(GunAssemblyCalibration::TotalDuration(J.CalibrationVersion),J.CalibrationTime+Dt);
        const float Active=GunAssemblyCalibration::ActiveElapsed(Time,J.CalibrationVersion)-GunAssemblyCalibration::ActiveElapsed(J.CalibrationTime,J.CalibrationVersion);
        const float Held=FMath::Min(GunAssemblyCalibration::ScoringSeconds,J.CalibrationSeconds+Active*Hit);
        Model()->StageGunCalibration(J.Id,Held,Time,J.CalibrationError+Active*E);
    }
    else if(J.CalibrationSeconds<J.CalibrationDuration)
        Model()->StageGunCalibration(J.Id,FMath::Min(J.CalibrationDuration,J.CalibrationSeconds+Dt*Hit),J.CalibrationTime+Dt,J.CalibrationError+Dt*E);
}
float UGunAssemblySystem::Score() const
{return float(ColdSteelAssemblyQuality::Score(Job()));}
FString UGunAssemblySystem::QualityName(float Value)
{return Value>=90?TEXT("精工"):Value>=75?TEXT("优良"):Value>=55?TEXT("合格"):TEXT("粗制");}
FString UGunAssemblySystem::BenefitText(float Value,double MaterialBonus)
{const double Base=FMath::Clamp(MaterialBonus,0.,ColdSteelAssemblyQuality::MaxMaterialBonus),Skill=ColdSteelAssemblyQuality::SkillBonus(Value);
return FString::Printf(TEXT("伤害 +%.2f%% · 材质 +%.2f%% ＋ 装配 +%.2f%%"),(Base+Skill)*100,Base*100,Skill*100);}
bool UGunAssemblySystem::Finish(FString& Reason)
{
    if(ColdSteelStationNet::IsClient(this))return RequestTransaction(TEXT("assembly.finish"),Reason);
    const auto& Data=Recipe();
    if(Job().bFinished)return true;
    const bool Complete=Job().CalibrationVersion>=GunAssemblyCalibration::FirstRoundsVersion?GunAssemblyCalibration::Complete(Job().CalibrationTime,Job().CalibrationVersion):Job().CalibrationSeconds>=Job().CalibrationDuration;
    if(!Assembled()||!Complete){Reason=TEXT("先完成全部装配和五组校准");return false;}
    Model()->SyncRuntime();auto P=Model()->Snapshot();auto& J=P.GunAssemblyJob;
    J.Quality=Score();J.bFinished=true;
    if(!ColdSteelAssemblyQuality::Apply(J.Item,J)){Reason=TEXT("枪械工艺保存失败，工件仍保留");return false;}
    if(!Model()->CommitState(MoveTemp(P))){Reason=Model()->ResultMessage();return false;}
    Reason=TEXT("拼装完成 · 成品保留待领");return true;
}
bool UGunAssemblySystem::Claim(FString& Reason)
{
    if(ColdSteelStationNet::IsClient(this))return RequestTransaction(TEXT("assembly.claim"),Reason);
    if(!Model()||!Job().bFinished){Reason=TEXT("尚无可领取成品");return false;}
    Model()->SyncRuntime();auto P=Model()->Snapshot();
    if(!ColdSteelInventory::Insert(P.Items,P.GunAssemblyJob.Item)){Reason=TEXT("背包空间不足，成品保留待领");return false;}
    const FString Name=ProductName();P.GunAssemblyJob={};
    if(!Model()->CommitState(MoveTemp(P))){Reason=Model()->ResultMessage();return false;}
    Reason=Name+TEXT(" 已放入背包 · 弹匣为空，请自行装填弹药");return true;
}
bool UGunAssemblySystem::GetPaidMaterials(TMap<FString,int64>& Paid) const
{
    Paid.Reset();
    if(Job().Id.IsEmpty())return false;
    if(Job().bMaterialsWaived)return true;
    Paid=Job().PaidMaterials;
    if(!Paid.IsEmpty())return true;
    if(Job().QualityVersion>=ColdSteelAssemblyQuality::Version)return false;
    // Match forging's old-save fallback in both the paid-material display and refund quote.
    const auto& Data=Recipe();
    if(Data.Id.IsNone()||Data.LegacyInputs.IsEmpty())return false;
    // Legacy jobs without a payment snapshot predate the search-material costs.
    for(const auto& In:Data.LegacyInputs)if(!In.Item.StartsWith(TEXT("search_")))Paid.Add(In.Item,In.Count);
    return true;
}
bool UGunAssemblySystem::GetDiscardRefund(TArray<FColdSteelCraftingInput>& Refund,FString& Reason) const
{
    Refund.Reset();Reason.Reset();
    if(!Model()||Job().Id.IsEmpty())
    {Reason=TEXT("没有可取消的工件或可废弃的成品");return false;}
    if(!GetWorld())
    {Reason=TEXT("拼装仅支持单人模式");return false;}
    TMap<FString,int64> Paid;
    if(!GetPaidMaterials(Paid))
    {Reason=TEXT("历史实付记录缺失 · 取消不返料");return true;}
    TArray<FString> Definitions;Paid.GetKeys(Definitions);Definitions.Sort();
    for(const auto& Definition:Definitions)
    {
        const int64 Count=Paid[Definition]/2;
        if(Count>0)Refund.Add({Definition,Count});
    }
    return true;
}
bool UGunAssemblySystem::Discard(FString& Reason)
{
    if(ColdSteelStationNet::IsClient(this))return RequestTransaction(TEXT("assembly.discard"),Reason);
    TArray<FColdSteelCraftingInput> Refund;
    if(!GetDiscardRefund(Refund,Reason))return false;
    auto* M=Model();M->SyncRuntime();auto P=M->Snapshot();
    TArray<FString> Returned;
    for(const auto& In:Refund)
    {
        const auto Material=M->CreateItem(In.Item,In.Count);
        if(Material.Data.IsEmpty()){Reason=TEXT("返还材料尚未就绪，成品保留待领");return false;}
        if(!ColdSteelInventory::Insert(P.Items,Material))
        {Reason=TEXT("背包空间不足，无法容纳全部返还材料；工件仍保留");return false;}
        Returned.Add(FString::Printf(TEXT("%s × %lld"),*ColdSteelInventory::Text(Material,TEXT("name")),In.Count));
    }
    // Clear the pending gun and deliver every refund in a single saved transaction.
    const bool Free=P.GunAssemblyJob.bMaterialsWaived;
    const FString ResultName=P.GunAssemblyJob.bFinished?TEXT("成品已废弃"):TEXT("工件已取消");
    const FString RefundWarning=Reason;
    P.GunAssemblyJob={};
    if(!M->CommitState(MoveTemp(P))){Reason=M->ResultMessage();return false;}
    Reason=ResultName+(Free?FString(TEXT(" · 免材料制作，无材料返还")):!RefundWarning.IsEmpty()?TEXT(" · ")+RefundWarning:
        Returned.IsEmpty()?FString(TEXT(" · 各项材料折半不足 1 个，无可返还材料")):TEXT("，已返还背包：")+FString::Join(Returned,TEXT("、")));
    return true;
}
bool UGunAssemblySystem::Pause(FString& Reason)
{
    if(ColdSteelStationNet::IsClient(this))
    {
        auto* M=Model();
        const bool SameJob=M&&M->RuntimePawn()&&CalibrationPawn.Get()==M->RuntimePawn()&&CalibrationJob==Job().Id;
        if(SameJob&&CalibrationAccum>0.f)
            ColdSteelStationNet::Input(this,TEXT("assembly"),1,NAME_None,0,FVector2D(CalibrationAccum,CalibrationErrorAccum/CalibrationAccum),FVector2D(CalibrationHitAccum/CalibrationAccum,0));
        NetworkSessionEnded();
        if(M&&!Job().Id.IsEmpty())ColdSteelStationNet::Input(this,TEXT("assembly"),2);
        Reason=TEXT("已暂停，等待服务器保存工件");return true;
    }
    if(!Model()||Job().Id.IsEmpty())return true;
    if(!Model()->SaveNow()){Reason=Model()->ResultMessage();return false;}
    Reason=TEXT("工件已保存，下次可以继续");return true;
}

UGunAssemblySystem* UGunAssemblySystem::CreateNetworkSession(UColdSteelStatusModel* M)
{auto* Session=NewObject<UGunAssemblySystem>(GetGameInstance());Session->Recipes=Recipes;Session->NetworkModel=M;return Session;}
