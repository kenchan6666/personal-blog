# 技术简历：文案标准与一页版式系统

研究日期：2026-09-22  
范围：一级来源（高校职业中心、Google/前 People Ops 原文、开源版式系统官方文档/schema、公开 SKILL.md raw）

---

## 问题

父 agent 要实现「技术简历」时需要可执行规则，回答两问：

1. **Copy**：怎样的项目/经历 bullet 才算 CV 级？公式、时态、量化、省略、一页密度、技术栈放哪、项目 vs 工作经历如何分？
2. **Layout**：最强一页技术简历版式在做什么？页边距、字号阶梯、章节顺序、项目标题模式、bullet 缩进、技能行式分组、留白？RenderCV / JSON Resume / 高校一页模板给出了哪些具体数字？

另查：是否存在以「写简历」为职责的公开 agent `SKILL.md`。

---

## 结论（可执行规则）

### A. Copy（文案）

#### A1. 子弹公式（三套可互换，择一贯用）

| 公式 | 结构 | 来源声称 |
|------|------|----------|
| **XYZ** | Accomplished **[X]** as measured by **[Y]** by doing **[Z]** | Laszlo Bock：每条成就用此式；主动动词 + 数值度量 + 基线对比 + 做法 |
| **CAR** | **C**ontext → **A**ction/Accomplishments → **R**esult | Stanford Career Education：每条 1–2 句演示技能；结果尽量量化，或写清目的/意义 |
| **压缩 STAR** | Verb + what you did + measurable outcome（把 Situation/Task 压进动作） | 公开 skill `resume-writer`；RenderCV 官方示例句式：action + technical context + measurable result |

**执行检查（每条 bullet 必须过）：**

1. 以**强动作动词**起句（非 “Responsible for / Helped with / Worked on / Duties included”）。
2. 含 **Y（度量）**：规模、%、金额、延迟、用户数、团队人数、吞吐等；无精确数则用可辩护的代理量或定性，**禁止编造**。
3. 含 **Z（做法）**：技术/方法/决策，使声明可面试追问。
4. 优先把**最有冲击力的事实放句首**（Stanford GSB）。
5. 能写对比基线更好（Bock：相对同伴/基线）。

#### A2. 时态与语法

- **过去职位 → 过去时动词；当前职位 → 现在时**（MIT CAPD checklist）。
- **禁止第一人称**（I / we / me）（Harvard College Guide；MIT）。
- 用**短语/片段**，不要叙事长句（Harvard HES 样板说明；Harvard College DON’T: narrative style）。
- 语言：**具体、主动、基于事实（quantify and qualify）、为快速扫描而写**（Harvard College）。

#### A3. 量化与「证据」

- 每条尽量给 **size / scale / budget / staff** 等影响证据（MIT checklist：“project, activity, and results”）。
- Google re:Work（审查侧）：看重**可量化的影响、贡献、实绩**（销售额、专利数、学术奖等无可辩驳的量化经验）。
- Bock：即使看似普通的工作也能量化（如日服务客户数 + 准确率 + 与均值对比）。

#### A4. 省略 / 不要写

Harvard College **DON’T**：人称代词、缩写堆砌、叙事体、俚语、照片、年龄/性别、references、**每行以日期开头**。  
MIT：**年龄/宗教/健康/婚姻状况、照片（美式）、薪资、未要求时的推荐人**；勿写职责说明书式句子。  
Stanford GSB：>15–20 年或不相关经历压到 “Additional Work Experience”，只留雇主+职位。  
公开 skill 共识：**禁止编造指标/雇主/职称**；技术清单 bullet 不属于 Experience（移到 Skills）。

#### A5. 一页密度

| 来源 | 页数 | 密度相关 |
|------|------|----------|
| MIT CAPD | 默认 **1 页**；高阶学位或 10+ 年可用 2 页 | 留足白边便于阅读 |
| Harvard GSAS Master’s | BA/BS、MA/MS、MBA **常规范 1 页**；资深/PhD 可 2 页 | — |
| Harvard GSAS PhD | 简历通常 **1–2 页** | — |
| Stanford Career Ed. | **1–2 页** | — |
| Stanford GSB（资深） | **最多 2 页**；每职 **3–4 条**，每条 **≤2 行** | 扫描约 6–8 秒 |
| Skill `resume-writer` | ~10 年以下 **1 页**；高管 **2 页** | 每职 3–5 条 |

