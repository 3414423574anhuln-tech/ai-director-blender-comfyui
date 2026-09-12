# Blender + ComfyUI AI Director

**简体中文** | [English](README.en.md)

这是一个 3D 导演工作流原型，用于把 Blender 中的相机、角色站位和导演参数传递到 ComfyUI。

## 功能

- Blender 3D 导演台面板
- 导演视角 / 机位视角一键切换
- 明显可见的相机视锥
- 轻量级导演预演人物模型
- 多种人物预设与完整角色复制
- 景别、运镜、时长、人物动作和画面情绪控制
- 一键导出 `director_scene.json`
- ComfyUI `AI Director Loader` 自定义节点
- 导出的 JSON 发生变化后，ComfyUI 可自动重新读取

## 环境要求

- Blender 5.2 或兼容版本
- ComfyUI
- 当前主要测试平台为 Windows

## 仓库结构

```text
blender_addon/
  ai_director_stage_tools.py

comfyui_custom_node/
  ComfyUI-AI-Director/
    __init__.py
    nodes.py

examples/
  director_scene.example.json
```

## 安装 Blender 插件

1. 打开 Blender。
2. 进入 `Edit > Preferences > Add-ons`。
3. 选择 `Install from Disk`。
4. 选择 `blender_addon/ai_director_stage_tools.py`。
5. 启用 **AI Director Stage Tools**。
6. 在 3D View 中按 `N`。
7. 打开 **3D导演台** 标签页。

## 安装 ComfyUI 节点

将：

```text
comfyui_custom_node/ComfyUI-AI-Director
```

复制到：

```text
ComfyUI/custom_nodes/ComfyUI-AI-Director
```

然后重启 ComfyUI，并搜索：

```text
AI Director Loader
```

## Blender 连接 ComfyUI

在 Blender 中：

1. 打开 `N > 3D导演台`。
2. 找到 **导演输出**。
3. 将 **ComfyUI目录** 设置为你实际的 `ComfyUI/custom_nodes/ComfyUI-AI-Director` 文件夹。
4. 设置景别、运镜、时长、人物动作和画面情绪。
5. 点击 **导出到 ComfyUI**。

Blender 会把：

```text
director_scene.json
```

写入 ComfyUI 自定义节点目录。

ComfyUI 的 `AI Director Loader` 会输出：

- `prompt`
- `shot`
- `movement`
- `lens_mm`
- `duration_s`
- `camera_data`

## 当前限制

这是一个早期原型。

- 当前人物系统是轻量级导演预演模型，不是完整的影视级角色 Rig。
- 当前工作流只导出一组全局导演指令。
- 修改部分相机参数后，可能需要手动刷新相机视锥。
- 当前 Blender 场景默认要求存在名为 `机位1` 的相机，并使用 `角色A` 作为基础人物模板。
- 多镜头时间线编辑和完整姿势 Rig 编辑尚未实现。

## License

MIT License，详见 `LICENSE`。
