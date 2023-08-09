from decimal import Decimal

import streamlit as st

from app.parse_billing import BillingInfo, BillingParser
from app.parse_invoice import InvoiceInfo, InvoiceParser

ip = InvoiceParser()
bp = BillingParser(
    st.secrets.aliyun_ocr.access_key_id, st.secrets.aliyun_ocr.access_key_secret
)


@st.cache_data(persist=True)
def parse_billing(file_content: bytes):
    return bp.parse_info(file_content)


def st_input_data() -> tuple[dict[str, InvoiceInfo], dict[str, BillingInfo]]:
    st.header("数据输入")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("上传账单 PDF")
        st.caption("目前支持的账单有：Mailgun、GitHub、Jira、1Password 和 Azure。")
        invoice_files = st.file_uploader(
            label="上传账单 PDF（支持多选）",
            type=["pdf"],
            accept_multiple_files=True,
        )
        st.write("账单解析结果：")
        invoice_result = {
            file.name: ip.parse_info(file.read()) for file in invoice_files
        }
        st.table(invoice_result)
    with col2:
        st.subheader("上传信用卡还款截图")
        st.caption("目前仅支持：招商银行信用卡设置外币消费人民币入账，在掌上生活 App 的还款截图。")
        billing_files = st.file_uploader(
            label="上传信用卡还款截图（支持多选）",
            type=["png", "jpg", "jpeg"],
            accept_multiple_files=True,
        )
        st.write("信用卡还款截图解析结果：")
        billing_result = {
            file.name: parse_billing(file.read()) for file in billing_files
        }
        st.table(billing_result)

    return invoice_result, billing_result


def process_data(
    invoice_result: dict[str, InvoiceInfo], billing_result: dict[str, BillingInfo]
):
    invoices = {}
    for filename, invoice_info in invoice_result.items():
        if invoice_info.payment_item not in invoices:
            invoices[invoice_info.payment_item] = {
                "paid": invoice_info.paid,
                "service_start": invoice_info.service_start,
                "service_through": invoice_info.service_through,
                "filenames": [filename],
            }
        else:
            invoices[invoice_info.payment_item]["paid"] += invoice_info.paid
            invoices[invoice_info.payment_item]["service_start"] = min(
                invoices[invoice_info.payment_item]["service_start"],
                invoice_info.service_start,
            )
            invoices[invoice_info.payment_item]["service_through"] = max(
                invoices[invoice_info.payment_item]["service_through"],
                invoice_info.service_through,
            )
            invoices[invoice_info.payment_item]["filenames"].append(filename)

    billings = {}
    for filename, billing_info in billing_result.items():
        if billing_info.payment_item not in billings:
            billings[billing_info.payment_item] = {
                "usd_amount": billing_info.usd_amount,
                "rmb_amount": billing_info.rmb_amount,
                "filenames": [filename],
            }
        else:
            billings[billing_info.payment_item]["usd_amount"] += billing_info.usd_amount
            billings[billing_info.payment_item]["rmb_amount"] += billing_info.rmb_amount
            billings[billing_info.payment_item]["filenames"].append(filename)

    result = []
    for payment_item in set(invoices) | set(billings):
        invoice_amount = invoices.get(payment_item, {}).get("paid", Decimal(0))
        billing_amount = billings.get(payment_item, {}).get("usd_amount", Decimal(0))
        if invoice_amount != billing_amount:
            raise ValueError(
                f"{payment_item!r}：账单金额 {invoice_amount} " f"与还款金额 {billing_amount} 不相等"
            )
        result.append(
            {
                "payment_item": payment_item,
                "usd_amount": billing_amount,
                "rmb_amount": billings.get(payment_item, {}).get(
                    "rmb_amount", Decimal(0)
                ),
                "service_start": invoices.get(payment_item, {}).get("service_start"),
                "service_through": invoices.get(payment_item, {}).get(
                    "service_through"
                ),
                "invoice_files": invoices.get(payment_item, {}).get("filenames", []),
                "billing_files": billings.get(payment_item, {}).get("filenames", []),
            }
        )

    return result


def main():
    st.set_page_config(layout="wide")
    st.title("彩云报销小助手 V2.0")
    st.write("上传账单 PDF 和信用卡还款截图，自动生成报销单和飞书审批内容。")

    invoice_result, billing_result = st_input_data()

    st.divider()

    st.header("数据校验")
    st.write("按 payment_item 分别校验账单中金额和信用卡还款截图中金额匹配。")

    try:
        result = process_data(invoice_result, billing_result)
    except ValueError as e:
        st.error(e)
        return

    st.success("校验通过，金额匹配无误。")
    st.table(result)

    st.divider()


if __name__ == "__main__":
    main()
