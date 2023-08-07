import re
from dataclasses import dataclass
from decimal import Decimal

import arrow
from fitz import Document

from app.common import PaymentItem

PAID_REGEX = {
    PaymentItem.GITHUB: r"Total\n\$(\d+\.\d{2}) USD\*",
    PaymentItem.MAILGUN: r"PAID\n\$(\d+\.\d{2})",
    PaymentItem.Jira: r"Total Paid: USD (\d+\.\d{2})",
    PaymentItem.ONEPASSWD: r"Paid\n\$(\d+\.\d{2})",
}

SERVICE_START_REGEX = {
    PaymentItem.GITHUB: r"Date\n(\d{4}-\d{2}-\d{2})",
    PaymentItem.MAILGUN: r"Foundation\n(\w+ \d{1,2}, \d{4}) - \w+ \d{1,2}, \d{4}",
    PaymentItem.Jira: r"Billing Period: (\w+ \d{1,2}, \d{4}) - \w+ \d{1,2}, \d{4}",
    PaymentItem.ONEPASSWD: r"(\w+ \d{1,2}, \d{4}) to \w+ \d{1,2}, \d{4}",
}

SERVICE_THROUGH_REGEX = {
    PaymentItem.GITHUB: r"For service through\n(\d{4}-\d{2}-\d{2})",
    PaymentItem.MAILGUN: r"Foundation\n\w+ \d{1,2}, \d{4} - (\w+ \d{1,2}, \d{4})",
    PaymentItem.Jira: r"Billing Period: \w+ \d{1,2}, \d{4} - (\w+ \d{1,2}, \d{4})",
    PaymentItem.ONEPASSWD: r"\w+ \d{1,2}, \d{4} to (\w+ \d{1,2}, \d{4})",
}

DATE_FORMAT = {
    PaymentItem.GITHUB: "YYYY-MM-DD",
    PaymentItem.MAILGUN: "MMM D, YYYY",
    PaymentItem.Jira: "MMM D, YYYY",
    PaymentItem.ONEPASSWD: "MMMM D, YYYY",
}

INVOICE_KEYWORDS = {
    "GitHub, Inc": PaymentItem.GITHUB,
    "Mailgun Technologies, Inc": PaymentItem.MAILGUN,
    "Atlassian Pty Ltd": PaymentItem.Jira,
    "1Password": PaymentItem.ONEPASSWD,
}


@dataclass
class InvoiceInfo:
    payment_item: PaymentItem
    paid: Decimal
    service_start: str
    service_through: str


class InvoiceParser:
    def __init__(self, filename, keywords: dict[str, PaymentItem] = INVOICE_KEYWORDS):
        self.contents = self.read_pdf(filename=filename)
        self.payment_item = self.get_payment_item(keywords=keywords)
        self.filename = filename

    def __repr__(self):
        return f"<InvoiceParser payment_item={self.payment_item!r} filename={self.filename!r}>"  # noqa: E501

    @staticmethod
    def read_pdf(filename) -> str:
        with Document(filename) as doc:
            return "\n".join(page.get_text() for page in doc)

    def get_payment_item(self, keywords: dict[str, PaymentItem]) -> PaymentItem:
        for keyword in keywords:
            if keyword in self.contents:
                return keywords[keyword]

        raise ValueError("Could not match any payment item")

    def parse_info(self) -> InvoiceInfo:
        paid_match = re.search(PAID_REGEX[self.payment_item], self.contents)
        if not paid_match:
            raise ValueError("Could not find paid amount")
        paid = Decimal(paid_match.group(1))

        service_start_match = re.search(
            SERVICE_START_REGEX[self.payment_item], self.contents
        )
        if not service_start_match:
            raise ValueError("Could not find service start date")
        service_start = arrow.get(
            service_start_match.group(1), DATE_FORMAT[self.payment_item]
        ).format("YYYY-MM-DD")

        service_through_match = re.search(
            SERVICE_THROUGH_REGEX[self.payment_item], self.contents
        )
        if not service_through_match:
            raise ValueError("Could not find service through date")
        service_through = arrow.get(
            service_through_match.group(1),
            DATE_FORMAT[self.payment_item],
        ).format("YYYY-MM-DD")

        return InvoiceInfo(
            payment_item=self.payment_item,
            paid=paid,
            service_start=service_start,
            service_through=service_through,
        )
