# 粉尘1024任务恢复

主机：SSH `r5080`，192.168.3.142。服务：远端8189，本机SSH转发18189。

未确认任务 ID：`a33d5e6c-022f-48fa-b460-941261dc3295`，完整工作流为 `magic_dust_high_workflow.json`。低分辨率形状32步已完成（约271秒）；最后采样观察到GPU占用约13GB且100%利用率。随后SSH、8188 HTTP均超时，局域网返回目标主机不可达。本机18189转发也已断开。这里只能确认连接中断，不能判断是否OOM、重启、休眠或网络变化。

主机恢复后先读取8189 `/queue` 及 `/history/a33d5e6c-022f-48fa-b460-941261dc3295`。如已完成，运行 `fetch_models.py` 下载、校验并执行 `render_models.py -- magic_dust_high`；不要重复提交。若仍在执行，继续观察；只有查明终止原因才决定重跑或降档。不得中断不属于本任务的工作，也不得因节点选项存在就标注硬件已支持。

重新建立本机转发：`ssh -o BatchMode=yes -o ExitOnForwardFailure=yes -N -L 18189:127.0.0.1:8189 r5080`。其余三次成功结果、母版和轻量交付已经完整保存在本机。

## 2026-09-11 恢复后的实际检查

SSH 恢复。旧 8189 服务已经不存在，输出目录没有粉尘 high GLB；当前 8188 队列为空。因此在 07:07 前后将已保存的同一工作流重新提交到 8188，回执 `magic_dust_high_recovery_submitted.json`，任务 `52a207e1-48f8-4344-8019-e7ca317908ad`。保留旧任务回执，不重启或清空服务。

当前恢复任务由 `recover_monitor.py` 记录显存、保存终态历史、下载模型并核对远端 SHA-256。`pipeline.py` 支持 `COMFY_BASE_URL` 环境变量覆盖历史端口。恢复任务结果以 recovery_history 和 recovery_remote_outputs 文件为准。

用户已接受当前精度并要求暂停。已向恢复任务发送带 prompt_id 的定向 interrupt，HTTP 200；检查时当前节点仍为 in_progress，未把请求接受记作任务已退出。共享队列其他任务保持不动，本地监测脚本已停止。此次粉尘高档对比不再继续，不记作成功或显存失败；最终采用已验收的分件模型。记录 `recovery_pause.json`。