**可执行压缩顺序（resume-tailor Phase 7）：** 删语言项 → 最旧职位压成一行 → 删教育附加（GPA/课程，5+ 年经验）→ 收紧技能分类 → 删次要 bullet → 再调字号/行距。

#### A6. 技术栈放置

1. **Skills 区**：按类别分行（Languages / Infrastructure / Data / Tools…），**label: details** 行式，非技能墙（RenderCV `OneLineEntry`；官方 SE 示例）。
2. **Experience/Project bullets 内嵌**：写「如何做」时带具体语言/工具（MIT：“include how you performed tasks… what language”；RenderCV 示例 bullet 内含 Kafka and Go）。
3. **可选 `bold_keywords`**：按 JD 加粗栈名，不改 bullet 正文（RenderCV settings）。
4. **禁止**单独一条只有技术列表的 Experience bullet（resume-tailor bullet-patterns）。

#### A7. 项目 vs 工作经历 bullets

| | 工作经历（Experience） | 项目（Projects） |
|--|------------------------|------------------|
| 标题字段 | 公司 + 职位 + 地点 + 日期 | 项目名 + 日期（+ 可选链接） |
| Schema | JSON Resume `work`；RenderCV `ExperienceEntry` | JSON Resume `projects`（`name`/`keywords`/`highlights`/`startDate`/`endDate`）；RenderCV `NormalEntry` |
| Bullet 重心 | 业务/产品结果、ownership、规模 | 构建了什么、技术决策、可验证产物（stars、集群规模、repo URL） |
| 何时强调 Projects | — | 早期职业、转岗、或最强工作在开源/课外（RenderCV SE 指南；MIT：class/personal projects 可用，须写清相关性） |
| 条数建议 | 近职 3–5（或 GSB 3–4×≤2 行） | 常 2–3 条：建成什么 / 技术 / 影响（cv-writer checklist） |

**章节顺序（技术求职常见，可按雇主重要性调换）：**  
Header →（可选 Summary）→ Education *或* Experience（学生偏教育在前；有经验者 GSB 建议 Experience 在 Education 前）→ Projects → Skills。  
Harvard：按**对雇主重要性**排 section；section 内**逆时序**。

---

### B. Layout（版式）

#### B1. 高校一页模板给出的数字

| 参数 | MIT CAPD | Harvard GSAS Master’s | Harvard GSAS PhD | Stanford Career Ed. | Stanford GSB |
|------|----------|----------------------|------------------|---------------------|--------------|
| 页边距 | **0.5–1.0 in**，一致 | **≥ 0.75 in**，四周相等 | **≥ 0.5 in**，四周相等 | **0.75–1.0 in**（上下可 **0.5**） | **≥ 0.70 in** |
| 正文字号 | **10–12 pt** | **10–12 pt** 全文一致 | **10–12 pt** | **10–12**（Times 类建议 **11–12**） | **11 或 12 pt** |
| 字体 | Arial / Calibri / Times 等易读体 | 常见易读体；避 text box/色/阴影 | Times / Arial；避 text box/下划线/阴影 | Times / Calibri / Cambria / Garamond / Helvetica / Arial | Calibri / Arial |
| 强调 | 粗/斜体用于标题或职位；**避免下划线** | 一致 spacing/粗斜 | — | 粗/斜/缩进/bullet 标出需先被看到的信息 | 粗体标**公司或职位**（择一更有冲击力）；少用线/图/斜体 |
| 对齐 | — | — | — | — | **左对齐**（美式招聘从左扫） |
| ATS/模板 | 勿用难解析模板；偏 Word 白纸 | 劝阻模板 | — | — | — |
| 留白 | 明确要求足够 whitespace | 平衡 white space（College Guide） | — | — | whitespace 帮助扫描 |

