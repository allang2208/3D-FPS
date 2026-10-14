#pragma once
#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "DragonBreathAuthorLibrary.generated.h"
class UNiagaraSystem;
class UMaterialInterface;
UCLASS()
class DRAGONBREATHAUTHOR_API UDragonBreathAuthorLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    /** Expose full authoring stacks hidden by the fluid template summary UI. */
    UFUNCTION(BlueprintCallable) static void PrepareFluidStack(UNiagaraSystem* System);
    UFUNCTION(BlueprintCallable) static FString DescribeFluidInputs(UNiagaraSystem* System);
    UFUNCTION(BlueprintCallable) static bool ConfigureFluidInputs(UNiagaraSystem* System,const FString& ChangesJson);
    UFUNCTION(BlueprintCallable) static bool SetFluidUserDefaults(UNiagaraSystem* System,const FString& DefaultsJson);
    UFUNCTION(BlueprintCallable) static bool CompileMaterialAssets(const TArray<UMaterialInterface*>& Materials);
    UFUNCTION(BlueprintCallable,Category="Weather|Editor")
    static bool SetInput(UNiagaraSystem* System,const FString& Emitter,const FString& Script,const FString& Module,const FString& Input,const FString& Type,const FString& Value);
    UFUNCTION(BlueprintCallable,Category="Weather|Editor")
    static bool CompileRain(UNiagaraSystem* System,bool bForce=false);
    /** Compile a spline effect with an explicit per-component UObject source. */
    UFUNCTION(BlueprintCallable,Category="VFX|Editor")
    static bool BindSplineUserObject(UNiagaraSystem* System,FName ParameterName);
    UFUNCTION(BlueprintCallable,Category="Weather|Editor")
    static FString ReadInput(UNiagaraSystem* System,const FString& Emitter,const FString& Script,const FString& Module,const FString& Input);
};
