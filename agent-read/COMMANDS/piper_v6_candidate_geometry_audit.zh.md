# Piper V6 候选几何审计

## 用途

只读取 raw AnyGrasp、V6 `plan_summary.json`、Foundation 背景和 object spatial anchors，为每个关键帧生成 2×3 候选图。不调用 IK、规划或执行，不覆盖旧素材。

六格依次是：raw dense candidates、V6 选中的 raw AnyGrasp poses、V6 stored `robot_replay` rotation、当前 `-5 cm @ stored +X` target、raw center 到 object anchor 距离、raw 与 current target 叠加。

## 参数模板（不可直接运行）

```bash
/home/zaijia001/ssd/miniconda3/envs/RoboTwin_bw/bin/python \
  /home/zaijia001/ssd/RoboTwin/code_painting/export_v6_candidate_geometry_audit.py \
  --config <AUDIT_CONFIG_JSON> \
  [--dry-run] [--overwrite]
```

## 可运行示例

```bash
cd /home/zaijia001/ssd/RoboTwin && \
/home/zaijia001/ssd/miniconda3/envs/RoboTwin_bw/bin/python \
  code_painting/export_v6_candidate_geometry_audit.py \
  --config /home/zaijia001/ssd/data/piper/paper_qualitative_assets/piper_v6_candidate_geometry_audit.json \
  --dry-run
```

```bash
cd /home/zaijia001/ssd/RoboTwin && \
/home/zaijia001/ssd/miniconda3/envs/RoboTwin_bw/bin/python \
  code_painting/export_v6_candidate_geometry_audit.py \
  --config /home/zaijia001/ssd/data/piper/paper_qualitative_assets/piper_v6_candidate_geometry_audit.json \
  --overwrite
```

正式输出位于：

```text
/home/zaijia001/ssd/data/piper/paper_qualitative_assets/outputs/keyframe_candidates/pick_diverse_bottles/id0/v6_red_forward_camera_back_up_candidate_videos/candidate_audit_v6
```

`manifest.json` 记录每帧候选 ID、raw/target 到 object anchor 的距离、分图路径、总图尺寸与 SHA-256。anchor 是物体 pose 原点，不是最近表面；瓶顶抓取到 anchor 较远并不自动表示候选脱离物体，必须结合投影图判断。
