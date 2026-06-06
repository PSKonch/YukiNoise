from enum import StrEnum


class NotificationType(StrEnum):
    NEW_FOLLOWER = "new_follower"
    NEW_LIKE = "new_like"
    NEW_COMMENTARY = "new_commentary"
    NEW_POST = "new_post"
    NEW_RELEASE = "new_release"
    EMAIL_VERIFICATION = "email_verification"
