#pragma once
#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "RainAssetEditor.generated.h"
class UNiagaraSystem;
UCLASS()
class FPSGAME_API URainAssetEditor : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintCallable,Category="Weather|Editor")
    static bool SetInput(UNiagaraSystem* System,const FString& Emitter,const FString& Script,const FString& Module,const FString& Input,const FString& Type,const FString& Value);
    UFUNCTION(BlueprintCallable,Category="Weather|Editor")
    static bool CompileRain(UNiagaraSystem* System);
    UFUNCTION(BlueprintCallable,Category="Weather|Editor")
    static FString ReadInput(UNiagaraSystem* System,const FString& Emitter,const FString& Script,const FString& Module,const FString& Input);
};
