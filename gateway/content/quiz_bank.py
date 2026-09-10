# -*- coding: utf-8 -*-
"""
gateway.content.quiz_bank
学海智导 (Xuehai Zhidao) — 30/30 考点微测验全覆盖题库 (Full Coverage Quiz Bank)

为全图谱 30 个微观经济学知识点提供权威试题库：
包含：
- 原 seed 13 道试题 (保持 Q-K08-01~03, Q-K01-01~02, Q-K02-01~02, Q-K04-01~02, Q-K06-01, Q-K07-01, Q-K09-01, Q-K11-01 100% 兼容)
- 新增补齐其余 22 个知识点 (K03, K05, K10, K12~K30) 的标准高质量微观经济学单选题
- 满足每个考点至少 1~3 道标准试题，标准答案、详尽解析与难度标注
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class QuizOption(BaseModel):
    key: str = Field(..., description="选项标识，如 A, B, C, D")
    text: str = Field(..., description="选项描述")


class QuizQuestionPublic(BaseModel):
    question_id: str
    knowledge_id: str
    stem: str
    options: List[QuizOption]
    difficulty: int


class QuizQuestionInternal(QuizQuestionPublic):
    answer: str
    explanation: str


# 30/30 考点完整内部题目库
ALL_QUIZ_QUESTIONS: List[QuizQuestionInternal] = [
    # ------------------ K01 (2题 - 种子兼容) ------------------
    QuizQuestionInternal(
        question_id="Q-K01-01",
        knowledge_id="K01",
        stem="经济学研究的核心出发点与根本事实是：",
        options=[
            QuizOption(key="A", text="政府权力的合理分配"),
            QuizOption(key="B", text="资源的相对稀缺性与人类欲望的无限性"),
            QuizOption(key="C", text="货币的发行量与通货膨胀控制"),
            QuizOption(key="D", text="国际贸易的顺差最大化"),
        ],
        answer="B",
        explanation="稀缺性是经济学的基石。因为相对于人类无限的物质与精神欲望，满足欲望的经济资源总是有限的，这才迫使人类必须做出最优配置选择。",
        difficulty=1,
    ),
    QuizQuestionInternal(
        question_id="Q-K01-02",
        knowledge_id="K01",
        stem="以下哪一项不属于微观经济学试图回答的社会三大基本问题？",
        options=[
            QuizOption(key="A", text="生产什么 (What)"),
            QuizOption(key="B", text="如何生产 (How)"),
            QuizOption(key="C", text="货币发行总量由谁决定 (Who controls money)"),
            QuizOption(key="D", text="为谁生产 (For whom)"),
        ],
        answer="C",
        explanation="微观经济学社会三大基本问题是：生产什么、如何生产、为谁生产。货币总量与宏观调控属于宏观经济学范畴。",
        difficulty=1,
    ),

    # ------------------ K02 (2题 - 种子兼容) ------------------
    QuizQuestionInternal(
        question_id="Q-K02-01",
        knowledge_id="K02",
        stem="某同学花 2 小时看了一场电影，电影票价 50 元。如果不看电影，他可以在图书馆做兼职家教获得 80 元收入。请问他看这场电影的经济学机会成本是：",
        options=[
            QuizOption(key="A", text="50 元"),
            QuizOption(key="B", text="80 元"),
            QuizOption(key="C", text="130 元"),
            QuizOption(key="D", text="30 元"),
        ],
        answer="C",
        explanation="机会成本包括显性成本与隐性成本。显性支出为门票 50 元，隐性代价为放弃的兼职收入 80 元，因此总机会成本为 50 + 80 = 130 元。",
        difficulty=1,
    ),
    QuizQuestionInternal(
        question_id="Q-K02-02",
        knowledge_id="K02",
        stem="生产可能性边界（PPF）向外凸出（凹向原点）反映了什么经济规律？",
        options=[
            QuizOption(key="A", text="边际效用递减规律"),
            QuizOption(key="B", text="机会成本递增规律"),
            QuizOption(key="C", text="规模报酬递减规律"),
            QuizOption(key="D", text="技术进步规律"),
        ],
        answer="B",
        explanation="生产可能性边界凹向原点（向外凸出），是因为随着一种产品产量的持续增加，转移生产该产品所需的要素专用性变弱，牺牲另一种产品的数量越来越多，即机会成本递增。",
        difficulty=1,
    ),

    # ------------------ K03 (新增 - 补齐) ------------------
    QuizQuestionInternal(
        question_id="Q-K03-01",
        knowledge_id="K03",
        stem="某工厂生产第 101 件商品增加的成本为 15 元，出售这件商品可获得 18 元收入。根据理性人边际分析原则，该工厂应该：",
        options=[
            QuizOption(key="A", text="停止生产，因为总成本已经很高"),
            QuizOption(key="B", text="生产这第 101 件商品，因为边际收益(18)大于边际成本(15)"),
            QuizOption(key="C", text="保持原产量不变，因为边际成本大于零"),
            QuizOption(key="D", text="取决于之前的平均利润是否为正"),
        ],
        answer="B",
        explanation="理性经济人做决策看边际。只要边际收益(MR=18)大于边际成本(MC=15)，生产增量就能为企业带来正向的边际利润(3元)，因此应当生产。",
        difficulty=1,
    ),

    # ------------------ K04 (2题 - 种子兼容) ------------------
    QuizQuestionInternal(
        question_id="Q-K04-01",
        knowledge_id="K04",
        stem="需求定理指出，在其他条件不变的情况下，某种商品的价格上升会导致该商品的：",
        options=[
            QuizOption(key="A", text="需求增加"),
            QuizOption(key="B", text="需求量减少"),
            QuizOption(key="C", text="需求减少"),
            QuizOption(key="D", text="需求量增加"),
        ],
        answer="B",
        explanation="自身价格变动引起的是‘需求量的变动’，价格上升导致需求量减少，在图像上表现为点沿同一条需求曲线向上移动。",
        difficulty=1,
    ),
    QuizQuestionInternal(
        question_id="Q-K04-02",
        knowledge_id="K04",
        stem="以下哪种情况会导致某正常商品的需求曲线向右平移（需求增加）？",
        options=[
            QuizOption(key="A", text="该商品自身价格大幅下降"),
            QuizOption(key="B", text="消费者的收入水平显著上升"),
            QuizOption(key="C", text="生产该商品的原材料成本上升"),
            QuizOption(key="D", text="该商品的替代品价格大幅下降"),
        ],
        answer="B",
        explanation="对于正常商品，消费者收入提高会促使任意价格水平下的购买意愿和能力增强，需求曲线整体向右平移。A是线上点移动，C影响供给曲线，D使替代品更有吸引力导致本品需求左移。",
        difficulty=1,
    ),

    # ------------------ K05 (新增 - 补齐) ------------------
    QuizQuestionInternal(
        question_id="Q-K05-01",
        knowledge_id="K05",
        stem="当某制造行业的生产技术发生重大突破、关键零配件成本下降时，该商品的供给曲线将：",
        options=[
            QuizOption(key="A", text="向左上方平移（供给减少）"),
            QuizOption(key="B", text="向右下方平移（供给增加）"),
            QuizOption(key="C", text="保持不动，仅在曲线上向右上方移动"),
            QuizOption(key="D", text="变得更加陡峭"),
        ],
        answer="B",
        explanation="生产技术进步和原料成本下降使得厂商在每一个价格水平上都愿意提供更多产品，供给曲线整体向右（或称向下）平移。",
        difficulty=1,
    ),

    # ------------------ K06 (1题 - 种子兼容) ------------------
    QuizQuestionInternal(
        question_id="Q-K06-01",
        knowledge_id="K06",
        stem="当某种商品的市场实际价格高于均衡价格时，市场上会出现什么状态，并通过什么机制使价格回归？",
        options=[
            QuizOption(key="A", text="供不应求（短缺），买方竞价促使价格上涨"),
            QuizOption(key="B", text="供过于求（过剩），卖方竞相降价促使价格回落"),
            QuizOption(key="C", text="市场自发静止，价格永久锁定在当前高位"),
            QuizOption(key="D", text="供给量小于需求量，政府必须出面限价"),
        ],
        answer="B",
        explanation="价格高于均衡价格时，高价抑制需求并刺激供给，出现供过于求（过剩）。卖方为了去库存而降价竞争，推动价格逐步回落至均衡价格。",
        difficulty=1,
    ),

    # ------------------ K07 (1题 - 种子兼容) ------------------
    QuizQuestionInternal(
        question_id="Q-K07-01",
        knowledge_id="K07",
        stem="当某商品的需求增加（需求曲线右移），同时该商品的供给也增加（供给曲线右移）时，关于新均衡的判断正确的是：",
        options=[
            QuizOption(key="A", text="均衡价格必然上升，均衡数量必然增加"),
            QuizOption(key="B", text="均衡价格必然下降，均衡数量必然减少"),
            QuizOption(key="C", text="均衡数量必然增加，均衡价格的变动方向无法确定"),
            QuizOption(key="D", text="均衡价格与均衡数量的变动方向均无法确定"),
        ],
        answer="C",
        explanation="需求右移使价升量增，供给右移使价降量增。两者在数量方向上同向叠加（数量必然增加），在价格方向上一升一降相互抵消，最终价格取决于二者相对移动幅度。",
        difficulty=2,
    ),

    # ------------------ K08 (3题 - 种子兼容) ------------------
    QuizQuestionInternal(
        question_id="Q-K08-01",
        knowledge_id="K08",
        stem="当某商品的需求价格弹性绝对值大于 1 时，降价会导致该商品厂商的总收益如何变化？",
        options=[
            QuizOption(key="A", text="总收益增加"),
            QuizOption(key="B", text="总收益减少"),
            QuizOption(key="C", text="总收益不变"),
            QuizOption(key="D", text="无法确定，取决于成本变化"),
        ],
        answer="A",
        explanation="需求富有弹性(|Ed|>1)时，价格下降引起的需求量增加百分比大于价格下降百分比，因此薄利多销使总收益(TR=P*Q)增加。",
        difficulty=2,
    ),
    QuizQuestionInternal(
        question_id="Q-K08-02",
        knowledge_id="K08",
        stem="某商品价格从 10 元降至 8 元，需求量从 100 件增加到 140 件。根据中点法（弧弹性公式），其需求价格弹性约为：",
        options=[
            QuizOption(key="A", text="-0.50"),
            QuizOption(key="B", text="-1.00"),
            QuizOption(key="C", text="-1.50"),
            QuizOption(key="D", text="-2.00"),
        ],
        answer="C",
        explanation="ΔQ/(Q平) = 40/120 = 1/3 ≈ 0.333；ΔP/(P平) = -2/9 ≈ -0.222；Ed = (1/3) / (-2/9) = -1.50。",
        difficulty=2,
    ),
    QuizQuestionInternal(
        question_id="Q-K08-03",
        knowledge_id="K08",
        stem="以下哪项通常会导致某商品的需求价格弹性更高？",
        options=[
            QuizOption(key="A", text="该商品是生活必需品"),
            QuizOption(key="B", text="该商品的支出占消费者预算比例极小"),
            QuizOption(key="C", text="消费者考察该商品的时间非常短促"),
            QuizOption(key="D", text="该商品拥有众多且容易获取的相近替代品"),
        ],
        answer="D",
        explanation="替代品越多、越容易获得，消费者对价格变动越敏感，一旦涨价可以迅速转购替代品，因此弹性更高。",
        difficulty=2,
    ),

    # ------------------ K09 (1题 - 种子兼容) ------------------
    QuizQuestionInternal(
        question_id="Q-K09-01",
        knowledge_id="K09",
        stem="如果商品 X 与商品 Y 的需求交叉价格弹性 Exy 为负值（Exy < 0），则说明这两种商品是：",
        options=[
            QuizOption(key="A", text="互补品"),
            QuizOption(key="B", text="替代品"),
            QuizOption(key="C", text="独立无关品"),
            QuizOption(key="D", text="劣等品"),
        ],
        answer="A",
        explanation="Exy < 0 意味着 Y 价格上涨时 X 的需求量下降，说明二者必须配合使用（如咖啡与伴侣、汽车与汽油），属于互补品。",
        difficulty=2,
    ),

    # ------------------ K10 (新增 - 补齐) ------------------
    QuizQuestionInternal(
        question_id="Q-K10-01",
        knowledge_id="K10",
        stem="关于生产周期与供给价格弹性的关系，以下表述最准确的是：",
        options=[
            QuizOption(key="A", text="在极短期内，供给量无法迅速调整，供给价格弹性往往接近于零"),
            QuizOption(key="B", text="时间周期越长，厂商越难调整要素，长期供给弹性小于短期供给弹性"),
            QuizOption(key="C", text="容易储存的商品通常供给弹性比不易储存的商品更低"),
            QuizOption(key="D", text="任何商品的供给弹性在长短期中都是固定不变的"),
        ],
        answer="A",
        explanation="极短期（瞬时）内由于生产要素和设备完全固定，产出无法增加，供给曲线呈垂直线状态，供给价格弹性接近于0。而在长期中所有要素皆可调整，长期供给弹性显著大于短期。",
        difficulty=2,
    ),

    # ------------------ K11 (1题 - 种子兼容) ------------------
    QuizQuestionInternal(
        question_id="Q-K11-01",
        knowledge_id="K11",
        stem="当政府对某商品征收从量税时，税收归宿（Tax Incidence）主要取决于供求双方的相对价格弹性。以下说法正确的是：",
        options=[
            QuizOption(key="A", text="法定向谁征税，税负就全部由谁承担"),
            QuizOption(key="B", text="相对更缺乏弹性的一方将承担更大部分的税负"),
            QuizOption(key="C", text="相对更富有弹性的一方将承担更大部分的税负"),
            QuizOption(key="D", text="买卖双方永远平摊税收"),
        ],
        answer="B",
        explanation="税负分担遵循弹性反比法则：谁的选择余地小（缺乏弹性、难以避税或无法寻找替代），谁就只能忍受不利价格，从而承担更多税负。",
        difficulty=3,
    ),

    # ------------------ K12 (新增 - 补齐) ------------------
    QuizQuestionInternal(
        question_id="Q-K12-01",
        knowledge_id="K12",
        stem="当消费者连续消费某一种商品时，若该商品的边际效用(MU)大于零但持续下降，则消费者的总效用(TU)将：",
        options=[
            QuizOption(key="A", text="持续递减"),
            QuizOption(key="B", text="保持不变"),
            QuizOption(key="C", text="以递减的速度持续增加"),
            QuizOption(key="D", text="立即降为零"),
        ],
        answer="C",
        explanation="根据导数关系，边际效用等于总效用的斜率(MU = dTU/dQ)。当 MU > 0 时总效用在增加；MU 递减意味着总效用以递减的速率增加，直到 MU = 0 时总效用达到峰值。",
        difficulty=1,
    ),

    # ------------------ K13 (新增 - 补齐) ------------------
    QuizQuestionInternal(
        question_id="Q-K13-01",
        knowledge_id="K13",
        stem="在标准消费者理论中，同一消费者的任意两条无差异曲线之所以绝不能相交，是因为如果相交将违背：",
        options=[
            QuizOption(key="A", text="边际报酬递减规律"),
            QuizOption(key="B", text="偏好的传递性公理"),
            QuizOption(key="C", text="货币中性假说"),
            QuizOption(key="D", text="边际成本递增原则"),
        ],
        answer="B",
        explanation="若两条代表不同满足程度的无差异曲线相交于点A，则根据曲线定义点A既有效用U1又有效用U2，这将导致同一个商品组合带来不同效用水平的逻辑矛盾，违背了偏好的一致性与传递性公理。",
        difficulty=2,
    ),

    # ------------------ K14 (新增 - 补齐) ------------------
    QuizQuestionInternal(
        question_id="Q-K14-01",
        knowledge_id="K14",
        stem="已知商品 X 的价格为 10 元，商品 Y 的价格为 5 元。在以 X 为横轴、Y 为纵轴的平面坐标系中，消费者预算约束线的斜率为：",
        options=[
            QuizOption(key="A", text="-0.5"),
            QuizOption(key="B", text="-2.0"),
            QuizOption(key="C", text="-10.0"),
            QuizOption(key="D", text="+2.0"),
        ],
        answer="B",
        explanation="预算约束线方程为 Px*X + Py*Y = I，整理可得 Y = I/Py - (Px/Py)*X。其斜率为 -Px/Py = -10/5 = -2.0。",
        difficulty=2,
    ),

    # ------------------ K15 (新增 - 补齐) ------------------
    QuizQuestionInternal(
        question_id="Q-K15-01",
        knowledge_id="K15",
        stem="消费者实现效用最大化的均衡条件可以表述为：无差异曲线与预算约束线相切。其数学条件是：",
        options=[
            QuizOption(key="A", text="MRS_xy = Px / Py (即 MUx / Px = MUy / Py)"),
            QuizOption(key="B", text="MRS_xy = Py / Px"),
            QuizOption(key="C", text="MUx * Px = MUy * Py"),
            QuizOption(key="D", text="MUx = MUy 且 Px = Py"),
        ],
        answer="A",
        explanation="相切意味着无差异曲线的斜率绝对值(MRS_xy = MUx/MUy)等于预算线的斜率绝对值(Px/Py)。移项即得 MUx/Px = MUy/Py，意为花在每种商品上的最后一元钱带来的边际效用均等。",
        difficulty=3,
    ),

    # ------------------ K16 (新增 - 补齐) ------------------
    QuizQuestionInternal(
        question_id="Q-K16-01",
        knowledge_id="K16",
        stem="某种商品价格下降时，消费者因该商品相对变得便宜而增加购买，这被称为：",
        options=[
            QuizOption(key="A", text="收入效应"),
            QuizOption(key="B", text="替代效应"),
            QuizOption(key="C", text="吉芬效应"),
            QuizOption(key="D", text="外部效应"),
        ],
        answer="B",
        explanation="商品价格变动引起的总效应可分解为替代效应与收入效应。仅因相对价格变化而促使消费者用相对便宜商品替代昂贵商品的效应，称为替代效应。",
        difficulty=3,
    ),

    # ------------------ K17 (新增 - 补齐) ------------------
    QuizQuestionInternal(
        question_id="Q-K17-01",
        knowledge_id="K17",
        stem="根据短期生产函数中的边际报酬递减规律，当劳动的边际产量(MPL)小于劳动的平均产量(APL)时，平均产量(APL)必定：",
        options=[
            QuizOption(key="A", text="处于递增阶段"),
            QuizOption(key="B", text="处于递减阶段"),
            QuizOption(key="C", text="处于最高点并保持恒定"),
            QuizOption(key="D", text="等于零"),
        ],
        answer="B",
        explanation="边际量与平均量的必然数学关系：当边际值小于平均值(MP < AP)时，新加入的产出会拉低原来的平均水平，导致平均产量下降；当 MP > AP 时，AP 上升；当 MP = AP 时，AP 达到最大值。",
        difficulty=2,
    ),

    # ------------------ K18 (新增 - 补齐) ------------------
    QuizQuestionInternal(
        question_id="Q-K18-01",
        knowledge_id="K18",
        stem="在经济学中区分生产与成本‘短期’与‘长期’的根本准则是：",
        options=[
            QuizOption(key="A", text="经营时间是否超过 1 个自然年"),
            QuizOption(key="B", text="是否所有生产要素的投入量都可以自由调整"),
            QuizOption(key="C", text="企业的总收益是否超过了会计成本"),
            QuizOption(key="D", text="是否引入了自动化计算机软件"),
        ],
        answer="B",
        explanation="微观经济学划分长短期的唯一标准是要素的可变性：若存在至少一种固定生产要素为短期；若所有投入要素（包括厂房、设备、土地等）均可调整，则为长期。",
        difficulty=2,
    ),

    # ------------------ K19 (新增 - 补齐) ------------------
    QuizQuestionInternal(
        question_id="Q-K19-01",
        knowledge_id="K19",
        stem="等产量曲线凸向原点（向外凸）反映了以下哪项经济学原理？",
        options=[
            QuizOption(key="A", text="边际技术替代率(MRTS)递减规律"),
            QuizOption(key="B", text="规模报酬递减规律"),
            QuizOption(key="C", text="机会成本不变假设"),
            QuizOption(key="D", text="要素价格均等化理论"),
        ],
        answer="A",
        explanation="等产量曲线向右下方倾斜且凸向原点，其几何斜率是边际技术替代率(MRTS_LK = MPL/MPK)。凸向原点表明随着劳动力连续增加，每增加一单位劳动所能替代的资本数量逐步减少，即 MRTS 递减。",
        difficulty=2,
    ),

    # ------------------ K20 (新增 - 补齐) ------------------
    QuizQuestionInternal(
        question_id="Q-K20-01",
        knowledge_id="K20",
        stem="某企业的生产函数为 Q = 2 * L^0.6 * K^0.7。当劳动力 L 和资本 K 同时增加 100% 时，该企业的产出 Q 将：",
        options=[
            QuizOption(key="A", text="增加恰好 100%（规模报酬不变）"),
            QuizOption(key="B", text="增加少于 100%（规模报酬递减）"),
            QuizOption(key="C", text="增加超过 100%（规模报酬递增）"),
            QuizOption(key="D", text="保持不变"),
        ],
        answer="C",
        explanation="对于柯布-道格拉斯生产函数 Q = A * L^α * K^β，规模报酬取决于指数之和 α + β。此处 0.6 + 0.7 = 1.3 > 1，属于规模报酬递增(IRS)，要素翻倍产出将增加超过 100% (2^1.3 ≈ 2.46倍)。",
        difficulty=3,
    ),

    # ------------------ K21 (新增 - 补齐) ------------------
    QuizQuestionInternal(
        question_id="Q-K21-01",
        knowledge_id="K21",
        stem="在短期生产中，随着产量 Q 的不断扩大，平均固定成本(AFC)将呈现什么变化趋势？",
        options=[
            QuizOption(key="A", text="先降后升呈现 U 形"),
            QuizOption(key="B", text="持续单调下降并无限趋近于零"),
            QuizOption(key="C", text="保持水平恒定不变"),
            QuizOption(key="D", text="持续单调上升"),
        ],
        answer="B",
        explanation="平均固定成本 AFC = FC / Q。由于固定成本 FC 恒定不变，随着产量 Q 持续增大，AFC 必单调递减并逐渐趋近于零，几何上表现为等轴双曲线的一支。",
        difficulty=2,
    ),

    # ------------------ K22 (新增 - 补齐) ------------------
    QuizQuestionInternal(
        question_id="Q-K22-01",
        knowledge_id="K22",
        stem="长期平均成本(LAC)曲线呈先下降后上升的平缓‘U’形，其背后的主要经济学原因是：",
        options=[
            QuizOption(key="A", text="短期的边际报酬递减规律"),
            QuizOption(key="B", text="企业由规模经济逐步转向规模不经济"),
            QuizOption(key="C", text="通货膨胀导致原材料价格上涨"),
            QuizOption(key="D", text="政府税率由低到高递增"),
        ],
        answer="B",
        explanation="短期成本曲线的 U 形源于边际报酬递减；而长期中所有要素皆可变，LAC 的 U 形由规模经济（初期分工协作均摊成本）与规模不经济（后期管理协调沟通成本膨胀）所决定。",
        difficulty=3,
    ),

    # ------------------ K23 (新增 - 补齐) ------------------
    QuizQuestionInternal(
        question_id="Q-K23-01",
        knowledge_id="K23",
        stem="某创业者年营业总收入为 80 万元，实际支付员工工资与原材料等显性成本 50 万元。如果他不创业，去知名企业工作可获得年薪 20 万元，将其自有店铺出租可得租金 15 万元。该创业者的‘经济利润’为：",
        options=[
            QuizOption(key="A", text="+30 万元"),
            QuizOption(key="B", text="+10 万元"),
            QuizOption(key="C", text="-5 万元"),
            QuizOption(key="D", text="+15 万元"),
        ],
        answer="C",
        explanation="会计利润 = 80 - 50 = 30 万元。隐性成本 = 放弃年薪 20 万 + 放弃租金 15 万 = 35 万元。经济利润 = 会计利润 - 隐性成本 = 30 - 35 = -5 万元（实际处于经济亏损状态）。",
        difficulty=1,
    ),

    # ------------------ K24 (新增 - 补齐) ------------------
    QuizQuestionInternal(
        question_id="Q-K24-01",
        knowledge_id="K24",
        stem="边际成本曲线(MC)与平均总成本曲线(ATC)在几何图形上的关键交点位置是：",
        options=[
            QuizOption(key="A", text="MC 曲线穿过 ATC 曲线的最高点"),
            QuizOption(key="B", text="MC 曲线在其自身的最低点与 ATC 相交"),
            QuizOption(key="C", text="MC 曲线穿过 ATC 曲线的最低点（有效规模点）"),
            QuizOption(key="D", text="两条曲线在横轴交割"),
        ],
        answer="C",
        explanation="当 MC < ATC 时 ATC 下降，当 MC > ATC 时 ATC 上升。因此，上升中的 MC 曲线必定在 ATC 曲线的最低点将其穿透，该最低点即企业的有效规模产出点。",
        difficulty=2,
    ),

    # ------------------ K25 (新增 - 补齐) ------------------
    QuizQuestionInternal(
        question_id="Q-K25-01",
        knowledge_id="K25",
        stem="在完全竞争市场中，个别厂商所面临的需求曲线形状是：",
        options=[
            QuizOption(key="A", text="一条向右下方倾斜的平缓曲线"),
            QuizOption(key="B", text="一条垂直于横轴的竖线"),
            QuizOption(key="C", text="一条由市场价格决定的水平直线 (P = MR = AR)"),
            QuizOption(key="D", text="一条向右上方倾斜的折弯线"),
        ],
        answer="C",
        explanation="完全竞争市场上厂商数量极多且产品同质，单个厂商是价格接受者(Price Taker)，无法改变市场价格，因此其面临的需求曲线是一条等于市场均衡价格的水平线，满足 P = AR = MR。",
        difficulty=2,
    ),

    # ------------------ K26 (新增 - 补齐) ------------------
    QuizQuestionInternal(
        question_id="Q-K26-01",
        knowledge_id="K26",
        stem="垄断厂商在追求利润最大化时遵循 MR = MC 原则，此时其销售价格 P 与边际成本 MC 的关系通常是：",
        options=[
            QuizOption(key="A", text="P = MC"),
            QuizOption(key="B", text="P > MC，从而导致社会福利出现无谓损失(Deadweight Loss)"),
            QuizOption(key="C", text="P < MC"),
            QuizOption(key="D", text="P 恒等于零"),
        ],
        answer="B",
        explanation="垄断厂商面临向下倾斜的需求曲线，边际收益始终小于价格(MR < P)。当其在 MR = MC 处确定产量时，按需求曲线索取的售价必满足 P > MC，这种加价造成资源配置扭曲并产生社会福利无谓损失。",
        difficulty=3,
    ),

    # ------------------ K27 (新增 - 补齐) ------------------
    QuizQuestionInternal(
        question_id="Q-K27-01",
        knowledge_id="K27",
        stem="垄断竞争市场（如服装、餐饮）与完全竞争市场的最本质区别在于：",
        options=[
            QuizOption(key="A", text="厂商数量的多寡"),
            QuizOption(key="B", text="是否存在行业进出壁垒"),
            QuizOption(key="C", text="各厂商生产的产品是否存在差异化(Product Differentiation)"),
            QuizOption(key="D", text="厂商是否追求利润最大化"),
        ],
        answer="C",
        explanation="垄断竞争和完全竞争一样拥有众多买卖双方且自由进出无壁垒，但完全竞争产品完全同质，而垄断竞争的核心特征是‘产品存在差异化’（品质、包装、品牌形象等不同），赋予厂商局部垄断定价权。",
        difficulty=2,
    ),

    # ------------------ K28 (新增 - 补齐) ------------------
    QuizQuestionInternal(
        question_id="Q-K28-01",
        knowledge_id="K28",
        stem="寡头市场最核心、最鲜明的运行特征是：",
        options=[
            QuizOption(key="A", text="厂商之间在决策上具有高度的相互依存性(Interdependence)"),
            QuizOption(key="B", text="行业内厂商数量极其庞大"),
            QuizOption(key="C", text="产品完全没有任何替代品"),
            QuizOption(key="D", text="不存在任何竞争行为"),
        ],
        answer="A",
        explanation="寡头市场由少数几家大企业主导。任何一家企业的价格、广告或产量决策都会直接影响竞争对手的利润并招致对方的反制行动，因此厂商之间存在高度战略博弈与相互依存性。",
        difficulty=3,
    ),

    # ------------------ K29 (新增 - 补齐) ------------------
    QuizQuestionInternal(
        question_id="Q-K29-01",
        knowledge_id="K29",
        stem="国防、灯塔、基础科学研究等属于纯公共物品，纯公共物品具有的两大根本特征是：",
        options=[
            QuizOption(key="A", text="排他性与竞争性"),
            QuizOption(key="B", text="非排他性与非竞争性"),
            QuizOption(key="C", text="非排他性与竞争性"),
            QuizOption(key="D", text="高昂成本与低效用"),
        ],
        answer="B",
        explanation="纯公共物品既无法排除任何人使用（非排他性），多一个人使用也不会减少其他人的享用量（非竞争性，边际成本为0）。这两大特性容易引发搭便车困境，市场自发供给不足，需政府出资提供。",
        difficulty=2,
    ),

    # ------------------ K30 (新增 - 补齐) ------------------
    QuizQuestionInternal(
        question_id="Q-K30-01",
        knowledge_id="K30",
        stem="在二手车交易或保险合同签订之前，由于买方无法确切了解车辆车况或投保人身体真实健康状况而导致的‘劣质品驱逐优质品’现象属于：",
        options=[
            QuizOption(key="A", text="道德风险 (Moral Hazard)"),
            QuizOption(key="B", text="逆向选择 (Adverse Selection)"),
            QuizOption(key="C", text="外部经济"),
            QuizOption(key="D", text="沉没成本"),
        ],
        answer="B",
        explanation="逆向选择发生在交易达成之前，因信息不对称（卖方知车况或投保人知健康）导致劣币驱逐良币；而道德风险发生在交易达成之后，代理人因有保险庇护而改变谨慎行为。",
        difficulty=3,
    ),
]


def get_quiz_questions_by_knowledge_id(knowledge_id: str) -> List[QuizQuestionInternal]:
    """获取指定考点的所有内部测验题目"""
    return [q for q in ALL_QUIZ_QUESTIONS if q.knowledge_id == knowledge_id]


def get_public_questions_by_knowledge_id(knowledge_id: str) -> List[QuizQuestionPublic]:
    """获取指定考点的脱敏公开试题（不含正确答案与详解）"""
    return [
        QuizQuestionPublic(
            question_id=q.question_id,
            knowledge_id=q.knowledge_id,
            stem=q.stem,
            options=q.options,
            difficulty=q.difficulty,
        )
        for q in ALL_QUIZ_QUESTIONS
        if q.knowledge_id == knowledge_id
    ]


def get_question_by_id(question_id: str) -> Optional[QuizQuestionInternal]:
    """通过题目编号查找单道题目内部数据"""
    for q in ALL_QUIZ_QUESTIONS:
        if q.question_id == question_id:
            return q
    return None


__all__ = [
    "QuizOption",
    "QuizQuestionPublic",
    "QuizQuestionInternal",
    "ALL_QUIZ_QUESTIONS",
    "get_quiz_questions_by_knowledge_id",
    "get_public_questions_by_knowledge_id",
    "get_question_by_id",
]
