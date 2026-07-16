# 论文定性素材：6×2 Episode 图片与 4×5 视频

## 用途

维护 `/home/zaijia001/ssd/data/piper/paper_qualitative_assets` 中的论文视频网格和关键帧候选图。工具只读取已有视频、Foundation/AnyGrasp 图像和 Selection Strategy Audit V4 metadata；不会运行 IK、修改 OursV2 或覆盖原始数据。

正式输出按 episode 聚合：

```text
outputs/keyframe_candidates/<TASK>/id<ID>/
├── frame_<FRAME>/
│   ├── 01_orientation_<left|right|both>.png
│   ├── 02_fused_<left|right|both>.png
│   ├── 03_top_score_<left|right|both>.png
│   ├── 04_oursv2_<left|right|both>.png
│   └── all_strategies_contact_sheet.png
├── _derived/06_anygrasp_candidates.mp4   # 仅当 D435 PNG 存在
├── pipeline_grid_4x5.mp4
├── pipeline_grid_4x5_config.json
├── pipeline_grid_4x5_manifest.json
└── README.md
```

## 参数模板（不可直接运行）

```json
{
  "metadata_root": "<SELECTION_STRATEGY_COMPARE_V4>",
  "output_root": "<PAPER_ASSET_ROOT>/outputs/keyframe_candidates",
  "base_grid_config": "<PAPER_ASSET_ROOT>/pipeline_grid_expanded_dense_urdfmatch_v2_config.json",
  "strategies": ["orientation", "fused", "top_score", "oursv2"],
  "episodes": [{"task": "<TASK>", "id": 0, "keyframes": [38, 78]}],
  "allow_missing": true
}
```

## 当前 6×2 选择

| Task | Episode | 关键帧 |
|---|---:|---|
| handover_bottle | 1, 3 | 39/80/103；23/44/57 |
| pick_diverse_bottles | 0, 1 | 38/78；46/79 |
| place_bread_basket | 0, 1 | 34/64/103/119；32/52/79/85 |
| pnp_bread | 7, 8 | 32/80/83/108；32/49/50/74 |
| pnp_tray | 2, 3 | 52/83；29/59 |
| stack_cups | 0, 1 | 51/106/139/195；40/45/84/141 |

## 可直接运行

先 dry run；它只探测路径、metadata 和视频属性：

```bash
cd /home/zaijia001/ssd/data/piper/paper_qualitative_assets
/home/zaijia001/ssd/miniconda3/envs/RoboTwin_bw/bin/python3.10 \
  export_keyframe_candidate_images.py \
  --config paper_episode_batch_config.json --dry-run
python3 generate_paper_episode_batch.py \
  --config paper_episode_batch_config.json --dry-run
```

正式重建：

```bash
cd /home/zaijia001/ssd/data/piper/paper_qualitative_assets
/home/zaijia001/ssd/miniconda3/envs/RoboTwin_bw/bin/python3.10 \
  export_keyframe_candidate_images.py \
  --config paper_episode_batch_config.json --overwrite
python3 generate_paper_episode_batch.py \
  --config paper_episode_batch_config.json --overwrite
```

候选图隔离检查使用 `--output-root <SMOKE_DIR>`；视频生成器的单集调试使用 `--only <TASK>:<ID> --output-root <SMOKE_DIR>`，批量续跑使用 `--skip-existing`。视频生成器的 `--require-complete` 会在任何源阶段缺失时失败，当前正式配置使用 `allow_missing=true` 保留显式 `MISSING` 格。

## 图片语义

- 每个策略/关键帧只使用一张 requested-keyframe Foundation replay 背景。
- LEFT/RIGHT 单手事件只画对应 gripper；BOTH 事件在同一张图上画左右 gripper，不分栏。
- 元数据缺少某手策略记录时写 `MISSING / NO SELECTION RECORD`，不伪造 pose。
- 局部坐标轴固定为 `X=红、Y=绿、Z=蓝`。
- Orientation/Fused/Top-score 显示所选 AnyGrasp candidate；OursV2 显示 synthetic human-retarget target，标为 `HUMAN TARGET`。
- 旧左右分栏版保留在 `outputs/keyframe_candidates_split_panels_v1/`。

