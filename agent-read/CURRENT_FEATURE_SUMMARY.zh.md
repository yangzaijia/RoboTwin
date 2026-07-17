# 当前功能摘要

## 当前主线

- 仓库默认版本仍按最新 v1.x 迭代管理；Foundation、AnyGrasp、OursV2、Dense Replay、Piper IK V3 和 PiperCanonicalTCP-v1 是独立实验线。
- 当前 Real-Piper-TCP 对比入口是 `PiperCanonicalTCP-v1`；它不修改 OursV2。

## 本轮新增

- V4 把红色 local `+X` 错认成 0515 腕部相机上侧；0515 标定实际把相机装在 link6 的 local `-X` 一侧。Canonical 轴仍是蓝 `+Z` approach、绿 `+Y` 开合、红 `+X=+Y×+Z`，但 mount-up 判据必须是 `dot(-R[:,0], world +Z)>0`。因此红轴朝下通常正是相机侧朝上。
- V5 新增 `--candidate_camera_top_axis_sign=-1`，同时启用 Piper global-axis 和 Curobo→SAPIEN link6 的固定 local `Ry(-90°)` 适配；旧默认均保持 0/+1，不修改历史 planner、V1–V4 或 OursV2。
- V4 的 6–10 秒 wrist roll 来自逐点 Cartesian IK、单 seed、最大约 180° 旋转放宽和缺失 link6 适配的组合，不是物体坐标变化。V5 改为 stage endpoint IK + 40 点关节插值 + 64 seeds，并新增可选 `joint_continuity` 多解选择。
- `pick_diverse_bottles/id0` 的正式 V5 2×2 位于 `paper_qualitative_assets/.../id0/v5_camera_mount_up_candidate_videos/candidate_retarget_grid_2x2_camera_mount_up_v5.mp4`。Orientation/Fused 使用 K1 `L16/R9`、K2 `L19/R16`；Top-score-feasible 使用 K1 `L1/R3`、K2 `L3/R1`；OursV2 原视频不变。
- Raw Top-score K2-left `#0` 会把 J5 推到 `+1.2217 rad` 上限并产生 `57 mm` action miss；改用同一分数排序中下一项满足 mount-up/IK/关节限位的 `#3` 后，左/右 action 为 `3.0/7.7 mm`，全部 stage reached。
- 两条 V5 replay 的实际 `-X·up` 在所有记录帧均为正（候选阶段范围约 `+0.695～+0.995`），`execution_failed=false`。最终四宫格为 H.264/yuv420p、1280×796、30 fps、642 帧/21.4 s，标题栏独立于画面；物体碰撞关闭，因此定位为定性 retargeting 可视化而不是物理抓取成功率。
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
7. `COMMANDS/candidate_camera_mount_up_v5.zh.md`

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
