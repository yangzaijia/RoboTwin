# 长期决策

## 2026-07-14：Dense Replay 修复采用隔离版本

- 保留旧 renderer、runner 和论文素材，方便复现实验历史。
- 新实现命名为 `Dense Replay URDF-match v2`，写入独立 `h2_pure_d435_urdfmatch_v2` 输出根目录。
- 关节顺序保持 `joint1..joint6`；固定误差通过显式坐标 adapter 修复，不通过交换或手工偏置关节修复。
- HaMeR 指尖中点统一解释为 TCP；link6 仅是 IK 的内部目标帧。
- Dense 仍是 dense retargeting baseline。机器人不可达的人手姿态不由该修复伪装为 Ours v2 能力。
- 六任务批量结果继续写入同一独立 V2 根目录，并以 episode 完整性检查支持安全续跑；不创建或覆盖 V1 文件。
- V2 raw replay 不能与现有 V1 Stage-2 repaint/HDF5 静默混用。论文扩展图允许并排诊断，但必须显式标记 `NOT V2`；训练数据升级必须整条重建并使用新标识。

## 2026-07-14：Selection Strategy V4 仅作为只读审计

- 保留 OursV2、Orientation、Fused、Top-score 的旧算法、summary 和可视化，不用 V4 回写或“修正”历史结果。
- Top-score 的真实选择以 `plan_summary.json -> selected_candidates_by_executed_arm` 为准；旧 rank preview 仅作为历史错误证据。
- raw/legacy Top-score 和 canonical 重建同时保留，canonical 结果明确标为 audit-only，不冒充历史执行结果。
- resolved frame 不同则使用各自 Foundation 背景分栏，不跨帧静默投影。
- 同 pose 的 Orientation/Fused 不做人为位置偏移；使用粗实线/细虚线和不同 marker 同址显示，避免改变数据语义。
- 任务输出采用 `<TASK>/id<ID>_keyframe_<FRAME>_*`，不再创建 episode 中间目录；旧嵌套版保存在独立可回滚备份。
- 批量 PNG/JSON/报告保持 Git ignore；只版本化两个脚本和双语说明。

## 2026-07-15：PiperCanonicalTCP-v1

- 保持 OursV2 完全独立；新 Real-TCP 语义只进入 `piper_canonical_tcp_v1/`。
- frame 名必须区分 `L6_SIM`、`L6_URDF`、`RTCP` 与 `CGRASP`，并区分 world/local 轴标签。
- `T_L6SIM_L6URDF` 使用运行时同-q 验证的精确 signed-axis matrix；服务器工具保持字面量 `-1.57` 和 `0.19`，不替换为理想角。
- Orientation/Fused 从 canonical preview 转回 raw/RTCP；Top-score raw source 使用 identity。两条数值相同的 90° 矩阵保持独立语义。
- batch 遇到策略 IK miss 后继续并记录失败；视频可合成，但失败策略不创建 SUCCESS。
- 代码与测试进入 Git；smoke、batch 视频、日志和大文件继续 ignore。
- canonical 生成视频统一使用 VSCode/Chromium 可解码契约：H.264、`yuv420p`、faststart。OpenCV 可读不等于浏览器兼容；替换前必须对临时文件做格式、几何/帧数和完整解码验证。
- 视频来源语义必须区分“D435 原始/预览输入”“D435 标定驱动的仿真 head camera”与“仿真 third/wrist/合成画面”，不能仅因路径含 `d435` 就把所有 MP4 称为 D435 视频。

## 2026-07-16：三链路 real control compare 保持隔离

- 不修改 OursV2；OursV2 branch 必须忠实保留旧 numeric pose -> link6 IK 语义。
- Joint 与 EE-pose 必须分别使用共同 real q 与共同 real `T_B_RTCP`，不能把 foundation candidate strategy 当作控制器对比。
- 不以 OursV2 自己的 TCP 定义评价 IK 后 q；两套 q 统一转换为物理 Canonical RTCP 后再和 real endPose 比较。
- 失败臂保留失败标记并排除曲线，不以 reference q fallback 伪造成功数值。
- 新结果使用独立 `outputs_real_control_compare_20260716`；现有 Canonical candidate batch 和 V1–V5 视频不覆盖。
- 用户所说“四种方式”定义为四个 Canonical 方法（Orientation/Fused/Top-score/Human Replay）；Legacy OursV2 retreat 只作为第五个基线。
- Canonical Human Replay 最终 `target_retreat_m` 固定为 0，保留 0.12 m pregrasp；Legacy retreat 在 runner 中必填，避免当前默认 0 与历史 12 cm 混淆。

## 2026-07-16：论文网格标题与关键帧候选图

- 不缩小或遮盖原有 480x270 视频内容；在每格上方增加独立 38 px 标题栏，使 4x5 网格变为 1920x1540。旧标题叠加版保留为独立备份。
- 论文候选图只画 V4 metadata 中的 Selection Pose，排除 planner offset、retreat、pregrasp 和 TCP compensation，避免把选择策略与后续规划混在一起。
- 同一关键帧/策略只使用一张 requested-keyframe replay 背景，左右 gripper 同图叠加；双手关键帧在总标题标为 `BOTH`，标题第二行分别列 LEFT/RIGHT 候选。局部轴固定使用 X 红、Y 绿、Z 蓝。
- OursV2 的点来自 synthetic human-retarget target，必须标为 `HUMAN TARGET`；Orientation/Fused/Top-score 才标 AnyGrasp candidate。

## 2026-07-16：论文素材采用 6×2 episode 聚合目录

- 固定选择 handover 1/3、pick 0/1、place 0/1、pnp_bread 7/8、pnp_tray 2/3、stack 0/1；每个 episode 的关键帧图和 4×5 视频放在同一 `<TASK>/id<ID>/`。
- 图片 scope 由 V4 metadata 决定：LEFT/RIGHT 只画对应手，BOTH 在同一 replay 背景画双手；缺少策略记录时显示 `MISSING`，不补默认 pose。
- D435 AnyGrasp 视频只能从同 episode 的 D435 PNG 派生。`place_bread_basket` 缺 D435 结果时不替换旧广角结果；`pnp_tray` 缺 Dense-v2 时不以 V1 或其他 episode 冒充。
- 大型源视频只在 config/manifest 中记录绝对路径；episode 包只保存生成的图、派生 AnyGrasp、合成视频和元数据，不复制源视频。

## 2026-07-17：Canonical candidate 的朝上分支绕 local-Z 选择

- `robot_replay` canonical candidate 固定以 local `+Z` 为 approach、local `+Y` 为开合、local `+X=+Y x +Z` 为相机/腕部上侧法线。
- camera-up 只在 `R` 与 `R @ diag(-1,-1,+1)` 两个平行夹爪等价姿态间选择，要求 local `+X` 对 world `+Z` 非负；不得用旧 local-X-forward 的 `diag(+1,-1,-1)`。
- 新轴参数必须显式传入；默认保持 `local_x/top=z`，不改变历史 planner、OursV2 或候选排序。
- camera-up 只解决离散 roll 二义性，不把 IK miss 解释为坐标轴失败。论文视频必须保留执行失败说明；新 V4 输出隔离于 V3。
