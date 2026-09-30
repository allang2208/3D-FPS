#include "RainAssetEditor.h"
#include "NiagaraSystem.h"
#if WITH_EDITOR
#include "NiagaraExternalSystemEditorUtilities.h"
#include "NiagaraDataInterfaceSpline.h"
#include "UObject/UObjectHash.h"
#endif
bool URainAssetEditor::BindSplineUserObject(UNiagaraSystem* System,FName ParameterName)
{
#if WITH_EDITOR
    if(!System||ParameterName.IsNone())return false;
    System->Modify();
    System->GetExposedParameters().AddParameter(FNiagaraVariable(FNiagaraTypeDefinition::GetUObjectDef(),ParameterName));
    // Build the instance parameter layout before setting the compiled spline
    // defaults. Compilation can replace these interfaces, so binding is last.
    System->RequestCompile(true);
    System->WaitForCompilationComplete(true,false);
    if(!System->IsValid())return false;
    TArray<UObject*> Objects;GetObjectsWithOuter(System,Objects,true);
    int32 Count=0;
    for(UObject* Object:Objects)
        if(auto* Spline=Cast<UNiagaraDataInterfaceSpline>(Object))
        {
            Spline->Modify();
            Spline->SourceMode=ENDISpline_SourceMode::ParameterBindingOnly;
            Spline->SplineUserParameter.Parameter=FNiagaraVariable(FNiagaraTypeDefinition::GetUObjectDef(),ParameterName);
            ++Count;
        }
    System->OnCompiledDataInterfaceChanged();System->MarkPackageDirty();
    UE_LOG(LogTemp,Display,TEXT("Spline asset binding %s parameter=%s interfaces=%d"),*System->GetPathName(),*ParameterName.ToString(),Count);
    return Count>0;
#else
    return false;
#endif
}
bool URainAssetEditor::SetInput(UNiagaraSystem* System,const FString& Emitter,const FString& Script,const FString& Module,const FString& Input,const FString& Type,const FString& Value)
{
#if WITH_EDITOR
    if(!System)return false;
    UScriptStruct* Struct=LoadObject<UScriptStruct>(nullptr,*Type);
    if(!Struct)return false;
    FNiagaraExt_StackInputValue Data;
    Data.InitializeAs(Struct);
    if(!Struct->ImportText(*Value,Data.GetMutableMemory(),nullptr,PPF_None,GWarn,Struct->GetName()))return false;
    FNiagaraExt_StackItemReference Ref;
    Ref.System=System;Ref.EmitterName=*Emitter;Ref.ScriptName=*Script;Ref.ModuleName=*Module;Ref.InputNameStack.Add(*Input);
    FNiagaraExternalEditContext Context(Ref);
    UNiagaraExternalEditUtilities::SetStackInputData(Ref,Data,Context);
    FNiagaraExt_StackInputValue Actual;
    UNiagaraExternalEditUtilities::GetStackInputData(Ref,Actual,Context);
    for(const auto& Error:Context.Errors)UE_LOG(LogTemp,Error,TEXT("RainAsset: %s"),*Error.ToString());
    return Context.Errors.IsEmpty()&&Actual.GetScriptStruct()==Struct&&Struct->CompareScriptStruct(Data.GetMemory(),Actual.GetMemory(),PPF_None);
#else
    return false;
#endif
}
FString URainAssetEditor::ReadInput(UNiagaraSystem* System,const FString& Emitter,const FString& Script,const FString& Module,const FString& Input)
{
#if WITH_EDITOR
    FNiagaraExt_StackItemReference Ref;
    Ref.System=System;Ref.EmitterName=*Emitter;Ref.ScriptName=*Script;Ref.ModuleName=*Module;Ref.InputNameStack.Add(*Input);
    FNiagaraExternalEditContext Context(Ref);
    FNiagaraExt_StackInputValue Actual;
    UNiagaraExternalEditUtilities::GetStackInputData(Ref,Actual,Context);
    FString Result;
    if(Actual.IsValid())Actual.GetScriptStruct()->ExportText(Result,Actual.GetMemory(),nullptr,nullptr,PPF_None,nullptr);
    return Result;
#else
    return FString();
#endif
}
bool URainAssetEditor::CompileRain(UNiagaraSystem* System)
{
#if WITH_EDITOR
    if(!System)return false;
    System->RequestCompile(false);
    System->WaitForCompilationComplete(true,false);
    UE_LOG(LogTemp,Display,TEXT("RainAsset compile %s valid=%d"),*System->GetPathName(),System->IsValid());
    return System->IsValid();
#else
    return false;
#endif
}
