import re
from dataclasses import dataclass
from decimal import Decimal

from app.aliyun_ocr import AliyunOCR
from app.common import PaymentItem

BILLING_KEYWORDS = {
    "github": PaymentItem.GITHUB,
    "mailgun": PaymentItem.MAILGUN,
    "atlassian": PaymentItem.JIRA,
    "1password": PaymentItem.ONEPASSWD,
    "microsoft": PaymentItem.AZURE,
}
BILLING_RMB_AMOUNT_REGEX = r"￥(\d+\.\d{2})已入账"
BILLING_USD_AMOUNT_REGEX = r"交易地金额：(\d+\.\d{2})"


@dataclass
class BillingInfo:
    payment_item: PaymentItem
    usd_amount: Decimal
    rmb_amount: Decimal


class BillingParser:
    def __init__(self, aliyun_access_key_id, aliyun_access_key_secret) -> None:
        self.aliyun_ocr_client = AliyunOCR(
            access_key_id=aliyun_access_key_id,
            access_key_secret=aliyun_access_key_secret,
        )

    def parse_info(self, filename) -> BillingInfo:
        content = self.aliyun_ocr_client.request(filename=filename)
        lower_content = content.replace(" ", "").lower()

        for keyword in BILLING_KEYWORDS:
            if keyword in lower_content:
                payment_item = BILLING_KEYWORDS[keyword]
                break
        else:
            raise ValueError(f"Unknown billing item for {filename}")

        rmb_amount_match = re.search(BILLING_RMB_AMOUNT_REGEX, lower_content)
        if not rmb_amount_match:
            raise ValueError(f"Could not find RMB amount for {filename}")
        rmb_amount = Decimal(rmb_amount_match.group(1))

        usd_amount_match = re.search(BILLING_USD_AMOUNT_REGEX, lower_content)
        if not usd_amount_match:
            raise ValueError(f"Could not find USD amount for {filename}")
        usd_amount = Decimal(usd_amount_match.group(1))

        return BillingInfo(
            payment_item=payment_item, usd_amount=usd_amount, rmb_amount=rmb_amount
        )
