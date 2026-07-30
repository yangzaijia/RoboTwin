# Piper 机器人专属材质调色

## 语义

`--piper_robot_gray_material_override 1` 只修改左右 Piper articulation 的渲染材质。它不使用最终帧 RGB 阈值，也不读取或修改瓶子、桌面与背景材质。默认将近中性灰且线性 RGB 均值位于 `[0.10, 0.80]` 的机器人材质改为 `[0.06, 0.06, 0.06]`。

该开关当前只支持 `--planner_backend urdfik`，默认关闭；未指定时旧链路不变。

## 参数模板（不可直接运行）

```bash
python code_painting/plan_anygrasp_keyframes_piper.py \
  <原有 V9p 参数> \
  --output_dir <新的隔离输出目录> \
  --piper_robot_gray_material_override 1 \
  --piper_robot_gray_material_target 0.06 \
  --piper_robot_gray_material_min 0.10 \
  --piper_robot_gray_material_max 0.80
```

## 本 episode 可直接运行的 Orientation 示例

```bash
cd /home/zaijia001/ssd/RoboTwin
ROOT=/home/zaijia001/ssd/data/piper/paper_qualitative_assets/outputs/matched_candidate_image_video_release_20260722
SRC="$ROOT/v9p_planning_runs_oursv2_close03_pure/oursv2-5/orientation"
DST="$ROOT/v10_robot_material_override_oursv2_20260730/orientation_reproduce/planner_output"
mkdir -p "$DST"
CMD=$(sed "s#--output_dir $SRC/planner_output#--output_dir $DST#" "$SRC/command.sh.txt")
eval "$CMD --piper_robot_gray_material_override 1 --piper_robot_gray_material_target 0.06 --piper_robot_gray_material_min 0.10 --piper_robot_gray_material_max 0.80"
```

## 验证

```bash
ffprobe -v error \
  -show_entries stream=codec_name,pix_fmt,width,height,r_frame_rate,nb_frames \
  -of json \
  /home/zaijia001/ssd/data/piper/paper_qualitative_assets/outputs/matched_candidate_image_video_release_20260722/v10_robot_material_override_oursv2_20260730/orientation/planner_output/head_cam_plan.mp4

ffmpeg -nostdin -v error \
  -i /home/zaijia001/ssd/data/piper/paper_qualitative_assets/outputs/matched_candidate_image_video_release_20260722/v9p_stage12_realbg_20260725/v10_oursv2_aligned_debug_robot_material_dark_4x6.mp4 \
  -f null -
```
