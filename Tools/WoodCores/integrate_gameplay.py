"""One-time narrow source integration, preserving the live shared checkout."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];BEFORE=ROOT/'SourceAssets/WoodCoreMaterials20261026/Before'
def edit(path,changes):
 p=ROOT/path;s=p.read_text(encoding='utf-8-sig');original=s
 for old,new in changes:
  if s.count(old)!=1:raise RuntimeError(f'{path}: expected one occurrence: {old[:95]} (found {s.count(old)})')
  s=s.replace(old,new,1)
 b=BEFORE/path;b.parent.mkdir(parents=True,exist_ok=True)
 if not b.exists():b.write_bytes(p.read_bytes())
 p.write_text(s,encoding='utf-8')

edit('Source/FPSGAME/UI/ColdSteelInventoryTypes.h',[(
'    UPROPERTY() int32 Version=1;\n    UPROPERTY() FString Id;\n    UPROPERTY() FName Pattern;',
'    UPROPERTY() int32 Version=1;\n    // Missing tagged fields in older jobs retain their original score curve.\n    UPROPERTY() int32 QualityVersion=1;\n    UPROPERTY() FName Core;\n    UPROPERTY() double MaterialBonus=0;\n    UPROPERTY() FString Id;\n    UPROPERTY() FName Pattern;')])
edit('Source/FPSGAME/Building/WoodworkingSystem.h',[
('enum class EWoodworkingPhase', 'struct FWoodworkingCore\n{\n    FName Id;\n    FString Name;\n    double Bonus=0;\n    FSoftObjectPath Material;\n};\n\nenum class EWoodworkingPhase'),
('    bool Select(FName Id);','    bool Select(FName Id);\n    const TArray<FWoodworkingCore>& Cores() const {return CoreCatalog;}\n    const FWoodworkingCore* FindCore(FName Id) const;\n    FName Core() const;\n    bool SelectCore(FName Id);\n    bool InputsFor(TArray<FColdSteelCraftingInput>& Inputs) const;\n    double MaterialBonus() const;\n    double ProcessingBonus() const;\n    FString BenefitSummary() const;'),
('    void Load();','    void Load();\n    bool LoadCores();'),
('    TArray<FWoodworkingPattern> Catalog;','    TArray<FWoodworkingPattern> Catalog;\n    TArray<FWoodworkingCore> CoreCatalog;\n    FName SelectedCore=TEXT("wood_core_plain");')])
edit('Source/FPSGAME/Building/WoodworkingSystem.cpp',[
('    Catalog=MoveTemp(Parsed);ConfigError.Reset();Selected=Catalog[0].Id;','    if(!LoadCores())return;\n    Catalog=MoveTemp(Parsed);ConfigError.Reset();Selected=Catalog[0].Id;'),
('    const bool Free=UDevelopmentTuningSubsystem::IsFreeCrafting(M);\n    if(!Free)for(const auto& Input:Recipe->Inputs)', '    TArray<FColdSteelCraftingInput> Inputs;\n    if(!InputsFor(Inputs)){Reason=TEXT("请选择可用木芯");return false;}\n    const bool Free=UDevelopmentTuningSubsystem::IsFreeCrafting(M);\n    if(!Free)for(const auto& Input:Inputs)'),
('ColdSteelStationNet::Request(this,TEXT("wood.start"),Selected)', 'ColdSteelStationNet::Request(this,TEXT("wood.start"),Selected,1,nullptr,FIntVector::ZeroValue,Core())'),
('ColdSteelWoodQuality::Apply(Next.WoodworkingJob.Item,Next.WoodworkingJob.Quality)','ColdSteelWoodQuality::Apply(Next.WoodworkingJob.Item,Next.WoodworkingJob)'),
('    for(const auto& Input:Recipe->Inputs)\n    {\n        const FString Name=', '    TArray<FColdSteelCraftingInput> Inputs;InputsFor(Inputs);\n    for(const auto& Input:Inputs)\n    {\n        const FString Name='),
('S->Catalog=Catalog;S->ConfigError=', 'S->Catalog=Catalog;S->CoreCatalog=CoreCatalog;S->SelectedCore=SelectedCore;S->ConfigError=')])
edit('Source/FPSGAME/Building/WoodworkingJob.cpp',[
('    M->SyncRuntime();auto Next=M->Snapshot();\n    const bool Free=', '    TArray<FColdSteelCraftingInput> Inputs;\n    if(!InputsFor(Inputs)){Notice=TEXT("请选择可用木芯");return false;}\n    M->SyncRuntime();auto Next=M->Snapshot();\n    const bool Free='),
('    if(!Free)for(const auto& Input:Recipe->Inputs)\n    {','    if(!Free)for(const auto& Input:Inputs)\n    {'),
('    Pending.bMaterialsWaived=Free;\n    if(!Free)for(const auto& Input:Recipe->Inputs)', '    Pending.bMaterialsWaived=Free;Pending.QualityVersion=ColdSteelWoodQuality::Version;\n    Pending.Core=Core();Pending.MaterialBonus=MaterialBonus();\n    if(!Free)for(const auto& Input:Inputs)'),
('ColdSteelWoodQuality::Apply(Pending.Item,Score)','ColdSteelWoodQuality::Apply(Pending.Item,Pending)'),
('(ColdSteelWoodQuality::FromScore(Score)-1)*100','(ColdSteelWoodQuality::FromJob(Pending)-1)*100')])
edit('Source/FPSGAME/Multiplayer/ColdSteelStationNetwork.cpp',[
('if(Mode==TEXT("forge.start")||Mode==TEXT("assembly.start"))R.Item=ForgeMetal.ToString();','if(Mode==TEXT("forge.start")||Mode==TEXT("assembly.start")||Mode==TEXT("wood.start"))R.Item=ForgeMetal.ToString();'),
('{if(!GuestWood->NetworkOpen())GuestWood->Open(false);if(GuestWood->Select(R.Definition))Ok=GuestWood->StartMode(EWoodworkingMode::Craft);}', '{if(!GuestWood->NetworkOpen())GuestWood->Open(false);if(GuestWood->Select(R.Definition)&&GuestWood->SelectCore(FName(*R.Item)))Ok=GuestWood->StartMode(EWoodworkingMode::Craft);}')])
edit('Source/FPSGAME/UI/ColdSteelInventoryRules.cpp',[
('        if(J.Version!=1||J.Pattern.IsNone()||J.Recipe.IsNone()||J.Item.InstanceId.IsEmpty()||!Object(J.Item)', '        if(J.Version!=1||(J.QualityVersion!=1&&J.QualityVersion!=2)\n            ||(J.QualityVersion==2&&(J.Core.IsNone()||!FMath::IsFinite(J.MaterialBonus)||J.MaterialBonus<0||J.MaterialBonus>.10\n                ||(!J.bMaterialsWaived&&J.PaidMaterials.FindRef(J.Core.ToString())!=1)))\n            ||J.Pattern.IsNone()||J.Recipe.IsNone()||J.Item.InstanceId.IsEmpty()||!Object(J.Item)')])
edit('Source/FPSGAME/Building/WoodworkingWorldView.cpp',[
('    PC=Player;Workbench=Station;System=InSystem;SetOwner(Player);', '    PC=Player;Workbench=Station;System=InSystem;SetOwner(Player);\n    if(const auto* Core=InSystem->FindCore(InSystem->Core()))StockMaterial=TSoftObjectPtr<UMaterialInterface>(Core->Material);')])
edit('Source/FPSGAME/Building/WoodworkingQuality.h',[
('struct FColdSteelItem;', 'struct FColdSteelItem;\nstruct FColdSteelWoodworkingJob;'),
('    double FromScore(double Score);','    constexpr int32 Version=2;\n    constexpr double MaxMaterialBonus=.10,MaxSkillBonus=.15;\n    double FromScore(double Score); // Legacy curve.\n    double SkillBonus(double Score);\n    double FromJob(const FColdSteelWoodworkingJob& Job);\n    bool UsesMaterials(const FColdSteelItem& Item);\n    double MaterialBonus(const FColdSteelItem& Item);'),
('    bool Apply(FColdSteelItem& Item,double Score);','    bool Apply(FColdSteelItem& Item,double Score,double MaterialBonus=0,FName Core=NAME_None,int32 QualityVersion=1);\n    bool Apply(FColdSteelItem& Item,const FColdSteelWoodworkingJob& Job);')])
edit('Source/FPSGAME/Building/WoodworkingQuality.cpp',[
('bool Read(const FColdSteelItem& Item,double& Score)', '''double SkillBonus(double Score){return FMath::IsFinite(Score)?FMath::Clamp(Score,0.,100.)*MaxSkillBonus/100.:0.;}
double FromJob(const FColdSteelWoodworkingJob& Job)
{return Job.QualityVersion>=Version?1.+FMath::Clamp(Job.MaterialBonus,0.,MaxMaterialBonus)+SkillBonus(Job.Quality):FromScore(Job.Quality);}
bool UsesMaterials(const FColdSteelItem& Item)
{
    const auto Data=ColdSteelItemData::Read(Item.Data);const TSharedPtr<FJsonObject>* Q=nullptr;double V=0;
    return Data&&Data->TryGetObjectField(Field,Q)&&Q&&*Q&&(*Q)->TryGetNumberField(TEXT("version"),V)&&V==Version;
}
double MaterialBonus(const FColdSteelItem& Item)
{
    const auto Data=ColdSteelItemData::Read(Item.Data);const TSharedPtr<FJsonObject>* Q=nullptr;double Bonus=0;
    if(!UsesMaterials(Item)||!Data->TryGetObjectField(Field,Q)||!Q||!*Q||!(*Q)->TryGetNumberField(TEXT("materialBonus"),Bonus)||!FMath::IsFinite(Bonus))return 0;
    return FMath::Clamp(Bonus,0.,MaxMaterialBonus);
}
bool Read(const FColdSteelItem& Item,double& Score)'''),
('&&Version==1','&&(Version==1||Version==ColdSteelWoodQuality::Version)'),
('{double Score=0;return Channel(Item)==Expected&&Read(Item,Score)?FromScore(Score):1.;}', '{double Score=0;if(Channel(Item)!=Expected||!Read(Item,Score))return 1.;return UsesMaterials(Item)?1.+MaterialBonus(Item)+SkillBonus(Score):FromScore(Score);}'),
('bool Apply(FColdSteelItem& Item,double Score)', 'bool Apply(FColdSteelItem& Item,double Score,double Bonus,FName Core,int32 QualityVersion)'),
('    if(!FMath::IsFinite(Score))return false;', '    if(!FMath::IsFinite(Score)||!FMath::IsFinite(Bonus)||(QualityVersion!=1&&QualityVersion!=Version))return false;'),
('    Q->SetNumberField(TEXT("version"),1);Q->SetNumberField(TEXT("score"),Score);\n    Q->SetNumberField(TEXT("multiplier"),FromScore(Score));', '    Q->SetNumberField(TEXT("version"),QualityVersion);Q->SetNumberField(TEXT("score"),Score);\n    if(QualityVersion>=Version){Q->SetNumberField(TEXT("materialBonus"),FMath::Clamp(Bonus,0.,MaxMaterialBonus));Q->SetStringField(TEXT("core"),Core.ToString());}\n    Q->SetNumberField(TEXT("multiplier"),QualityVersion>=Version?1.+FMath::Clamp(Bonus,0.,MaxMaterialBonus)+SkillBonus(Score):FromScore(Score));'),
('void PreserveAuthoritative(', 'bool Apply(FColdSteelItem& Item,const FColdSteelWoodworkingJob& Job)\n{return Apply(Item,Job.Quality,Job.MaterialBonus,Job.Core,Job.QualityVersion);}\nvoid PreserveAuthoritative(')])
edit('Source/FPSGAME/UI/ColdSteelItemTooltipData.cpp',[
('const double Multiplier=ColdSteelWoodQuality::FromScore(WoodScore),Percent=', 'const double Multiplier=ColdSteelWoodQuality::Multiplier(I,ColdSteelWoodQuality::Channel(I)),Percent='),
('        Note(C,TEXT("评分规则"),TEXT("50 分无修正，100 分 +25%，最低 -25%；品质随成品保存"));', '''        if(ColdSteelWoodQuality::UsesMaterials(I))
        {
            const double Material=ColdSteelWoodQuality::MaterialBonus(I)*100,Skill=ColdSteelWoodQuality::SkillBonus(WoodScore)*100;
            Row(C,TEXT("木芯保底"),Signed(Material,TEXT("%")),Material>0?1:0);
            Row(C,TEXT("加工加成"),Signed(Skill,TEXT("%")),Skill>0?1:0);
            Note(C,TEXT("评分规则"),TEXT("木芯保底与加工加成相加，最高 +25%；加工满分 +15%"));
        }
        else Note(C,TEXT("评分规则"),TEXT("旧版工艺：50 分无修正，100 分 +25%，最低 -25%；保留原数值"));''')])
print('Woodworking material gameplay source integrated')
