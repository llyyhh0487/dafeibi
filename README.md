# 合成大菲比

一个纯前端的合成类小游戏（Suika / 西瓜游戏玩法）：拖动瞄准、松手投放，两个相同的撞在一起就合成更大的一只。
**没有任何第三方依赖**，不上框架、不打包，直接打开 `index.html` 就能玩。

🔗 在线玩：https://llyyhh0487.github.io/dafeibi/

手机浏览器直接打开即可，已针对触屏和刘海屏做过适配。

---

## 玩法

- **鼠标**：移动瞄准、点击投放
- **触屏**：拖动瞄准、松手投放
- **键盘**：`←` `→` 微调位置，`空格` 投放，`R` 重开

两只最大的「菲比」撞在一起会一起炸掉，换 **500 分 + 一枚复活币**。
每累计 2000 分发一枚复活币，只在本局有效。

## 实现要点

- **物理**：自己写的 PBD（位置约束求解），3 个子步 × 6 次迭代，静止堆叠稳定不抖
- **碰撞体不是圆**：按贴图 alpha 轮廓自动生成多子圆碰撞形状（`assets/fruits/parts.js`）
- **贴图三级兜底**：真图 → 内联模糊占位（`blur.js`）→ 程序化水果，弱网也不会看到「图挂了」
- **音效**：合成音是 WebAudio 程序化合成，零音频文件；合成时会随机播一句「菲比啾比」/「菲比比」
- **无后端**：没有排行榜、不上报任何数据，纯静态站点；最高分只存在本机 `localStorage`

## 目录

```
index.html            入口
game.js               游戏主体（物理 / 渲染 / 音效 / 语音）
style.css
assets/
  fruits/*.webp       12 级贴图
  fruits/parts.js     碰撞形状（自动生成）
  fruits/blur.js      模糊占位图（自动生成）
  bg/*.webp           背景图 + 按钮底图（生图后压缩，见 tools/compress_bg.py）
  sfx/                合成语音素材 + 切句表
tools/                素材管线脚本（离线跑，不参与部署）
```

## 素材管线

贴图、碰撞形状、占位图、语音切句表都是脚本生成的，改完源图重跑即可：

```bash
python tools/normalize_assets.py    # 抠图 + 归一化 -> assets/fruits/*.webp
python tools/build_parts.py         # alpha 轮廓 -> parts.js
python tools/make_blur.py           # 缩略图 -> blur.js
python tools/build_sfx_table.py     # 切点 json -> assets/sfx/phoebe.js
```

语音的打点工具在 `tools/make_sfx_marker.py`（生成一个单文件 HTML，双击即可用）。

## 部署

纯静态站点，推到 GitHub 后在仓库 **Settings → Pages** 里选 `main` 分支根目录即可。
仓库根目录的 `.nojekyll` 用来关掉 Jekyll 处理。
