import dataclasses
import pathlib
from collections import defaultdict
from decimal import Decimal
from io import BytesIO

import arrow
import fitz
import openpyxl
import streamlit as st
from streamlit.runtime.uploaded_file_manager import UploadedFile

from app.common import PaymentItem
from app.parse_billing import BillingInfo, BillingParser
from app.parse_invoice import InvoiceInfo, InvoiceParser


@dataclasses.dataclass
class PaymentItemData:
    payment_item: PaymentItem
    usd_amount: Decimal
    rmb_amount: Decimal
    service_start: str
    service_through: str
    invoice_files: list[UploadedFile]
    billing_files: list[UploadedFile]


class StreamlitApp:
    def __init__(self) -> None:
        # parser 初始化
        self.invoice_parser = InvoiceParser()
        self.billing_parser = BillingParser(
            st.secrets.aliyun_ocr.access_key_id, st.secrets.aliyun_ocr.access_key_secret
        )

        # 报销申请表 sheet 初始化
        application_tpl_path = pathlib.Path(
            st.secrets.reimbursement_application.template_path
        )
        if not application_tpl_path.exists() or not application_tpl_path.is_file():
            st.error("报销申请表模板文件不存在！")
            st.stop()
        self.workbook = openpyxl.load_workbook(application_tpl_path, keep_vba=True)
        self.worksheet = self.workbook["日常报销单"]

        self.application_submitter = st.secrets.reimbursement_application.submitter

    @st.cache_data(persist=True)
    def parse_billing_with_cache(_self, file_content: bytes) -> BillingInfo:
        return _self.billing_parser.parse_info(file_content)

    def st_unique_file_uploader(self, *args, **kw) -> None | list[UploadedFile]:
        file_or_files = st.file_uploader(*args, **kw)
        if file_or_files is None:
            return None
        elif isinstance(file_or_files, UploadedFile):
            return [file_or_files]

        file_contents = set()
        unique_files = []
        for file in file_or_files:
            file_content = file.getvalue()
            if file_content not in file_contents:
                file_contents.add(file_content)
                unique_files.append(file)
        return unique_files

    def part1_input_data(
        self,
    ) -> tuple[
        list[tuple[UploadedFile, InvoiceInfo]], list[tuple[UploadedFile, BillingInfo]]
    ]:
        st.header("上传")
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("上传账单 PDF")
            st.caption("目前支持的账单有：Mailgun、GitHub、Jira、1Password 和 Azure。")
            invoice_files = self.st_unique_file_uploader(
                label="上传账单 PDF（支持多选）",
                type=["pdf"],
                accept_multiple_files=True,
            )
            invoice_result = (
                [
                    (file, self.invoice_parser.parse_info(file.read()))
                    for file in invoice_files
                ]
                if invoice_files
                else []
            )
            invoice_result.sort(key=lambda x: (x[1].payment_item, x[1].paid))

            st.write("账单解析结果：")
            st.table({file.name: info for file, info in invoice_result})

        with col2:
            st.subheader("上传信用卡还款截图")
            st.caption("目前仅支持：招商银行信用卡设置外币消费人民币入账，在掌上生活 App 的还款截图。")
            billing_files = self.st_unique_file_uploader(
                label="上传信用卡还款截图（支持多选）",
                type=["png", "jpg", "jpeg"],
                accept_multiple_files=True,
            )
            billing_result = (
                [
                    (file, self.parse_billing_with_cache(file.read()))
                    for file in billing_files
                ]
                if billing_files
                else []
            )
            billing_result.sort(key=lambda x: (x[1].payment_item, x[1].usd_amount))

            st.write("信用卡还款截图解析结果：")
            st.table({file.name: info for file, info in billing_result})

        if not (invoice_result and billing_result):
            st.info("请上传账单 PDF 和信用卡还款截图。")
            st.stop()

        return invoice_result, billing_result

    def part2_process_data(
        self,
        invoice_result: list[tuple[UploadedFile, InvoiceInfo]],
        billing_result: list[tuple[UploadedFile, BillingInfo]],
    ) -> list[PaymentItemData]:
        st.header("校验")
        st.write("按 payment_item 分别校验账单中金额和信用卡还款截图中金额匹配。")

        invoices: dict[
            PaymentItem, list[tuple[UploadedFile, InvoiceInfo]]
        ] = defaultdict(list)
        for file, invoice_info in invoice_result:
            invoices[invoice_info.payment_item].append((file, invoice_info))

        billings: dict[
            PaymentItem, list[tuple[UploadedFile, BillingInfo]]
        ] = defaultdict(list)
        for file, billing_info in billing_result:
            billings[billing_info.payment_item].append((file, billing_info))

        payment_items = []
        for payment_item in PaymentItem:
            invoice_amount = sum(
                [info.paid for _, info in invoices[payment_item]], start=Decimal(0)
            )
            billing_amount = sum(
                [info.usd_amount for _, info in billings[payment_item]],
                start=Decimal(0),
            )
            if invoice_amount != billing_amount:
                st.error(
                    f"[{payment_item}]账单金额 {invoice_amount} "
                    f"与还款金额 {billing_amount} 不相等"
                )
                st.stop()
            if invoice_amount != Decimal(0):
                payment_items.append(
                    PaymentItemData(
                        payment_item=payment_item,
                        usd_amount=billing_amount,
                        rmb_amount=sum(
                            [info.rmb_amount for _, info in billings[payment_item]],
                            start=Decimal(0),
                        ),
                        service_start=min(
                            info.service_start for _, info in invoices[payment_item]
                        ),
                        service_through=max(
                            info.service_through for _, info in invoices[payment_item]
                        ),
                        invoice_files=[file for file, _ in invoices[payment_item]],
                        billing_files=[file for file, _ in billings[payment_item]],
                    )
                )

        st.success("校验通过，金额匹配无误。")
        st.balloons()

        display_items = []
        for item in payment_items:
            data = dataclasses.asdict(item)
            data["invoice_files"] = [file.name for file in data["invoice_files"]]
            data["billing_files"] = [file.name for file in data["billing_files"]]
            display_items.append(data)
        st.table(display_items)

        return payment_items

    def part3_generate_copies(self, payment_items: list[PaymentItemData]):
        st.subheader("生成飞书审批文案")

        st.write("报销事由")
        total_usd = sum([item.usd_amount for item in payment_items], start=Decimal(0))
        st.code(
            "\n".join(
                [
                    (
                        f"{item.payment_item.name}"
                        f"({item.payment_item.description}) 付款 USD {item.usd_amount}；"
                    )
                    for item in payment_items
                ]
                + ["----------", f"共计 USD {total_usd}。"]
            ),
            language=None,
        )
        st.write("费用明细")
        for item in payment_items:
            st.code(
                f"{item.payment_item.name}({item.payment_item.description}) "
                f"付款周期 {item.service_start} - {item.service_through}"
            )
            st.code(item.rmb_amount)

    def part4_generate_reimbursement_application(
        self, payment_items: list[PaymentItemData]
    ):
        st.subheader("生成彩云报销单")

        today = arrow.now(tz="Asia/Shanghai")

        self.worksheet["C5"] = self.application_submitter
        self.worksheet["F5"] = today.format("YYYY.MM")
        self.worksheet["C42"] = self.application_submitter
        self.worksheet["F42"] = today.format("YYYY.MM.DD")

        for index, item in enumerate(payment_items):
            row = index + 9
            self.worksheet[f"B{row}"] = item.service_start
            self.worksheet[f"C{row}"] = "200300"
            self.worksheet[f"D{row}"] = "软件"
            self.worksheet[f"E{row}"] = item.payment_item.capitalize()
            self.worksheet[f"G{row}"] = item.rmb_amount

        fp = BytesIO()
        self.workbook.save(fp)
        filename = f"{self.application_submitter}-{today.format('YYYYMMDD')}.xlsx"

        st.success("报销单生成成功！")
        st.download_button(label="下载报销单", data=fp, file_name=filename)

    def part5_generate_billing_pdf(self, payment_items: list[PaymentItemData]):
        st.subheader("生成还款截图 PDF")

        billing_files = sum([item.billing_files for item in payment_items], start=[])

        page_width, page_height = fitz.paper_size("A4-L")
        images_per_page = 4
        page_margin = 20
        inner_margin = 10
        image_rects = [
            fitz.Rect(
                (page_width - 2 * page_margin - (images_per_page - 1) * inner_margin)
                / images_per_page
                * idx
                + page_margin
                + inner_margin * idx,
                0,
                (page_width - 2 * page_margin - (images_per_page - 1) * inner_margin)
                / images_per_page
                * (idx + 1)
                + page_margin
                + inner_margin * idx,
                page_height,
            )
            for idx in range(images_per_page)
        ]

        billing_pdf = fitz.Document()
        current_page = None
        for idx, file in enumerate(billing_files):
            page_idx = idx % images_per_page
            if not current_page or page_idx == 0:
                current_page = billing_pdf.new_page(
                    pno=-1, width=page_width, height=page_height
                )
            current_page.insert_image(image_rects[page_idx], stream=file.getvalue())

        fp = BytesIO()
        billing_pdf.ez_save(fp)
        st.success("还款截图 PDF 生成成功！")
        st.download_button(
            label="下载还款截图 PDF",
            data=fp,
            file_name=f"还款截图-{arrow.now(tz='Asia/Shanghai').format('YYYYMMDD')}.pdf",
        )

    def run(self):
        st.set_page_config(layout="wide")
        st.title("彩云报销小助手 V2.0")
        st.write("上传账单 PDF 和信用卡还款截图，自动生成报销单和飞书审批内容。")

        invoice_result, billing_result = self.part1_input_data()

        st.divider()

        payment_items = self.part2_process_data(invoice_result, billing_result)

        st.divider()

        st.header("生成")
        col1, col2 = st.columns(2)

        with col1:
            self.part3_generate_copies(payment_items)
        with col2:
            self.part4_generate_reimbursement_application(payment_items)
            self.part5_generate_billing_pdf(payment_items)


if __name__ == "__main__":
    stapp = StreamlitApp()
    stapp.run()