## 视频语义和真实缺失项

- 每个 4×5 视频为 H.264、`yuv420p`、1920×1540、30 fps；每格 480×270 内容上方是独立 38 px 标题栏。
- 每个 episode 的目标时长取 Foundation replay 与 OursV2 的较长者，各路按完整进度归一化并冻结末帧。
- AnyGrasp 视频仅从已有 D435 `grasp_result_*.png` 派生，不重跑模型。
- `place_bread_basket/id0,id1` 缺 D435 AnyGrasp 和 human-guided preview；对应格显式 `MISSING`，不混入旧广角版本。
- `pnp_tray/id2,id3` 缺 Dense URDF-match-v2 raw 和相邻 legacy Dense repaint；对应格显式 `MISSING`，不伪造 Dense 结果。
- 其他 8 个 episode 的 17 个视频源阶段完整。

## 验证

```bash
cd /home/zaijia001/ssd/data/piper/paper_qualitative_assets
python3 -m json.tool outputs/keyframe_candidates/manifest.json >/dev/null
python3 -m json.tool outputs/keyframe_candidates/episode_batch_manifest.json >/dev/null
find outputs/keyframe_candidates -name pipeline_grid_4x5.mp4 -print0 | \
  xargs -0 -n1 ffprobe -v error -select_streams v:0 \
  -show_entries 'stream=codec_name,width,height,pix_fmt,r_frame_rate,nb_frames:format=duration,size' -of json
for video in outputs/keyframe_candidates/*/id*/pipeline_grid_4x5.mp4; do
  ffmpeg -v error -i "$video" -f null -
done
```

正式结果应为：12 个 episode、152 张 640×576 单策略 PNG、38 张 1280×1152 contact sheet、12 个主视频和 10 个由现有 D435 PNG 派生的 AnyGrasp 视频。pine2 默认 `python3` 没有 OpenCV；候选图导出和图像验证必须直接使用上述 `RoboTwin_bw` Python。

## `pick_diverse_bottles/id0` V3 候选复用视频

六格候选图位于：

```text
/home/zaijia001/ssd/data/piper/paper_qualitative_assets/outputs/keyframe_candidates/pick_diverse_bottles/id0/frame_000038/all_strategies_contact_sheet.png
```

对应候选已在不覆盖旧结果的前提下重新生成规划视频。新目录为：

```text
/home/zaijia001/ssd/data/piper/paper_qualitative_assets/outputs/keyframe_candidates/pick_diverse_bottles/id0/v3_candidate_videos/
├── candidate_retarget_grid_2x2.mp4
├── candidate_retarget_grid_2x2_config.json
├── candidate_retarget_grid_2x2_manifest.json
├── pipeline_grid_4x5_v3_candidates.mp4
├── pipeline_grid_4x5_v3_candidates_config.json
└── pipeline_grid_4x5_v3_candidates_manifest.json
```

2×2 为 Orientation/Fused/Top-score/OursV2。4×5 保留人类 RGB、HaMeR、inpainting、FoundationPose、Foundation replay、AnyGrasp、Dense V2、OursV2 与匹配的 OursV2 repaint。新 Top/Orientation/Fused 没有重新生成 Stage-2 repaint，因此相邻格使用说明卡片；旧 repaint 不会被错误配给新候选。

方法视频按完整进度归一化到 21.4 秒：Orientation/Fused 原始 10.3 秒，Top-score 10.5 秒，OursV2 21.4 秒。输出均为 H.264、`yuv420p`、30 fps 并通过完整解码。Top-score 最后左臂 action miss `53.6 mm`，标题和 manifest 均明确标记。
