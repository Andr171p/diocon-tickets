from dataclasses import dataclass, field
from uuid import UUID, uuid4


@dataclass
class Example:
    uid: UUID = field(default_factory=uuid4)

    @classmethod
    def create(cls):
        e = cls()
        print(e)
        return e


e = Example.create()
print(e.uid)
