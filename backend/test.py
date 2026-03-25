from dataclasses import asdict
from uuid import uuid4

from pydantic import SecretStr

from src.iam.domain.entities import User
from src.iam.domain.vo import Username, UserRole

user = User(
    username=Username("exampleuser"),
    role=UserRole.CUSTOMER,
    email="email@example.com",
    password_hash=SecretStr("cokWIFNGGN"),
    counterparty_id=uuid4(),
)

print(asdict(user))
