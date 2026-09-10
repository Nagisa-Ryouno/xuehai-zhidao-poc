# -*- coding: utf-8 -*-
"""
gateway.content.concept_cards
学海智导 (Xuehai Zhidao) — 30/30 考点概念微卡知识库 (Concept Micro-Card Repository)

为全图谱 30 个微观经济学知识点提供标准化微学习内容：
包含：
1. 知识点 ID 与名称 (knowledge_id, knowledge_name)
2. 所属章节 (chapter)
3. 一句话理解 (one_line_intuition)
4. 核心概念与关键结论 (core_concept)
5. 典型生活/商业例子 (simple_example)
6. 常见考试易错误区 (common_misconceptions)
7. 学习目标 (learning_objective)
8. 建议阅读时间 (reading_time_seconds)
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ConceptMicroCard(BaseModel):
    knowledge_id: str = Field(..., description="考点ID，如 K01")
    knowledge_name: str = Field(..., description="考点名称")
    chapter: str = Field(..., description="所属章节")
    one_line_intuition: str = Field(..., description="一句话直观理解")
    core_concept: str = Field(..., description="核心概念与关键结论")
    simple_example: str = Field(..., description="生活或商业典型例子")
    common_misconceptions: str = Field(..., description="考试常见易错陷阱")
    learning_objective: str = Field(..., description="掌握目标")
    reading_time_seconds: int = Field(default=45, description="建议速读秒数")


CONCEPT_CARDS: Dict[str, ConceptMicroCard] = {
    "K01": ConceptMicroCard(
        knowledge_id="K01",
        knowledge_name="稀缺性与经济学基本问题",
        chapter="第一章 导论",
        one_line_intuition="人的欲望是无限的，而满足欲望的资源总是有限的，这就产生了选择的必要。",
        core_concept="稀缺性(Scarcity)是经济学研究的基石。因为资源有限，任何社会都必须回答三大基本问题：生产什么(What)、如何生产(How)、为谁生产(For whom)。",
        simple_example="每天只有24小时（有限资源），你选择用来复习微观经济学，就无法同时用来兼职打工或睡懒觉。",
        common_misconceptions="误以为‘稀缺’等于‘贫困’。事实上即使是世界首富，其可支配的时间和精力依然是稀缺的。",
        learning_objective="理解稀缺性的相对性与普遍性，掌握社会资源配置的三大基本问题。",
        reading_time_seconds=45,
    ),
    "K02": ConceptMicroCard(
        knowledge_id="K02",
        knowledge_name="机会成本与生产可能性边界",
        chapter="第一章 导论",
        one_line_intuition="为了得到某种东西所必须放弃的最大价值的其他东西，就是你的机会成本。",
        core_concept="机会成本(Opportunity Cost)是指在面临多项选择时，放弃的最高价值备选方案。生产可能性边界(PPF)表示在现有技术和资源下所能生产的最大产出组合，其向外凸出的形状反映了机会成本递增规律。",
        simple_example="大学毕业你可以选择读研或去大厂工作（年薪20万）。若选择读研，放弃的20万年薪就是读研的一项重要机会成本。",
        common_misconceptions="误将已经发生的‘沉没成本’（不可收回支出）计入机会成本中；或将所有备选方案收益相加而非取‘最大者’。",
        learning_objective="掌握机会成本的准确定义与计算，理解PPF边界上的效率与递增机会成本。",
        reading_time_seconds=50,
    ),
    "K03": ConceptMicroCard(
        knowledge_id="K03",
        knowledge_name="理性人假设与边际分析",
        chapter="第一章 导论",
        one_line_intuition="做决策看增量：只有当追加的收益大于追加的成本时，行动才值得继续。",
        core_concept="经济学基本假设是‘理性经济人’，追求自身效益最大化。核心决策工具是边际分析：比较边际收益(MR)与边际成本(MC)。最优选择处于边际收益等于边际成本(MR = MC)之时。",
        simple_example="你在吃自助餐时，纠结要不要再拿一盘烤肉，此时不需要考虑前面门票花了多少钱，只需考虑‘多吃这一盘带来的快乐’是否大于‘撑肚子的难受程度’。",
        common_misconceptions="误用‘平均值’或‘总量’来决定是否增产或行动，忽视了最优决策必须基于‘增量（边际）’对比。",
        learning_objective="树立边际思维，掌握利用 MR >= MC 进行行为与产出决策的分析方法。",
        reading_time_seconds=45,
    ),
    "K04": ConceptMicroCard(
        knowledge_id="K04",
        knowledge_name="需求定理与需求曲线",
        chapter="第二章 需求与供给",
        one_line_intuition="其他条件不变时，价格越贵买得越少，价格越便宜买得越多。",
        core_concept="需求定理指出：在其他因素保持不变时，商品价格与需求量之间呈反方向变动。需求曲线是一条向右下方倾斜的曲线。需要严格区分‘需求量的变动’（价格变动引起，点在曲线上移动）与‘需求的变动’（偏好/收入变动引起，整条曲线平移）。",
        simple_example="苹果价格从10元/斤降到3元/斤，超市里买苹果的顾客数量和单人购买量显著增加。",
        common_misconceptions="把‘需求变动’和‘需求量变动’混为一谈；考试中因消费者收入上升而使曲线平移，误答成沿曲线移动。",
        learning_objective="掌握需求定理的内涵，熟练区分需求量变动与需求自身变动的图示与成因。",
        reading_time_seconds=50,
    ),
    "K05": ConceptMicroCard(
        knowledge_id="K05",
        knowledge_name="供给定理与供给曲线",
        chapter="第二章 需求与供给",
        one_line_intuition="有利可图才多卖：其他条件不变时，价格越高厂商越愿意提供更多商品。",
        core_concept="供给定理表明：在其他条件不变的情况下，商品价格与供给量呈同方向变动。供给曲线向右上方倾斜。生产成本、技术进步、要素价格变动会促使供给曲线发生左右整体平移。",
        simple_example="咖啡豆市场价格大涨时，种植户会开垦更多土地扩种咖啡豆，厂商也愿意加班加点烘焙供货。",
        common_misconceptions="误以为原料成本下降会使供给曲线上移；实际上成本下降使得相同价格下产量增加，供给曲线向右（下）平移。",
        learning_objective="理解供给定理的正向变动关系，掌握供给曲线上移动与曲线整体平移的区别。",
        reading_time_seconds=45,
    ),
    "K06": ConceptMicroCard(
        knowledge_id="K06",
        knowledge_name="市场均衡与均衡价格",
        chapter="第二章 需求与供给",
        one_line_intuition="供给与需求就像一把剪刀的两面刃，相交处决定了市场价格与成交量。",
        core_concept="当市场需求量等于市场供给量时，市场处于均衡状态。此时的价格为均衡价格(Pe)，数量为均衡数量(Qe)。供过于求会导致降价压力（过剩），供不应求会导致涨价压力（短缺），市场机制自发引导回归均衡。",
        simple_example="演唱会门票原价300元但求购者众多产生短缺，二级市场上门票价格被推高至供需平衡点。",
        common_misconceptions="误以为均衡价格是政府人为设定的‘合理价格’，实质上它是买卖双方自发撮合交易的结果。",
        learning_objective="掌握均衡价格与均衡产量的数学求解与几何交点判定，理解供求失衡时的自发调整机制。",
        reading_time_seconds=45,
    ),
    "K07": ConceptMicroCard(
        knowledge_id="K07",
        knowledge_name="供求变动与均衡分析",
        chapter="第二章 需求与供给",
        one_line_intuition="需求增加价量齐升，供给增加量增价降；双向变动时其中一个量方向必确定，另一个取决于幅度。",
        core_concept="供求变动四项基本法则：需求增加导致均衡价量俱增；需求减少导致均衡价量俱减；供给增加导致均衡价格下降、数量增加；供给减少导致均衡价格上升、数量减少。当供需同时发生变动时，价或量必有一个变动方向是确定的，另一个取决于相对移动幅度。",
        simple_example="新能源汽车技术进步（供给右移）同时国家发放购车补贴（需求右移），两者叠加必然导致交易量大幅增加，而价格是否变化取决于两者谁变动更大。",
        common_misconceptions="面对供求同时变动题目，死记结论导致判断错误，务必在草稿纸上画出双曲线平移对比相对斜率。",
        learning_objective="能够熟练绘制供求双移动坐标图，推导均衡价格与均衡数量的最终变动区间。",
        reading_time_seconds=55,
    ),
    "K08": ConceptMicroCard(
        knowledge_id="K08",
        knowledge_name="需求价格弹性",
        chapter="第三章 弹性",
        one_line_intuition="价格变动1%，需求量会相应变动百分之几？富有弹性的商品降价能多赚钱。",
        core_concept="需求价格弹性(Ed)衡量需求量对价格变动的敏感程度，计算公式为需求量变动百分比除以价格变动百分比。当 |Ed| > 1（富有弹性）时，降价会增加总收益；当 |Ed| < 1（缺乏弹性）时，提价才能增加总收益；当 |Ed| = 1（单位弹性）时，总收益最大。",
        simple_example="普通感冒药属于生活必需品缺乏弹性，降价大家也不会囤药；而奢侈品包包降价促销，销量往往成倍爆发。",
        common_misconceptions="误认为需求曲线斜率就是弹性。斜率是绝对值比率(ΔP/ΔQ)，而弹性是百分比变动比率；直线型需求曲线上各点斜率恒定，但弹性从上到下由无穷大递减为0。",
        learning_objective="熟练掌握点弹性与弧弹性计算公式，深刻领悟弹性与厂商总收益(TR)之间的定量联动关系。",
        reading_time_seconds=60,
    ),
    "K09": ConceptMicroCard(
        knowledge_id="K09",
        knowledge_name="需求收入弹性与交叉弹性",
        chapter="第三章 弹性",
        one_line_intuition="收入增加买更多的叫正常品，越有钱越不买的叫劣等品；交叉弹性正数是替代，负数是互补。",
        core_concept="需求收入弹性(Ey)：大于0为正常品（其中>1为奢侈品，0~1为必需品），小于0为劣等品(低档品)。需求交叉价格弹性(Exy)：大于0表示X与Y为替代品（如可乐与雪碧），小于0表示互补品（如打印机与墨盒），等于0表示无关独立品。",
        simple_example="当大学生月生活费增加时，去高档餐厅就餐次数增加(正常品/奢侈品)，而吃泡面的次数明显减少(劣等品)。",
        common_misconceptions="混淆交叉弹性的正负号含义。必须牢记：替代品同向涨跌(正号)，互补品反向涨跌(负号)。",
        learning_objective="掌握按收入弹性对商品类别的判定，掌握通过交叉弹性正负号识别替代品与互补品。",
        reading_time_seconds=50,
    ),
    "K10": ConceptMicroCard(
        knowledge_id="K10",
        knowledge_name="供给弹性",
        chapter="第三章 弹性",
        one_line_intuition="涨价后工厂能否迅速增产？能迅速扩产的供给弹性高，受限自然周期的弹性低。",
        core_concept="供给价格弹性(Es)衡量供给量对商品价格变动的反应程度。决定供给弹性的首要因素是‘时间周期’：极短期内产量无法调整，供给无弹性(垂直线)；短期内可通过加班或增加原材料扩产，弹性较小；长期中厂房设备均可投资增建，供给富有弹性。",
        simple_example="生鲜海鲜一网打捞上来必须当天卖完，当天供给完全无弹性；而软件产品只需复制一份安装包，供给具有极高弹性。",
        common_misconceptions="误以为易于储存的商品供给弹性低；实际上容易储存的商品在涨价时可迅速调拨库存入市，供给弹性反而更高。",
        learning_objective="理解影响供给弹性的核心因素（生产周期、技术转移难易度、储存成本），熟练判定供给长短期特性。",
        reading_time_seconds=45,
    ),
    "K11": ConceptMicroCard(
        knowledge_id="K11",
        knowledge_name="弹性与税收归宿",
        chapter="第三章 弹性",
        one_line_intuition="谁的选择余地更小（弹性更弱），谁就承担更沉重的税负。",
        core_concept="税收归宿(Tax Incidence)是指税收负担最终落在哪一方头上。税负分担并不取决于税法规定向谁征税，而完全取决于供求双方的相对价格弹性。哪一方更缺乏弹性（难以逃避或寻找替代品），哪一方承担的税负份额就越多；如果需求完全无弹性，消费者承担全部税款。",
        simple_example="对香烟加征消费税，由于烟瘾难戒（消费者需求极度缺乏弹性），烟草公司很容易把税金完全转嫁到售价中由烟民承担。",
        common_misconceptions="误认为政府立法‘对卖家征税’就一定是卖家出钱。在市场机制中价格会调整，税负会在买卖双方间按弹性反比转移。",
        learning_objective="掌握税收归宿与弹性的关系公式：买方负担/卖方负担 = 供给弹性/需求弹性。",
        reading_time_seconds=55,
    ),
    "K12": ConceptMicroCard(
        knowledge_id="K12",
        knowledge_name="效用与边际效用递减",
        chapter="第四章 消费者行为",
        one_line_intuition="同一个汉堡，饥肠辘辘时的第一个带来极大满足，吃到第四个甚至让你痛苦。",
        core_concept="效用是消费者消费商品所获得的心理满足感。边际效用(MU)指每增加一单位商品消费所增加的效用。边际效用递减规律指出：在其他条件不变时，随着商品消费数量的增加，消费者从中获得的边际效用是递减的。总效用达到最大时，边际效用降至零。",
        simple_example="跑完马拉松喝第一杯冰镇可乐时爽快至极(MU极高)，连喝三杯后第4杯只觉得发胀甜腻(MU甚至为负)。",
        common_misconceptions="认为边际效用递减意味着总效用也下降。只要边际效用依然大于0，每多消费一个单位，总效用依然在增加，只是增加的步子变小了。",
        learning_objective="掌握总效用(TU)与边际效用(MU)的数学导数关系，理解递减规律对需求曲线向下倾斜的理论支撑。",
        reading_time_seconds=50,
    ),
    "K13": ConceptMicroCard(
        knowledge_id="K13",
        knowledge_name="无差异曲线",
        chapter="第四章 消费者行为",
        one_line_intuition="把所有能带给你相同快乐程度的商品消费组合连成一条线，就是无差异曲线。",
        core_concept="无差异曲线(Indifference Curve)是表示能给消费者带来同等满足程度的两种商品的不同消费数量组合的曲线。四大特征：1. 离原点越远效用越高；2. 具有负斜率（向右下方倾斜）；3. 任意两条无差异曲线绝不相交；4. 凸向原点（反映边际替代率MRS递减）。",
        simple_example="对你而言，‘2张电影票+1盒爆米花’和‘1张电影票+3盒爆米花’带来的快乐完全一样，这两个点就在同一条无差异曲线上。",
        common_misconceptions="考试常考‘两条无差异曲线为什么不能相交’，如果相交会违背偏好的传递性公理（同一个点既有效用U1又有效用U2）。",
        learning_objective="掌握无差异曲线的四大几何特征及其背后的经济学公理假定。",
        reading_time_seconds=50,
    ),
    "K14": ConceptMicroCard(
        knowledge_id="K14",
        knowledge_name="预算约束线",
        chapter="第四章 消费者行为",
        one_line_intuition="钱包有多鼓，选择面就有多大：收入等于在两种商品上的总支出。",
        core_concept="预算线方程式为 P1*X1 + P2*X2 = I。斜率为 -P1/P2（商品相对价格的相反数）。当消费者收入(I)变动时，预算线发生平行移动；当其中一种商品价格变化时，预算线以另一个截距点为轴心发生旋转。",
        simple_example="你手里只有100元零花钱，奶茶10元/杯，炸鸡20元/份，你买的所有奶茶和炸鸡总费用不能突破100元上限。",
        common_misconceptions="收入增加和两种商品价格同比例下降在几何效果上是一样的，都会促使预算线平行向外平移。",
        learning_objective="能够列出预算方程，准确计算预算线截距与斜率，并分析价格与收入变动时的图示位移。",
        reading_time_seconds=45,
    ),
    "K15": ConceptMicroCard(
        knowledge_id="K15",
        knowledge_name="消费者最优选择",
        chapter="第四章 消费者行为",
        one_line_intuition="好钢用在刀刃上：花在每一种商品上的最后一元钱带来的边际效用必须完全相等。",
        core_concept="消费者效用最大化的切点条件：无差异曲线与预算约束线相切，即边际替代率等于价格比率：MRS_xy = Px / Py，等价于 MUx / Px = MUy / Py。这表明消费者每一块钱花在各商品上获得的边际效用均等。",
        simple_example="如果买苹果每花1元能得5点效用，买橘子每花1元只能得2点效用，理性人就会少买橘子、多买苹果，直到两边每元效用相等。",
        common_misconceptions="误以为最优解是总效用最高的任意组合。最优解必须满足‘花光预算且位于最高无差异曲线上’（切点）。",
        learning_objective="掌握消费者均衡条件的两种数学形式(MRS=Px/Py 及 MUx/Px=MUy/Py)，能够联立方程解出最优商品购买量。",
        reading_time_seconds=55,
    ),
    "K16": ConceptMicroCard(
        knowledge_id="K16",
        knowledge_name="收入效应与替代效应",
        chapter="第四章 消费者行为",
        one_line_intuition="降价使商品相对便宜（替代效应），也让你钱包购买力变大（收入效应）。",
        core_concept="某商品价格下降引起需求总量变动可分解为两部分：1. 替代效应(SE)：由于相对价格变动，放弃昂贵商品转向便宜商品（方向恒与价格反向）；2. 收入效应(IE)：由于实际购买力上升带来的消费量变动。正常品：SE与IE同向叠加；低档品：IE与SE反向削弱；吉芬商品：特殊的劣等品，IE反向极大完全压过SE，导致降价反而少买。",
        simple_example="咖啡降价了：你觉得奶茶贵了转买咖啡（替代效应）；同时你省钱了手头变阔气多喝了一杯咖啡（收入效应）。",
        common_misconceptions="所有吉芬商品都是劣等品，但并不是所有劣等品都是吉芬商品，必须满足‘收入效应的反向拉力大于替代效应’。",
        learning_objective="掌握斯勒茨基(Slutsky)与希克斯(Hicks)效应分解，清晰判断正常品、低档品与吉芬商品的总效应方向。",
        reading_time_seconds=60,
    ),
    "K17": ConceptMicroCard(
        knowledge_id="K17",
        knowledge_name="生产函数与边际报酬递减",
        chapter="第五章 生产者行为",
        one_line_intuition="厨师太多挤在同一个厨房里，再多招一个厨师多炒出的菜甚至不如前面几位。",
        core_concept="短期生产中厂房设备等资本(K)固定，只变动劳动力(L)。边际报酬递减规律(Law of Diminishing Marginal Returns)：当连续等额向固定要素中追加某种可变生产要素时，起初边际产量(MP)上升，但超过某临界点后，追加要素带来的MP必然递减。这是短期成本曲线向上倾斜的技术根源。",
        simple_example="一块固定面积的农田，施用第1包化肥小麦大幅增产，施加到第10包时增产微弱，施加第20包甚至把庄稼烧死。",
        common_misconceptions="边际报酬递减的前提是‘至少有一种生产要素保持固定’（短期），如果是所有要素同比例扩大，讨论的是规模报酬。",
        learning_objective="掌握总产量(TP)、平均产量(AP)与边际产量(MP)的关系曲线，牢记MP穿过AP最高点的规律。",
        reading_time_seconds=50,
    ),
    "K18": ConceptMicroCard(
        knowledge_id="K18",
        knowledge_name="短期生产与长期生产",
        chapter="第五章 生产者行为",
        one_line_intuition="短期内只能靠工人加班（要素部分固定），长期中可以建新厂房买新流水线（要素皆可变）。",
        core_concept="微观经济学中‘短期’与‘长期’的划分不是按日历时间（如3个月或1年），而是依据‘生产要素是否全部可以调整’。短期：存在至少一种固定生产要素(通常为资本K)；长期：所有投入要素都是可变调整的，企业可根据市场自由调整生产规模或退出行业。",
        simple_example="奶茶店今天订单暴增，店长只能让店员加班（短期调整）；若看到长盛不衰，店长决定租赁隔壁店铺扩大面积并多买制冰机（长期调整）。",
        common_misconceptions="误以为一年以上就是长期。若企业建设一座核电站需要10年，在这10年内该规模依然是固定不可随时变动的短期特征。",
        learning_objective="深刻理解经济学长短期的本质划分标准，为后续短期成本与长期成本分析打好基础。",
        reading_time_seconds=45,
    ),
    "K19": ConceptMicroCard(
        knowledge_id="K19",
        knowledge_name="等产量曲线与边际技术替代率",
        chapter="第五章 生产者行为",
        one_line_intuition="不同的人工与机器配比，却能造出数量完全一样的一批货物。",
        core_concept="等产量曲线表示能生产出相同产量的不同生产要素组合轨迹。边际技术替代率(MRTS_LK)是指在产量不变前提下，增加一单位劳动必须减少的资本数量，其值等于要素边际产量之比：MRTS_LK = MPL / MPK。由于要素递减规律，MRTS同样具有递减特征，表现为等产量曲线凸向原点。",
        simple_example="快递分拣中心既可以雇佣100名工人纯手工搬运，也可以雇佣20名工人配合自动分拣传送带，二者每天都能分拣5万件包裹。",
        common_misconceptions="将消费者的边际替代率(MRS)与生产者的边际技术替代率(MRTS)符号或公式混淆，记住MRTS由边际产量比(MPL/MPK)决定。",
        learning_objective="掌握等产量曲线的几何特征，能计算边际技术替代率MRTS并理解其递减原理。",
        reading_time_seconds=50,
    ),
    "K20": ConceptMicroCard(
        knowledge_id="K20",
        knowledge_name="规模报酬",
        chapter="第五章 生产者行为",
        one_line_intuition="当工厂规模、机器和工人都翻一倍，产量是翻了一倍多，还是正好一倍，还是不到一倍？",
        core_concept="规模报酬(Returns to Scale)研究当所有生产要素同比例变动时产量的变动情况。若要素增加λ倍，产量增加大于λ倍，为规模报酬递增(IRS，专业化分工协作)；若等于λ倍，为规模报酬不变(CRS)；若小于λ倍，为规模报酬递减(DRS，大企业管理协调成本激增)。在柯布-道格拉斯生产函数 Q = A * L^α * K^β 中，根据 α+β 与 1 的大小直接判定。",
        simple_example="大型汽车制造厂通过自动化流水线和集团采购降低单车成本（规模报酬递增）；而官僚臃肿跨国集团内部沟通不畅（规模报酬递减）。",
        common_misconceptions="把‘边际报酬’与‘规模报酬’混淆。边际报酬是单一要素变动其他固定；规模报酬是所有要素按相同比例扩大。",
        learning_objective="掌握规模报酬三种形态的数学判定（尤其C-D生产函数指数和），能解释企业内部规模经济成因。",
        reading_time_seconds=50,
    ),
    "K21": ConceptMicroCard(
        knowledge_id="K21",
        knowledge_name="短期成本曲线",
        chapter="第六章 成本理论",
        one_line_intuition="即使一件衣服都不做，房租照交（固定成本）；开工做的衣服越多，布料水电花得越多（可变成本）。",
        core_concept="短期总成本(TC) = 固定成本(FC) + 可变成本(VC)。平均成本(AC) = 平均固定成本(AFC) + 平均可变成本(AVC)。AFC随着产量增加持续趋近于0（双曲线）；而MC、AVC和AC均呈现典型的‘U’形特征，其技术根源完全是要素边际报酬先增后减规律。",
        simple_example="奶茶店每月房租1万元(FC)，不论卖0杯还是1万杯都必须交；每杯奶茶的茶叶牛奶成本是5元(VC)。",
        common_misconceptions="误以为U形成本曲线是因为规模经济；短期成本的U形纯粹由‘边际报酬递减规律’所主导，只有长期成本U形才归因于规模经济。",
        learning_objective="熟练绘制短期7条成本曲线（TC, FC, VC, MC, AC, AVC, AFC）并掌握彼此几何相对位置。",
        reading_time_seconds=55,
    ),
    "K22": ConceptMicroCard(
        knowledge_id="K22",
        knowledge_name="长期成本曲线",
        chapter="第六章 成本理论",
        one_line_intuition="长期平均成本曲线是无数条短期平均成本曲线的‘包络线’，代表各产量下的最优工厂规模选择。",
        core_concept="长期平均成本(LAC)曲线是所有短期平均成本(SAC)曲线的下包络线。在长期内厂商可以根据目标产量挑选最优工厂规模。LAC通常呈平缓的U形，左侧下降阶段反映规模经济(Economies of Scale)，右侧上升阶段反映规模不经济。",
        simple_example="小作坊做蛋糕均摊成本高；换成中央厨房流水线做蛋糕均摊成本大幅下降；但若盲目扩张全国管辖失效，仓储损耗导致成本再度回升。",
        common_misconceptions="误以为LAC必定与每一条SAC的最低点相切。实际上除LAC自身最低点外，相切点均位于SAC最低点的左侧（规模经济时）或右侧（规模不经济时）。",
        learning_objective="理解长期总成本(LTC)与长期平均成本(LAC)的包络线形成机制，掌握规模经济与外在经济的概念。",
        reading_time_seconds=55,
    ),
    "K23": ConceptMicroCard(
        knowledge_id="K23",
        knowledge_name="经济成本与会计成本",
        chapter="第六章 成本理论",
        one_line_intuition="会计只算账面支出的真金白银，经济学还要算你放弃其他机会的隐性代价。",
        core_concept="会计成本仅计算企业经营中的显性成本(Explicit Costs，实际货币支出)。经济成本 = 显性成本 + 隐性成本(Implicit Costs，自有要素放弃的机会成本，如自有房屋房租、自有资金利息、自己的薪水)。经济利润 = 总收益 - 经济成本。当经济利润为0时，企业其实已经赚到了应得的‘正常利润’。",
        simple_example="你辞去年薪15万工作，用自有门面开咖啡馆，一年收入50万，买原料雇人花30万。会计利润为+20万；但扣除放弃的薪水15万和门面潜在租金10万后，经济利润实为 -5万元（亏损）。",
        common_misconceptions="看到‘经济利润为零’就以为企业要破产。经济利润为0意味着企业投资回报恰好达到全行业平均水平（获得全部正常利润）。",
        learning_objective="掌握显性成本与隐性成本区别，能熟练换算会计利润、经济利润与正常利润。",
        reading_time_seconds=50,
    ),
    "K24": ConceptMicroCard(
        knowledge_id="K24",
        knowledge_name="边际成本与平均成本关系",
        chapter="第六章 成本理论",
        one_line_intuition="只要新生身高的平均数被新来的高个子拉高，就说明新来的人（边际）比原来平均水平高。",
        core_concept="边际成本(MC)与平均总成本(ATC)及平均可变成本(AVC)的数学必然规律：当 MC < ATC 时，ATC 处于下降阶段；当 MC > ATC 时，ATC 处于上升阶段；MC 曲线必定穿过 ATC 和 AVC 各自的最低点。ATC最低点被称为企业的‘有效规模’(Efficient Scale)。",
        simple_example="全班平均成绩是80分，下一位交卷同学考了90分（MC=90），全班平均分就被拉高了；下一位考了60分（MC=60），全班平均分就被拉低了。",
        common_misconceptions="误以为MC最低点对应AC最低点。MC通常更早达到最低点，随后在上升过程中去穿透AC的最低点。",
        learning_objective="深刻掌握导数意义下 MC 穿过 AC 和 AVC 最低点的证明与画图规范。",
        reading_time_seconds=45,
    ),
    "K25": ConceptMicroCard(
        knowledge_id="K25",
        knowledge_name="完全竞争市场",
        chapter="第七章 市场结构",
        one_line_intuition="千千万万个小摊贩卖一模一样的标准土豆，没有任何一个人能单方面左右市场价格。",
        core_concept="完全竞争市场具备四大特征：买卖双方极多、产品同质无差别、要素自由进出、信息完全透明。单个厂商是价格接受者(Price Taker)，其面临的需求曲线是水平线：P = AR = MR。短期均衡条件为 MR = MC；停止营业点为 P = min(AVC)；长期均衡时自由进出导致经济利润归零：P = MR = LMC = LAC最低点。",
        simple_example="大宗农产品或金融外汇市场，普通麦农只能按照当天国际期货报价交割小麦，想要标高一分钱就根本没人买。",
        common_misconceptions="只要 P < AC 企业就应该立刻关门？错！在短期内只要 P >= AVC，虽然亏损但继续生产可以补偿一部分固定成本，只有 P < AVC 才关门。",
        learning_objective="掌握完全竞争厂商短期供给曲线由 MC>=AVC 段构成的原理，熟练推导长期零利润均衡状态。",
        reading_time_seconds=60,
    ),
    "K26": ConceptMicroCard(
        knowledge_id="K26",
        knowledge_name="垄断市场",
        chapter="第七章 市场结构",
        one_line_intuition="整个市场只有一家独大，没有相近替代品，想要多卖就得降价，带来效率净损失。",
        core_concept="垄断市场是指市场上仅有一家供应商。垄断厂商面临向右下方倾斜的市场需求曲线，因而其边际收益曲线在需求曲线下方(MR < P)。垄断定价原则仍是 MR = MC，但价格高于边际成本(P > MC)，导致消费者剩余缩水并产生无谓损失(Deadweight Loss)。实行一级/二级/三级价格歧视可攫取消费者剩余。",
        simple_example="在某些没有竞品的自来水公用事业或拥有绝对专利保护的特种创新药市场上，企业拥有极高的自主定价权。",
        common_misconceptions="误以为垄断者可以随心所欲定出‘无限高’的天价。垄断者定价依然受消费者需求曲线严格约束，价格定太高销量就会萎缩，使其总利润下降。",
        learning_objective="掌握垄断厂商的利润最大化求解，理解垄断无谓损失与三类价格歧视机制。",
        reading_time_seconds=55,
    ),
    "K27": ConceptMicroCard(
        knowledge_id="K27",
        knowledge_name="垄断竞争市场",
        chapter="第七章 市场结构",
        one_line_intuition="各家餐厅菜品各有特色（垄断性），但整条街上餐馆多如牛毛自由开张（竞争性）。",
        core_concept="垄断竞争特征：厂商众多、自由进出，但产品存在‘差异化’(Product Differentiation)。由于有差异，每家对自己的产品拥有一定定价权，面临向下倾斜的需求曲线；由于自由进出，长期中超额利润被新进入者瓜分直至 P = LAC（此时依然高于MC最低点，存在过剩生产能力Excess Capacity）。",
        simple_example="学校后街的奶茶店，虽然都有卖奶茶，但每家店配方、包装、品牌形象不同，各自拥有一群忠实拥趸。",
        common_misconceptions="误以为垄断竞争长期能维持超额利润。只要无进出壁垒，新竞争者就会不断模仿挤占市场，使需求曲线左移直至相切归零。",
        learning_objective="掌握垄断竞争的短期超额利润与长期零利润均衡机制，理解品牌差异化与过剩生产能力的经济含义。",
        reading_time_seconds=50,
    ),
    "K28": ConceptMicroCard(
        knowledge_id="K28",
        knowledge_name="寡头市场与博弈论入门",
        chapter="第七章 市场结构",
        one_line_intuition="市场上就我们几个巨头玩游戏，我出什么招，必须严密紧盯对手怎么接招。",
        core_concept="寡头市场(Oligopoly)由少数几家巨头控制市场份额，其最本质特征是‘厂商之间存在极强的相互依赖性(Interdependence)’。常用模型包括古诺模型(Cournot，同时选产量)、斯塔克伯格模型(主导者与跟随者)、折弯需求曲线(涨价不跟降价跟)。博弈论中囚徒困境展示了各方追求个人理性导致的纳什均衡，往往不及合作下的集体最优。",
        simple_example="可口可乐与百事可乐，或者波音与空客。如果一方降价打价格战，另一方必须立即跟进降价以防市场份额被夺走。",
        common_misconceptions="误以为寡头勾结串通成立卡特尔(Cartel)后就能永久稳固高价。由于每家私下增产都有巨大偷吃诱惑，卡特尔组织天然存在不稳定性。",
        learning_objective="理解相互依赖决策机制，掌握古诺模型反应函数联立解法与纳什均衡基本概念。",
        reading_time_seconds=60,
    ),
    "K29": ConceptMicroCard(
        knowledge_id="K29",
        knowledge_name="外部性与公共物品",
        chapter="第八章 市场失灵",
        one_line_intuition="化工厂排污让下游居民得病不用赔（负外部性）；灯塔照亮所有人，没人愿意自觉买单（公共物品）。",
        core_concept="外部性(Externality)是指经济主体的行为对旁人产生了未反映在市价中的影响（负外部性导致市场产量过剩，正外部性导致产量不足）。解决之道包括科斯定理(明确产权与交易)与庇古税。公共物品具备非排他性与非竞争性两大特征，会导致搭便车(Free-rider)困境，纯靠私营市场将供给不足，需政府出资介入。",
        simple_example="接种传染病疫苗使自己免疫的同时切断了传播链保护了周围人（正外部性）；城市路灯谁都能照亮且无法排除不交税的人蹭光（公共物品）。",
        common_misconceptions="以为有收费门槛的高速公路也是纯公共物品。若存在排他手段（设收费站收费），则属于俱乐部物品而非纯公共物品。",
        learning_objective="熟练区分私人物品、公共物品、俱乐部物品和公共资源四象限，掌握矫正外部性的税收与产权机制。",
        reading_time_seconds=55,
    ),
    "K30": ConceptMicroCard(
        knowledge_id="K30",
        knowledge_name="信息不对称",
        chapter="第八章 市场失灵",
        one_line_intuition="买的没有卖的精：买家辨别不出二手车好坏只愿出均价，结果好车全退市只剩烂车（逆向选择）。",
        core_concept="信息不对称导致两大约束：1. 逆向选择(Adverse Selection)：交易发生前因信息隐藏导致的‘劣币驱逐良币’（如二手车柠檬市场、健康保险高风险群体投保）；2. 道德风险(Moral Hazard)：交易发生后由于行为无法完全监督，代理人产生的不负责任行为（如买了全额车险后开车变鲁莽）。对策包括信号传递(学历/质保)与信息甄别。",
        simple_example="二手车市场上买家看不出真实车况，只愿意按照50%好车50%坏车的平均价出价，导致优质好车车主纷纷退出市场，市场上最后全变成事故车破烂车。",
        common_misconceptions="混淆‘逆向选择’和‘道德风险’。关键时间节点：签约交易前发生的是逆向选择；签约交易后行为改变的是道德风险。",
        learning_objective="掌握逆向选择与道德风险的区别，理解市场机制如何通过品牌信誉、质量担保及契约设计缓解信息不对称。",
        reading_time_seconds=55,
    ),
}


def get_concept_card(knowledge_id: str) -> Optional[ConceptMicroCard]:
    """获取指定知识点的概念微卡"""
    return CONCEPT_CARDS.get(knowledge_id)


def get_all_concept_cards() -> List[ConceptMicroCard]:
    """获取全量 30 个考点概念微卡列表"""
    return [CONCEPT_CARDS[k] for k in sorted(CONCEPT_CARDS.keys())]


__all__ = [
    "ConceptMicroCard",
    "CONCEPT_CARDS",
    "get_concept_card",
    "get_all_concept_cards",
]
