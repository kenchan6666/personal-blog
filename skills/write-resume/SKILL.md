---
name: write-resume
description: Write or rewrite one-page Resume copy. Use when drafting a CV, filling or polishing summary, education, internship, projects, activities, skills, or extras, or the Owner asks to 写履历 / 改简历 / 改 CV bullets.
---

# Write Resume

纸上只印 `header.name`。不要另写一份 title；后台列表名保存时等于姓名。Resume 不是 About。

## Steps

1. `portfolio_list_resumes` 或 `portfolio_get_resume`，看现有栏目和版式。
2. 取证：`portfolio_list_knowledge`，必要时读已发布 Project / About。只写已确认事实。
3. 按下面栏目公式起草，一页为限。
4. `portfolio_update_resume` 只传改动的字段。
5. 同一轮把已确认事实写入「关于我」RAG。Owner 没说发布就不要 `portfolio_publish_resume`。

完成：目标栏目已写入，且没有虚构经历、数字或职称。

## 栏目

每条要点用 **动词 + 内容 + 方法 + 结果**。一行一件事，能量化就量化。

| 栏目 | 字段 | 写什么 |
| --- | --- | --- |
| header | name, phone, email, city | 姓名印在纸顶；联系方式各一行，不写段落 |
| summary | `summary[]` | 2–3 句：身份、方向、最硬的一条证据。不要目标空话 |
| education | institution, field, degree, start, end, city, honor, related_courses | 学校与学位为主；课程只留和投递相关的 |
| internship | organization, role, start, end, city, description[] | 职责用要点，不用「负责日常事务」 |
| projects | name, start, end, tech_stack[], description[] | 做出了什么、用什么、结果是什么；栈放 tech_stack |
| activities | 同实习条目 | 社团/志愿；没有就空着，不要硬凑 |
| skillsOthers | skills[], languages[] | 真用过的技能；语言写程度 |
| extras | title, lines[], entries[] | 证书、奖项等自订段；title 是印在纸上的栏目标题 |

自订栏目用 extras，不要塞进 About。版式先 `portfolio_list_resume_templates`，按投递类型换 `templateSlug`。只有 `classic-a4` 不可改；其余是 `cv` 仓 `template/{slug}.json`，改名或栏目用 `portfolio_update_resume_template`。不要另存一份和 classic-a4 栏目完全相同的版式。
