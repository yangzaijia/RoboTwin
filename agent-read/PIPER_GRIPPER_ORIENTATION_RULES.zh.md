# Piper 夹爪朝向规则说明

## 当前结论

在当前 `pnp_star_pear_hamer_output_v2/hand_detections_0.npz` 和 `PiperPika` 标定场景下，图里的 RGB 轴含义可以按下面理解：

- 红色 `+X`：由手指骨架平面叉乘得到的侧向/法向轴，不是主要前进轴。
- 绿色 `+Y`：拇指指尖到食指指尖方向，最接近夹爪开合轴。
- 蓝色 `+Z`：由 `X cross Y` 得到，当前观察上最接近夹爪前进/接近方向。

也就是说，你看到“蓝色轴是前进轴、绿色轴是开合、红色是另一个侧向轴”是符合当前代码定义和可视化结果的。

## 为什么之前默认只 debug 左手

最近新增的几个 debug wrapper 默认用了：

- `ARM=left`
- 或 `ARMS=left`

原因是先减少变量：单臂 IK 更快，失败来源更少，也方便先判断局部轴语义。不是代码只能跑左手。

如果要右手：

```bash
ARM=right ...
```

或：

```bash
ARMS=right ...
```

如果要左右一起：

```bash
ARMS=both ...
```

注意：左右一起跑时，某些候选只要一边不可达，就会让观察更乱。当前建议先左手确认轴，再右手单独验证。

## HaMeR / NPZ 里的 gripper 局部轴

入口逻辑在：

- `code_painting/render_hand_retarget_r1_npz.py`
- `calc_gripper_pose_from_keypoints(...)`

如果 NPZ 里有 `left_gripper_rotation_matrix` / `right_gripper_rotation_matrix`，脚本直接读。否则会用同一套公式从 keypoints 重算。

重算公式：

```text
gripper_position = 0.5 * (thumb_tip + index_tip)

+Y = normalize(thumb_tip - index_tip)
temp = index_joint - index_tip
+X = normalize(cross(temp, +Y))
+Z = normalize(cross(+X, +Y))

rotation_matrix = [ +X  +Y  +Z ]  # 三列分别是局部 x/y/z 轴
retreat_position = gripper_position - retreat_distance * +Z
```

含义：

- `+Y` 是两指之间的方向，所以最像开合轴。
- `+Z` 用来计算 retreat：`retreat = center - d * Z`，所以 `+Z` 从 retreat/wrist 侧指向夹爪中心/接近方向。
- `+X` 是为了补齐右手系的第三根轴，更像手掌/手指平面的法向或侧向。

## 朝向修正顺序

每帧的目标朝向从 `rotation_cam` 开始。

代码路径：

- `remap_target_rotation(...)`

公式：

```text
R_cam_fixed = R_cam * R_post * R_remap
```

其中：

- `R_cam`：HaMeR/NPZ 的 gripper rotation。
- `R_post`：命令行 `--stored_orientation_post_rot_xyz_deg RX RY RZ`。
- `R_remap`：命令行 `--orientation_remap_label` 对应的固定轴重排。

重要点：

- 这里是右乘，所以 `R_post` / `R_remap` 作用在 gripper 局部坐标系上。
- 如果你想把“蓝色 `+Z` 前进轴”映射成机器人期望的某根轴，本质上就是在这里找一个稳定的 `R_post` 或 `R_remap`。

## Head camera 到 world 的转换

代码路径：

- `camera_to_world_pose(...)`

当前命令使用：

```text
--camera_cv_axis_mode legacy_r1
--head_camera_local_pos 0.107882 -0.2693875 0.464396
--head_camera_local_quat_wxyz 0.85401166 0.01255256 0.51885652 -0.0359783
```

公式：

```text
pos_world = p_head_world + R_head_world * C_legacy * pos_cam
R_world = R_head_world * C_legacy * R_cam_fixed
```

`legacy_r1` 矩阵是：

```text
C_legacy =
[[ 0,  0,  1],
 [-1,  0,  0],
 [ 0, -1,  0]]
```

Piper 双臂场景里，head camera 是固定在 left base 上的标定位姿：

```text
world_T_head = world_T_left_base * left_base_T_head_camera
```

## Piper base 和双臂位置

当前配置：

- `robot_config_PiperPika_agx_dual_table.json`
- `dual_arm_embodied=false`
- `embodiment_dis=0.60`

因此左右臂是两个独立 Piper 实例：

```text
left_base  ~= [-0.3, -0.25, 0.75]
right_base ~= [ 0.3, -0.25, 0.75]
base_quat  = [0.70710678, 0, 0, 0.70710678]
```

`PiperDualReplayRenderer` 会分别用 left/right base 把 world target 转回各自 base：

```text
target_base = inv(world_T_arm_base) * target_world
```

## Gripper target 到 Piper link6 / URDFIK 的转换

关键路径：

