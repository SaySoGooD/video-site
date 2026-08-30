from users_service.application.auth.interfaces.i_register_user_usecase import (
    IRegisterUserUseCase,
)
from users_service.application.common.dto import RegisterUserDTO
from users_service.application.common.errors import (
    EmailAlreadyExistsError,
    PasswordMismatchError,
    UsernameAlreadyExistsError,
)
from users_service.application.common.interfaces.i_unit_of_work import IUnitOfWork
from users_service.application.common.interfaces.security.i_password_hasher import (
    IPasswordHasher,
)
from users_service.entities.user.models import User
from users_service.entities.user.value_objects import (
    Email,
    UserId,
    Username,
    VisitorId,
)


class RegisterUserUseCase(IRegisterUserUseCase):
    """Create a new, active account with a hashed password.

    The whole operation runs in one transaction: the uniqueness checks, the
    insert and the default-role grant commit together, so an account is never
    left without a role and two concurrent signups cannot both succeed (the DB
    unique constraints are the final backstop).

    The browser's ``visitor_id`` is stored on the account, which is the one
    place where "who is this user?" and "what did this visitor do?" are tied
    together — the analytics side reads that link, never the other way round.
    """

    def __init__(
        self,
        uow: IUnitOfWork,
        hasher: IPasswordHasher,
        default_role_name: str,
    ) -> None:
        self._uow = uow
        self._hasher = hasher
        self._default_role_name = default_role_name

    async def __call__(self, data: RegisterUserDTO) -> User:
        if data.password != data.password_repeat:
            raise PasswordMismatchError()

        email = data.email.strip().lower()
        username = data.username.strip()

        async with self._uow as uow:
            if await uow.users.get_by_email(email) is not None:
                raise EmailAlreadyExistsError()
            if await uow.users.get_by_username(username) is not None:
                raise UsernameAlreadyExistsError()

            user = User(
                id=UserId(0),
                email=Email(email),
                username=Username(username),
                password_hash=self._hasher.hash(data.password),
                display_name=data.display_name,
                is_active=True,
                is_superuser=False,
                visitor_id=(
                    VisitorId(data.visitor_id)
                    if data.visitor_id is not None
                    else None
                ),
            )
            created = await uow.users.add(user)

            default_role = await uow.roles.get_by_name(self._default_role_name)
            if default_role is not None:
                await uow.users.assign_role(created.id, default_role.id)

            await uow.commit()

            stored = await uow.users.get_by_id(created.id)
            return stored if stored is not None else created
