#include "ColdSteelDoorInteraction.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "UObject/Class.h"
#include "UObject/UnrealType.h"

namespace
{
    // 包里的门入口：蓝图接口的函数名在前，其余是各门自己的自定义事件名。
    const FName DoorEntryNames[] =
    {
        // 本工程自己的门先匹配：ToggleDoor 才是开关语义；包的蓝图里没有这个名字。
        FName(TEXT("ToggleDoor")),
        FName(TEXT("OnInteraction")),
        FName(TEXT("AutoDoorActivated")),
        FName(TEXT("OpenDoor")),
        FName(TEXT("Interact")),
        FName(TEXT("Activate")),
    };
    const TCHAR* InteractInterfacePath = TEXT("/Game/DoorSystem/Player/Blueprints/BI_Interact.BI_Interact_C");
    UClass* LoadInteractInterface()
    {
        static UClass* Cached = LoadObject<UClass>(nullptr, InteractInterfacePath);
        return Cached;
    }
}

bool UColdSteelDoorInteraction::IsDoor(const AActor* Target)
{
    if (!Target) return false;
    if (const UClass* Interface = LoadInteractInterface())
    {
        const UClass* Class = Target->GetClass();
        if (Class->ImplementsInterface(Interface)) return true;
    }
    for (const FName& Name : DoorEntryNames)
        if (Target->FindFunction(Name)) return true;
    return false;
}

UFunction* UColdSteelDoorInteraction::FindEntry(AActor* Target) const
{
    if (!Target) return nullptr;
    for (const FName& Name : DoorEntryNames)
        if (UFunction* Function = Target->FindFunction(Name))
        {
            // 只接「无参」或「单个对象参数」的入口，避免误调需要额外参数的门逻辑。
            int32 Params = 0;
            bool bOnlyObjects = true;
            for (TFieldIterator<FProperty> It(Function); It && It->HasAnyPropertyFlags(CPF_Parm); ++It)
            {
                if (It->HasAnyPropertyFlags(CPF_ReturnParm)) continue;
                ++Params;
                if (!CastField<FObjectPropertyBase>(*It)) bOnlyObjects = false;
            }
            if (Params <= 1 && bOnlyObjects) return Function;
        }
    return nullptr;
}

UObject* UColdSteelDoorInteraction::ResolvePlayerArgument(UClass* Required, APawn* Player)
{
    if (!Required || !Player) return Player;
    if (Player->IsA(Required)) return Player;
    // 门的参数写的是包自己的角色：用一个隐藏代理顶替，只同步位置与朝向。
    if (PlayerProxy && PlayerProxyClass == Required && PlayerProxy->GetWorld() == GetWorld())
    {
        PlayerProxy->SetActorLocationAndRotation(Player->GetActorLocation(), Player->GetActorRotation());
        return PlayerProxy;
    }
    UWorld* World = GetWorld();
    if (!World || !Required->IsChildOf(AActor::StaticClass())) return Player;
    FActorSpawnParameters Spawn;
    Spawn.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    Spawn.ObjectFlags |= RF_Transient;
    AActor* Proxy = World->SpawnActor<AActor>(Required, Player->GetActorTransform(), Spawn);
    if (!Proxy) return Player;
    Proxy->SetActorHiddenInGame(true);
    Proxy->SetActorEnableCollision(false);
    Proxy->SetActorTickEnabled(false);
    PlayerProxy = Proxy;
    PlayerProxyClass = Required;
    UE_LOG(LogTemp, Display, TEXT("ColdSteelDoors: 生成隐藏玩家代理 %s（门要求的参数类型）"), *Required->GetName());
    return Proxy;
}

void UColdSteelDoorInteraction::LogDoorFunctions(const AActor* Target)
{
    if (!Target) return;
    UClass* Class = Target->GetClass();
    if (LoggedClasses.Contains(Class)) return;
    LoggedClasses.Add(Class);
    FString Names;
    for (TFieldIterator<UFunction> It(Class); It; ++It)
    {
        const UFunction* Function = *It;
        if (!Function->HasAnyFunctionFlags(FUNC_Public | FUNC_BlueprintCallable | FUNC_BlueprintEvent)) continue;
        Names += Function->GetName();
        Names += TEXT(", ");
    }
    UE_LOG(LogTemp, Display, TEXT("ColdSteelDoors: %s 的可调用入口: %s"), *Class->GetName(), *Names);
}

bool UColdSteelDoorInteraction::TryInteract(AActor* Target, APawn* Player, FString& OutMessage)
{
    OutMessage.Empty();
    if (!Target || !Player) return false;
    UFunction* Entry = FindEntry(Target);
    if (!Entry)
    {
        LogDoorFunctions(Target);
        return false;
    }
    TArray<uint8> Parameters;
    Parameters.SetNumZeroed(FMath::Max<int32>(Entry->ParmsSize, 1));
    int32 PlayerArgs = 0;
    for (TFieldIterator<FProperty> It(Entry); It && It->HasAnyPropertyFlags(CPF_Parm); ++It)
    {
        FProperty* Property = *It;
        if (Property->HasAnyPropertyFlags(CPF_ReturnParm)) continue;
        if (auto* ObjectProperty = CastField<FObjectPropertyBase>(Property))
        {
            UObject* Argument = ResolvePlayerArgument(ObjectProperty->PropertyClass, Player);
            ObjectProperty->SetObjectPropertyValue_InContainer(Parameters.GetData(), Argument);
            ++PlayerArgs;
            continue;
        }
        // 标量参数（例如方向/强度）保持默认值，交给门自己的默认行为。
    }
    if (PlayerProxy) PlayerProxy->SetActorLocationAndRotation(Player->GetActorLocation(), Player->GetActorRotation());
    // 只第一次记录签名：门的入口参数写死了它自己的角色时，这里能立刻看出来。
    if (!LoggedClasses.Contains(Target->GetClass()))
    {
        LogDoorFunctions(Target);
        FString Signature;
        for (TFieldIterator<FProperty> It(Entry); It && It->HasAnyPropertyFlags(CPF_Parm); ++It)
        {
            if (It->HasAnyPropertyFlags(CPF_ReturnParm)) continue;
            Signature += FString::Printf(TEXT("%s:%s "), *It->GetName(), *It->GetCPPType());
        }
        UE_LOG(LogTemp, Display, TEXT("ColdSteelDoors: 入口 %s(%s)"), *Entry->GetName(), *Signature);
    }
    Target->ProcessEvent(Entry, Parameters.GetData());
    OutMessage = FString::Printf(TEXT("%s · %s"), *Target->GetClass()->GetName(), *Entry->GetName());
    return true;
}