- `render_hand_retarget_piper_dual_npz_urdfik.py`
- `_target_tcp_world_to_ee_base(...)`
- `envs/robot/robot.py`
- `_trans_from_gripper_to_endlink(...)`

当前 Piper URDFIK 求解的是：

```text
base_link -> link6
```

目标进入 IK 前先执行：

```text
target_pose_base = world_pose_to_base_pose_for_arm(target_world, arm)
target_pose_ee = robot._trans_from_gripper_to_endlink(target_pose_base, arm)
```

当前配置中的关键参数：

```text
gripper_bias = 0.12
delta_matrix = I
global_trans_matrix = diag(1, -1, -1)
```

`_trans_from_gripper_to_endlink(...)` 里：

```text
position += R_gripper * [0.12 - gripper_bias, 0, 0]
R_ee = R_gripper * inv(delta_matrix)
```

因为 `gripper_bias=0.12` 且 `delta_matrix=I`：

```text
position offset = 0
R_ee = R_gripper
```

所以在当前 PiperPika 配置下，送进 URDFIK 的 `link6` 目标基本就是 retarget 产生的目标位姿本身。

## 一个容易混淆的不对称点

`get_left_tcp_pose()` / `get_right_tcp_pose()` 读回 TCP 时，会走 `_trans_endpose(..., is_endpose=True)`：

```text
R_tcp_readback = R_link6 * global_trans_matrix * delta_matrix
```

当前：

```text
global_trans_matrix = diag(1, -1, -1)
delta_matrix = I
```

所以读回的 TCP 朝向和 `link6` 朝向之间存在 `Y/Z` 翻转。

但 `_trans_from_gripper_to_endlink(...)` 当前把目标送进 IK 时没有再乘 `global_trans_matrix` 的逆，只乘了 `inv(delta_matrix)`。

实际影响：

- target axis actor 显示的是 retarget 目标轴。
- URDFIK 接收的是接近同一套目标轴。
- `get_*_tcp_pose()` 的 post-execute debug 读回轴会额外带 `diag(1,-1,-1)`。

因此，看“目标轴颜色语义”时，应优先看 target axis 和 board 图；看“执行误差”时，要意识到读回 TCP frame 可能比目标 frame 多一层 `global_trans_matrix`。

## 对当前调试的建议

当前观察结果说明：

- HaMeR/重算 gripper 的蓝色 `+Z` 更像前进轴。
- 绿色 `+Y` 更像开合轴。
- 机器人/IK 侧不是天然把 `+Z` 当作前进轴；现有历史命令里曾使用 `swap_red_blue_keep_green`，本质上就是把红蓝轴关系调到更接近机器人习惯。

建议调试顺序：

1. 先用 `run_piper_retarget_postrot_board_video.sh` 的 `CASE_MODE=standard` 看完整 retarget 回放里哪个后旋转视觉最合理。
2. 再用 `CASE_MODE=axis90` 扩大到单轴 90/180 度旋转。
3. 最后只对视觉合理的 1-2 个候选跑更长帧数或左右手。
4. 如果候选视觉合理但 success 少，优先调 `TARGET_DY/TARGET_DZ` 和 IK 初始姿态，而不是继续盲扫朝向。

## 常用命令

左手，标准 8 候选：

```bash
GPU=3 FPS=5 FRAME_START=0 MAX_FRAMES=32 ARMS=left CASE_MODE=standard \
TARGET_DY=0.1 TARGET_DZ=0.1 ORIENTATION_REMAP_LABEL=identity \
bash /home/zaijia001/ssd/RoboTwin/code_painting/run_piper_retarget_postrot_board_video.sh \
  /home/zaijia001/ssd/data/piper/hand/pnp_star_pear_hamer_output_v2/hand_detections_0.npz \
  /home/zaijia001/ssd/RoboTwin/code_painting/output_piper_retarget_postrot_board_standard
```

右手，标准 8 候选：

```bash
GPU=3 FPS=5 FRAME_START=0 MAX_FRAMES=32 ARMS=right CASE_MODE=standard \
TARGET_DY=0.1 TARGET_DZ=0.1 ORIENTATION_REMAP_LABEL=identity \
bash /home/zaijia001/ssd/RoboTwin/code_painting/run_piper_retarget_postrot_board_video.sh \
  /home/zaijia001/ssd/data/piper/hand/pnp_star_pear_hamer_output_v2/hand_detections_0.npz \
  /home/zaijia001/ssd/RoboTwin/code_painting/output_piper_retarget_postrot_board_standard_right
```

输出：

```text
board/board_zed.mp4
board/board_third.mp4
board/board_zed_frame0000.png
board/board_third_frame0000.png
index.csv
```

## 2026-07-17：Canonical local-Z 前进轴的 camera-up 规则（V4，0515 安装判据已被 V5 修正）

> 注意：下面的 `local +X` 朝上结论只记录 V4 历史。0515 标定显示腕部相机主要位于 link6 的 local `-X` 一侧；正式 V5 必须使用本节末尾的 `-X` mount-up 规则。