**推荐默认（综合一页技术简历，落在多方交集）：**  
页边距 **0.7 in**；正文 **10–11 pt**；姓名更大且粗；单栏；section 标题粗体；日期右栏或右对齐；Skills 用分类一行。

#### B2. RenderCV（官方 design 默认值，`classic` 文档示例）

来源：`https://docs.rendercv.com/user_guide/yaml_input_structure/design/`

| 项 | 默认/文档值 |
|----|-------------|
| 纸张 | `us-letter` |
| 页边距 | **top/bottom/left/right = 0.7in** |
| 正文 | **10pt**，`Source Sans 3` |
| 姓名 | **30pt**，bold |
| Section 标题 | **1.4em**，bold；`with_partial_line`，线粗 **0.5pt**；上 **0.5cm** / 下 **0.3cm** |
| 行距 | `line_spacing: 0.6em` |
| 日期/地点栏宽 | `date_and_location_width: 4.15cm`，右对齐 |
| Entry 侧距 | `side_space: 0.2cm`；栏间距 `0.1cm` |
| Entry 间距 | `space_between_regular_entries: 1.2em` |
| Highlight（bullet）缩进 | `space_left: 0.15cm`；bullet↔文本 `0.5em`；bullet 字符 `•` |
| Experience 标题模板 | `**COMPANY**, POSITION` + 右栏 LOCATION/DATE |
| Project（NormalEntry） | `**NAME**` + SUMMARY + HIGHLIGHTS + 右栏 DATE |
| Skills | `OneLineEntry`：`**LABEL:** DETAILS`（分组行，非墙） |
| 技术主题 | `engineeringresumes`：单栏密排（官方称基于 r/EngineeringResumes）；`engineeringclassic`：更多留白 |

**关于「name | tech | dates」：**  
官方 YAML **不**强制管道符字符串。等价结构是：

- **字段拆分**：`name` + `date`（+ highlights 内技术）；或 JSON Resume `projects.name` + `keywords[]` + `startDate`/`endDate`。
- **Experience 行**：`**COMPANY**, POSITION` ‖ 右栏日期。
- 社区常见的视觉「Name | Tech | Date」一行，可用 `NormalEntry.name` 写成 `kv-store | Go, Raft | 2024`，或把 tech 放 `summary`；schema 推荐字段分离以便主题排版。

#### B3. JSON Resume（官方 schema）

来源：`https://raw.githubusercontent.com/jsonresume/resume-schema/master/schema.json`；文档 `https://jsonresume.org/docs/013-schema-definitions`

- **结构契约，不是像素版式**：版式由 theme 的 `render(resume) → HTML` 决定；官方不规定 margin/pt。
- **工作**：`work[]` → name, position, location, startDate, endDate, summary, **highlights[]**（示例即成就句）。
- **项目**：`projects[]` → **name**, description, **highlights[]**, **keywords[]**（技术元素）, startDate, endDate, url, roles。
- **技能**：`skills[]` → **name**（类别）+ **keywords[]**（该组技术）— 天然支持「分组 inline」，主题应渲染为组而非无序墙。
- **basics.summary**：schema 描述为短 2–3 句简介。

实现一页技术简历时：数据按上述字段建模；视觉数字跟 RenderCV 或高校表。

#### B4. Reactive Resume / AltaCV / ModernCV（一级来源能确认的）

- **Reactive Resume**（`amruthpillai/reactive-resume`）：隐私/自托管构建器，PDF/JSON 导出；**官方文档未给出统一 margin/字号数值规范**（版式由模板 UI 决定）。不宜当作数字权威。
- **AltaCV**（`liantze/AltaCV`）：现代双栏，侧栏技能条等；需较新 TeX；**ATS 友好性作者不作保证**。
- **ModernCV**：RenderCV 内置 theme 名之一；经典 LaTeX CV 类。具体 pt 以所用 class/theme 默认为准。
- 一页**技术**向优先：**RenderCV `engineeringresumes` / `engineeringclassic`** + 高校页边距/字号约束。

#### B5. 版式可执行清单（给 skill）

