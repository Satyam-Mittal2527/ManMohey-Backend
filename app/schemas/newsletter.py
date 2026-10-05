from pydantic import BaseModel, EmailStr, field_validator


class NewsletterSubscribeRequest(BaseModel):
    email: EmailStr

    @field_validator("email", mode="before")
    @classmethod
    def trim_email(cls, value):
        return value.strip() if isinstance(value, str) else value
