from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    display_name: str = Field(min_length=1, max_length=120)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class UserOut(BaseModel):
    id: str
    email: str
    display_name: str
    target_band: float | None
    preferred_module: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=120)
    target_band: float | None = Field(default=None, ge=4, le=9)
    preferred_module: str | None = Field(default=None, pattern="^(academic|general)$")
