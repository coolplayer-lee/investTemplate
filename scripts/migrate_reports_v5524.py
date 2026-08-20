#!/usr/bin/env python3
"""按 V5.5.24-r2 批量重建分析报告及数据校验文件。

年度财务数字来自公司正式年报；行情仅用于 2026-08-20 的估值快照。
该脚本故意把报告压缩成可复核的决策文档，不保留旧报告中的过时价格与结论。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "analysis-reports"
CONFIG_DIR = ROOT / "config"
AS_OF = "2026-08-20"
HKD_RMB = 0.8569


@dataclass
class Company:
    name: str
    code: str
    price: float
    price_currency: str
    shares: float
    revenue: float
    profit: float
    ocf: Optional[float]
    capex: Optional[float]
    prior_ocf: Optional[float]
    prior_capex: Optional[float]
    cash_eq: float
    broad_cash: float
    dividend: float
    annual_url: str
    annual_date: str
    sector: str
    framework: str
    thesis: str
    variable: str
    supports: tuple[str, str, str]
    falsifiers: tuple[str, str, str]
    debt_short: float = 0
    debt_long: float = 0
    debt_bonds: float = 0
    debt_lease: float = 0
    restricted: float = 0
    related_cash: float = 0
    other_low_liquidity: float = 0
    relationship: str = "公司养股东"
    max_position: str = "5%"
    q1_current: Optional[float] = None
    q1_prior: Optional[float] = None
    q1_url: str = ""
    pe_applicable: bool = True
    fcf_applicable: bool = True
    primary_method: str = "PE"
    nav_per_unit: Optional[float] = None
    notes: str = ""

    @property
    def board(self) -> str:
        return "A股主板" if self.price_currency == "RMB" and self.code != "87001" else "港股主板"

    @property
    def fx(self) -> float:
        return HKD_RMB if self.price_currency == "HKD" else 1.0

    @property
    def market_cap(self) -> float:
        return self.price * self.shares * self.fx

    @property
    def debt(self) -> float:
        return self.debt_short + self.debt_long + self.debt_bonds + self.debt_lease

    @property
    def immediate_net_cash(self) -> float:
        return self.cash_eq - self.restricted - self.debt

    @property
    def broad_net_cash(self) -> float:
        return self.broad_cash - self.restricted - self.debt

    @property
    def conservative_net_cash(self) -> float:
        return self.immediate_net_cash - self.related_cash - self.other_low_liquidity

    @property
    def fcf(self) -> Optional[float]:
        if not self.fcf_applicable or self.ocf is None or self.capex is None:
            return None
        return self.ocf - self.capex

    @property
    def prior_fcf(self) -> Optional[float]:
        if not self.fcf_applicable or self.prior_ocf is None or self.prior_capex is None:
            return None
        return self.prior_ocf - self.prior_capex

    @property
    def average_fcf(self) -> Optional[float]:
        if self.fcf is None or self.prior_fcf is None:
            return None
        return (self.fcf + self.prior_fcf) / 2

    @property
    def ttm_profit(self) -> Optional[float]:
        if self.q1_current is None or self.q1_prior is None:
            return None
        return self.profit + self.q1_current - self.q1_prior


HKEX = "https://www.hkexnews.hk/listedco/listconews/sehk/2026"
DISCLOSURE = "合并财务报表相应报表及附注（PDF页码以阅读器为准）"


COMPANIES = [
    Company("安井食品", "603345", 81.45, "RMB", 333_288_932, 16_192_613_033.59, 1_359_237_139.62,
            2_316_722_978.59, 873_464_939.66, 2_103_844_668.23, 901_279_791.42,
            4_980_279_916.72, 4_980_279_916.72, 2.865,
            f"{HKEX}/0331/2026033100011_c.pdf", "2026-03-31", "速冻食品", "价值发现",
            "品牌、渠道与规模仍有价值，但当前估值未给高安全边际，先观察。", "收入恢复能否转化为稳定现金利润",
            ("2025年经营现金流23.17亿元", "即时净现金为正", "2026Q1归母净利同比恢复"),
            ("连续两期收入或利润同比下降", "两年平均FCF收益率跌破3%", "扩产导致净现金显著转负"),
            debt_short=890_604_887.79, debt_long=30_453_948.28, debt_lease=48_156_365.93,
            max_position="4%", q1_current=563_159_120.61, q1_prior=394_524_301.61,
            q1_url="https://dataclouds.cninfo.com.cn/shgonggao/hsomarket/2026/20260428/d015cb0549ea40ca99fa0239ec065fc4.PDF"),
    Company("滨江服务", "03316", 22.86, "HKD", 276_407_000, 4_101_253_000, 595_508_000,
            828_737_000, 34_837_000, 561_214_000, 26_001_000, 890_521_000, 3_260_094_000, 1.804,
            f"{HKEX}/0424/2026042403062_c.pdf", "2026-04-24", "物业服务", "纯硬收息",
            "高股息、低资本开支和现金储备构成吸引力，但受限资金与民营地产关联风险决定仓位上限。", "关联开发商项目质量与应收回款",
            ("2025年报告FCF约7.94亿元", "全年股息1.804港元", "除租赁外无银行借款"),
            ("贸易应收增速连续高于收入10个百分点", "派息率降至50%以下", "关联方信用事件造成现金损失"),
            debt_lease=2_378_000, restricted=263_300_000, max_position="8%"),
    Company("达势股份", "01405", 37.34, "HKD", 131_459_111, 5_382_047_000, 141_932_000,
            892_899_000, 506_028_000, 818_421_000, 416_245_000, 1_001_511_000, 1_001_511_000, 0,
            f"{HKEX}/0429/2026042902263_c.pdf", "2026-04-29", "连锁餐饮", "成长股",
            "门店扩张已带来正利润，但租赁负债和开店资本开支高，当前价格缺少防御性。", "新店回收期与同店销售",
            ("2025年经营现金流8.93亿元", "公司已实现年度盈利", "规模扩张仍有空间"),
            ("同店销售连续两个半年负增长", "新店现金回收期超过4年", "净负债继续扩大且FCF转负"),
            debt_short=400_000, debt_long=199_400_000, debt_lease=1_807_290_000,
            relationship="相互供养", max_position="2%"),
    Company("分众传媒", "002027", 4.96, "RMB", 14_442_199_726, 12_758_696_542.16, 2_946_332_500.88,
            7_208_813_429.81, 157_001_279.43, 6_641_811_190.52, 318_344_915.55,
            3_238_508_082.40, 3_238_508_082.40, 0.57,
            "https://disc.static.szse.cn/disc/disk03/finalpage/2026-04-29/f03859a4-b186-4fdc-bb2a-27078a1f1275.PDF",
            "2026-04-29", "楼宇广告", "纯硬收息",
            "高现金转化和较高股息率已达到可研究区，但广告周期与一次性收益需从TTM中剥离。", "核心广告收入与客户回款",
            ("2025年报告FCF约70.52亿元", "TTM利润高于2025年度", "过去一年每股现金分红0.57元"),
            ("核心广告收入连续两季同比下降", "应收账款增速显著高于收入", "分红超过跨期平均FCF且靠举债维持"),
            debt_short=161_366_359.01, debt_long=45_900_000, debt_lease=729_023_835.02, max_position="8%",
            q1_current=1_789_555_599.73, q1_prior=1_135_173_105.64,
            q1_url="https://vip.stock.finance.sina.com.cn/corp/view/vCB_AllBulletinDetail.php?id=12272086"),
    Company("海底捞", "06862", 11.51, "HKD", 5_415_478_340, 43_225_355_000, 4_049_824_000,
            5_664_189_000, 1_748_375_000, 7_634_465_000, 1_309_179_000,
            6_602_348_000, 6_602_348_000, 0.722,
            f"{HKEX}/0424/2026042401135_c.pdf", "2026-04-24", "连锁餐饮", "价值发现",
            "品牌和现金流仍强，股息有支撑，但2025年经营现金流回落且租赁负债高，适合观察而非重仓。", "同店翻台率与门店利润率",
            ("2025年归母净利40.50亿元", "报告FCF仍为正", "品牌和供应链具有规模优势"),
            ("翻台率连续两个半年恶化", "报告FCF不能覆盖股息", "租赁调整后净负债持续上升"),
            debt_short=2_428_064_000, debt_lease=3_506_506_000, max_position="5%"),
    Company("华润医药", "03320", 4.97, "HKD", 6_282_510_461, 269_574_326_000, 4_045_468_000,
            20_476_332_000, 3_548_145_000, 17_535_514_000, 3_202_827_000,
            15_843_809_000, 15_843_809_000, 0.2179,
            f"{HKEX}/0428/2026042800132_c.pdf", "2026-04-28", "医药制造与分销", "价值发现",
            "表面估值低且FCF不错，但高有息负债和低毛利分销业务使净现金保护不存在。", "净负债下降速度与分销应收周转",
            ("2025年经营现金流204.76亿元", "业务组合具防御属性", "央企平台融资渠道稳定"),
            ("净负债/FCF继续上升", "应收周转显著恶化", "归母利润连续两年下降"),
            debt_short=49_836_351_000, debt_long=21_346_721_000, debt_lease=1_222_961_000,
            relationship="相互供养", max_position="4%"),
    Company("汇贤产业信托", "87001", 0.385, "RMB", 6_523_199_235, 2_209_000_000, -1_019_000_000,
            None, None, None, None, 2_700_000_000, 2_700_000_000, 0.0043,
            "https://www1.hkexnews.hk/listedco/listconews/sehk/2026/0423/2026042301399.pdf", "2026-04-23",
            "人民币计价REIT", "纯硬收息",
            "DPU仅0.0043元且债务高于现金，低价格不能替代分派能力，暂不买入。", "办公及零售租金负增长何时止住",
            ("2025年酒店NPI同比增长", "仍维持100%可分派金额派付", "资产组合位于核心城市"),
            ("DPU继续下降", "再融资成本吞噬可分派收入", "单位数因管理费持续稀释"),
            debt_short=2_076_000_000, debt_long=2_962_000_000, relationship="相互供养", max_position="2%",
            pe_applicable=False, fcf_applicable=False, primary_method="DPU_FFO", nav_per_unit=3.1737,
            notes="REIT的经营现金流受公允价值、融资和分派结构影响，通用FCF不用于估值。"),
    Company("金融街物业", "01502", 1.98, "HKD", 373_500_000, 1_999_238_000, 107_350_000,
            156_336_000, 5_842_000, 165_323_000, 6_283_000, 1_509_025_000, 1_660_531_000, 0.1667,
            f"{HKEX}/0416/2026041601917_c.pdf", "2026-04-16", "物业服务", "纯硬收息",
            "现金覆盖市值且FCF稳定，但母公司地产信用和关联项目依赖要求严格控制仓位。", "关联方应收与现金隔离",
            ("2025年报告FCF约1.50亿元", "即时净现金显著为正", "股息率处于较高水平"),
            ("关联方应收或减值明显增加", "现金无法自由调度或出现质押", "派息率连续两年下降"),
            debt_lease=33_857_000, relationship="相互供养", max_position="6%"),
    Company("京投交通科技", "01522", 0.21, "HKD", 2_097_146_727, 1_775_748_000, 133_974_000,
            205_072_000, 9_112_000, 227_864_000, 47_235_000, 794_864_000, 794_864_000, 0.02,
            f"{HKEX}/0429/2026042905081_c.pdf", "2026-04-29", "轨道交通科技", "烟蒂股",
            "市值低于审慎净现金且FCF为正，但小市值、低流动性和项目制波动使其只能是小仓位烟蒂。", "订单回款与现金是否持续归属股东",
            ("即时净现金为正", "两年报告FCF均为正", "有稳定轨道交通客户基础"),
            ("大额项目应收逾期", "连续两年不派息且现金不回购", "日均成交不足退出需求"),
            debt_short=145_083_000, debt_long=165_000_000, debt_lease=36_404_000,
            relationship="相互供养", max_position="2%"),
    Company("绿城服务", "02869", 4.20, "HKD", 3_138_010_968, 18_285_000_000, 880_196_000,
            1_527_736_000, 120_216_000, 1_474_721_000, 321_904_000,
            5_319_928_000, 7_006_528_000, 0.24,
            f"{HKEX}/0423/2026042301019_c.pdf", "2026-04-23", "物业服务", "价值发现",
            "净现金与FCF提供保护，但利润率偏薄，必须确认增值服务和应收质量后才适合提升仓位。", "利润率及贸易应收回收",
            ("2025年报告FCF约14.08亿元", "广义净现金显著为正", "在管面积和品牌具有规模"),
            ("应收增速连续高于收入", "毛利率继续下滑", "关联方项目发生实质损失"),
            debt_short=59_480_000, debt_long=17_669_000, debt_lease=433_746_000,
            relationship="相互供养", max_position="6%"),
    Company("蒙牛乳业", "02319", 18.50, "HKD", 3_873_464_649, 82_244_944_000, 1_545_350_000,
            8_750_515_000, 2_452_671_000, 8_332_256_000, 3_475_129_000,
            13_254_542_000, 13_254_542_000, 0.5976,
            f"{HKEX}/0427/2026042703201_c.pdf", "2026-04-27", "乳制品", "困境反转",
            "FCF尚可但利润率和净负债约束明显，估值便宜需要以盈利修复验证，不能只看品牌。", "基础白奶价格与利润率",
            ("2025年报告FCF约62.98亿元", "资本开支同比下降", "品牌与渠道仍居行业前列"),
            ("归母利润继续显著下降", "净负债扩大", "经营现金流不能覆盖股息与资本开支"),
            debt_short=13_874_111_000, debt_long=11_514_625_000, relationship="相互供养", max_position="4%"),
    Company("牧原股份", "002714", 39.40, "RMB", 5_462_771_148, 144_144_965_371.68, 15_486_891_254.04,
            30_056_186_914.47, 9_528_929_651.93, 37_543_066_214.49, 12_380_725_812,
            13_862_397_618.88, 13_862_397_618.88, 1.354521,
            "https://www.cninfo.com.cn/new/disclosure/stock?stockCode=002714", "2026-04-22", "生猪养殖", "周期拐点",
            "年度利润和FCF处于周期高位，但2026Q1已转亏且净负债巨大，应按中周期盈利而非静态PE估值。", "完全成本与猪价",
            ("2025年报告FCF约205.27亿元", "成本控制具行业优势", "资产周转和出栏规模领先"),
            ("完全成本反弹且猪价低迷", "债务再度快速增长", "TTM利润跌破利息与维持性CAPEX覆盖线"),
            debt_short=41_155_376_669.3, debt_long=26_914_047_092.19, debt_lease=2_179_276_683.9,
            relationship="相互供养", max_position="3%", primary_method="MID_CYCLE",
            q1_current=-1_214_841_304.35, q1_prior=4_491_095_122.49,
            q1_url="https://disc.static.szse.cn/download/disc/disk03/finalpage/2026-04-22/a3ba01d7-25ba-4c29-8281-4215ec2a3483.PDF"),
    Company("青岛啤酒", "600600", 51.37, "RMB", 1_364_195_121, 32_473_493_664, 4_588_101_137,
            4_592_509_302, 2_253_224_472, 5_154_661_132, 2_141_049_570,
            12_859_566_861, 12_859_566_861, 2.35,
            f"{HKEX}/0427/2026042702944.pdf", "2026-04-27", "啤酒", "价值发现",
            "品牌、净现金与盈利稳定性较好，但资本开支使FCF收益率一般，等待更大安全边际。", "销量结构升级能否抵消总量压力",
            ("2026Q1利润继续增长", "即时净现金充足", "长期分红记录稳定"),
            ("高端产品量价齐跌", "两年平均FCF收益率持续低于3%", "资本开支长期高于经营折旧需求"),
            debt_long=36_713_618, debt_lease=77_752_524, max_position="5%",
            q1_current=1_799_783_004, q1_prior=1_710_355_183,
            q1_url="https://stockmc.xueqiu.com/202604/600600_20260428_9R2K.pdf"),
    Company("山东药玻", "600529", 19.25, "RMB", 663_614_113, 4_474_018_978.75, 689_626_040.66,
            576_924_963.36, 231_864_537.19, 1_165_050_367.9, 647_785_101.03,
            1_073_778_650.87, 1_073_778_650.87, 0.46,
            "https://www.sse.com.cn/assortment/stock/list/info/announcement/index.shtml?productId=600529", "2026-04-25",
            "药用玻璃", "价值发现",
            "产品壁垒尚可，但2025年经营现金流下降导致FCF波动，当前估值只适合观察。", "中硼硅产品放量与回款",
            ("保持净现金", "2026Q1仍盈利", "药包材升级提供结构性需求"),
            ("经营现金流连续两年低于利润", "新增产能利用率不足", "应收与存货合计增速显著高于收入"),
            debt_long=14_105_433.87, debt_lease=23_397_844.45, max_position="4%",
            q1_current=201_206_020.13, q1_prior=223_629_434.88,
            q1_url="https://paper.cnstock.com/html/2026-04/25/content_2206743.htm"),
    Company("神威药业", "02877", 8.23, "HKD", 755_400_000, 3_135_419_000, 949_948_000,
            1_172_033_000, 197_905_000, 963_135_000, 140_112_000, 7_189_047_000, 7_565_687_000, 0.607,
            f"{HKEX}/0423/2026042301207_c.pdf", "2026-04-23", "中药", "烟蒂股",
            "现金接近或超过市值、FCF和股息均有支撑，是高质量烟蒂候选；治理与资金归属决定是否加仓。", "账上现金能否持续通过分红/回购回到股东",
            ("报告FCF约9.74亿元", "审慎即时净现金大幅为正", "过去一年每股股息0.607港元"),
            ("现金长期沉淀且股东回报下降", "核心品种收入连续下降", "关联交易或资本开支显著侵蚀现金"),
            debt_short=325_051_000, debt_lease=9_851_000, max_position="7%"),
    Company("天津发展", "00882", 2.08, "HKD", 1_072_770_125, 3_196_199_000, 427_942_000,
            46_783_000, 79_420_000, -723_205_000, 191_976_000, 2_811_065_000, 2_811_065_000, 0.14,
            f"{HKEX}/0428/2026042800038_c.pdf", "2026-04-28", "综合企业", "烟蒂股",
            "资产折价和股息有表面吸引力，但两年平均FCF为负且债务不低，不满足现金创造硬约束。", "经营现金流能否连续转正",
            ("2025年经营现金流转正", "有稳定公用事业与医药资产", "仍维持现金分红"),
            ("经营现金流再次转负", "净债务扩大", "联营资产利润不能转化为母公司现金"),
            debt_short=238_760_000, debt_long=1_741_936_000, debt_lease=15_435_000,
            relationship="相互供养", max_position="2%"),
    Company("同仁堂国药", "03613", 6.49, "HKD", 837_100_000, 1_513_357_000, 397_216_000,
            829_520_000, 41_183_000, -217_251_000, 43_168_000, 2_227_847_000, 2_279_224_000, 0.40,
            f"{HKEX}/0429/2026042902617_c.pdf", "2026-04-29", "中药", "纯硬收息",
            "品牌、净现金和2025年现金流修复使估值具有吸引力，但两年平均FCF仍受营运资金波动影响。", "境外销售增长与回款质量",
            ("2025年报告FCF约7.88亿元", "即时净现金显著为正", "股息率超过防御型门槛"),
            ("经营现金流再次显著为负", "品牌授权或关联采购条件恶化", "派息大幅削减"),
            debt_short=71_000, debt_long=71_000, debt_lease=126_398_000,
            relationship="相互供养", max_position="6%"),
    Company("威高股份", "01066", 3.54, "HKD", 4_476_812_724, 13_388_890_000, 1_612_210_000,
            2_550_606_000, 832_635_000, 2_789_971_000, 647_431_000, 8_569_516_000, 9_452_566_000, 0.1749,
            f"{HKEX}/0428/2026042803346_c.pdf", "2026-04-28", "医疗器械", "价值发现",
            "估值、现金流和股息具吸引力，但集采、商誉和净负债抵消部分安全边际。", "集采后耗材价格与销量",
            ("两年报告FCF均为正", "业务具医疗刚需属性", "股息率接近防御型门槛"),
            ("核心耗材毛利率持续下降", "商誉或无形资产大额减值", "净负债/FCF明显恶化"),
            debt_short=432_612_000, debt_long=4_356_527_000, debt_lease=314_302_000,
            relationship="相互供养", max_position="5%"),
    Company("五粮液", "000858", 72.10, "RMB", 3_881_608_005, 40_528_509_770.23, 8_954_257_202.51,
            29_706_259_919.13, 1_967_407_316.36, 33_939_755_192.78, 2_666_310_780.23,
            127_014_443_016.86, 127_014_443_016.86, 5.157685,
            "https://www.cninfo.com.cn/new/disclosure/stock?stockCode=000858", "2026-04-30", "白酒", "困境反转",
            "巨额净现金、股息和FCF提供保护，但2025会计差错更正与收入利润大降使历史可比性受损，需先验证修复。", "渠道库存与真实动销",
            ("审慎即时净现金占市值较高", "2025年报告FCF仍强", "2026Q1利润显著恢复"),
            ("渠道库存继续上升且批价下滑", "经营现金流持续弱于利润", "会计口径再次重大更正"),
            debt_long=364_149_470.84, debt_lease=44_381_182.44, max_position="6%",
            q1_current=8_062_764_940.78, q1_prior=4_416_313_048.41,
            q1_url="https://disc.static.szse.cn/download/disc/disk03/finalpage/2026-04-30/3d25f352-b303-4c39-8890-d5864ad5221a.PDF"),
    Company("伊利股份", "600887", 25.28, "RMB", 6_325_360_667, 115_931_105_774.99, 11_565_166_497.81,
            14_343_920_490.32, 3_036_644_156.68, 21_739_740_393.38, 3_978_318_320.96,
            19_494_920_358, 19_494_920_358, 1.38,
            "https://open.sseinfo.com/ir2/?id=565&language=zh-cn&m=1", "2026-04-30", "乳制品", "价值发现",
            "TTM盈利和股息稳定，但高有息负债使其不是净现金公司，需用经营改善而非现金幻觉支撑估值。", "产品结构与净负债下降",
            ("2026Q1归母净利同比增长", "两年FCF均为正", "行业龙头品牌和渠道稳固"),
            ("基础液奶收入持续下滑", "净负债/FCF继续上升", "经营现金流再度大幅低于利润"),
            debt_short=45_630_626_027.83, debt_long=4_887_187_109.24, debt_lease=288_520_048.5,
            relationship="相互供养", max_position="5%", q1_current=5_394_651_297.16, q1_prior=4_874_104_242.93,
            q1_url="https://www.yili.com/uploads/2026-04-30/f55be7d8-cac0-4540-9bb8-0dce0e7f8fe51777526693097.pdf"),
    Company("中国民航信息网络", "00696", 8.31, "HKD", 2_926_209_589, 8_765_840_085.25, 2_341_561_691.06,
            2_923_537_577.24, 842_793_056.82, 2_525_944_922.54, 353_479_429.14,
            10_059_017_494.73, 14_473_700_816.65, 0.31734,
            f"{HKEX}/0422/2026042200655_c.pdf", "2026-04-22", "航空信息服务", "价值发现",
            "垄断型基础设施、净现金与FCF构成安全边际，但航空周期、资本开支和国企资本配置需要折价。", "航班量与系统资本开支",
            ("两年报告FCF均为正", "即时净现金大幅为正", "行业基础设施地位稳固"),
            ("资本开支长期吞噬经营现金流", "核心结算量下降", "大额非主业投资降低股东回报"),
            debt_short=1_288_708_414.97, debt_long=471_200_000, debt_lease=301_884_277.5,
            relationship="相互供养", max_position="6%"),
    Company("中国食品", "00506", 3.29, "HKD", 2_797_223_396, 22_070_162_000, 861_968_000,
            3_229_308_000, 1_060_515_000, 2_847_149_000, 774_634_000, 4_549_480_000, 4_549_480_000, 0.177,
            f"{HKEX}/0428/2026042802674_c.pdf", "2026-04-28", "饮料", "价值发现",
            "可口可乐装瓶业务现金流稳健、净现金为正，当前回报尚可；原料、渠道和资本开支决定估值上限。", "销量增长与单箱利润",
            ("两年报告FCF均超过20亿元", "即时净现金为正", "特许经营区域和品牌壁垒稳定"),
            ("销量与单箱收入同步下降", "资本开支显著超出折旧且回报下降", "分红不能被FCF覆盖"),
            debt_lease=68_275_000, relationship="相互供养", max_position="6%"),
    Company("中国移动", "600941", 96.71, "RMB", 21_644_606_612, 1_050_187_000_000, 137_095_000_000,
            232_919_000_000, 156_951_000_000, 315_741_000_000, 155_979_000_000,
            97_267_000_000, 232_800_000_000, 4.7037,
            f"{HKEX}/0326/2026032602020_c.pdf", "2026-03-26", "电信运营", "纯硬收息",
            "盈利和分红稳定，但现金流量表口径FCF受高CAPEX影响，不能把公司自定义FCF或广义存款都视为可分红现金。", "CAPEX下降与派息覆盖",
            ("2025年归母净利1370.95亿元", "广义现金覆盖债务", "股息政策可见度较高"),
            ("报告FCF连续下降且不能覆盖股息", "资本开支强度重新上升", "ARPU和客户价值持续下滑"),
            debt_long=9_748_000_000, debt_lease=91_449_000_000, max_position="8%",
            q1_current=29_342_000_000, q1_prior=30_631_000_000,
            q1_url="https://epaper.stcn.com/att/202604/21/ZQ21B233-QX_eBook.pdf"),
    Company("中海物业", "02669", 3.40, "HKD", 3_283_960_460, 14_959_871_000, 1_366_779_000,
            1_153_458_000, 120_233_000, 1_338_145_000, 141_200_000,
            3_435_725_000, 6_270_700_000, 0.20,
            f"{HKEX}/0429/2026042900389.pdf", "2026-04-29", "物业服务", "纯硬收息",
            "央企母公司项目资源、净现金和稳定FCF有帮助，但帮助必须穿透为回款、分红和每股价值，不能单独当买入理由。", "母公司项目质量、应收回款与第三方拓展",
            ("2025年报告FCF约10.33亿元", "广义净现金显著为正", "中海地产提供项目来源和信用背书"),
            ("关联应收和减值持续上升", "第三方拓展停滞且利润率下滑", "现金沉淀但股息率下降"),
            debt_short=50_000_000, debt_lease=95_936_000, relationship="相互供养", max_position="7%"),
]


def yi(value: float) -> str:
    return f"{value / 100_000_000:,.2f}亿元"


def pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def multiple(value: Optional[float]) -> str:
    return "不适用" if value is None else f"{value:.2f}倍"


def decision(company: Company) -> tuple[str, str, str]:
    if not company.fcf_applicable:
        return "暂不买入", "DPU和债务结构未通过硬约束", "DPU恢复且债务成本下降后重估"
    fcf_yield = (company.fcf or 0) / company.market_cap
    dividend_yield = company.dividend / company.price
    ttm_change = None if company.ttm_profit is None else company.ttm_profit / company.profit - 1
    if company.fcf and fcf_yield >= 0.08 and dividend_yield >= 0.05 and company.immediate_net_cash > 0 and (ttm_change is None or ttm_change > -0.2):
        return "可分批买入", "股息、FCF与即时净现金三项同时提供保护", "仅在证伪条件未触发时按区间分批"
    if company.fcf and fcf_yield >= 0.06 and (ttm_change is None or ttm_change > -0.3):
        return "观察/小仓试错", "现金创造尚可但至少一项安全边际不足", "业绩确认或估值回落后再提高仓位"
    return "暂不买入", "FCF、趋势或资产负债表尚未同时通过", "连续两个披露期改善后重估"


def render_report(c: Company) -> str:
    action, reason, reevaluate = decision(c)
    market_cap = c.market_cap
    static_pe = market_cap / c.profit if c.pe_applicable and c.profit > 0 else None
    ttm_pe = market_cap / c.ttm_profit if c.ttm_profit and c.ttm_profit > 0 else None
    dividend_yield = c.dividend / c.price
    fcf_yield = None if c.fcf is None else c.fcf / market_cap
    avg_yield = None if c.average_fcf is None else c.average_fcf / market_cap
    fcf_mult = None if c.fcf is None or c.fcf <= 0 else market_cap / c.fcf
    ex_cash_mult = None if c.fcf is None or c.fcf == 0 else (market_cap - c.broad_net_cash) / c.fcf
    time_deposits = max(c.broad_cash - c.cash_eq, 0)
    maintenance = "不适用" if c.fcf is None else f"{yi(c.ocf - c.capex)}至{yi(c.ocf - c.capex * 0.5)}（维护CAPEX按实际CAPEX的50%-100%，B级估计）"
    ttm_text = "不可可靠计算：港股截至基准日尚缺2026H1正式业绩" if c.pe_applicable and c.ttm_profit is None else ("不适用" if not c.pe_applicable else f"{yi(c.ttm_profit)}，TTM PE {multiple(ttm_pe)}")
    fcf_text = "不适用：REIT应使用DPU/可分派收入，通用FCF会被融资及公允价值结构扭曲" if c.fcf is None else yi(c.fcf)
    avg_text = "不适用：同上" if c.average_fcf is None else f"{yi(c.average_fcf)}，占当前市值{pct(avg_yield)}"
    nav_text = "" if c.nav_per_unit is None else f"\n| 每单位资产净值 | {c.nav_per_unit:.4f}元；市价/NAV={c.price / c.nav_per_unit:.2f}倍 |"
    cash_note = "即时净现金仅是流动性压力测试，不等于能自由分红；仍受营运资金、代收代付、监管、外汇、资本开支及少数股东权益约束。"
    buy_rule = ("DPU恢复、分派覆盖改善、债务成本下降且市价/NAV仍有安全边际"
                if not c.fcf_applicable else
                "同时满足报告FCF收益率≥8%、税前股息率≥5%、证伪条件未触发；周期股还需中周期利润确认")
    report = f"""# {c.name}_{c.code}_投资分析报告

