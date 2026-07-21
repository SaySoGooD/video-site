from abc import ABC, abstractmethod

from auth_test.application.common.dto import AuthTokenDTO, LoginDTO


class ILoginUseCase(ABC):
    @abstractmethod
    async def __call__(self, data: LoginDTO) -> AuthTokenDTO: ...
