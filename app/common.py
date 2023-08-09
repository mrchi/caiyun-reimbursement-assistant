from enum import StrEnum


class PaymentItem(StrEnum):
    GITHUB = "github"
    MAILGUN = "mailgun"
    JIRA = "jira"
    ONEPASSWD = "1password"
    AZURE = "azure"