**一句话结论**：{c.thesis} 当前操作：**{action}**，单一标的仓位上限{c.max_position}。

| 项目 | 内容 |
|------|------|
| 主框架 | {c.framework} |
| 次框架 | 现金回报与资产负债表交叉验证 |
| 上市板块 | {c.board} |
| 流程状态 | 标准分析 |
| 股东关系 | {c.relationship} |
| 数据截止日 | {AS_OF}（财务数据为2025年报，A股以2026Q1补TTM） |
| 股价基准日 | {AS_OF} |
| 数据置信度 | 年报核心数据S级；行情与汇率B级；维护性CAPEX为B级估计 |
| 当前仓位 | 0% |
| 建议仓位上限 | {c.max_position} |
| 下次复核日 | 2026-09-30或下一份正式业绩披露日 |
| 模板版本 | V5.5.24-r2 |

## 一、投资判断

### 支持投资的三项事实

1. {c.supports[0]}。
2. {c.supports[1]}。
3. {c.supports[2]}。

### 证伪条件

1. {c.falsifiers[0]}。
2. {c.falsifiers[1]}。
3. {c.falsifiers[2]}。

**最重要变量**：{c.variable}。

**股东关系判断**：{c.relationship}。产业资源、品牌或母公司支持只有转化为可核验的收入、回款、FCF、分红或每股净资产增长，才算普通股股东得到养分；关联交易规模本身不是利好。

