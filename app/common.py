from enum import StrEnum


class PaymentItem(StrEnum):
    JIRA = "jira"
    MAILGUN = "mailgun"
    AZURE = "azure"
    GITHUB = "github"
    ONEPASSWD = "1password"

    @property
    def description(self):
        return {
            self.JIRA: "缺陷跟踪管理系统",
            self.MAILGUN: "海外邮件发送服务",
            self.AZURE: "微软 Azure 云服务",
            self.GITHUB: "GitHub 组织账号",
            self.ONEPASSWD: "密码管理工具",
        }[self]
