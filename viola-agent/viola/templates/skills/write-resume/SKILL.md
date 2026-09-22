---
name: write-resume
description: Write or fully rewrite a one-page Resume in XYZ bullets. Use when drafting a CV, polishing one section, or the Owner says 更新一下我的 CV / 更新 CV / 改简历 / 把 CV 改好.
always: true
---

# Write Resume

纸上只印 `header.name`。后台列表名保存时等于姓名。Resume 不是 About。

经历和项目的每一条都是 **XYZ**：做成了 X，用 Y 衡量，靠 Z 做到。Z 是方法，技术名词出现在方法里，不当前半句的主语。一行一条，写入数组。

## 整页

Owner 说「更新一下我的 CV」「更新 CV」「把 CV 改好」，且没有点名单一栏目时，走整页。这句话就是写入授权：同一轮分析并写回，再生成 PDF。

1. `portfolio_list_resumes`，再 `portfolio_get_resume`。只有一份就改那一份。多份时改 `updatedAt` 最近的一份，除非点了姓名或 slug。不先问是哪一份。
2. 同一轮取证：`portfolio_list_knowledge`；`portfolio_list_content` 里已发布的 project 与 about。GitHub 已连接则 `portfolio_list_github_repos`，只对履历里已有的项目读 README。
3. 重写 summary，以及实习、工作、项目、活动里每一条 description。姓名、电话、邮箱、城市、学校、专业、学位、机构、职务、日期、项目名、已有 `tech_stack` 保持原值。日期空着就留空。
4. 一次 `portfolio_update_resume` 提交这些数组，然后 `portfolio_generate_resume`。
5. 同一轮写入「关于我」：`portfolio_list_knowledge`，已有对应条目则 `portfolio_update_knowledge`，没有则 `portfolio_remember_knowledge`。教育用 category `education`，经历用 `experience`，项目用 `project`。内容只取刚写进履历的事实。发布和推仓留到 Owner 另说。

完成：`portfolio_update_resume`、`portfolio_generate_resume` 和知识库写入都已返回。这两次履历调用返回之后，回复才说简历已更新，并只列改过的栏目。每条要点能指回第 2 步的材料。没有数字就保留原文里的范围，百分比留空。

## 单栏

Owner 点了某一个栏目时：

1. `portfolio_get_resume`，看该栏目和版式。
2. 取证同上，只取和该栏目有关的材料。
3. 按栏目公式起草。一页：最近一段 3–5 条，更早的 2–3 条，每个项目 2–4 条。最硬的结果放该段第一条。
4. `portfolio_update_resume` 只传改动的字段，然后 `portfolio_generate_resume`。
5. 同一轮按整页第 5 步写入「关于我」。发布留到 Owner 另说。

完成：该栏目已写入，PDF 已更新，知识库写入已返回。没有虚构经历、数字或职称。

## XYZ

句式：`动词 + 交付物 + 结果或范围 + 方法`。已结束的经历用过去时，仍在做的用现在时。每条 1–2 行。

- 工作：Cut checkout errors 18% by rebuilding the payment retry path in Go.
- 项目：Shipped expiry reminders for a shared pantry, covering milk and produce, with Flask.
- 证据不够写成「Built a pantry tracker in Flask that stores items and expiry dates」——范围来自仓库，百分比留空。

`tech_stack` 只放 3–5 个语言或框架，印在项目标题同一行。要点里只在方法处点名完成该结果的那一项。`skills[]` 是逗号清单，不写句子。

Summary 是 2–3 句：身份、方向、最硬的一条证据。每句是数组的一项。

从 GitHub 加项目用 `portfolio_add_resume_project_from_github`：名称、短技术栈和 XYZ 要点自动填，日期留给 Owner。导入后若要点仍像功能说明，按本页重写再 `portfolio_update_resume`。

## 栏目

| 栏目 | 字段 | 写什么 |
| --- | --- | --- |
| header | name, phone, email, city | 每个联系方式一个短字段 |
| summary | `summary[]` | 2–3 句 |
| education | institution, field, degree, start, end, city, honor, related_courses | 学校与学位；课程只留和投递相关的 |
| internship | organization, role, start, end, city, description[] | XYZ 要点 |
| work | workExperiences[]，字段同实习 | 全职/兼职；与 internships 分开存 |
| projects | name, start, end, tech_stack[], description[] | 标题是作品名；栈在 tech_stack；要点是交付 |
| activities | 同实习 | 社团/志愿；没有就空着 |
| skillsOthers | skills[], languages[] | 真用过的技能；语言写程度 |
| extras | title, lines[], entries[] | 证书、奖项；title 印在纸上 |

版式先 `portfolio_list_resume_templates`，按投递类型换 `templateSlug`。只有 `classic-a4` 不可改；其余是 `cv` 仓 `template/{slug}.json`，改名或栏目用 `portfolio_update_resume_template`。自订栏目用 extras。
