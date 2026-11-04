#include "SwordBladeFinishAuditCommandlet.h"
#include "ModularSwordVisual.h"
#include "../Characters/FPSBodyRuneVisual.h"
#include "../Characters/FPSPlayerBodyTypes.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Engine/StaticMesh.h"
#include "Engine/Texture.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/ObjectAndNameAsStringProxyArchive.h"
#include "Serialization/MemoryReader.h"
#include "Serialization/MemoryWriter.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/Parse.h"

int32 RunSharedTwoHandFinishAudit(const FString& Params);

int32 USwordBladeFinishAuditCommandlet::Main(const FString& Params)
{
    if(FParse::Param(*Params,TEXT("Shared")))return RunSharedTwoHandFinishAudit(Params);
    const FString Original=FCommandLine::Get();
    const FString Profile=TEXT("SwordBladeFinishAudit_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FCommandLine::Set(*(TEXT("SwordBladeFinishAudit -ColdSteelProfile=")+Profile));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("BladeFinishAuditWorld"));
    auto* World=GI->GetWorld();auto* Host=GI->GetSubsystem<UColdSteelStatusModel>();auto* G=GI->GetSubsystem<UGunsmithSystem>();
    if(!World||!Host||!G||!Host->IsAudit()||Host->ProfileSlot()!=TEXT("ColdSteel_")+Profile)return 2;
    int32 Checks=0,Failures=0,Cases=0;TArray<TSharedPtr<FJsonValue>> Errors;
    const auto Check=[&](bool Pass,const FString& Label)
    {
        ++Checks;if(Pass)return;++Failures;Errors.Add(MakeShared<FJsonValueString>(Label));
        UE_LOG(LogTemp,Error,TEXT("BLADE_FINISH_FAIL %s"),*Label);
    };
    const TArray<FString> Blades={TEXT("false"),TEXT("extended_edge"),TEXT("heavy_spine"),TEXT("feather_edge")};
    const TArray<FString> Guards={TEXT("false"),TEXT("bastion_guard"),TEXT("riposte_guard"),TEXT("light_guard"),TEXT("twin_star_guard"),TEXT("starfall_nexus_guard")};
    const TArray<FString> Runes={TEXT("false"),TEXT("strength_rune"),TEXT("haste_rune"),TEXT("resonance_rune"),TEXT("erosion_rune"),TEXT("conduction_rune"),TEXT("golden_glow_rune"),TEXT("silver_glow_rune")};
    const TArray<FString> Finishes={TEXT("false"),TEXT("folded_steel"),TEXT("dark_iron"),TEXT("mithril"),TEXT("damascus_steel"),TEXT("meteoric_iron"),TEXT("false")};
    auto Item=Host->CreateItem(TEXT("ue_rune_sword"));
    const auto SetParts=[&](const FString& Blade,const FString& Guard,const FString& Rune,const FString& Finish)
    {
        TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data);
        auto Parts=MakeShared<FJsonObject>();Parts->SetStringField(TEXT("blade_1"),Blade);Parts->SetStringField(TEXT("guard"),Guard);
        Parts->SetStringField(TEXT("blade_2"),Rune);Parts->SetStringField(TEXT("blade_material"),Finish);
        Data->SetObjectField(TEXT("gunsmith_parts"),Parts);Item.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Item.Data));
    };
    for(const auto& Blade:Blades)for(const auto& Guard:Guards)for(const auto& Rune:Runes)
    {
        auto* Actor=World->SpawnActor<AActor>();auto* Root=NewObject<UStaticMeshComponent>(Actor);
        Actor->SetRootComponent(Root);Actor->AddInstanceComponent(Root);Root->RegisterComponent();
        TMap<FName,FString> PreviousKeys;
        for(int32 Step=0;Step<Finishes.Num();++Step)
        {
            const auto& Finish=Finishes[Step];const uint8 Mode=Step==6?0:uint8(Step);
            const FString Label=Blade+TEXT("/")+Guard+TEXT("/")+Rune+TEXT("/")+Finish;
            SetParts(Blade,Guard,Rune,Finish);++Cases;
            Check(G->Installed(Item).FindRef(TEXT("blade_material"))==(Mode?Finish:FString()),Label+TEXT(" catalog normalize"));
            Check(ColdSteelModularSword::BladeFinishMode(Item)==Mode,Label+TEXT(" catalog mode"));
            if(!ColdSteelModularSword::Apply(Root,Item)){Check(false,Label+TEXT(" assembly"));continue;}
            int32 Carriers=0;
            for(auto* Source:ColdSteelModularSword::Components(Root))
            {
                const bool IsRoot=Source->ComponentHasTag(TEXT("SwordSlot=guard"));
                const bool IsBlade=Source==Root;
                if(!IsRoot&&!IsBlade)continue;
                FFPSBodyAttachment Description;FPSBodyRuneVisual::Capture(Source,&Item,Description);
                Check(Description.BladeFinishMode==Mode&&Description.bBladeFinishGuardRoot==IsRoot,Label+TEXT(" capture"));
                TArray<uint8> Bytes;
                {FMemoryWriter Writer(Bytes);FObjectAndNameAsStringProxyArchive Ar(Writer,false);FFPSBodyAttachment::StaticStruct()->SerializeItem(Ar,&Description,nullptr);}
                FFPSBodyAttachment Read;
                {FMemoryReader Reader(Bytes);FObjectAndNameAsStringProxyArchive Ar(Reader,true);FFPSBodyAttachment::StaticStruct()->SerializeItem(Ar,&Read,nullptr);}
                const FString Key=FPSBodyRuneVisual::Key(Read);const FName Slot=IsRoot?TEXT("guard"):TEXT("blade_1");
                Check(Key==FPSBodyRuneVisual::Key(Description)&&Read.BladeFinishMode==Mode&&Read.bBladeFinishGuardRoot==IsRoot,Label+TEXT(" reflected snapshot roundtrip"));
                if(Step>0)Check(PreviousKeys.FindRef(Slot)!=Key,Label+TEXT(" finish-only cache invalidation"));
                PreviousKeys.Add(Slot,Key);
                auto* Remote=NewObject<UStaticMeshComponent>(Actor);Actor->AddInstanceComponent(Remote);Remote->SetStaticMesh(Source->GetStaticMesh());
                for(int32 Index=0;Index<Source->GetNumMaterials();++Index)
                {
                    UMaterialInterface* Material=Source->GetMaterial(Index);while(auto* MID=Cast<UMaterialInstanceDynamic>(Material))Material=MID->Parent;
                    Remote->SetMaterial(Index,Material);
                }
                FPSBodyRuneVisual::Apply(Remote,Read);int32 Surfaces=0;
                for(int32 Index=0;Index<Source->GetNumMaterials();++Index)
                {
                    float SourceMode=0,RemoteMode=0,RootMask=0;auto* SM=Source->GetMaterial(Index);auto* RM=Remote->GetMaterial(Index);
                    if(!SM||!SM->GetScalarParameterValue(FMaterialParameterInfo(TEXT("BladeFinishMode")),SourceMode))
                    {Check(SM==RM,Label+TEXT(" ornament/gem unchanged"));continue;}
                    ++Surfaces;
                    Check(FMath::IsNearlyEqual(SourceMode,float(Mode)),Label+TEXT(" local mode"));
                    Check(RM&&RM->GetScalarParameterValue(FMaterialParameterInfo(TEXT("BladeFinishMode")),RemoteMode)&&FMath::IsNearlyEqual(RemoteMode,float(Mode)),Label+TEXT(" observer mode"));
                    Check(RM&&RM->GetScalarParameterValue(FMaterialParameterInfo(TEXT("BladeFinishGuardRoot")),RootMask)&&RootMask==(IsRoot?1.f:0.f),Label+TEXT(" observer root coverage"));
                    if(Rune==TEXT("golden_glow_rune")||Rune==TEXT("silver_glow_rune"))
                    {
                        auto* MID=Cast<UMaterialInstanceDynamic>(RM);auto* Mask=MID?MID->K2_GetTextureParameterValue(TEXT("NativeRuneMask")):nullptr;
                        Check(Mask&&Mask->GetName()==(IsRoot?TEXT("T_RuneSword_GuardNativeMask"):TEXT("T_RuneSword_NativeMask")),Label+TEXT(" native rune mask retained"));
                    }
                }
                Check(Surfaces>0,Label+TEXT(" finish-capable surface"));++Carriers;
                Actor->RemoveInstanceComponent(Remote);Remote->DestroyComponent();
            }
            Check(Carriers==2,Label+TEXT(" blade and base covered"));
        }
        ColdSteelModularSword::Clear(Root);Actor->Destroy();
    }
    auto Report=MakeShared<FJsonObject>();Report->SetNumberField(TEXT("cases"),Cases);Report->SetNumberField(TEXT("checks"),Checks);
    Report->SetNumberField(TEXT("failures"),Failures);Report->SetArrayField(TEXT("errors"),Errors);
    Report->SetBoolField(TEXT("actual_network_transport"),false);Report->SetBoolField(TEXT("visual_rendering"),false);
    Report->SetStringField(TEXT("scope"),TEXT("all 4 blades x 6 guards x 8 rune states x 6 finishes plus factory reset; reflected equipment snapshot and production observer reconstruction"));
    FString Output=FPaths::ProjectSavedDir()/TEXT("SwordBladeFinishAudit.json");FParse::Value(*Params,TEXT("Output="),Output);
    FString Json;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));FFileHelper::SaveStringToFile(Json,*Output);
    UE_LOG(LogTemp,Display,TEXT("BLADE_FINISH_AUDIT cases=%d checks=%d failures=%d report=%s"),Cases,Checks,Failures,*Output);
    GI->Shutdown();GI->RemoveFromRoot();FCommandLine::Set(*Original);return Failures?1:0;
}