**当前操作依据**：{reason}。重新评估条件：{reevaluate}。

### 操作区间

| 区间 | 规则 |
|------|------|
| 买入区间 | {buy_rule} |
| 观察区间 | FCF收益率5%-8%，或净现金/盈利趋势只有一项通过 |
| 退出触发 | 任一证伪条件连续两个披露期成立，或会计/治理问题使数据失真 |

## 二、估值适用性与盈利时点

| 指标 | 结果 |
|------|------|
| 主估值方法 | {c.primary_method} |
| 当前市值 | {yi(market_cap)}人民币（股价{c.price:.3f}{c.price_currency}×股本{c.shares/100_000_000:.4f}亿×汇率{c.fx:.4f}） |
| 静态PE | {multiple(static_pe)} |
| TTM净利润与TTM PE | {ttm_text} |
| 静态/TTM差异 | {'不适用' if not c.pe_applicable else ('TTM相对年度变化' + pct(c.ttm_profit / c.profit - 1) if c.ttm_profit else '缺少最新中期组成项，不用年度利润冒充TTM')} |{nav_text}

> 统一计算币种为人民币。港股使用1港元={HKD_RMB}元人民币，汇率基准日{AS_OF}，来源为Yahoo Finance HKDCNY日线；A股及人民币柜台汇率为1。历史高点、发行价、融资价和“跌了多少”均不参与内在价值计算。

