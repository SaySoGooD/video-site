from abc import ABC, abstractmethod

from auth_test.application.common.dto import AuthTokenDTO


class IRefreshTokenUseCase(ABC):
    @abstractmethod
    async def __call__(self, refresh_token: str) -> AuthTokenDTO: ...