1. 单栏、US Letter、页边距 ≥ **0.5 in**（目标 **0.7 in**）。  
2. 正文 **10–11 pt**；姓名显著更大；section **粗体 + 细线**。  
3. 每条 entry：**左主栏标题，右日期（及地点）**。  
4. Bullet 左缩进小而一致（RenderCV ~0.15cm + 0.5em）。  
5. Skills：**`类别: a, b, c` 多行**，禁止大段无标签关键词墙。  
6. Entry 间保留可见间距（~1.2em）；勿用表格/多栏/文本框若需 ATS（MIT/公开 ATS skills）。  
7. 章节按雇主重要性排序；条目逆时序。  
8. 技术栈：Skills 分组 + bullet 内上下文；可选 bold keywords。

---

### C. 公开 Agent SKILL.md（简历向）

**Anthropic 官方 skills 仓库 / awesome-claude-skills 目录内：未发现以「撰写简历文案」为职责的一级 `SKILL.md`。**  
检索（2026-09-22）：`SKILL.md resume writing site:github.com`；`site:github.com/anthropics … resume SKILL.md`；`awesome-claude-skills resume` — 命中均为第三方仓库或「resume」会话 bug，非 Anthropic 官方写简历 skill。

**存在的一级 raw URL（第三方，可引用）：**

| Path | Trigger description 风格 | 性质 |
|------|--------------------------|------|
| `https://raw.githubusercontent.com/SkillMedev/resume-toolkit/main/skills/resume-writer/SKILL.md` | 单行：`Builds an ATS-optimized resume… Use when someone needs to write or rebuild a resume.` | **文案+ATS docx** |
| `https://raw.githubusercontent.com/vignzpie/resume-agent-skills/main/resume-tailor/SKILL.md` | 长 description：列触发短语（tailor / ATS-optimize / 贴 JD…）；要求先有 `career_profile.md` | **按 JD 裁剪** |
| `https://raw.githubusercontent.com/adedayoagarau/-cv-writer-skill/main/cv-writer/SKILL.md` | 超长 description：列 create/update/ATS/tailor/gaps/formats 等场景 | **全能 CV writer** |
| `https://raw.githubusercontent.com/rendercv/rendercv-skill/master/skills/rendercv/SKILL.md` | `Use when the user wants to create, edit, customize, or render a CV or resume` | **版式/渲染 YAML→PDF**，非文案方法论 |

#### 最可迁移的 5 条规则（跨文案 skills 交集）

1. **先取证再写**：目标职位 + 近 2–3 段经历的 ownership/指标；**不编造数字**。  
2. **Bullet = 动词 + 所做 + 可测结果**；禁用 Responsible for / Helped / Worked on。  
3. **时态**：过去职过去时，当前职现在时；无人称。  
4. **Skills 分组关键词行**；Experience 不写纯技术列表。  
5. **长度**：早期/中级压 **1 页**；每职约 **3–5** 条、**1–2 行**；超页按固定优先级压缩。

（RenderCV skill 额外可迁移：**内容 YAML 与 design 分离**；用 schema 校验；`engineeringresumes` 做密排一页。）

---

## 来源

### 文案与高校版式

1. Harvard FAS Mignone Center — *Harvard College Guide to Creating a Strong Resume*  
   https://careerservices.fas.harvard.edu/resources/create-a-strong-resume/  
   → 语言原则；DON’T/DO；逆时序；平衡留白；禁止叙事与人称。

2. Harvard Griffin GSAS — *Resumes & Cover Letters for Master’s Students*（PDF）  
   https://cdn-careerservices.fas.harvard.edu/wp-content/uploads/sites/161/2025/08/MASTERS-RESUME-COVER-LETTER-GUIDE.pdf  
   → 一页常态；字体 10–12pt；边距 ≥0.75in；避 text box/色/阴影。

3. Harvard Griffin GSAS — PhD Resume & Cover Letter Guide（PDF）  
   https://cdn-careerservices.fas.harvard.edu/wp-content/uploads/sites/161/2024/08/2024-GSAS_phd_resume_cover_letters-1.pdf  
   → 简历 1–2 页；边距 ≥0.5in；字体 10–12pt。