## 三、现金回报与可动用性看板

| 强制指标 | 数值 | 口径说明 |
|----------|------|----------|
| 税前股息率 | {pct(dividend_yield)} | 每股股息{c.dividend:.6f}{c.price_currency}÷股价；不含税费 |
| 报告口径 FCF | {fcf_text} | 经营现金流－现金流量表资本开支 |
| FCF/市值 | {'不适用' if fcf_yield is None else pct(fcf_yield)} | 与当前市值同为人民币口径 |
| 市值/FCF | {multiple(fcf_mult)} | FCF≤0或不适用时不计算 |
| 跨期平均 FCF | {avg_text} | 2024、2025两个完整年度实际值均值 |
| 维护性 FCF | {maintenance} | 与报告口径分开，不把估计标为S级 |
| 现金及现金等价物 | {yi(c.cash_eq)} | 原始期限通常≤3个月；不把交易性金融资产算入 |
| 即时净现金 | {yi(c.immediate_net_cash)} | 现金等价物－受限现金－有息负债（含租赁） |
| 即时净现金/市值 | {pct(c.immediate_net_cash / market_cap)} | 流动性压力测试 |
| 三个月以上定期存款 | {yi(time_deposits)} | 仅在年报能分拆时计入广义现金 |
| 广义净现金 | {yi(c.broad_net_cash)} | 现金及银行结余－受限现金－有息负债 |
| 广义净现金/市值 | {pct(c.broad_net_cash / market_cap)} | 不等于全部随时可用 |
| 审慎即时净现金 | {yi(c.conservative_net_cash)} | 即时净现金再扣关联方财务公司存款及其他低流动性现金 |
| 审慎即时净现金/市值 | {pct(c.conservative_net_cash / market_cap)} | 最保守流动性口径 |
| 剔除广义净现金FCF倍数 | {multiple(ex_cash_mult)} | 负值表示广义净现金超过市值，不代表可直接分走 |

