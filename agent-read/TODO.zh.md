# 项目级 TODO

## 延后：基于正确 Piper 物理轴的 IK-feasible 候选筛选

- 状态：延后，不属于当前候选策略视频比较范围。
- 当前策略：严格使用 Orientation、Fused、Top-score 的原始选中候选；不做替换、重排或自动 fallback。IK/执行失败必须保存在 `plan_summary.json`、独立视频及拼接视频中，供人工筛选。
- 后续目标：在 `robot_replay → anygrasp_raw/Piper +X` 正确换基后，对每个策略内部候选执行 IK、关节限位、相机朝向和连续性检查，再选择该策略排序中首个可行项。
- 后续约束：不得跨策略替换候选；不得放宽 reach/rotation tolerance 制造成功；必须同时报告原始排名、替代排名、失败原因和最终候选编号。
- 验收：固定 episode 上 raw top 与 feasible top 可并排复现，失败原因可区分 IK 无解、关节限位、执行未收敛和碰撞，并且旧 raw-strategy 输出不被覆盖。