`robot_replay` canonical candidate 的局部轴定义为：

```text
local +Z（蓝） = 夹爪前进 / approach 轴
local +Y（绿） = 两指开合轴
local +X（红） = (+Y) x (+Z)，即开合--前进平面的法线
world +Z       = 上方
```

因此“手腕相机不要落在腕部下方”的离散约束是：

```text
dot(R[:, 0], world_up) >= 0
```

平行两指夹爪允许交换两根手指而保持同一物理抓取。Canonical local-Z 模式比较：

```text
R_base = R
R_flip = R @ diag(-1, -1, +1)
```

`R_flip` 是绕 local `+Z` 的 180° roll，严格保持蓝色前进轴，只翻转红/绿轴。第一关键帧选择红轴朝上的分支；后续关键帧在两个等价分支中优先保持与上一关键帧的旋转连续性。`plan_summary.json` 记录 `original_top_axis_up_dot`、`top_axis_up_dot`、`camera_up_flip_applied`、`forward_axis_change_deg` 和选择模式。

不要在 canonical local-Z candidate 上复用旧的 `diag(+1,-1,-1)`：旧矩阵是绕 local `+X` 翻转，适用于历史 local-X-forward 约定，但会反转 canonical local `+Z` 前进轴。代码因此新增显式 `--candidate_camera_forward_axis=local_x|local_z`；默认 `local_x` 保持旧行为。

这条规则只消除平行夹爪的离散 wrist-roll 二义性，不改变候选编号、接近方向或目标位置，也不替代 IK 可达性/碰撞检查。OursV2 human-target replay 不经过该 AnyGrasp candidate 后处理。

## ~~2026-07-17：V5 校准相机安装侧与 link6 适配~~（已撤销）

> V5 把腕部相机的安装平移方向当成了相机姿态方向，并把 Piper AnyGrasp 的前进轴误写成 local `+Z`。以下内容仅用于复现旧 V5，不得作为当前轴规则。

0515 wrist 外参的 link6 局部平移为左 `[-0.0743,+0.0207,+0.0936] m`、右 `[-0.0600,-0.0274,+0.0894] m`，相机主体位于 local `-X` 一侧。因此正确的 mount-up 判据是：

```text
camera_mount_normal = -R[:, 0]
dot(camera_mount_normal, world_up) > 0
```

调试轴颜色不变：红/绿/蓝仍表示 local `+X/+Y/+Z`。相机侧朝上时，红色 `+X` 朝下是预期现象，不能再据此判断相机倒置。

候选目标进入 Piper IK 前还必须应用两层独立适配：

```text
Piper replay global axis conversion
R_sapien_link6 = R_curobo_link6 @ Ry(-90 deg)
```

V5 使用 `--candidate_camera_top_axis x --candidate_camera_top_axis_sign -1`、`--piper_apply_global_trans_to_ik 1` 和 `--piper_apply_curobo_to_sapien_link_rotation 1`。为避免 V4 逐 waypoint IK 的 wrist branch 跳变，正式路径使用 stage endpoint IK、40 点关节插值和 64 seeds；Top-score-feasible 额外使用 `joint_continuity`，已成功的 Orientation/Fused 保留 `pose_error`。camera-up 仍不等于可执行：候选若把关节推到硬限位，必须使用同一策略排序中下一项满足 mount-up、IK 和关节限位的候选，并在标题/manifest 中标为 constrained/feasible。

## 2026-07-18：V6 红轴前进与 camera-back-up 正式规则

实际候选几何与视频中的颜色轴为：红 `+X` 是夹爪前进/approach，绿 `+Y` 是平行两指开合，蓝 `+Z` 是两者平面的法向。0515 标定中的相机平移只说明相机装在哪里，不能说明相机朝哪里；因此 V5 的 `-X` mount-normal 推断无效。

V6 保持红 `+X` 不变，只在绕红轴 180° 的两指等价分支之间选择，并要求：

```text
forward = R[:, 0]                 # red +X
camera_back_or_plane_normal = -R[:, 2]
dot(camera_back_or_plane_normal, world_up) >= 0
```

第一关键帧选择满足 `-blue up` 的分支。后续关键帧必须先硬过滤 `top_axis_up_dot >= 0`，再在合格分支中最小化与上一关键帧的旋转差；不能把 camera-up 仅作为连续性同分项，否则 6--10 秒处可能重新翻回倒置分支。正式参数是 `--candidate_camera_forward_axis local_x --candidate_camera_top_axis z --candidate_camera_top_axis_sign -1`，candidate offset 与 pregrasp 也都沿 local `+X`。

`pick_diverse_bottles/id0` 的 V6 可达候选为 K1 `L16/R18`、K2 `L6/R5`。Orientation、Fused 和 constrained Top-score 在轴、camera-back-up、IK 与关节限位约束后收敛到同一组 ID。旧 V5 视频保留但不再用于判断轴定义。