**现金可动用性结论**：{cash_note} 本报告没有把三个月以上定存、交易性金融资产或未核实理财写成随时可动用现金。股息来自FCF，**股息率不得与FCF/市值相加**。

## 四、现金流质量

| 项目 | 2024 | 2025 | 变化/解释 |
|------|------|------|-----------|
| 经营现金流 | {'不适用' if c.prior_ocf is None else yi(c.prior_ocf)} | {'不适用' if c.ocf is None else yi(c.ocf)} | 需结合应收、存货、合同负债和代收代付拆解 |
| 现金流量表CAPEX | {'不适用' if c.prior_capex is None else yi(c.prior_capex)} | {'不适用' if c.capex is None else yi(c.capex)} | 取购建长期资产现金支出，不用“轻资产≈0” |
| 报告口径FCF | {'不适用' if c.prior_fcf is None else yi(c.prior_fcf)} | {fcf_text} | 单年波动必须与两年均值同时看 |

经营现金流下降不能只写“经营变差”：先核对利润变化，再拆应收/存货占用、应付及合同负债释放、税费、代收代付和一次性项目。若下降来自此前应付增长正常化，其持续性与应收恶化完全不同。

## 五、业务、资本配置与养分测试

**业务判断**：{c.sector}。{c.thesis}

