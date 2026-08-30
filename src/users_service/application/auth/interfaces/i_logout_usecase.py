from abc import ABC, abstractmethod


class ILogoutUseCase(ABC):
    @abstractmethod
    async def __call__(self, token: str) -> None: ...
