# Visual system

求职作品集的公开 UI 设计规范。实现时以本文 + `docs/adr/0009-*.md` 为准（ADR-0006 深紫方向已 superseded）。

## 1. Mood（一句话）

浅色扁平液态玻璃：高饱和度高斯模糊色斑作底，半透明白玻璃承载内容；珊瑚 CTA 与像素点缀作签名，不抢阅读。

## 2. Color tokens

在 CSS 中建立同名变量（可微调数值，但语义名固定）：

| Token | 角色 | 建议起点 |
| --- | --- | --- |
| `--bg-deep` | 页面最底层 | `#f3f0fa` 浅薰衣草白 |
| `--bg-mid` | 区块过渡 | `#eef4ff` 浅天蓝 |
| `--glass` / `--glass-tint` | 液态玻璃面板 | `rgba(255,255,255,0.46)` → `0.28` 对角渐变 + `backdrop-filter: blur(32px) saturate(180%)` |
| `--glass-border` | 玻璃高光描边 | `rgba(255,255,255,0.78)` |
| `--glass-highlight` | 内沿高光 | `rgba(255,255,255,0.95)` inset 1px |
| `--hairline` | 分割线 | `rgba(90,70,140,0.12)` |
| `--field-bg` | 表单控件 | `rgba(255,255,255,0.55)` |
| `--text-primary` | 主文案 | `#1a1630` |
| `--text-muted` | 副文案 | `rgba(26,22,48,0.62)` |
| `--accent-cta` | 主按钮 | `#ff5c7a` → `#ff7a59` 小渐变 |
| `--accent-cta-hover` | 按钮悬停 | 略提亮 + 轻微 scale |
| `--accent-link` | 行内链 / 侧栏激活 | `#5b4cdb`（浅底上需更深，保证对比） |
| `--danger` | 表单错误 | `#d63d5c` |
| `--success` | 后台状态 | 克制使用，勿大面积 |

暗色模式（`html[data-theme="dark"]`，见 ADR-0010）沿用同一套语义 token，只换数值：

| Token | 暗色起点 |
| --- | --- |
| `--bg-deep` / `--bg-mid` / `--bg-end` | `#12101c` / `#1a1d2e` / `#16141f` |
| `--glass` / `--glass-tint` | `rgba(28,26,42,0.55)` → `0.38` |
| `--text-primary` / `--text-muted` | `#f2effa` / `rgba(242,239,250,0.62)` |
| `--accent-link` | `#9d92ff`（深底上更浅，保证对比） |

珊瑚 CTA 不换色。访客可在右上角切换；默认跟系统，选择写入 `localStorage`。

**不要**：回到大面积深紫底 + 白字；不要用纯白不透明卡片替代玻璃；正文对比度优先于「再亮一点」；暗色不要做成 ADR-0006 的 Digicrypt 壳。

## 3. Typography

- **展示标题（Hero / 页面 H1）**：几何无衬线，偏粗（类似 Space Grotesk / Plus Jakarta Sans / Syne）。字重 700–800，行高略紧。
- **正文**：同一家族的 Regular/Medium，或搭配可读性更好的第二无衬线（如 Source Sans 3）。**禁止**整站用像素字体跑长文。
- **代码 / 源码浏览**：等宽（JetBrains Mono / Geist Mono）。源码区留在同一浅色玻璃壳内（`--code-bg` 轻墨水渍），不要整页跳成 GitHub 深色主题。
- **像素点缀**：仅短标签、徽章、吉祥物旁小字；位图字体可接受。

默认 locale 文案为繁中：注意标题断行与英文混排时的字距；英文切换后标题可略放大 tracking。

## 4. Shape & liquid glass

- 半径：`--radius-control` 999px（胶囊按钮）、`--radius-card` 16–24px、`--radius-panel` 20–28px。
- **扁平**：单层极轻阴影；禁止多层发光、深色 vignette、斜向网格叠纹。
- **高斯模糊底**：页面固定层放大色斑（lilac / peach / sky），`filter: blur(72px)`；玻璃面板用 `backdrop-filter` 折射这些色斑，而不是在面板上画假纹理。
- **液态玻璃**：半透明白填充 + 高光描边 + inset 顶沿高光 + `saturate`。侧栏可比内容卡略更不透明，保证叠在 Hero 上仍可读。
- 卡片 / 侧栏 / 对话框共用 `.glass` / `.sidebar-panel`；表单控件用 `.field`。
- Hero **不要**用 inset 小图卡片当主视觉；主视觉应是右栏（或全幅背景）的主导形象。

## 5. Layout（公开站）

### 第一屏 Hero（首页）

一个构图，不是仪表盘：

1. 品牌名（Hero 级，可压过普通标题）
2. 一句定位（我是谁 / 做什么）
3. 一句短支持句
4. CTA 组（例如「查看项目」「阅读文章」）
5. 右侧或全幅主导视觉（插画 / 个人 3D 静物 / 抽象玻璃层——**不要**堆满互不相关的 SaaS 图标）

**不要**在第一屏塞：统计条、日程、地址、多个营销卡片、飘浮 badge。

侧栏：桌面常驻（Projects / Articles / Journals / 语言切换）；移动端收成抽屉。毛玻璃侧栏贴左，全站统一。

### 内容页

- 单栏阅读宽（文章约 65–72ch）+ 可选右侧 TOC。
- Project 详情：上描述（Markdown），下仿 GitHub 仓库页排版的源码区（文件表 + README 卡片；颜色用本站 token，Markdown 用 GFM）。

### Admin

同一色板与圆角；密度更高（表单、表格）；CTA 仍用 `--accent-cta`，但少装饰插画。

## 6. Motion（至少 2–3 个有意动作）

1. Hero 入场：标题与视觉轻微错开 fade/slide（200–400ms）。
2. 玻璃卡片 hover：border 提亮 + 最多 1px 上浮（保持扁平，不要深阴影抬起）。
3. 底色斑缓慢漂移；`prefers-reduced-motion` 时关掉漂移与 hover 位移。

像素彩蛋可另加：头像框「咬边」闪一下、点击 CTA 极短像素粒子——默认安静，尊重 `prefers-reduced-motion`。

## 7. Pixel accents（允许 / 禁止）

**允许**：像素头像框、1 个小吉祥物、分隔符、加载时的像素 spinner、可选点击音效。  
**禁止**：整站像素正文、仿 Windows 95 窗体、闪烁跑马灯、密集像素背景干扰阅读。

## 8. i18n chrome

壳层字符串走字典（`zh-Hant` / `zh-Hans` / `en`）。Owner 输入的 Markdown / 标题原样渲染，不做机翻。

## 9. 参考图用法

`hero-mood-digicrypt-purple.png` 只保留 **Hero 双栏构图与胶囊 CTA 形状**。  
不借：深紫底、加密货币文案、金币、过长导航、把个人站做成 Token landing。

## 10. 实现备忘（给前端）

- Next.js App Router + CSS 变量（`frontend/src/app/globals.css`）；Tailwind 只做布局，玻璃与控件走语义 class。
- 插画优先静态优化图或轻量 Lottie；避免首屏巨型未压缩 3D。
- 无 `backdrop-filter` 时回退为更高不透明度白底，不回退成深紫。