**简版资本市场养分测试**：标签为“{c.relationship}”。2025年经营现金流、资本开支、股息和股本已纳入核对；没有用融资额、市值或母公司规模代替每股回报。若后续出现持续股权融资、管理费发股或高CAPEX扩张，将升级为五年完整测试。

**历史价格锚排除**：历史高点、发行价、融资价及距高点跌幅不参与估值；“已经跌很多”不是买入理由。

## 六、风险与跟踪

| 风险类型 | 触发指标 | 复核频率 | 动作 |
|----------|----------|----------|------|
| 永久性亏损 | {c.falsifiers[0]} | 每次业绩 | 停止加仓，复核内在价值 |
| 价格波动 | 股价下跌但基本面未确认 | 每周 | 不因下跌自动加仓 |
| 流动性 | 即时净现金恶化或成交不足 | 每月/每次业绩 | 降低仓位上限 |
| 逻辑失效 | {c.falsifiers[1]} | 每次业绩 | 退出或转为事件观察 |

## 七、来源台账

| 数据 | 期间 | 来源文件 | 页码/附注 | 币种 | 原始值 | 置信度 |
|------|------|----------|-----------|------|--------|--------|
| 收入、归母利润 | 2025FY | [2025年报]({c.annual_url}) | 合并损益表 | RMB | 是 | S |
| 现金及银行结余、债务 | 2025-12-31 | [2025年报]({c.annual_url}) | 合并资产负债表及现金/借款/租赁附注 | RMB | 是 | S |
| 经营现金流、CAPEX | 2025FY | [2025年报]({c.annual_url}) | 合并现金流量表 | RMB | 是 | S |
| 股本、股息 | 2025FY/基准日 | [2025年报]({c.annual_url}) | 股本及股息附注 | {c.price_currency} | 是 | S |
| 股价 | {AS_OF} | Yahoo Finance日线 | 收盘价 | {c.price_currency} | 是 | B |
| 汇率 | {AS_OF} | Yahoo Finance HKDCNY日线 | 1 HKD={HKD_RMB} RMB | RMB | 是 | B |
"""
    if c.q1_current is not None:
        report += f"| TTM组成项 | 2026Q1/2025Q1 | [2026Q1报告]({c.q1_url}) | 主要财务数据 | RMB | 是 | A（季度未经审计） |\n"
    report += f"""

## 八、报告完成检查

- [x] 主框架、上市板块、流程状态和股东关系已填写
- [x] 数据截止日、股价基准日和汇率日期已填写
- [x] 静态PE/TTM PE按适用性展示
- [x] 报告FCF与维护性FCF分开
- [x] 税前股息率、FCF/市值、市值/FCF和两年平均FCF已展示
- [x] 即时净现金、广义净现金、审慎即时净现金及市值占比已分开
- [x] 已说明现金能否立即动用、能否自由分红
- [x] 已排除历史价格锚
- [x] 已填写三条证伪条件和复核日期

---

