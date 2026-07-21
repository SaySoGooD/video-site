from dependency_injector import containers, providers
from redis.asyncio import from_url as redis_from_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from auth_test.adapter.cache.null_cache import NullCache
from auth_test.adapter.cache.redis_cache import RedisCache
from auth_test.adapter.database.unit_of_work import SqlAlchemyUnitOfWork
from auth_test.adapter.memory.storage import InMemoryStorage
from auth_test.adapter.memory.unit_of_work import InMemoryUnitOfWork
from auth_test.adapter.security.argon2_password_hasher import (
    Argon2PasswordHasher,
)
from auth_test.adapter.security.password_hasher import PBKDF2PasswordHasher
from auth_test.adapter.security.token_service import JwtTokenService
from auth_test.application.access_control.usecases.assign_role_to_user_usecase import (
    AssignRoleToUserUseCase,
)
from auth_test.application.access_control.usecases.create_permission_usecase import (
    CreatePermissionUseCase,
)
from auth_test.application.access_control.usecases.create_role_usecase import (
    CreateRoleUseCase,
)
from auth_test.application.access_control.usecases.delete_role_usecase import (
    DeleteRoleUseCase,
)
from auth_test.application.access_control.usecases.grant_permission_to_role_usecase import (
    GrantPermissionToRoleUseCase,
)
from auth_test.application.access_control.usecases.list_permissions_usecase import (
    ListPermissionsUseCase,
)
from auth_test.application.access_control.usecases.list_roles_usecase import (
    ListRolesUseCase,
)
from auth_test.application.access_control.usecases.list_users_usecase import (
    ListUsersUseCase,
)
from auth_test.application.access_control.usecases.revoke_permission_from_role_usecase import (
    RevokePermissionFromRoleUseCase,
)
from auth_test.application.access_control.usecases.revoke_role_from_user_usecase import (
    RevokeRoleFromUserUseCase,
)
from auth_test.application.auth.usecases.authenticate_usecase import (
    AuthenticateUseCase,
)
from auth_test.application.auth.usecases.delete_user_usecase import (
    DeleteUserUseCase,
)
from auth_test.application.auth.usecases.login_usecase import LoginUseCase
from auth_test.application.auth.usecases.logout_usecase import LogoutUseCase
from auth_test.application.auth.usecases.refresh_token_usecase import (
    RefreshTokenUseCase,
)
from auth_test.application.auth.usecases.register_user_usecase import (
    RegisterUserUseCase,
)
from auth_test.application.auth.usecases.update_user_usecase import (
    UpdateUserUseCase,
)
from auth_test.infrastructure.config import Config


class Container(containers.DeclarativeContainer):
    """Application dependency injection container.

    Singletons hold process-wide resources (config, DB engine, hasher, token
    service). The unit of work is a ``Factory`` so every use case resolution
    gets a fresh transaction; use cases are ``Factory`` too and receive that
    unit of work.
    """

    config: providers.Singleton[Config] = providers.Singleton(Config)

    engine = providers.Singleton(
        create_async_engine,
        config.provided.database_url,
        pool_pre_ping=True,
    )

    session_factory = providers.Singleton(
        async_sessionmaker,
        bind=engine,
        expire_on_commit=False,
    )

    memory_storage = providers.Singleton(InMemoryStorage)

    _db_backend = providers.Callable(
        lambda mock: "memory" if mock else "postgres",
        config.provided.MOCK_DB,
    )

    uow = providers.Selector(
        _db_backend,
        postgres=providers.Factory(
            SqlAlchemyUnitOfWork, session_factory=session_factory
        ),
        memory=providers.Factory(InMemoryUnitOfWork, storage=memory_storage),
    )

    password_hasher = providers.Selector(
        config.provided.PASSWORD_HASHER,
        argon2=providers.Singleton(Argon2PasswordHasher),
        pbkdf2=providers.Singleton(PBKDF2PasswordHasher),
    )

    _cache_backend = providers.Callable(
        lambda url: "redis" if url else "null",
        config.provided.REDIS_URL,
    )
    redis_client = providers.Singleton(
        redis_from_url,
        config.provided.REDIS_URL,
        decode_responses=True,
    )
    cache = providers.Selector(
        _cache_backend,
        redis=providers.Singleton(RedisCache, client=redis_client),
        null=providers.Singleton(NullCache),
    )

    token_service = providers.Singleton(
        JwtTokenService,
        secret=config.provided.JWT_SECRET,
        algorithm=config.provided.JWT_ALGORITHM,
        access_expire_minutes=config.provided.ACCESS_TOKEN_EXPIRE_MINUTES,
        refresh_expire_minutes=config.provided.REFRESH_TOKEN_EXPIRE_MINUTES,
    )

    register_user_usecase = providers.Factory(
        RegisterUserUseCase, uow=uow, hasher=password_hasher
    )
    login_usecase = providers.Factory(
        LoginUseCase, uow=uow, hasher=password_hasher, token_service=token_service
    )
    logout_usecase = providers.Factory(
        LogoutUseCase, uow=uow, token_service=token_service
    )
    refresh_token_usecase = providers.Factory(
        RefreshTokenUseCase, uow=uow, token_service=token_service
    )
    authenticate_usecase = providers.Factory(
        AuthenticateUseCase,
        uow=uow,
        token_service=token_service,
        cache=cache,
        cache_ttl_seconds=config.provided.AUTH_CACHE_TTL_SECONDS,
    )
    update_user_usecase = providers.Factory(
        UpdateUserUseCase, uow=uow, cache=cache
    )
    delete_user_usecase = providers.Factory(
        DeleteUserUseCase, uow=uow, cache=cache
    )

    list_roles_usecase = providers.Factory(ListRolesUseCase, uow=uow)
    create_role_usecase = providers.Factory(CreateRoleUseCase, uow=uow)
    delete_role_usecase = providers.Factory(DeleteRoleUseCase, uow=uow)
    grant_permission_to_role_usecase = providers.Factory(
        GrantPermissionToRoleUseCase, uow=uow
    )
    revoke_permission_from_role_usecase = providers.Factory(
        RevokePermissionFromRoleUseCase, uow=uow
    )

    list_permissions_usecase = providers.Factory(ListPermissionsUseCase, uow=uow)
    create_permission_usecase = providers.Factory(CreatePermissionUseCase, uow=uow)

    list_users_usecase = providers.Factory(ListUsersUseCase, uow=uow)
    assign_role_to_user_usecase = providers.Factory(
        AssignRoleToUserUseCase, uow=uow, cache=cache
    )
    revoke_role_from_user_usecase = providers.Factory(
        RevokeRoleFromUserUseCase, uow=uow, cache=cache
    )
