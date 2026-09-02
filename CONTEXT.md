# Personal Portfolio

求职向个人作品集站点：先展示「我是谁、做过什么」，再以写作证明深度。公开内容由唯一 Owner 经后台 CMS 维护。壳层 UI 提供繁中 / 简中 / 英文切换。需要多语呈现的内容字段（如品牌名、Hero 文案、Profile、About 模块、Project / Journal / Article 标题与正文）在 CMS 中分别提供 `zh-Hant`、`zh-Hans` 与 `en` 三套输入；Owner 可先写一语，再点「翻译」按字最多的那一语重填另外两语（中文为字形转换，英文为机翻，须核对方可保存）。公开展示时按当前语言取对应原文，该语未填则按 `zh-Hans ↔ zh-Hant ↔ en` 回退。中文之间回退只做繁简字形转换，不机翻、不代写。

## Language

**Profile**:
Owner 的身份面：简介、经历、技能、公开邮箱、头像，以及一排有序外链。头像支持 Owner 上传；访客联系方式以 Links + 公开邮箱为准（无站内私信）。首页身份条与 About 页分工：Profile 是首页摘要，About 是个人详情。
_Avoid_: 咨詢, Consulting

**About**:
公开个人详情页（`/about`），由 Owner 在后台维护的多个模块组成，类似 CV：自我描述、学历、成绩、经历，以及自定义模块。每个模块有标题与 Markdown 正文，支持 Draft / Published。访客从顶栏与侧栏进入。
_Avoid_: 把 About 做成独立「关于我们」公司页；与 Profile 混成同一实体

**Link**:
挂在 Profile 上的外链条目（如 GitHub、电话、WhatsApp、Twitter/X、LinkedIn、简历 PDF），有展示顺序。号码或账号可写成 `tel:` / `wa.me` / 用户名，公开页按类型显示图标。
_Avoid_: Social, bookmark, 链接墙（本站不做独立链接墙页）

**Project**:
一件希望被雇主评估的作品展示。仅当 Owner 在后台显式「加入站点」后才对访客可见。可关联一个 SourceRepo；公开页含 Owner 撰写的描述，以及（若已关联）仿 GitHub 的只读源码浏览。
_Avoid_: Portfolio item, case study（未单独建模前）, 与「GitHub 上有的仓」划等号

**Journal**:
日常向公开写作（短、偏生活/随笔）。与技术深度文分流；不挂 Project。
_Avoid_: 日常（作类型名时）, blog post（统称）

**Article**:
技术或项目向的深度公开写作。可与 Project 可选关联（`relatedProject`，不强制）。可属一个 ArticleCategory，也可没有分类。
_Avoid_: 技术笔记（作类型名时）, post（统称）

**ArticleCategory**:
Owner 维护的 Article 分组，全部可改可删。删除后，原属该分类的 Article 变为无分类。访客在列表筛选；详情页仅轻量标示，列表卡片不展示分类。
_Avoid_: tag（作实体名时）, topic, label, 栏目

**Comment**:
挂在已发布 Journal 或 Article 下的公开回复。访客以昵称 + 邮箱提交（邮箱不公开展示）；默认待审核，Owner Approve 后可见。Owner 可以站点身份回复。Project 不挂评论。
_Avoid_: message, review, 未审核即公开

**Owner**:
唯一可进入后台、修改全部公开内容的人。以邮箱验证码登录（生产用 Resend HTTPS 发信；SMTP 仅作本机备选）；非密码登录。
_Avoid_: Admin（指人时）, user（泛称）

**SourceRepo**:
与某个 Project 绑定的 GitHub 仓库引用。后台可选/浏览 Owner GitHub 上的仓库列表；访客只能通过已加入站点且已发布的 Project 看到对应源码浏览。**Private 仓不对访客提供 tree/blob**（可展示 Owner 描述与指向 GitHub 的链接）。
_Avoid_: clone, mirror（本站不镜像整仓）

**Draft**:
尚未对访客公开的内容状态。Journal / Article / Project 均支持 Draft → Published；Draft 对访客不可见。
_Avoid_: unpublished（作状态名时用 Draft）
