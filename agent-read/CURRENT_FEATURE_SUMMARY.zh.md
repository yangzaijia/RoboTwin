# 当前功能摘要

## 当前主线

- 仓库默认版本仍按最新 v1.x 迭代管理；Foundation、AnyGrasp、OursV2、Dense Replay、Piper IK V3 和 PiperCanonicalTCP-v1 是独立实验线。
- 当前 Real-Piper-TCP 对比入口是 `PiperCanonicalTCP-v1`；它不修改 OursV2。

## 本轮新增

- 新增默认关闭的 `--action_target_mode rigid_object_transport`。V8 的 K1 候选、`robot_replay → Piper physical` 换基、camera-up、`-5 cm @ local +X` 与 IK 参数保持不变；K1 到位后以当前 EE 和当前 object actor 建立 `T_EE_object`，再用 `T_W_EE2 = T_W_object2 @ inverse(T_EE_object)` 构造 K2。
- 审计确认旧 V8 K2 是新的独立抓取候选，但物体已按 K1 关系刚性附着，因此会改变夹爪—物体关系。第一版 V9 错把 planner target 点当 TCP，留下约 9–12 cm 固定误差；正式 `v9_ee_rigid_object_transport_20260723` 使用 EE/link6 目标点，Orientation/Fused 的最终物体误差为左 `7.8 mm / 6.0°`、右 `4.7 mm / 1.9°`。
- 六联转换图和新 2×2 视频发布在 `paper_qualitative_assets/outputs/matched_candidate_image_video_release_20260722/`。Top-score 仍保留 K1 右手 `33.24°` miss 并在 close/action 前停止；没有加入 IK-feasible fallback。复现见 `COMMANDS/rigid_object_transport_v9.zh.md`。
- V8 修正 V7 对两个独立变换的误判：候选侧 `robot_replay → anygrasp_raw/Piper physical TCP` 是任务目标换基；IK 侧 Curobo-link6 → SAPIEN-link6 adapter 是求解 URDF 与渲染 URDF 的模型帧换基。正确链路必须同时执行两者，各执行一次。
- `robot_replay` 输入以 canonical `+Z` 为 approach，经 `swap_red_blue_keep_green` 转为 Piper 物理 `+X` approach 后再进入原有 Piper URDFIK；IK 侧继续保留 global adapter 与 Curobo→SAPIEN link6 adapter。这里不存在独立的“canonical IK”求解器。
- 正确物理轴对应为 `raw +X = canonical +Z`、`raw +Y = canonical +Y`、`raw +Z = -canonical +X`。`pick_diverse_bottles/id0` 的三组映射误差均为 `0°`；camera-back-up 使用 `-canonical X = raw +Z` 朝 world up。
- V7 六联图的 raw/canonical 朝向对应仍然正确；V7 四视角执行视频的 planner target 坐标链错误，仅保留作历史反例。当前 V8 固定原始策略候选，不做 IK-feasible fallback，并以严格 30° reach 门限保留真实失败。
- V8 `pick_diverse_bottles/id0` 已按原始候选实跑：Orientation/Fused 均为 K1 `L16/R5`、K2 `L14/R16`，左 pregrasp 旋转 `35.44°` miss，但 grasp/action 完成；当前 6×2 扁平发布视频中的 Top-score 为 K1 `L8/R3`、K2 `L3/R2`，K1 右 grasp 仍有 `33.22°` 旋转误差并在 close 前安全停止，因此 K2 未执行。原速 2×2 视频与 manifest 位于 `paper_qualitative_assets/.../id0/v8_physical_axes_raw_strategy_videos/`。
- 新增只读 `overlay_v8_execution_pose_audit.py`：直接读取 V8 `plan_summary.json` 与 `debug_execution_metrics.jsonl`，在执行视频上同时画彩色目标 C-gripper、白色实测 EE、物理 Piper `+X/+Y/+Z` 红绿蓝轴，并将 grasp/action 到位帧保持 1 秒。扁平输出 `*_00b_retarget_2x2_v8_pose_audit.mp4`、`*_03_v8_video_matched_arrivals_2x3.png` 与 `*_pose_audit_manifest.json`；历史 `legacy_v3` 图片不是该 V8 视频的逐候选匹配图。
- 新增只读 `export_v8_video_matched_candidate_contact_sheets.py`，把 V8 plan summary 中精确的最终 candidate target 投影到对应 D435/Foundation 帧，生成与旧 `all_strategies_contact_sheet.png` 同布局的 2×3 六格图。`pick_diverse_bottles/id0` 的 frame38/frame78 图已发布到 `matched_candidate_image_video_release_20260722/`；它们与 arrival sheet 分别表示“计划 target”和“实际到位 EE”。
- V6 候选几何审计推翻了“V6 已统一 AnyGrasp 轴语义”的结论。输入候选仍为 `candidate_frame_mode=robot_replay`：canonical 蓝 `+Z = raw AnyGrasp +X approach`；V6 却把同一旋转按红 `+X = forward` 使用。选中候选的 V6 stored rotation 与 `anygrasp_raw` 固定相差 `90°`。
- V6 的 `-0.05 m` candidate offset 沿 stored red `+X`，而不是沿 raw AnyGrasp approach。`pick_diverse_bottles/id0/frame78/right #5` 从 raw center 到 object anchor 的 `4.68 cm` 增为 current target 的 `9.62 cm`。因此 V6 视频只能证明该错误目标可被 IK/关节执行，不能证明候选坐标链正确。
- 新增只读导出器 `code_painting/export_v6_candidate_geometry_audit.py`。它为 frame 38/78 各生成 2×3 图：raw dense candidates、选中 raw poses、V6 stored remap、当前 `-5 cm` target、object-anchor 距离和 raw-vs-target overlay；不调用 IK、不覆盖旧素材。
- 审计输出位于 `paper_qualitative_assets/.../id0/v6_red_forward_camera_back_up_candidate_videos/candidate_audit_v6/`。两张 contact sheet 均为 1920×1152；frame 38 使用 `L16/R18`，frame 78 使用 `L6/R5`。
- `candidate_keep_camera_up` 的“每个关键帧先硬过滤 camera-up，再优化连续性”修复本身仍有效，但它应用在哪个局部轴上必须等候后续统一 `anygrasp_raw` 与 `robot_replay` 语义。OursV2 未修改。
- planner target、current readback、reach check 和可视化统一为 `T_W_RTCP`。
- SAPIEN `L6_SIM` 与 CuRobo/server `L6_URDF` 原点一致、局部轴固定差精确 `Ry(+pi/2)`；适配后同-q FK 误差小于 `7.5e-8 m / 0.000016 deg`。
- 服务器工具保持字面量 `T_L6URDF_RTCP = Ry(-1.57) @ Tx(0.19)`。preview 的 `CGRASP -> RTCP` remap 是另一层独立变换。
- corrected same-q OursV2 TCP 与 Real TCP 左右 mean/max distance 都约 `70.0001 mm`，对应统一前进轴上的 12 cm 与 19 cm 差；旧 224.6 mm 结论无效。
- EE-pose 支持 Orientation、Fused、Top-score。`pnp_bread/id8/left` 三策略与 corrected joint 对比全部通过媒体/ffprobe/视觉 QA。
- 新增真正的三链路控制对比：Joint 使用同一组 Piper real q，分别画 Piper real endPose、OursV2 0.12 m TCP 与 Canonical 0.19 m RTCP；EE-pose 使用同一 Piper real `T_B_RTCP` 目标，分别执行 OursV2 旧数值直通 link6 IK 和 Canonical 服务器逆工具 IK，最后统一按物理 RTCP 评价。
- `handover_bottle/episode0` 8 帧 smoke 中，Canonical same-q 位置误差为左/右 `9.77/9.59 mm`；Canonical EE-pose IK 为 `0.011/0.004 mm`，OursV2 旧语义约 `195 mm`。两支 1920×1080 MP4 均通过 H.264/yuv420p/完整解码检查和视觉 QA。
- Real-control raw manifest 已补齐并审计为 6 tasks × 5 episodes；30 集的 D435、双 wrist、双 jointState、双 endPose 均非空。它与 AnyGrasp 6×5 foundation IDs 是不同样本集合。
- 6 tasks × 5 episodes manifest、独立 batch orchestrator 和 tmux 命令已准备。策略 IK miss 保留视频与 failures TSV，不伪造 SUCCESS。
- canonical MP4 现在有统一的 H.264/`yuv420p`/faststart 后处理与严格原子转码审计；2026-07-15 batch 的 186 个 `mpeg4` 已转换，终态 258/258 完整解码通过。joint summary 也显式记录 OursV2 human-replay 输入和仿真 head-camera 来源语义。
- Selection Strategy Audit V4 与 Dense Replay URDF-match v2 仍为独立历史线。

