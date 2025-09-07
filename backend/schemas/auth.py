from pydantic import BaseModel, EmailStr, constr


class RegisterIn(BaseModel):
    username: constr(strip_whitespace=True, min_length=3, max_length=40)
    email: EmailStr
    password: constr(min_length=8)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class MeOut(BaseModel):
    username: str
    email: EmailStr
