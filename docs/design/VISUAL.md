# Visual system

求职作品集的公开 UI 设计规范。实现时以本文 + `docs/adr/0006-*.md` 为准；情绪板参考图：`docs/design/references/hero-mood-digicrypt-purple.png`。

## 1. Mood（一句话）

深紫渐变科技感 Hero + 清晰双栏排版 + 毛玻璃内容区；像素只作个人签名，不抢第一眼。

## 2. Color tokens

在 CSS 中建立同名变量（可微调数值，但语义名固定）：

| Token | 角色 | 建议起点 |
| --- | --- | --- |
| `--bg-deep` | 页面最底层 | `#1a0a3e` → `#4c1d95` 径向/对角渐变 |
| `--bg-mid` | 区块过渡 | `#5b21b6` |
| `--glass` | 毛玻璃面板 | `rgba(255,255,255,0.08)` + `backdrop-filter: blur(16px)` |
| `--glass-border` | 玻璃描边 | `rgba(255,255,255,0.18)` |
| `--text-primary` | 主文案 | `#ffffff` |
| `--text-muted` | 副文案 | `rgba(255,255,255,0.72)` |
| `--accent-cta` | 主按钮 | `#ff5c7a` → `#ff7a59` 小渐变（参考图珊瑚粉） |
| `--accent-cta-hover` | 按钮悬停 | 略提亮 + 轻微 scale |
| `--accent-link` | 行内链 / 侧栏激活 | `#c4b5fd` |
| `--success` / `--danger` | 后台状态 | 克制使用，勿大面积 |

**不要**：大面积纯白底 + 紫字（那是另一套模板）；正文区可读性优先于「再紫一点」。

## 3. Typography

- **展示标题（Hero / 页面 H1）**：几何无衬线，偏粗（类似 Space Grotesk / Plus Jakarta Sans / Syne）。字重 700–800，行高略紧。
- **正文**：同一家族的 Regular/Medium，或搭配可读性更好的第二无衬线（如 Source Sans 3）。**禁止**整站用像素字体跑长文。
- **代码 / 源码浏览**：等宽（JetBrains Mono / Geist Mono）。
- **像素点缀**：仅短标签、徽章、吉祥物旁小字；位图字体可接受。

默认 locale 文案为繁中：注意标题断行与英文混排时的字距；英文切换后标题可略放大 tracking。

## 4. Shape & glass

- 半径：`--radius-control` 999px（胶囊按钮）、`--radius-card` 16–24px、`--radius-panel` 20–28px。
- 卡片 / 侧栏 / 对话框：`background: var(--glass)` + `border: 1px solid var(--glass-border)` + 轻阴影（单层，忌多层发光堆叠）。
- Hero **不要**用 inset 小图卡片当主视觉；主视觉应是右栏（或全幅背景）的主导形象。

## 5. Layout（公开站）

### 第一屏 Hero（首页）

一个构图，不是仪表盘：

1. 品牌名（Hero 级，可压过普通标题）
2. 一句定位（我是谁 / 做什么）
3. 一句短支持句
4. CTA 组（例如「查看项目」「阅读文章」）
5. 右侧或全幅主导视觉（插画 / 个人 3D 静物 / 抽象几何——**不要**堆满互不相关的 SaaS 图标）

**不要**在第一屏塞：统计条、日程、地址、多个营销卡片、飘浮 badge。

侧栏：桌面常驻（Projects / Articles / Journals / 语言切换）；移动端收成抽屉。毛玻璃侧栏贴左或贴右二选一，全站统一。

### 内容页

- 单栏阅读宽（文章约 65–72ch）+ 可选右侧 TOC。
- Project 详情：上描述（Markdown），下「仿 GitHub」源码区（单独玻璃面板，等宽 UI）。

### Admin

同一色板与圆角；密度更高（表单、表格）；CTA 仍用 `--accent-cta`，但少装饰插画。

## 6. Motion（至少 2–3 个有意动作）

1. Hero 入场：标题与视觉轻微错开 fade/slide（200–400ms）。
2. 玻璃卡片 hover：border 提亮 + 1–2px 上浮。
3. 路由切换：内容区短 fade（避免整页闪白）。

像素彩蛋可另加：头像框「咬边」闪一下、点击 CTA 极短像素粒子——默认安静，尊重 `prefers-reduced-motion`。

## 7. Pixel accents（允许 / 禁止）

**允许**：像素头像框、1 个小吉祥物、分隔符、加载时的像素 spinner、可选点击音效。  
**禁止**：整站像素正文、仿 Windows 95 窗体、闪烁跑马灯、密集像素背景干扰阅读。

## 8. i18n chrome

壳层字符串走字典（`zh-Hant` / `en`）。Owner 输入的 Markdown / 标题原样渲染，不做机翻。

## 9. 参考图用法

`hero-mood-digicrypt-purple.png` 只借：**色温、Hero 双栏、按钮形状、背景几何**。  
不借：加密货币文案、金币、过长导航、把个人站做成 Token landing。

## 10. 实现备忘（给前端）

- Next.js App Router + CSS 变量（或 CSS Modules / Tailwind theme extend 映射到上表）。
- 插画优先静态优化图或轻量 Lottie；避免首屏巨型未压缩 3D。
- 源码浏览区视觉可偏「GitHub 深色」，但仍挂在紫色站点壳内，用玻璃面板过渡，不要整页跳成另一个产品。