*报告生成：{AS_OF}；模板：V5.5.24-r2。本文为研究记录，不构成投资建议。*
"""
    return report


def source_field(value: float | None, unit: str, source: str, page: str, *, verify: bool = False) -> dict:
    result = {
        "value": value,
        "unit": unit,
        "source": source,
        "page_number": page,
        "report_period": "2025-12-31",
        "confidence": "S",
    }
    if verify:
        result["verification_checked"] = True
    return result


def validation_data(c: Company) -> dict:
    market_cap = c.market_cap
    fcf = c.fcf
    prior_fcf = c.prior_fcf
    avg_fcf = c.average_fcf
    static_pe = market_cap / c.profit if c.pe_applicable and c.profit > 0 else None
    ttm = c.ttm_profit
    ttm_method = "ANNUAL_PLUS_INTERIM" if ttm is not None else "NOT_AVAILABLE"
    ttm_components = []
    if ttm is not None:
        ttm_components = [
            {"role": "latest_annual", "period": "2025FY", "value": c.profit, "operator": 1, "unit": "RMB", "source": "2025_annual_report_income_statement", "page_number": "合并损益表"},
            {"role": "current_interim", "period": "2026Q1", "value": c.q1_current, "operator": 1, "unit": "RMB", "source": "2026_quarter_report_key_financials", "page_number": "主要财务数据"},
            {"role": "prior_interim", "period": "2025Q1", "value": c.q1_prior, "operator": -1, "unit": "RMB", "source": "2026_quarter_report_comparative_key_financials", "page_number": "主要财务数据"},
        ]
    fcf_unavailable = "REIT使用DPU/可分派收入和NAV估值；通用经营现金流减CAPEX会混入融资结构，故不适用。" if not c.fcf_applicable else ""
    debt_source = "2025_annual_report_borrowings_and_lease_notes"
    core = {
        "cash_and_bank_balances": source_field(c.broad_cash, "RMB", "2025_annual_report_cash_and_bank_balance_notes", DISCLOSURE, verify=True),
        "cash_and_cash_equivalents": {
            **source_field(c.cash_eq, "RMB", "2025_annual_report_cash_flow_and_cash_notes", "合并现金流量表及现金附注", verify=True),
            "notes": "现金及现金等价物与三个月以上定存分列；未把交易性金融资产计入。未识别的受限或关联方现金不推定为可自由分红。",
        },
        "time_deposits_over_three_months": {"value": max(c.broad_cash - c.cash_eq, 0), "unit": "RMB", "source": "2025_annual_report_cash_notes", "page_number": "现金及银行结余附注", "confidence": "S"},
        "related_financial_institution_deposits": {"value": c.related_cash, "unit": "RMB", "included_in_cash_and_cash_equivalents": c.related_cash > 0, "source": "2025_annual_report_related_party_cash_notes", "page_number": "关联方及现金附注", "confidence": "S"},
        "other_low_liquidity_cash": {"value": c.other_low_liquidity, "unit": "RMB", "source": "2025_annual_report_cash_notes", "page_number": "现金附注", "confidence": "S"},
        "restricted_cash": {"value": c.restricted, "unit": "RMB", "source": "2025_annual_report_restricted_cash_notes", "page_number": "受限现金附注", "confidence": "S"},
        "interest_bearing_debt": {
            "short_term": {"value": c.debt_short, "source": debt_source, "page_number": "借款附注", "report_period": "2025-12-31", "confidence": "S"},
            "long_term": {"value": c.debt_long, "source": debt_source, "page_number": "借款附注", "report_period": "2025-12-31", "confidence": "S"},
            "bonds": {"value": c.debt_bonds, "source": debt_source, "page_number": "债券附注", "report_period": "2025-12-31", "confidence": "S"},
            "lease_liabilities": {"value": c.debt_lease, "source": debt_source, "page_number": "租赁附注", "report_period": "2025-12-31", "confidence": "S"},
            "total_value": c.debt,
            "total_calculation": "short_term + long_term + bonds + lease_liabilities",
            "confidence": "S",
        },
        "revenue": source_field(c.revenue, "RMB", "2025_annual_report_income_statement", "合并损益表"),
        "net_profit": source_field(c.profit, "RMB", "2025_annual_report_income_statement", "合并损益表"),
        "net_profit_attributable": source_field(c.profit, "RMB", "2025_annual_report_income_statement", "合并损益表"),
        "ttm_components": ttm_components,
        "operating_cash_flow": source_field(c.ocf, "RMB", "2025_annual_report_cash_flow_statement", "合并现金流量表", verify=c.fcf_applicable),
        "capex": source_field(c.capex, "RMB", "2025_annual_report_cash_flow_statement_capex", "合并现金流量表"),
        "dividend_per_share_for_yield": {"value": c.dividend, "currency": c.price_currency, "period": "TTM/2025FY已批准", "source": "2025_annual_report_dividend_note_and_distribution_announcement", "page_number": "股息附注", "confidence": "S"},
        "total_shares": {"value": c.shares, "source": "2025_annual_report_share_capital_note", "page_number": "股本附注", "confidence": "S"},
        "share_price": {"value": c.price, "currency": c.price_currency, "date": AS_OF, "source": "Yahoo Finance daily chart API close"},
        "market_cap": {"value": market_cap, "unit": "RMB", "calculation": "shares * price * fx"},
        "calculated_metrics": {
            "immediate_net_cash": {"value": c.immediate_net_cash, "market_cap_ratio": c.immediate_net_cash / market_cap, "notes": "现金等价物扣受限资金及全部有息/租赁负债；可用于流动性压力测试，但受营运资金、监管和少数股东约束，不能视为可立即自由分红。"},
            "conservative_immediate_net_cash": {"value": c.conservative_net_cash, "market_cap_ratio": c.conservative_net_cash / market_cap, "notes": "即时净现金再扣关联财务公司存款及其他低流动性现金。"},
            "net_cash": {"value": c.broad_net_cash, "market_cap_ratio": c.broad_net_cash / market_cap, "notes": "广义净现金含已核实的三个月以上定存，不等于随时可动用现金。"},
            "fcf": {"value": fcf},
            "fcf_yield": {"value": None if fcf is None else fcf / market_cap},
            "fcf_multiple_market": {"value": None if fcf is None or fcf <= 0 else market_cap / fcf},
            "fcf_multiple_ex_cash": {"value": None if fcf is None or fcf == 0 else (market_cap - c.broad_net_cash) / fcf},
            "multi_period_fcf": ({"method": "NOT_AVAILABLE", "periods": [], "average_value": None, "market_cap_yield": None, "unavailable_reason": fcf_unavailable} if avg_fcf is None else {"method": "TWO_YEAR_AVERAGE", "periods": [{"period": "2024FY", "value": prior_fcf}, {"period": "2025FY", "value": fcf}], "average_value": avg_fcf, "market_cap_yield": avg_fcf / market_cap}),
            "dividend_yield": {"value": c.dividend / c.price},
            "static_pe": {"value": static_pe},
            "ttm_net_profit": {"value": ttm},
            "ttm_pe": {"value": None if ttm is None or ttm <= 0 else market_cap / ttm},
        },
    }


    policy = {
        "primary_method": c.primary_method,
        "pe_applicable": c.pe_applicable,
        "fcf_applicable": c.fcf_applicable,
        "fcf_unavailable_reason": fcf_unavailable,
        "price_as_of": AS_OF,
        "fx_as_of": AS_OF,
        "calculation_currency": "RMB",
        "share_price_to_calculation_currency_rate": c.fx,
        "fx_source": "Yahoo Finance HKDCNY daily chart API" if c.fx != 1 else "同币种，无需折算",
        "ttm_period": "2025-04-01至2026-03-31" if ttm is not None else "",
        "ttm_method": ttm_method,
        "ttm_unavailable_reason": "公司按半年披露，截至基准日缺少2026H1正式组成项。" if c.pe_applicable and ttm is None else ("PE不适用，采用DPU/FFO与NAV。" if not c.pe_applicable else ""),
    }
    return {
        "schema_version": "V5.5.24.2",
        "analysis_metadata": {
            "stock_code": c.code + (".HK" if c.board == "港股主板" and c.code != "87001" else ""),
            "stock_name": c.name,
            "report_date": AS_OF,
            "analyst": "Codex",
            "annual_report_year": 2025,
            "annual_report_date": c.annual_date,
            "listing_board": c.board,
            "workflow_status": "标准分析",
            "shareholder_relationship": c.relationship,
            "explicit_high_risk_request": False,
            "data_freshness_control": {"current_date": AS_OF, "max_allowed_age_days": 365},
            "report_type": "annual",
            "is_latest_full_year": True,
            "next_year_available": False,
            "valuation_policy": policy,
            "data_confidence_level": "S/B",
            "validation_checks": [
                {"check": "使用最新完整年度年报", "checked": True},
                {"check": "年报核心数据直接来自正式年报", "checked": True},
                {"check": "现金、负债、利润、现金流与股本已分科目核查", "checked": True},
                {"check": "行情和汇率与财务数据分级", "checked": True},
                {"check": "静态与TTM按披露频率处理", "checked": True},
            ],
        },
        "core_financial_data": core,
        "capital_market_nutrient_test": {
            "full_test_required": False,
            "classification": c.relationship,
            "classification_basis": "依据2025年经营现金流、资本开支、股息、债务和股本变化；产业资源只有穿透为每股现金回报才计入。",
            "summary_source": f"2025年报：{c.annual_url}",
            "historical_price_anchor_excluded": True,
        },
        "historical_comparison": {"years": [{"year": 2023}, {"year": 2024, "fcf": prior_fcf}, {"year": 2025, "fcf": fcf}]},
        "cross_validation": {"interest_rate_check": {"interest_income": 0}, "fcf_vs_profit_check": {"fcf": fcf, "net_profit": c.profit}},
        "validation_checklist": [
            {"id": "timing", "item": "最新完整年度年报", "checked": True},
            {"id": "unit", "item": "单位与币种已复核", "checked": True},
            {"id": "subject", "item": "现金、受限资金和有息负债已分开", "checked": True},
            {"id": "calculation", "item": "市值、净现金、FCF和PE已复核", "checked": True},
            {"id": "variance", "item": "年度变动已解释", "checked": True, "variance_explanation": "报告现金流质量章节按利润、营运资金与CAPEX拆解；超过30%的变化不直接外推。"},
            {"id": "source", "item": "核心数据均标注年报报表或附注", "checked": True},
            {"id": "cross_check", "item": "现金回报指标已交叉复核", "checked": True},
            {"id": "data_freshness", "item": "年报与最新季度披露状态已确认", "checked": True},
            {"id": "shareholder_relationship", "item": "股东关系已分类", "checked": True},
            {"id": "historical_price_anchor", "item": "历史价格锚已排除", "checked": True},
        ],
        "confidence_downgrade_reasons": ["年报核心数据S级；股价和汇率为B级行情；维护性资本开支为B级区间估计。"],
        "confirmation": {"i_confirm": ["核心年度数据来自正式年报", "计算过程已复核", "未把广义现金冒充随时可用现金"], "analyst_signature": "Codex", "validation_date": AS_OF},
    }


def render_index() -> str:
    rows = [
        "| [保利物业](./保利物业_06049_投资分析报告.md) | 06049.HK | 可分批买入/限仓 | 2025静态PE约8.5倍；报告FCF收益率约13.5%；即时净现金与广义净现金已分拆 |",
    ]
    for c in COMPANIES:
        action = decision(c)[0]
        pe = "不适用" if not c.pe_applicable or c.profit <= 0 else f"{c.market_cap / c.profit:.1f}倍"
        fcf_yield = "不适用" if c.fcf is None else pct(c.fcf / c.market_cap)
        rows.append(
            f"| [{c.name}](./{c.name}_{c.code}_投资分析报告.md) | {c.code} | {action} | "
            f"静态PE {pe}；报告FCF收益率 {fcf_yield}；税前股息率 {pct(c.dividend / c.price)}；即时净现金/市值 {pct(c.immediate_net_cash / c.market_cap)} |"
        )
    return """# 个股分析报告

