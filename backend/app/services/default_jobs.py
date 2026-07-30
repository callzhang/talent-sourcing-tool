from __future__ import annotations

from app.schemas import JobCreate


DEFAULT_JOBS: tuple[JobCreate, ...] = (
    JobCreate(
        title="L5 技术总监",
        description=(
            "负责技术部 L5 技术总监岗位，作为懂 AI 的产品技术负责人，既能压住复杂系统和平台架构，"
            "也能把模糊业务需求翻译成可执行的技术路线，并搭建高密度研发团队与工程体系。岗位需要覆盖"
            "后端与平台工程、真实产品架构、AI 工程化落地、研发质量机制、团队建设，以及对产品和商业"
            "的前瞻判断。候选人应能在关键问题上亲自下场做核心代码、验证原型、判断架构与 AI/Agent/"
            "平台化方向，而不是只做传统管理或交付。"
        ),
        region="北京",
        target_profile_text=(
            "技术上能压住场，能判断架构、AI/Agent/平台化方向，并在关键问题上亲自写核心代码或做验证。"
            "能把模糊业务需求转成技术路线，明确先后顺序、边界和验收标准。具备研发体系搭建能力，包括代码"
            "质量、评审、版本、测试、上线、复盘和研发节奏。能够带高密度团队，招到强人、识别低效人员、"
            "让高手服气并培养年轻人。对产品和商业有感觉，能提前 6-12 个月判断底座能力要补什么。"
        ),
        red_flags_text=(
            "纯交付 PM；大厂流程型干部；只会讲架构不动手；只会救火不建系统；只会管理、只会交付、只会"
            "传统后端；只是大型 C 端项目里的边缘参与者而不是复杂系统 owner；只有高并发、性能优化、"
            "业务增长经验但没有 AI 和平台能力。"
        ),
        search_notes=(
            "L5 技术总监; 技术总监 AI; AI 技术负责人; AI 平台负责人; 技术架构负责人; 后端平台架构; "
            "分布式系统; 多租户; CI/CD; 可观测性; Agent; RAG; LLM 落地; AI 工程化; 北京"
        ),
        search_channels=["linkedin", "github", "exa", "brightdata_discover"],
    ),
    JobCreate(
        title="美国市场产品营销与 PMF 探索负责人",
        description=(
            "作为 Friday / PreSeen 首位美国市场产品营销和市场探索成员，负责北美 PMF 探索。该岗位不是传统 "
            "PMM、活动营销或企业销售 GTM 岗位；需要把产品的记忆、智能体和工作空间能力转化为清晰的美国市场 "
            "定位，验证 ICP 和 PMF 切入点，推进设计合作伙伴探索，并把用户证据沉淀为产品决策。"
        ),
        region="San Francisco, CA",
        target_profile_text=(
            "具备优秀的英文产品叙事与定位能力和高质量用户访谈能力；有 0-1 AI/SaaS 或早期产品营销经验；能区分 "
            "礼貌性兴趣与真实使用或付费意愿；深度使用主流 AI 工具；能与工程团队协作，把反馈转化为可验证实验。"
        ),
        red_flags_text=(
            "仅有活动、品牌、公关或企业成交背景；只写文案却无法判断 PMF 的 PMM；只能汇总反馈、没有产品取舍判断；"
            "不深度使用 AI 工具。"
        ),
        search_notes=(
            "founding PMM; product marketing AI; product-led growth AI; PMF; early stage SaaS; user research AI; "
            "growth PM; AI workflow; prosumer SaaS; founder in residence; design partner; 0-1 positioning; ICP discovery"
        ),
        search_channels=["linkedin", "github", "exa", "brightdata_discover"],
    ),
    JobCreate(
        title="AI 产品工程师",
        description=(
            "基于 Friday 核心能力，为北美 PMF 探索构建 AI 原生原型、演示和工作流。该岗位不是纯 AI 工程、纯全栈、"
            "传统售前或只做演示的 vibe coding 岗位；需要听取客户和用户需求，将其转化为可展示的工作流，并判断哪些 "
            "必须成为真实产品能力、哪些可以用模拟方案快速学习。"
        ),
        region="San Francisco, CA",
        target_profile_text=(
            "具备很强的 vibe coding 速度和真实工程基础；有产品感；能向客户讲清演示、确认需求并记录反馈；亲自构建过 "
            "全栈或 AI 应用；理解智能体工作流、连接器、记忆、产物、配方、任务/线程和可复用模板。"
        ),
        red_flags_text=(
            "只有算法或后端面试能力、缺少用户好奇心；只有漂亮演示却没有系统约束意识；只有提示词经验、没有真实工程能力；"
            "只能讲解、不能构建的传统售前工程师。"
        ),
        search_notes=(
            "founding engineer AI; product engineer AI; AI prototyping; agent workflow; full-stack AI; Cursor; "
            "Claude Code; Codex; developer tools; AI app builder; vibe coding"
        ),
        search_channels=["linkedin", "github", "exa", "brightdata_discover"],
    ),
)
