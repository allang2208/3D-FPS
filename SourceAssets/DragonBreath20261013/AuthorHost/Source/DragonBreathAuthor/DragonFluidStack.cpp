#include "DragonBreathAuthorLibrary.h"
#include "NiagaraSystem.h"
#include "NiagaraNodeFunctionCall.h"
#include "ViewModels/NiagaraSystemViewModel.h"
#include "ViewModels/NiagaraEmitterHandleViewModel.h"
#include "ViewModels/Stack/NiagaraStackViewModel.h"
#include "ViewModels/Stack/NiagaraStackEntry.h"
#include "ViewModels/Stack/NiagaraStackModuleItem.h"
#include "ViewModels/Stack/NiagaraStackFunctionInput.h"
#include "UObject/StructOnScope.h"
#include "Serialization/JsonSerializer.h"

namespace
{
struct FDragonFluidEdit
{
    TSharedRef<FNiagaraSystemViewModel> VM=MakeShared<FNiagaraSystemViewModel>();
    explicit FDragonFluidEdit(UNiagaraSystem& System)
    {
        UDragonBreathAuthorLibrary::PrepareFluidStack(&System);
        FNiagaraSystemViewModelOptions Options;
        Options.bCanModifyEmittersFromTimeline=false;
        Options.bCompileForEdit=false;
        Options.bCanSimulate=false;
        Options.bCanAutoCompile=false;
        Options.bIsForDataProcessingOnly=true;
        Options.MessageLogGuid=System.GetAssetGuid();
        VM->Initialize(System,Options);
    }
    // The exported view-model destructor performs Cleanup on final release.
};
}

bool UDragonBreathAuthorLibrary::SetFluidUserDefaults(UNiagaraSystem* System,const FString& DefaultsJson)
{
    if(!System)return false;
    TArray<TSharedPtr<FJsonValue>> Defaults;
    if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(DefaultsJson),Defaults))return false;
    System->Modify();
    for(const auto& Item:Defaults)
    {
        auto D=Item->AsObject();if(!D.IsValid())return false;
        auto* Struct=LoadObject<UScriptStruct>(nullptr,*D->GetStringField(TEXT("type")));if(!Struct)return false;
        const FNiagaraVariable Var(FNiagaraTypeDefinition(Struct),*D->GetStringField(TEXT("name")));
        FStructOnScope Value(Struct);
        if(!Struct->ImportText(*D->GetStringField(TEXT("value")),Value.GetStructMemory(),nullptr,PPF_None,GWarn,Struct->GetName()))return false;
        System->GetExposedParameters().SetParameterData(Value.GetStructMemory(),Var,true);
    }
    System->MarkPackageDirty();return true;
}

FString UDragonBreathAuthorLibrary::DescribeFluidInputs(UNiagaraSystem* System)
{
    if(!System)return TEXT("[]");
    FDragonFluidEdit Edit(*System);
    TArray<TSharedPtr<FJsonValue>> Records;
    for(const auto& Handle:Edit.VM->GetEmitterHandleViewModels())
    {
        TArray<UNiagaraStackModuleItem*> Modules;
        Handle->GetEmitterStackViewModel()->GetRootEntry()->GetUnfilteredChildrenOfType(Modules,true);
        for(auto* Module:Modules)
        {
            auto Record=MakeShared<FJsonObject>();
            Record->SetStringField(TEXT("emitter"),Handle->GetName().ToString());
            Record->SetStringField(TEXT("module"),Module->GetModuleNode().GetFunctionName());
            TArray<UNiagaraStackFunctionInput*> Inputs;
            Module->GetUnfilteredChildrenOfType(Inputs,true);
            TArray<TSharedPtr<FJsonValue>> Values;
            for(auto* Input:Inputs)
            {
                if(Input->GetInputParameterHandlePath().Num()!=1)continue;
                auto Item=MakeShared<FJsonObject>();
                Item->SetStringField(TEXT("input"),Input->GetInputParameterHandle().GetName().ToString());
                Item->SetStringField(TEXT("type"),Input->GetInputType().GetName());
                if(auto Local=Input->GetLocalValueStruct();Local.IsValid())
                {
                    FString Text;
                    auto* Struct=CastChecked<UScriptStruct>(Local->GetStruct());
                    Struct->ExportText(Text,Local->GetStructMemory(),nullptr,nullptr,PPF_None,nullptr);
                    Item->SetStringField(TEXT("value"),Text);
                }
                if(auto* Enum=Input->GetInputType().GetEnum())
                {
                    TArray<TSharedPtr<FJsonValue>> Names;
                    for(int32 I=0;I<Enum->NumEnums();++I)
                        Names.Add(MakeShared<FJsonValueString>(FString::Printf(TEXT("%lld:%s"),Enum->GetValueByIndex(I),*Enum->GetDisplayNameTextByIndex(I).ToString())));
                    Item->SetArrayField(TEXT("enum"),Names);
                }
                Values.Add(MakeShared<FJsonValueObject>(Item));
            }
            Record->SetArrayField(TEXT("inputs"),Values);
            Records.Add(MakeShared<FJsonValueObject>(Record));
        }
    }
    FString Result;FJsonSerializer::Serialize(Records,TJsonWriterFactory<>::Create(&Result));return Result;
}

bool UDragonBreathAuthorLibrary::ConfigureFluidInputs(UNiagaraSystem* System,const FString& ChangesJson)
{
    if(!System)return false;
    TArray<TSharedPtr<FJsonValue>> Changes;
    if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(ChangesJson),Changes))return false;
    System->Modify();FDragonFluidEdit Edit(*System);
    for(const auto& Change:Changes)
    {
        auto C=Change->AsObject();if(!C.IsValid())return false;
        const FString Emitter=C->GetStringField(TEXT("emitter"));
        const FString ModuleName=C->GetStringField(TEXT("module"));
        const FString InputName=C->GetStringField(TEXT("input"));
        UNiagaraStackFunctionInput* Target=nullptr;
        for(const auto& Handle:Edit.VM->GetEmitterHandleViewModels())
        {
            if(Handle->GetName().ToString()!=Emitter)continue;
            TArray<UNiagaraStackModuleItem*> Modules;
            Handle->GetEmitterStackViewModel()->GetRootEntry()->GetUnfilteredChildrenOfType(Modules,true);
            for(auto* Module:Modules)
            {
                if(Module->GetModuleNode().GetFunctionName()!=ModuleName)continue;
                TArray<UNiagaraStackFunctionInput*> Inputs;Module->GetUnfilteredChildrenOfType(Inputs,true);
                for(auto* Input:Inputs)
                    if(Input->GetInputParameterHandlePath().Num()==1&&Input->GetInputParameterHandle().GetName().ToString()==InputName)
                        Target=Input;
            }
        }
        if(!Target){UE_LOG(LogTemp,Error,TEXT("Dragon fluid input missing %s/%s/%s"),*Emitter,*ModuleName,*InputName);return false;}
        FString Expr;
        if(C->TryGetStringField(TEXT("expression"),Expr))Target->SetCustomExpression(Expr);
        else
        {
            auto* Struct=Target->GetInputType().GetScriptStruct();if(!Struct)return false;
            auto Value=MakeShared<FStructOnScope>(Struct);
            if(!Struct->ImportText(*C->GetStringField(TEXT("value")),Value->GetStructMemory(),nullptr,PPF_None,GWarn,Struct->GetName()))return false;
            Target->SetLocalValue(Value);
        }
        UE_LOG(LogTemp,Display,TEXT("Dragon fluid configured %s/%s/%s"),*Emitter,*ModuleName,*InputName);
    }
    System->MarkPackageDirty();return true;
}
