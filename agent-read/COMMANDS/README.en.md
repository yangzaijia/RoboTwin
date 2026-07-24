# Command Documentation Template

Use the following lightweight format when maintaining reusable command notes.

## Recommended format

### Purpose
Short sentence describing what the command is for.

### Command list format
- One-line comment
- One command block immediately below it

### Example
- Export the calibrated version-B overview image/video.
```bash
python some_script.py --some-flag
```

## Notes
- Prefer absolute paths for commands that the user is likely to copy directly.
- Keep comments short and action-oriented.
- Group commands by task/topic.

See `paper_qualitative_assets.en.md` for the paper video-grid and keyframe-candidate commands.

See `candidate_camera_mount_up_v5.en.md` for the calibrated 0515 camera-side rule, Curobo/SAPIEN link6 adapter, and V5 candidate-replay commands.

See `rigid_object_transport_v9.en.md` for rigid K1-to-K2 object transport, the six-panel transform audit, and the 2x2 comparison.

See `planning_compare_v9_1.en.md` for the four-strategy Canonical RTCP versus OursV2+5 cm planning comparison.
