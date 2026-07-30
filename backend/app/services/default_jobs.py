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
        title="Founding PMM / PMF Discovery Lead",
        description=(
            "Own North America PMF discovery for Friday / PreSeen as the first US product marketing and "
            "market discovery hire. This is not a traditional PMM, campaign marketing, or enterprise GTM role. "
            "The role translates the product from memory / agent / workspace language into sharp US market "
            "positioning, validates ICPs and PMF wedges, manages design partner discovery, and turns user evidence "
            "into product decisions."
        ),
        region="San Francisco, CA",
        target_profile_text=(
            "Strong English product narrative and positioning ability; high-quality user interview skill; "
            "0-1 AI/SaaS or early-stage product marketing experience; ability to distinguish polite interest "
            "from real usage or payment intent; deep hands-on usage of mainstream AI tools; able to work with "
            "engineering to turn feedback into testable experiments."
        ),
        red_flags_text=(
            "Traditional campaign-only, brand-only, PR-only, or enterprise closing background; PMM who only "
            "writes copy and cannot judge PMF; candidates who only summarize feedback without product tradeoff "
            "judgment; candidates who do not use AI tools intensively."
        ),
        search_notes=(
            "founding PMM; product marketing AI; product-led growth AI; PMF; early stage SaaS; user research AI; "
            "growth PM; AI workflow; prosumer SaaS; founder in residence; design partner; 0-1 positioning; ICP discovery"
        ),
        search_channels=["linkedin", "github", "exa", "brightdata_discover"],
    ),
    JobCreate(
        title="AI Product Engineer",
        description=(
            "Build AI-native prototypes, demos, and workflows for North America PMF discovery on top of Friday's "
            "core capabilities. This is not a pure AI engineer, pure full-stack engineer, traditional sales "
            "engineer, or demo-only vibe coder role. The role listens to customer/user needs, turns them into "
            "demonstrable workflows, and separates what must be real product capability from what can be mocked "
            "for fast learning."
        ),
        region="San Francisco, CA",
        target_profile_text=(
            "Very strong vibe-coding velocity plus real engineering fundamentals; product sense; customer "
            "communication sufficient to explain demos, confirm requirements, and record feedback; hands-on "
            "full-stack or AI application building; understanding of agent workflows, connectors, memory, "
            "artifacts, recipes, tasks/threads, and reusable templates."
        ),
        red_flags_text=(
            "Only algorithm/backend interview strength with no user curiosity; only beautiful demos with no "
            "system constraints; prompt-only background without real engineering; traditional presales engineer "
            "who can explain but cannot build."
        ),
        search_notes=(
            "founding engineer AI; product engineer AI; AI prototyping; agent workflow; full-stack AI; Cursor; "
            "Claude Code; Codex; developer tools; AI app builder; vibe coding"
        ),
        search_channels=["linkedin", "github", "exa", "brightdata_discover"],
    ),
)
