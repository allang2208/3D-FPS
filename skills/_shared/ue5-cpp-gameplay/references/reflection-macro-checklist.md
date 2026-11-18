# Reflection Macro Checklist

## Class/Struct
- `UCLASS()` / `USTRUCT(BlueprintType)` / `UENUM(BlueprintType)` as needed.
- `GENERATED_BODY()` present and correctly scoped.

## Properties
- Choose `EditDefaultsOnly` vs `EditAnywhere` deliberately. 原因：默认值编辑与实例编辑的作用范围不同，错误暴露会让关卡实例绕过统一配置。
- Add `BlueprintReadOnly` or `BlueprintReadWrite` intentionally. 原因：蓝图只读与可写决定谁能修改属性，默认开放写入可能绕过既有业务入口。
- Add metadata (`ClampMin`, `AllowPrivateAccess`, etc.) only when justified. 原因：元数据会改变编辑与访问行为，缺少实际用途的约束会制造额外接口复杂度。

## Functions
- Use `BlueprintCallable` for actions. 原因：有副作用的操作需要显式执行链，不能伪装成会被重复求值的纯查询。
- Use `BlueprintPure` for read-only queries. 原因：纯查询不应改变状态，蓝图求值次数不受执行链保证。
- Use explicit `Category` naming. 原因：明确分类能让蓝图和属性面板按功能定位接口，减少同名或无分类项混杂。

## Networking
- Mark RPC with `Server/Client/NetMulticast` and reliability intentionally. 原因：RPC 方向和可靠性决定拥有者与传输语义，不能按统一模板覆盖所有请求。
- Add validation/authority checks in implementation path. 原因：反射或 RPC 声明本身不会实现业务权限和输入约束，实现入口仍需遵守已有权威分工。