## 读取顺序

1. `README.zh.md`
2. `CURRENT_FEATURE_SUMMARY.zh.md`
3. `VERSION_SUMMARY.zh.md`
4. `PIPER_CANONICAL_TCP_V1.zh.md`
5. `COMMANDS/piper_canonical_tcp_v1.zh.md`
6. `SELECTION_STRATEGY_AUDIT_V4.zh.md`
7. `COMMANDS/candidate_frame_contract_v8.zh.md`
8. `COMMANDS/piper_v6_candidate_geometry_audit.zh.md`
9. `COMMANDS/candidate_camera_mount_up_v6.zh.md`（历史 V6 复现，当前有已知轴混用）

## 2026-07-16 补充

- Canonical Human Replay 将人手/CGRASP 局部轴显式映射到 RTCP，最终 `target_retreat=0`，只保留 local RTCP +X 的 0.12 m pregrasp。
- `canonical_four_method_d435.mp4` 比较四个 Canonical 方法；`canonical_vs_legacy_five_method_d435.mp4` 再加入显式 0.12 m Legacy retreat 基线。源语义和视频属性均写入 manifest。
- `run_ik_logic_grid.sh` 已升级为 2×4 语义源 V2：上行完整复现 Legacy 原 candidate offset/Human retreat/EE reach，下行把同一 candidate 或 Human center 转为 Canonical RTCP。它不是单一 link6 变量消融；两行保持各自原生求解设置。
- 旧五路不是完整 Legacy/Canonical 2×4，且旧正式 Human Replay 记录 retreat=0.14 m，五路中的 0.12 m 只是显式 ablation。
- 旧 `outputs_ik_logic_grid_20260716` V1 因移除 Legacy `-0.05 m @ local +Z`/Human 0.14 m 适配，并误以为 Human remap 标签会作用于 reuse-plan-summary，结论撤销。新结果写入 `outputs_ik_semantic_grid_v2_20260716`。
- `handover_bottle/id1` 的 V2 审计中，所有语义源 world xyz 差为 0，轴关系误差不超过 `4.2e-16`；Legacy Orientation/Top 与历史原结果 target 差为 0。Canonical Human 内部完成完整 handover，但通用 summary 仍因早期 action miss 返回失败。最终 1920×648、265 帧视频通过完整解码与视觉 QA。
- 快速阅读：`OUTPUTS_REAL_CONTROL_COMPARE_GUIDE.zh.md`、`PIPER_CANONICAL_REPLAY_METHOD_COMPARE.zh.md`。

## 2026-07-16 论文定性素材补充

- Dense URDF-match v2 的 4x5 网格已把标题移到每格独立的 38 px 顶栏；视频内容仍为 480x270，最终输出为 1920x1540，旧标题叠加版另行保留。
- 论文素材已扩展为 6 tasks × 2 episodes：38 个交互关键帧导出 152 张四策略单图和 38 张 contact sheet；每个 `<TASK>/id<ID>/` 同目录还包含 episode 专属 4×5 视频、config、manifest 和 README。LEFT/RIGHT/BOTH 按关键帧 metadata 动态绘制，OursV2 是 `HUMAN TARGET`，不是 AnyGrasp candidate；旧左右分栏版独立保留。
- 12 个 4×5 视频均为 H.264/yuv420p、1920×1540、30 fps 并通过完整解码。`place_bread_basket/id0,id1` 的 D435 AnyGrasp/human-filtered、`pnp_tray/id2,id3` 的 Dense-v2/legacy repaint 确实缺失，保留 `MISSING` 格而不混用或伪造。
- 复现与验证命令见 `COMMANDS/paper_qualitative_assets.zh.md`。
