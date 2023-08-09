import pathlib
import re
from dataclasses import dataclass
from decimal import Decimal

import arrow
from fitz import Document

from app.common import PaymentItem

PAID_REGEX = {
    PaymentItem.GITHUB: r"Total\n\$(\d+\.\d{2}) USD\*",
    PaymentItem.MAILGUN: r"PAID\n\$(\d+\.\d{2})",
    PaymentItem.JIRA: r"Total Paid: USD (\d+\.\d{2})",
    PaymentItem.ONEPASSWD: r"Paid\n\$([\d,]+\.\d{2})",
    PaymentItem.AZURE: r"Total Amount\nUSD ([\d,]+\.\d{2})",
}

SERVICE_START_REGEX = {
    PaymentItem.GITHUB: r"Date\n(\d{4}-\d{2}-\d{2})",
    PaymentItem.MAILGUN: r"Foundation\n\d\n.+?\n(\w+ \d{1,2}, \d{4}) - \w+ \d{1,2}, \d{4}",  # noqa: E501
    PaymentItem.JIRA: r"Billing Period: (\w+ \d{1,2}, \d{4}) - \w+ \d{1,2}, \d{4}",
    PaymentItem.ONEPASSWD: r"(\w+ \d{1,2}, \d{4}) to \w+ \d{1,2}, \d{4}",
    PaymentItem.AZURE: r"This invoice is for the billing period (\d{2}/\d{2}/\d{4}) - \d{2}/\d{2}/\d{4}",  # noqa: E501
}

SERVICE_THROUGH_REGEX = {
    PaymentItem.GITHUB: r"For service through\n(\d{4}-\d{2}-\d{2})",
    PaymentItem.MAILGUN: r"Foundation\n\d\n.+?\n\w+ \d{1,2}, \d{4} - (\w+ \d{1,2}, \d{4})",  # noqa: E501
    PaymentItem.JIRA: r"Billing Period: \w+ \d{1,2}, \d{4} - (\w+ \d{1,2}, \d{4})",
    PaymentItem.ONEPASSWD: r"\w+ \d{1,2}, \d{4} to (\w+ \d{1,2}, \d{4})",
    PaymentItem.AZURE: r"This invoice is for the billing period \d{2}/\d{2}/\d{4} - (\d{2}/\d{2}/\d{4})",  # noqa: E501
}

DATE_FORMAT = {
    PaymentItem.GITHUB: "YYYY-MM-DD",
    PaymentItem.MAILGUN: "MMM D, YYYY",
    PaymentItem.JIRA: "MMM D, YYYY",
    PaymentItem.ONEPASSWD: "MMMM D, YYYY",
    PaymentItem.AZURE: "MM/DD/YYYY",
}

INVOICE_KEYWORDS = {
    "GitHub, Inc": PaymentItem.GITHUB,
    "Mailgun Technologies, Inc": PaymentItem.MAILGUN,
    "Atlassian Pty Ltd": PaymentItem.JIRA,
    "1Password": PaymentItem.ONEPASSWD,
    "Microsoft Corporation": PaymentItem.AZURE,
}


@dataclass
class InvoiceInfo:
    payment_item: PaymentItem
    paid: Decimal
    service_start: str
    service_through: str


class InvoiceParser:
    def __init__(self):
        pass

    @staticmethod
    def read_pdf(filename: bytes | str | pathlib.Path) -> str:
        if isinstance(filename, bytes):
            params = {"stream": filename}
        elif isinstance(filename, (str, pathlib.Path)):
            params = {"filename": filename}
        else:
            raise TypeError(f"Unsupported type: {type(filename)}")

        with Document(**params) as doc:
            return "\n".join(page.get_text(sort=True) for page in doc)

    def parse_info(self, filename: bytes | str | pathlib.Path) -> InvoiceInfo:
        content = self.read_pdf(filename=filename)

        for keyword in INVOICE_KEYWORDS:
            if keyword in content:
                payment_item = INVOICE_KEYWORDS[keyword]
                break
        else:
            raise ValueError(f"Could not match any payment item for {filename}")

        paid_match = re.search(PAID_REGEX[payment_item], content)
        if not paid_match:
            raise ValueError(f"Could not find paid amount for {filename}")
        paid = Decimal(paid_match.group(1).replace(",", ""))

        service_start_match = re.search(SERVICE_START_REGEX[payment_item], content)
        if not service_start_match:
            raise ValueError(f"Could not find service start date for {filename}")
        service_start = arrow.get(
            service_start_match.group(1), DATE_FORMAT[payment_item]
        ).format("YYYY-MM-DD")

        service_through_match = re.search(SERVICE_THROUGH_REGEX[payment_item], content)
        if not service_through_match:
            raise ValueError(f"Could not find service through date for {filename}")
        service_through = arrow.get(
            service_through_match.group(1),
            DATE_FORMAT[payment_item],
        ).format("YYYY-MM-DD")

        return InvoiceInfo(
            payment_item=payment_item,
            paid=paid,
            service_start=service_start,
            service_through=service_through,
        )