4. MIT CAPD — Resume checklist  
   https://capd.mit.edu/resources/resume-checklist/  
   → 边距 0.5–1.0in；字号 10–12；一页默认；动作动词+时态；量化；无人称；whitespace。

5. MIT CAPD — Resumes（五步）  
   https://capd.mit.edu/resources/resumes/  
   → 按 JD 裁剪；≥0.5in 边距；成就非职责；技术写进描述；项目可纳入。

6. Stanford Career Education — *4 Steps / Developing Your Resume*（PDF）  
   https://careered.stanford.edu/sites/g/files/sbiybj22801/files/media/file/developing_your_resume_handout.pdf  
   → CAR；描述性 section 标题；1–2 页；0.75–1.0in（上下可 0.5）；10–12pt。

7. Stanford Career Education — *CAR Method*（PDF）  
   https://careered.stanford.edu/sites/g/files/sbiybj22801/files/media/file/car-method-for-developing-resume-content.docx-1.pdf  
   → CAR 每 bullet 1–2 句。

8. Stanford GSB — Resumes & Cover Letters  
   https://www.gsb.stanford.edu/alumni/career-resources/job-search/resumes  
   → 6–8 秒扫描；3–4 bullets×≤2 行；边距 ≥0.70；11–12pt；结果前置；左对齐。

9. Laszlo Bock — *How to write a résumé that gets you hired at Google*（原文称先发于 LinkedIn；Quartz 转载署名 Bock）  
   https://qz.com/273818/how-to-write-a-resume-that-gets-you-hired-at-google  
   → **Accomplished [X] as measured by [Y] by doing [Z]**；数值+基线+做法。

10. Google re:Work — 履歴書を審査する  
    https://rework.withgoogle.com/intl/jp/guides/hiring-review-resumes  
    → 审查侧重视可量化影响与完整度。（英文同路径 2026-09-22 返回 404，日文版可用。）

### 开源版式系统

11. RenderCV design 字段  
    https://docs.rendercv.com/user_guide/yaml_input_structure/design/  
    → 0.7in 边距、10pt/30pt/1.4em、highlight 缩进、entry 模板。

12. RenderCV cv 字段 / entry 类型  
    https://docs.rendercv.com/user_guide/yaml_input_structure/cv/  
    → ExperienceEntry / NormalEntry / OneLineEntry。

13. RenderCV — Software Engineer Resume Example（第一方博客，2026-03-15）  
    https://rendercv.com/blog/software-engineer-resume-example  
    → action+tech+result；Skills 分组；`engineeringresumes`；`bold_keywords`。

14. JSON Resume schema（raw）  
    https://raw.githubusercontent.com/jsonresume/resume-schema/master/schema.json  

15. JSON Resume schema 文档  
    https://jsonresume.org/docs/013-schema-definitions  

16. Reactive Resume 仓库说明  
    https://github.com/amruthpillai/reactive-resume  

17. AltaCV README  
    https://github.com/liantze/AltaCV  

### Agent skills（raw）

18. https://raw.githubusercontent.com/SkillMedev/resume-toolkit/main/skills/resume-writer/SKILL.md  
19. https://raw.githubusercontent.com/vignzpie/resume-agent-skills/main/resume-tailor/SKILL.md  
20. https://raw.githubusercontent.com/vignzpie/resume-agent-skills/main/resume-tailor/references/bullet-patterns.md  
21. https://raw.githubusercontent.com/adedayoagarau/-cv-writer-skill/main/cv-writer/SKILL.md  
22. https://raw.githubusercontent.com/rendercv/rendercv-skill/master/skills/rendercv/SKILL.md  

### 检索备忘（官方写简历 skill 未找到）

- WebSearch：`SKILL.md resume writing OR CV writing site:github.com`  
- WebSearch：`awesome-claude-skills resume OR Anthropic skills resume SKILL.md`  
- WebSearch：`site:github.com/anthropics resume SKILL.md`  
→ 无 Anthropic 官方「写简历」SKILL；仅有第三方与 RenderCV 渲染 skill。
