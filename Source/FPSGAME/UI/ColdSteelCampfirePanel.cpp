#include "ColdSteelCampfirePanel.h"
#include "ColdSteelHUDWidget.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelUIStyle.h"
#include "GunsmithUIStyle.h"
#include "ColdSteelConsumablePresentation.h"
#include "ColdSteelItemReadCache.h"
#include "../Building/ColdSteelCampfire.h"
#include "../Building/SmeltingSystem.h"
#include "../Development/DevelopmentTuningSubsystem.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "Blueprint/WidgetTree.h"
#include "Components/Border.h"
#include "Components/Button.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/Image.h"
#include "Components/ProgressBar.h"
#include "Components/ScaleBox.h"
#include "Components/ScrollBox.h"
#include "Components/SizeBox.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Engine/GameInstance.h"
#include "Engine/Texture2D.h"
#include "GameFramework/PlayerController.h"
#include "ImageUtils.h"
#include "Misc/Paths.h"

namespace
{
    void Put(UTextBlock* Label,const FString& Text,const FLinearColor& Color=ColdSteelUI::TextSecondary)
    {
        if(Label->GetText().ToString()!=Text)Label->SetText(FText::FromString(Text));
        Label->SetColorAndOpacity(Color);
    }
    FString Fresh(double Days){return Days>=0.?FString::Printf(TEXT(" · 保鲜 %.1f 天"),Days):FString();}
}
void UColdSteelCampfirePanel::NativeOnInitialized()
{
    Super::NativeOnInitialized();
    Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    System=GetGameInstance()->GetSubsystem<UColdSteelSmeltingSystem>();
    Build();
}
UTextBlock* UColdSteelCampfirePanel::Label(const FString& Text,float Size,bool Wrap)
{
    auto* T=WidgetTree->ConstructWidget<UTextBlock>();T->SetText(FText::FromString(Text));
    T->SetFont(GunsmithUI::TextFont(Size/Scale,Size>=16));T->SetColorAndOpacity(ColdSteelUI::TextSecondary);
    T->SetAutoWrapText(Wrap);T->SetVisibility(ESlateVisibility::HitTestInvisible);return T;
}
UButton* UColdSteelCampfirePanel::Button(const FString& Text)
{
    auto* B=WidgetTree->ConstructWidget<UButton>();B->SetStyle(ColdSteelUI::ButtonStyle(Scale));
    B->SetContent(Label(Text,14,false));return B;
}
UVerticalBox* UColdSteelCampfirePanel::Section(UVerticalBox* Parent,const FString& Title)
{
    auto* Card=WidgetTree->ConstructWidget<UBorder>();
    Card->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::StatusCard,ColdSteelUI::CardRadius/Scale));
    Card->SetPadding(FMargin(10/Scale));Parent->AddChildToVerticalBox(Card)->SetPadding(FMargin(0,0,0,8/Scale));
    auto* Box=WidgetTree->ConstructWidget<UVerticalBox>();Card->SetContent(Box);
    auto* TitleLabel=Label(Title,16);TitleLabel->SetColorAndOpacity(ColdSteelUI::TextPrimary);
    Box->AddChildToVerticalBox(TitleLabel)->SetPadding(FMargin(0,0,0,8/Scale));return Box;
}
const FColdSteelItem& UColdSteelCampfirePanel::Item(const FString& Id)
{
    if(const auto* Found=Items.Find(Id))return *Found;
    return Items.Add(Id,Model?Model->CreateItem(Id):FColdSteelItem());
}
FString UColdSteelCampfirePanel::Name(const FString& Id)
{
    const FString N=ColdSteelInventory::Text(Item(Id),TEXT("name"));return N.IsEmpty()?Id:N;
}
void UColdSteelCampfirePanel::Build()
{
    Scale=ColdSteelUI::PixelScale(this);Rows.Reset();Proxies.Reset();Textures.Reset();ProductLabels.Reset();
    auto* Root=Cast<UVerticalBox>(WidgetTree->RootWidget);
    if(Root)Root->ClearChildren();else {Root=WidgetTree->ConstructWidget<UVerticalBox>();WidgetTree->RootWidget=Root;}
    auto* Header=WidgetTree->ConstructWidget<UBorder>();Header->SetPadding(FMargin(12/Scale));
    Header->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::HeaderTint,10/Scale));Root->AddChildToVerticalBox(Header);
    auto* Head=WidgetTree->ConstructWidget<UHorizontalBox>();Header->SetContent(Head);
    auto* Title=Label(TEXT("篝火 · 共享烧烤"),20,false);Title->SetColorAndOpacity(ColdSteelUI::TextPrimary);
    auto* TS=Head->AddChildToHorizontalBox(Title);TS->SetSize(FSlateChildSize(ESlateSizeRule::Fill));TS->SetVerticalAlignment(VAlign_Center);
    auto* X=Button(TEXT("×"));X->OnClicked.AddDynamic(this,&ThisClass::Close);Head->AddChildToHorizontalBox(X);
    auto* Scroll=WidgetTree->ConstructWidget<UScrollBox>();Scroll->SetConsumeMouseWheel(EConsumeMouseWheel::Always);
    Scroll->SetScrollbarThickness(FVector2D(6/Scale));
    auto* SS=Root->AddChildToVerticalBox(Scroll);SS->SetSize(FSlateChildSize(ESlateSizeRule::Fill));SS->SetPadding(FMargin(12/Scale,8/Scale));
    auto* Body=WidgetTree->ConstructWidget<UVerticalBox>();Scroll->AddChild(Body);
    auto* Current=Section(Body,TEXT("当前加工"));StateText=Label(TEXT("等待篝火同步"),16);Current->AddChildToVerticalBox(StateText);
    TimeText=Label(TEXT(""),12);Current->AddChildToVerticalBox(TimeText)->SetPadding(FMargin(0,6/Scale));
    auto* BarSize=WidgetTree->ConstructWidget<USizeBox>();BarSize->SetHeightOverride(5/Scale);
    CookingBar=WidgetTree->ConstructWidget<UProgressBar>();BarSize->SetContent(CookingBar);Current->AddChildToVerticalBox(BarSize);
    FProgressBarStyle BarStyle;
    BarStyle.SetBackgroundImage(ColdSteelUI::RoundedBrush(ColdSteelUI::Content,2/Scale,FLinearColor::Transparent,0));
    BarStyle.SetFillImage(ColdSteelUI::RoundedBrush(FLinearColor::White,2/Scale,FLinearColor::Transparent,0));CookingBar->SetWidgetStyle(BarStyle);
    auto* Queue=Section(Body,TEXT("等待队列"));QueueText=Label(TEXT(""),14);Queue->AddChildToVerticalBox(QueueText);
    auto* Products=Section(Body,TEXT("公共成品"));ProductsText=Label(TEXT(""),14);Products->AddChildToVerticalBox(ProductsText);
    ProductRows=WidgetTree->ConstructWidget<UVerticalBox>();Products->AddChildToVerticalBox(ProductRows);
    auto* Recipes=Section(Body,TEXT("烧烤菜谱"));FilterButton=Button(bOnlyCraftable?TEXT("仅看可制作：开"):TEXT("仅看可制作：关"));
    FilterButton->OnClicked.AddDynamic(this,&ThisClass::Filter);Recipes->AddChildToVerticalBox(FilterButton)->SetPadding(FMargin(0,0,0,6/Scale));
    if(System)for(const auto& R:System->Catalog())if(R.bCampfire)
    {
        auto* Choice=Button(TEXT(""));auto* Row=WidgetTree->ConstructWidget<UHorizontalBox>();Choice->SetContent(Row);
        const FString Path=ColdSteelInventory::Text(Item(R.Input),TEXT("ue_icon"));
        if(!Path.IsEmpty())if(auto* Texture=FImageUtils::ImportFileAsTexture2D(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/Path))
        {
            Textures.Add(Texture);auto* Size=WidgetTree->ConstructWidget<USizeBox>();Size->SetWidthOverride(40/Scale);Size->SetHeightOverride(48/Scale);
            auto* Fit=WidgetTree->ConstructWidget<UScaleBox>();Fit->SetStretch(EStretch::ScaleToFit);Size->SetContent(Fit);
            auto* Icon=WidgetTree->ConstructWidget<UImage>();Icon->SetBrushFromTexture(Texture,true);Fit->SetContent(Icon);
            Row->AddChildToHorizontalBox(Size)->SetPadding(FMargin(0,0,8/Scale,0));
        }
        auto* Copy=WidgetTree->ConstructWidget<UVerticalBox>();
        auto* CopySlot=Row->AddChildToHorizontalBox(Copy);CopySlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));CopySlot->SetVerticalAlignment(VAlign_Center);
        auto* N=Label(Name(R.Output),14);N->SetColorAndOpacity(ColdSteelUI::TextPrimary);Copy->AddChildToVerticalBox(N);
        auto* Stock=Label(TEXT(""),12);Copy->AddChildToVerticalBox(Stock);
        Recipes->AddChildToVerticalBox(Choice)->SetPadding(FMargin(0,2/Scale));
        auto* Proxy=NewObject<UColdSteelCampfireRecipeProxy>(this);Proxy->Panel=this;Proxy->Recipe=R.Id;Proxies.Add(Proxy);
        Choice->OnClicked.AddDynamic(Proxy,&UColdSteelCampfireRecipeProxy::Clicked);Rows.Add({R.Id,Choice,Stock});
        if(Selected.IsNone())Selected=R.Id;
    }
    EmptyText=Label(TEXT("没有符合筛选的菜谱"),12);Recipes->AddChildToVerticalBox(EmptyText);
    Details=Section(Body,TEXT("所选菜品"));ShowDetails();
    Body->AddChildToVerticalBox(Label(TEXT("燃烧时，5 米内饥饿与缺水的自然消耗各减缓 50%，不叠加。木材持续燃烧，离线也计时；食材和成品会随游戏内自然日腐败。"),12));
    auto* Actions=WidgetTree->ConstructWidget<UBorder>();Actions->SetPadding(FMargin(12/Scale,8/Scale));
    Actions->SetBrush(ColdSteelUI::RoundedBrush(ColdSteelUI::Content,8/Scale));Root->AddChildToVerticalBox(Actions);
    auto* Controls=WidgetTree->ConstructWidget<UVerticalBox>();Actions->SetContent(Controls);
    FuelText=Label(TEXT(""),12);Controls->AddChildToVerticalBox(FuelText);
    FreeText=Label(TEXT(""),12);Controls->AddChildToVerticalBox(FreeText)->SetPadding(FMargin(0,4/Scale));
    auto* BatchRow=WidgetTree->ConstructWidget<UHorizontalBox>();Controls->AddChildToVerticalBox(BatchRow)->SetPadding(FMargin(0,4/Scale));
    MinusButton=Button(TEXT("−"));MinusButton->OnClicked.AddDynamic(this,&ThisClass::Minus);BatchRow->AddChildToHorizontalBox(MinusButton);
    BatchText=Label(TEXT(""),14,false);BatchText->SetJustification(ETextJustify::Center);
    auto* BS=BatchRow->AddChildToHorizontalBox(BatchText);BS->SetSize(FSlateChildSize(ESlateSizeRule::Fill));BS->SetVerticalAlignment(VAlign_Center);
    PlusButton=Button(TEXT("＋"));PlusButton->OnClicked.AddDynamic(this,&ThisClass::Plus);BatchRow->AddChildToHorizontalBox(PlusButton);
    auto* Buttons=WidgetTree->ConstructWidget<UHorizontalBox>();Controls->AddChildToVerticalBox(Buttons)->SetPadding(FMargin(0,4/Scale));
    StartButton=Button(TEXT("加入队列"));StartButton->OnClicked.AddDynamic(this,&ThisClass::Start);
    CollectButton=Button(TEXT("领取成品"));CollectButton->OnClicked.AddDynamic(this,&ThisClass::Collect);
    FuelButton=Button(TEXT("添柴 ×1"));FuelButton->OnClicked.AddDynamic(this,&ThisClass::AddFuel);
    for(UButton* B:{StartButton.Get(),CollectButton.Get(),FuelButton.Get()})
    {
        auto* Size=WidgetTree->ConstructWidget<USizeBox>();Size->SetHeightOverride(ColdSteelUI::ActionHeight/Scale);Size->SetContent(B);
        auto* ButtonSlot=Buttons->AddChildToHorizontalBox(Size);ButtonSlot->SetSize(FSlateChildSize(ESlateSizeRule::Fill));ButtonSlot->SetPadding(FMargin(2/Scale,0));
    }
    StatusText=Label(TEXT("食材由操作者投入，队列与成品全员共享"),12);Controls->AddChildToVerticalBox(StatusText);
}
void UColdSteelCampfirePanel::Configure(UColdSteelHUDWidget* Owner,AColdSteelCampfire* Station)
{
    HUD=Owner;Fire=Station;Batch=1;Refresh();
}
void UColdSteelCampfirePanel::NativeTick(const FGeometry& Geometry,float Delta)
{
    Super::NativeTick(Geometry,Delta);if(!Fire.IsValid())return;
    if(!FMath::IsNearlyEqual(Scale,ColdSteelUI::PixelScale(this),.001f)){Build();Refresh();return;}
    RefreshTime+=Delta;if(RefreshTime<.2f)return;RefreshTime=0;Refresh();
}
void UColdSteelCampfirePanel::SelectRecipe(FName Recipe){Selected=Recipe;Batch=1;ShowDetails();Refresh();}
void UColdSteelCampfirePanel::ShowDetails()
{
    if(!Details||!System)return;
    // Keep the section title; replace only the selected item's description.
    while(Details->GetChildrenCount()>1)Details->RemoveChildAt(1);
    const auto* R=System->Find(Selected);if(!R)return;
    Details->AddChildToVerticalBox(Label(FString::Printf(TEXT("%s ×%lld → %s ×%lld · 每份 %.0f 秒"),*Name(R->Input),R->InputCount,*Name(R->Output),R->OutputCount,R->Seconds),14));
    TArray<ColdSteelConsumable::FRow> Effects;
    const auto& Product=Item(R->Output);const auto Data=ColdSteelItemData::Read(Product.Data);
    ColdSteelConsumable::BuildDetailRows(Product,nullptr,Data.Get(),Effects);
    for(const auto& E:Effects)
    {
        auto* Text=Label(E.Label+(E.Value.IsEmpty()?FString():TEXT("  ")+E.Value),E.bSection?14:12);
        Text->SetColorAndOpacity(E.Tone>0?ColdSteelUI::Success:E.Tone<0?ColdSteelUI::Danger:ColdSteelUI::TextSecondary);
        Details->AddChildToVerticalBox(Text)->SetPadding(FMargin(0,3/Scale,0,0));
        if(!E.Note.IsEmpty())Details->AddChildToVerticalBox(Label(E.Note,12));
    }
}
void UColdSteelCampfirePanel::Refresh()
{
    const auto* Station=Fire.Get();if(!Station||!System||!Model)return;
    const auto& S=Station->SharedState();const auto& FC=System->FuelConfig();
    const auto* PC=GetOwningPlayer();const auto* PS=PC?PC->GetPlayerState<AColdSteelPlayerState>():nullptr;
    const bool Pending=PS&&(PS->CampfireRequestPending()||PS->InventoryRequestPending());
    const bool Ready=Station->IsAvailable()&&S.Revision>0&&!S.bSaveBlocked&&PS&&!Pending;
    const bool Free=UDevelopmentTuningSubsystem::IsFreeCrafting(Model);
    const double Fuel=Station->DisplayFuel();const auto* Active=System->Find(S.Recipe);
    const double Progress=Active?FMath::Clamp(Station->DisplayProgress(),0.,Active->Seconds):0.;
    double Need=Active?FMath::Max(0.,(S.Batch-S.Produced)*Active->Seconds-Progress):0.;
    const double BatchNeed=Need;int64 Stored=0;TMap<FString,int64> Counts;TMap<FString,double> Days;
    for(const auto& P:S.Products)
    {
        Stored+=P.Count;Counts.FindOrAdd(P.Item)+=P.Count;
        if(P.FreshDays>=0.){auto* D=Days.Find(P.Item);if(D)*D=FMath::Min(*D,P.FreshDays);else Days.Add(P.Item,P.FreshDays);}
    }
    FString Queue=FString::Printf(TEXT("%d / 8 项"),S.Queue.Num());
    for(int32 I=0;I<S.Queue.Num();++I)
    {
        const auto& Q=S.Queue[I];const auto* R=System->Find(Q.Recipe);if(R)Need+=R->Seconds*Q.Batch;
        Queue+=FString::Printf(TEXT("\n%d. %s ×%lld%s%s"),I+1,R?*Name(R->Output):*Q.Recipe.ToString(),Q.Batch,*Fresh(Q.FreshDays),Q.bMaterialsWaived?TEXT(" · 免食材"):TEXT(""));
    }
    Put(QueueText,Queue);
    Put(ProductsText,FString::Printf(TEXT("%lld / 60 份 · 按品类汇总"),Stored));
    for(const auto& Pair:ProductLabels)Pair.Value->SetVisibility(Counts.Contains(Pair.Key)?ESlateVisibility::HitTestInvisible:ESlateVisibility::Collapsed);
    TArray<FString> Keys;Counts.GetKeys(Keys);Keys.Sort();
    for(const auto& K:Keys)
    {
        auto* Text=ProductLabels.FindRef(K).Get();
        if(!Text){Text=Label(TEXT(""),14);ProductLabels.Add(K,Text);ProductRows->AddChildToVerticalBox(Text)->SetPadding(FMargin(0,4/Scale,0,0));}
        const double Remaining=Days.Contains(K)?Days[K]:-1.;
        const double Lifetime=ColdSteelInventory::Number(Item(K),TEXT("spoilDays"));
        const FLinearColor Color=K==TEXT("spoiled_food")||Remaining==0.||(Lifetime>0.&&Remaining>=0.&&Remaining/Lifetime<.2)
            ?ColdSteelUI::Danger:Lifetime>0.&&Remaining>=0.&&Remaining/Lifetime<.5?ColdSteelUI::Warning:ColdSteelUI::TextSecondary;
        Put(Text,FString::Printf(TEXT("%s ×%lld%s"),*Name(K),Counts[K],*Fresh(Remaining)),Color);
    }
    const bool Full=Active&&Stored+Active->OutputCount>UColdSteelSmeltingSystem::CastingCapacity;
    const FString State=S.bSaveBlocked?TEXT("保存待恢复"):S.Revision<=0?TEXT("等待篝火同步"):Full?TEXT("成品已满 · 烧烤暂停"):
        Active?(Fuel>0?TEXT("烧烤中"):TEXT("缺少木材 · 进度保留")):Fuel>0?TEXT("燃烧中 · 可以投料"):TEXT("篝火已熄灭");
    Put(StateText,State,S.bSaveBlocked?ColdSteelUI::Danger:Full||(Active&&Fuel<=0)?ColdSteelUI::Warning:ColdSteelUI::TextPrimary);
    Put(TimeText,Active?FString::Printf(TEXT("%s · %lld / %lld 份%s\n本份剩余 %.1f 秒 · 本批剩余 %.0f 秒%s"),*Name(Active->Output),S.Produced,S.Batch,*Fresh(S.FreshDays),Active->Seconds-Progress,BatchNeed,S.bMaterialsWaived?TEXT(" · 免食材"):TEXT("")):TEXT("无加工任务"));
    const float Ratio=Active?Progress/Active->Seconds:0.f;CookingBar->SetPercent(Ratio);CookingBar->SetFillColorAndOpacity(ColdSteelUI::ActionProgressColor(Ratio));
    const int64 Wood=Model->CountMaterial(FC.Item);const double Missing=FMath::Max(0.,Need-Fuel);
    Put(FuelText,FString::Printf(TEXT("木材 %lld · 燃料 %.0f / %.0f 秒\n全部队列需 %.0f 秒%s"),Wood,Fuel,FC.Capacity,Need,
        Missing>0?*FString::Printf(TEXT(" · 还需添柴 %lld 份"),FMath::CeilToInt64(Missing/FC.SecondsPerUnit)):Need>0?TEXT(" · 燃料充足"):TEXT(" · 暂无加工需求")),Missing>0?ColdSteelUI::Warning:ColdSteelUI::TextSecondary);
    Put(FreeText,Free?TEXT("F6 免食材 · 木材照常消耗 · 免费食材不退料"):TEXT("扣除新鲜食材 · 无燃料也可排队"),Free?ColdSteelUI::Warning:ColdSteelUI::TextTertiary);
    int32 Visible=0;
    for(const auto& Row:Rows)if(const auto* R=System->Find(Row.Id))
    {
        const int64 FreshCount=UColdSteelSmeltingSystem::FreshCampfireCount(Model,R->Input);
        const bool Can=Free||FreshCount>=R->InputCount;
        if(auto* B=Row.Button.Get())
        {
            B->SetVisibility(!bOnlyCraftable||Can?ESlateVisibility::Visible:ESlateVisibility::Collapsed);
            B->SetIsEnabled(!Pending);auto Style=ColdSteelUI::ButtonStyle(Scale);
            if(Selected==Row.Id)Style.Normal=ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonHover,6/Scale,ColdSteelUI::Accent,1/Scale);
            B->SetStyle(Style);
        }
        if(!bOnlyCraftable||Can)++Visible;
        if(auto* T=Row.Stock.Get())Put(T,FString::Printf(TEXT("新鲜 %lld / 每份需 %lld · %.0f 秒%s"),FreshCount,R->InputCount,R->Seconds,Free?TEXT(" · 免食材"):Can?TEXT(""):TEXT(" · 食材不足")),Can?ColdSteelUI::TextSecondary:ColdSteelUI::Danger);
    }
    EmptyText->SetVisibility(Visible?ESlateVisibility::Collapsed:ESlateVisibility::HitTestInvisible);
    const auto* R=System->Find(Selected);
    MaxBatch=R?(Free?5:FMath::Min<int64>(5,UColdSteelSmeltingSystem::FreshCampfireCount(Model,R->Input)/R->InputCount)):0;
    Batch=FMath::Clamp<int64>(Batch,1,FMath::Max<int64>(1,MaxBatch));
    Put(BatchText,FString::Printf(TEXT("批量 ×%lld · 可做 %lld"),Batch,MaxBatch));
    MinusButton->SetIsEnabled(!Pending&&Batch>1);PlusButton->SetIsEnabled(!Pending&&Batch<MaxBatch);
    StartButton->SetIsEnabled(Ready&&R&&MaxBatch>=Batch&&S.Queue.Num()<8);
    CollectButton->SetIsEnabled(Ready&&Stored>0);
    FuelButton->SetIsEnabled(Ready&&Wood>0&&Fuel+FC.SecondsPerUnit<=FC.Capacity+1e-6);
    const FString Message=PS?PS->CampfireMessage():FString();
    Put(StatusText,Pending?TEXT("正在同步操作，请稍候…"):Message.IsEmpty()?TEXT("食材由操作者投入，队列与成品全员共享"):Message,
        Pending||S.bSaveBlocked?ColdSteelUI::Warning:Message.IsEmpty()?ColdSteelUI::TextTertiary:PS->CampfireResultSucceeded()?ColdSteelUI::Success:ColdSteelUI::Danger);
}
void UColdSteelCampfirePanel::Submit(uint8 Action)
{
    if(auto* PC=GetOwningPlayer())if(auto* PS=PC->GetPlayerState<AColdSteelPlayerState>())if(Fire.IsValid())
        PS->RequestCampfire(Fire.Get(),Action,Action==1?Selected:NAME_None,Action==1?Batch:1);
    Refresh();
}
void UColdSteelCampfirePanel::Close(){if(HUD.IsValid())HUD->CloseSmelting();}
void UColdSteelCampfirePanel::Start(){Submit(1);}
void UColdSteelCampfirePanel::Collect(){Submit(2);}
void UColdSteelCampfirePanel::AddFuel(){Submit(0);}
void UColdSteelCampfirePanel::Minus(){Batch=FMath::Max<int64>(1,Batch-1);Refresh();}
void UColdSteelCampfirePanel::Plus(){Batch=FMath::Min(MaxBatch,Batch+1);Refresh();}
void UColdSteelCampfirePanel::Filter()
{
    bOnlyCraftable=!bOnlyCraftable;
    Cast<UTextBlock>(FilterButton->GetContent())->SetText(FText::FromString(bOnlyCraftable?TEXT("仅看可制作：开"):TEXT("仅看可制作：关")));Refresh();
}
