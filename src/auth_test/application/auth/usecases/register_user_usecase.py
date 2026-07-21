from auth_test.application.auth.interfaces.i_register_user_usecase import (
    IRegisterUserUseCase,
)
from auth_test.application.common.dto import RegisterUserDTO
from auth_test.application.common.errors import (
    EmailAlreadyExistsError,
    PasswordMismatchError,
)
from auth_test.application.common.interfaces.i_unit_of_work import IUnitOfWork
from auth_test.application.common.interfaces.security.i_password_hasher import (
    IPasswordHasher,
)
from auth_test.entities.user.models import User
from auth_test.entities.user.value_objects import Email, UserId


class RegisterUserUseCase(IRegisterUserUseCase):
    """Create a new, active account with a hashed password.

    The whole operation runs in one transaction: the uniqueness check and the
    insert commit together, so two concurrent signups cannot both succeed
    (the DB unique constraint is the final backstop).
    """

    def __init__(self, uow: IUnitOfWork, hasher: IPasswordHasher) -> None:
        self._uow = uow
        self._hasher = hasher

    async def __call__(self, data: RegisterUserDTO) -> User:
        if data.password != data.password_repeat:
            raise PasswordMismatchError()

        async with self._uow as uow:
            if await uow.users.get_by_email(data.email) is not None:
                raise EmailAlreadyExistsError()

            user = User(
                id=UserId(0),
                email=Email(data.email),
                password_hash=self._hasher.hash(data.password),
                first_name=data.first_name,
                last_name=data.last_name,
                middle_name=data.middle_name,
                is_active=True,
                is_superuser=False,
            )
            created = await uow.users.add(user)
            await uow.commit()
            return created
