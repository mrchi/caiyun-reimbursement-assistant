from enum import StrEnum


class PaymentItem(StrEnum):
    GITHUB = "github"
    MAILGUN = "mailgun"
    Jira = "jira"
    ONEPASSWD = "1password"
