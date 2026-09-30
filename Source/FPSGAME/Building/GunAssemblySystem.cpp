#include "GunAssemblySystem.h"
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
{return GetGameInstance()?GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;}
const FColdSteelGunAssemblyJob& UGunAssemblySystem::Job() const
{static const FColdSteelGunAssemblyJob Empty;return Model()?Model()->GunAssemblyJob():Empty;}
void UGunAssemblySystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);Collection.InitializeDependency<UColdSteelStatusModel>();
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
    Data.CalibrationDuration=Entry->GetNumberField(TEXT("calibration_seconds"));
    for(const auto& V:Entry->GetArrayField(TEXT("inputs")))
    {const auto O=V->AsObject();Data.Inputs.Add({O->GetStringField(TEXT("item")),int64(O->GetNumberField(TEXT("count")))});}
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
    if(!GetWorld()||GetWorld()->GetNetMode()!=NM_Standalone){Reason=TEXT("拼装仅支持单人模式");return false;}
    if(!Job().Id.IsEmpty()){Reason=TEXT("已有工件，请继续拼装或领取成品");return false;}
    if(M->CreateItem(Data.Output).Data.IsEmpty()){Reason=TEXT("枪械目录未就绪");return false;}
    for(const auto& In:Data.Inputs)if(M->CountMaterial(In.Item)<In.Count)
    {Reason=FString::Printf(TEXT("缺少 %lld 个%s"),In.Count-M->CountMaterial(In.Item),*ColdSteelInventory::Text(M->CreateItem(In.Item),TEXT("name")));return false;}
    Reason=TEXT("材料充足 · 制作一把 ")+ProductName();return true;
}
bool UGunAssemblySystem::Start(FString& Reason)
{
    const auto& Data=Recipe();
    if(!CanStart(Reason))return false;
    auto* M=Model();M->SyncRuntime();auto P=M->Snapshot();
    for(const auto& In:Data.Inputs)
    {
        int64 Left=In.Count;
        for(int32 Place:{0,4})for(int32 I=P.Items.Num()-1;I>=0&&Left>0;--I)
        {
            auto& Item=P.Items[I];if(Item.Definition!=In.Item||Item.Place!=Place||!Item.Container.IsEmpty())continue;
            const int64 N=FMath::Min(Left,Item.Count);Item.Count-=N;Left-=N;if(Item.Count==0)P.Items.RemoveAt(I);
        }
        if(Left>0){Reason=TEXT("材料已变化，未扣除材料");return false;}
    }
    auto& J=P.GunAssemblyJob;J={};J.Id=FGuid::NewGuid().ToString(EGuidFormats::Digits);J.Recipe=Data.Id;
    J.Item=M->CreateItem(Data.Output);J.Item.Magazine=0;J.Item.Reserve=0;J.Item.VirtualMagazineAmmo=0;
    J.PartCount=Data.Parts.Num();J.CalibrationDuration=Data.CalibrationDuration;
    J.Scores.Init(0,Data.Parts.Num());J.Misses.Init(0,Data.Parts.Num());
    for(const auto& In:Data.Inputs)J.PaidMaterials.Add(In.Item,In.Count);
    if(!M->CommitState(MoveTemp(P))){Reason=M->ResultMessage();return false;}
    Reason=TEXT("材料已投入 · 拿起组件开始拼装");return true;
}
bool UGunAssemblySystem::Installed(int32 Part) const
{return Recipe().Parts.IsValidIndex(Part)&&(Job().InstalledMask&(1<<Part))!=0;}
int32 UGunAssemblySystem::InstalledCount() const
{int32 N=0;for(int32 I=0;I<Recipe().Parts.Num();++I)if(Installed(I))++N;return N;}
bool UGunAssemblySystem::Assembled() const
{return !Job().Id.IsEmpty()&&!Recipe().Parts.IsEmpty()&&InstalledCount()==Recipe().Parts.Num();}
bool UGunAssemblySystem::Install(int32 Part,float Distance,float Angle,FString& Reason)
{
    const auto& Data=Recipe();
    if(!Model()||Job().Id.IsEmpty()||Job().bFinished||!Data.Parts.IsValidIndex(Part)||Installed(Part))return false;
    if(!FMath::IsFinite(Distance)||!FMath::IsFinite(Angle))return false;
    Model()->SyncRuntime();auto P=Model()->Snapshot();auto& J=P.GunAssemblyJob;
    const bool Accept=Distance<=Data.PositionTolerance&&FMath::Abs(Angle)<=Data.AngleTolerance;
    if(!Accept)
    {J.Misses[Part]=FMath::Min(10,J.Misses[Part]+1);Reason=Distance>Data.PositionTolerance?TEXT("位置未对准 · 零件已回到托位"):TEXT("朝向未对准 · 滚轮或 Q / R 旋转");}
    else
    {
        J.InstalledMask|=1<<Part;
        J.Scores[Part]=FMath::Clamp(100.f-18.f*Distance/Data.PositionTolerance-18.f*FMath::Abs(Angle)/Data.AngleTolerance-3.f*J.Misses[Part],40.f,100.f);
        Reason=FString::Printf(TEXT("%s已安装 · 对位 %.0f 分"),*Data.Parts[Part].Name,J.Scores[Part]);
    }
    if(!Model()->CommitState(MoveTemp(P))){Reason=Model()->ResultMessage();return false;}
    return Accept;
}
void UGunAssemblySystem::Calibrate(float DeltaTime,float Error)
{
    const auto& Data=Recipe();
    if(!Assembled()||Job().bFinished||!Model()||Job().CalibrationSeconds>=Job().CalibrationDuration)return;
    const float Dt=FMath::Clamp(DeltaTime,0.f,.05f),E=FMath::Clamp(Error,0.f,2.f);
    const auto J=Job();const float Held=FMath::Min(J.CalibrationDuration,J.CalibrationSeconds+(E<=1?Dt:0));
    Model()->StageGunCalibration(J.Id,Held,J.CalibrationTime+Dt,J.CalibrationError+Dt*E);
}
float UGunAssemblySystem::Score() const
{
    const auto& Data=Recipe();
    const auto& J=Job();if(J.bFinished)return J.Quality;
    float Sum=0;for(float S:J.Scores)Sum+=S;
    const float Fit=Sum/FMath::Max(1,Data.Parts.Num());
    const float Calibration=100.f*(1.f-.65f*FMath::Clamp(J.CalibrationError/FMath::Max(.01f,J.CalibrationTime),0.f,1.f));
    return FMath::Clamp(.7f*Fit+.3f*Calibration,0.f,100.f);
}
FString UGunAssemblySystem::QualityName(float Value)
{return Value>=90?TEXT("精工"):Value>=75?TEXT("优良"):Value>=55?TEXT("合格"):TEXT("粗制");}
FString UGunAssemblySystem::BenefitText(float Value)
{return FString::Printf(TEXT("后坐力 −%.1f%% · 腰射散布 −%.1f%%"),Value*.12f,Value*.15f);}
bool UGunAssemblySystem::Finish(FString& Reason)
{
    const auto& Data=Recipe();
    if(Job().bFinished)return true;
    if(!Assembled()||Job().CalibrationSeconds<Job().CalibrationDuration){Reason=TEXT("先完成全部装配和校准");return false;}
    Model()->SyncRuntime();auto P=Model()->Snapshot();auto& J=P.GunAssemblyJob;
    TSharedPtr<FJsonObject> O;if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(J.Item.Data),O)||!O)return false;
    J.Quality=Score();J.bFinished=true;
    auto Q=MakeShared<FJsonObject>();Q->SetNumberField(TEXT("score"),J.Quality);Q->SetStringField(TEXT("label"),QualityName(J.Quality));
    Q->SetNumberField(TEXT("recoil"),1.-J.Quality*.0012);Q->SetNumberField(TEXT("spread"),1.-J.Quality*.0015);
    O->SetObjectField(TEXT("_assemblyQuality"),Q);
    FString Serialized;FJsonSerializer::Serialize(O.ToSharedRef(),TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&Serialized));
    J.Item.Data=MoveTemp(Serialized);
    if(!Model()->CommitState(MoveTemp(P))){Reason=Model()->ResultMessage();return false;}
    Reason=TEXT("拼装完成 · 成品保留待领");return true;
}
bool UGunAssemblySystem::Claim(FString& Reason)
{
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
    Paid=Job().PaidMaterials;
    if(!Paid.IsEmpty())return true;
    // Match forging's old-save fallback in both the paid-material display and refund quote.
    const auto& Data=Recipe();
    if(Data.Id.IsNone()||Data.Inputs.IsEmpty())return false;
    for(const auto& In:Data.Inputs)Paid.Add(In.Item,In.Count);
    return true;
}
bool UGunAssemblySystem::GetDiscardRefund(TArray<FColdSteelCraftingInput>& Refund,FString& Reason) const
{
    Refund.Reset();Reason.Reset();
    if(!Model()||Job().Id.IsEmpty()||!Job().bFinished)
    {Reason=TEXT("只有已完成、尚未领取的成品可以废弃");return false;}
    if(!GetWorld()||GetWorld()->GetNetMode()!=NM_Standalone)
    {Reason=TEXT("拼装仅支持单人模式");return false;}
    TMap<FString,int64> Paid;
    if(!GetPaidMaterials(Paid)){Reason=TEXT("无法读取返还材料，成品保留待领");return false;}
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
    TArray<FColdSteelCraftingInput> Refund;
    if(!GetDiscardRefund(Refund,Reason))return false;
    auto* M=Model();M->SyncRuntime();auto P=M->Snapshot();
    TArray<FString> Returned;
    for(const auto& In:Refund)
    {
        const auto Material=M->CreateItem(In.Item,In.Count);
        if(Material.Data.IsEmpty()){Reason=TEXT("返还材料尚未就绪，成品保留待领");return false;}
        if(!ColdSteelInventory::Insert(P.Items,Material))
        {Reason=TEXT("背包空间不足，无法容纳全部返还材料；成品保留待领");return false;}
        Returned.Add(FString::Printf(TEXT("%s × %lld"),*ColdSteelInventory::Text(Material,TEXT("name")),In.Count));
    }
    // Clear the pending gun and deliver every refund in a single saved transaction.
    P.GunAssemblyJob={};
    if(!M->CommitState(MoveTemp(P))){Reason=M->ResultMessage();return false;}
    Reason=Returned.IsEmpty()?TEXT("成品已废弃，各项材料折半不足 1 个，无可返还材料")
        :TEXT("成品已废弃，已返还背包：")+FString::Join(Returned,TEXT("、"));
    return true;
}
bool UGunAssemblySystem::Pause(FString& Reason)
{
    if(!Model()||Job().Id.IsEmpty())return true;
    if(!Model()->SaveNow()){Reason=Model()->ResultMessage();return false;}
    Reason=TEXT("工件已保存，下次可以继续");return true;
}