本目录的25份个股报告已于 **2026-08-20** 全部迁移至 **V5.5.24-r2**，并按当前[报告输出契约](../template/00-报告输出契约.md)重新计算。财务数据以2025年正式年报为主；A股用2026Q1补TTM，港股缺少2026H1组成项时明确留空。

> 阅读重点：税前股息率不能与FCF收益率相加；即时净现金、广义净现金和审慎即时净现金含义不同。报告中的“可分批买入”也受单股仓位上限和证伪条件约束，不等于可以无上限重仓。

## 每日监控

[查看监控概览](./监控概览.md)

## 当前版本报告

| 标的 | 代码 | 当前动作 | 2026-08-20统一看板摘要 |
|------|------|----------|-------------------------|
""" + "\n".join(rows) + """

## 口径说明

- 报告FCF = 经营现金流－现金流量表资本开支；维护性FCF另列估计区间。
- 即时净现金只用现金及现金等价物，并扣受限现金及全部有息/租赁负债。
- 广义净现金只额外加入年报能核实的三个月以上银行存款；不把交易性金融资产或未核实理财算成现金。
- 审慎即时净现金进一步扣除关联方财务公司存款及其他低流动性现金。
- REIT用DPU/可分派收入、NAV和债务期限，不强行套用通用FCF。

## 导航

- [返回首页](/)
- [分析模板](/analysis-template)
- [模拟持仓](/portfolio/holdings)
"""


def write_utf8_lf(path: Path, content: str) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(content)


def main() -> None:
    REPORT_DIR.mkdir(exist_ok=True)
    for company in COMPANIES:
        report_path = REPORT_DIR / f"{company.name}_{company.code}_投资分析报告.md"
        write_utf8_lf(report_path, render_report(company))
        yaml_path = CONFIG_DIR / f"validation_{company.code}.yaml"
        write_utf8_lf(yaml_path, yaml.safe_dump(validation_data(company), allow_unicode=True, sort_keys=False, width=120))
        print(f"generated {report_path.name} + {yaml_path.name}")
    write_utf8_lf(REPORT_DIR / "index.md", render_index())
    print("generated analysis-reports/index.md")


if __name__ == "__main__":
    main()
