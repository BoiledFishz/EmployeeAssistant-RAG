from .models import Document


SAMPLE_DOCUMENTS = [
    Document(
        doc_id="hr-leave-cn-2026",
        title="中国区休假政策",
        text="""# 年假
中国区正式员工每个自然年享有 12 天带薪年假。入职当年按剩余自然日比例折算。年假申请应至少提前三个工作日在 HR 系统提交，并由直属经理批准。

# 试用期
试用期员工可以使用已经按比例累积的年假。连续请假超过 2 天时，HR 系统会额外通知直属经理和 HRBP。

# 病假
员工每年享有 10 天全薪病假。连续病假超过 2 个工作日，需要提交合规医疗机构证明。""",
        source_url="https://sharepoint.example/policies/hr/leave-cn-2026.pdf",
        department="HR",
        allowed_groups=frozenset({"all-employees-cn"}),
        version="2026.1",
        effective_date="2026-01-01",
    ),
    Document(
        doc_id="admin-expense-sh-2026",
        title="上海办公室差旅与费用报销政策",
        text="""# 市内交通
因加班晚于 21:30 离开办公室，员工可报销从办公室到常住地址的出租车或网约车费用。报销时须附行程单和电子发票，并填写加班事由。

# 提交流程
费用应在发生后 30 个自然日内通过费用系统提交。单笔超过 500 元需要成本中心负责人二次审批。""",
        source_url="https://sharepoint.example/policies/admin/sh-expense-2026.pdf",
        department="Administration",
        allowed_groups=frozenset({"all-employees-cn", "shanghai-office"}),
        version="2026.2",
        effective_date="2026-03-01",
    ),
    Document(
        doc_id="hr-holiday-cn-2026",
        title="中国区法定节假日与调休政策",
        text="""# 法定节假日
中国区员工适用的法定节假日包括元旦、春节、清明节、劳动节、端午节、中秋节和国庆节。每年的具体放假日期及调班安排以国务院办公厅公布的年度通知和公司 HR 日历为准。

# 调休
因业务需要在休息日加班且未支付加班工资的，经直属经理批准后可获得等时调休。调休余额和有效期以 HR 系统显示为准，应优先在获得后的 6 个月内使用。

# 查询方式
员工可以在 HR 系统的“休假余额”页面查询个人调休天数。由于调休余额取决于个人已审批的加班记录，知识库助手不能直接推断某位员工还剩几天调休。""",
        source_url="https://sharepoint.example/policies/hr/holiday-cn-2026.pdf",
        department="HR",
        allowed_groups=frozenset({"all-employees-cn"}),
        version="2026.1",
        effective_date="2026-01-01",
    ),
    Document(
        doc_id="hr-manager-comp-2026",
        title="经理薪酬校准指南",
        text="""# 访问范围
本指南仅供 people managers 和 HR 使用。

# 校准
年度薪酬校准需要结合绩效等级、岗位范围和内部公平性，不得向员工披露其他个人的薪酬数据。""",
        source_url="https://sharepoint.example/restricted/hr/comp-2026.pdf",
        department="HR",
        allowed_groups=frozenset({"people-managers", "hr"}),
        version="2026.1",
        effective_date="2026-01-01",
    ),
]
