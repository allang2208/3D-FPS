#include "ShotgunAmmoIconDiagnosisCommandlet.h"
#include "ColdSteelAmmoWheel.h"
#include "ColdSteelStatusModel.h"
#include "Engine/GameInstance.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Slate/WidgetRenderer.h"
#include "Widgets/SLeafWidget.h"
#include "Framework/Application/SlateApplication.h"
#include "RenderingThread.h"
#include "ImageUtils.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/Parse.h"
#include "UObject/StrongObjectPtr.h"
#include "HAL/FileManager.h"
#include "Styling/SlateBrush.h"
#if WITH_EDITOR
#include "Interfaces/ISlateRHIRendererModule.h"
#include "Modules/ModuleManager.h"
#endif

namespace
{
class SAmmoWheelDiagnosis : public SLeafWidget
{
public:
    SLATE_BEGIN_ARGS(SAmmoWheelDiagnosis) {} SLATE_END_ARGS()
    using FPaint=TFunction<int32(const FPaintArgs&,const FGeometry&,const FSlateRect&,FSlateWindowElementList&,int32,const FWidgetStyle&,bool)>;
    FPaint Paint;
    void Construct(const FArguments&) {}
    virtual FVector2D ComputeDesiredSize(float) const override {return FVector2D(1280,900);}
    virtual int32 OnPaint(const FPaintArgs& A,const FGeometry& G,const FSlateRect& C,FSlateWindowElementList& O,int32 L,const FWidgetStyle& S,bool E) const override
    {return Paint(A,G,C,O,L,S,E);}
};
}
int32 UShotgunAmmoIconDiagnosisCommandlet::Main(const FString& Params)
{
#if WITH_EDITOR
    if(!FSlateApplication::IsInitialized())
    {
        auto& Module=FModuleManager::LoadModuleChecked<ISlateRHIRendererModule>(TEXT("SlateRHIRenderer"));
        FSlateApplication::InitializeAsStandaloneApplication(Module.CreateSlateRHIRenderer());
    }
#else
    return 1;
#endif
    // No GameInstance::Init, profile restore, inventory grants or save writes.
    TStrongObjectPtr<UGameInstance> Owner(NewObject<UGameInstance>());
    TStrongObjectPtr<UColdSteelStatusModel> Model(NewObject<UColdSteelStatusModel>(Owner.Get()));
    Model->LoadAmmoCatalog();
    TStrongObjectPtr<UColdSteelAmmoWheel> Wheel(NewObject<UColdSteelAmmoWheel>(Owner.Get()));
    Wheel->Model=Model.Get();
    FColdSteelItem Gun;Gun.InstanceId=TEXT("ammo-icon-diagnosis");Gun.Definition=TEXT("ue_super90");Gun.LoadedAmmoType=TEXT("ammo_12g");
    Gun.Data=TEXT("{\"name\":\"SUPER90\"}");Model->Current.Items.Add(Gun);
    for(const auto& Type:Model->AmmoCatalog())if(Type.Group==TEXT("ammo_12g"))Model->Current.AmmoPouch.Add(Type.Id,24);
    if(FParse::Param(*Params,TEXT("ReopenAfterMissingIcon")))
    {
        auto* Type=Model->AmmoTypes.FindByPredicate([](const auto& T){return T.Id==TEXT("ammo_12g");});
        if(!Type)return 6;
        const FString IconPath=Type->Icon;Type->Icon=TEXT("Icons/__shotgun_diagnosis_missing__.png");
        Wheel->OpenForWeapon(Gun.InstanceId);
        const bool bInitialMissing=Wheel->FramedIcon(Type->Id)==nullptr;
        UE_LOG(LogTemp,Display,TEXT("AMMO_ICON_DIAG initial_missing=%d"),bInitialMissing);
        if(!bInitialMissing)return 7;
        Type->Icon=IconPath;
    }
    Wheel->OpenForWeapon(Gun.InstanceId);Wheel->ActiveDisc=0;
    for(const auto& Type:Model->AmmoCatalog())if(Type.Group==TEXT("ammo_12g"))
    {
        const auto* Brush=Wheel->FramedIcon(Type.Id);
        UE_LOG(LogTemp,Display,TEXT("AMMO_ICON_DIAG %s brush=%d resource=%s"),*Type.Id,Brush!=nullptr,*GetNameSafe(Brush?Brush->GetResourceObject():nullptr));
        if(!Brush||!Brush->GetResourceObject())return 2;
    }
    if(Wheel->Discs.Num()!=1||Wheel->Discs[0].Choices.Num()!=3)return 3;
    auto Proxy=SNew(SAmmoWheelDiagnosis);
    Proxy->Paint=[&](const FPaintArgs& A,const FGeometry& G,const FSlateRect& C,FSlateWindowElementList& O,int32 L,const FWidgetStyle& S,bool E)
    {return Wheel->NativePaint(A,G,C,O,L,S,E);};
    FlushRenderingCommands();
    FWidgetRenderer Renderer(true,true);
    TStrongObjectPtr<UTextureRenderTarget2D> Target(Renderer.DrawWidget(Proxy,FVector2D(1280,900)));
    FlushRenderingCommands();
    TArray<FColor> Pixels;
    if(!Target.IsValid()||!Target->GameThread_GetRenderTargetResource()->ReadPixels(Pixels))return 4;
    TArray64<uint8> PNG;FImageUtils::PNGCompressImageArray(1280,900,Pixels,PNG);
    FString Output=FPaths::ProjectSavedDir()/TEXT("ShotgunAmmoModels20261012/wheel.png");FParse::Value(*Params,TEXT("Output="),Output);
    IFileManager::Get().MakeDirectory(*FPaths::GetPath(Output),true);
    if(!FFileHelper::SaveArrayToFile(PNG,*Output))return 5;
    UE_LOG(LogTemp,Display,TEXT("AMMO_ICON_DIAG rendered=%s"),*Output);
    return 0;
}
