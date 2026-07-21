# auth-test — руководство пользователя

Руководство по эксплуатации развёрнутого API системы аутентификации и
авторизации.

- **Базовый URL:** `https://api.saysogood.dev/auth-test`
- **Интерактивная документация (Swagger):** https://api.saysogood.dev/auth-test/docs

---

## 1. Ключевые понятия

**Аутентификация (подтверждение личности)** — вход по адресу электронной почты
и паролю. В ответ выдаётся **JWT-токен**, который необходимо передавать в каждом
последующем запросе в заголовке:

```
Authorization: Bearer <access_token>
```

Если запрос невозможно сопоставить с вошедшим пользователем (токен отсутствует,
повреждён, истёк либо сессия отозвана), сервер возвращает **401 Unauthorized**.

**Авторизация (проверка полномочий)** — модель RBAC: **пользователь → роли →
права**. Право представляет собой пару `ресурс:действие` (например,
`document:read`). Права предоставляются пользователю исключительно через роли.
Если пользователь идентифицирован, но необходимое право отсутствует, сервер
возвращает **403 Forbidden**.

**Два типа токенов: access и refresh.** При входе выдаётся пара токенов:

- **access** — токен с коротким сроком действия (**15 минут**,
  `ACCESS_TOKEN_EXPIRE_MINUTES`), передаётся в заголовке `Authorization` при
  каждом запросе. В случае компрометации срок его использования ограничен.
- **refresh** — токен с длительным сроком действия (**7 дней**,
  `REFRESH_TOKEN_EXPIRE_MINUTES`), предназначен исключительно для запроса
  `POST /auth/refresh` и позволяет получить новый access-токен без повторного
  ввода пароля.

**Сессии и отзыв токенов.** При каждом входе на сервере создаётся запись сессии,
её идентификатор (`jti`) включается в оба токена. Благодаря этому операции
logout и мягкого удаления немедленно аннулируют ещё не истёкшие токены (сессия
помечается как отозванная). При обновлении токенов предыдущая сессия отзывается
и создаётся новая (**ротация**): повторное использование одного refresh-токена
невозможно. Если скомпрометированный refresh-токен будет использован после его
применения легитимным клиентом, сервер вернёт `401`, что позволяет выявить факт
компрометации.

Роли пользователя считываются из базы данных **при каждом запросе**.
Следовательно, изменение ролей или прав, выполненное администратором, вступает в
силу при следующем запросе; повторный вход не требуется при условии, что ранее
выданный токен ещё действителен.

**Хранение паролей.** Пароли хранятся исключительно в виде хэшей. По умолчанию
применяется алгоритм **Argon2id** (memory-hard, устойчивый к перебору на
GPU/ASIC); альтернативно доступен PBKDF2. Алгоритм задаётся параметром
`PASSWORD_HASHER`.

**Кэширование (необязательно).** При указании параметра `REDIS_URL` загрузка
пользователя при аутентификации кэшируется в Redis, что снижает нагрузку на базу
данных. Кэш не влияет на гарантии безопасности: действительность сессии
проверяется в базе данных при каждом запросе (logout и удаление учётной записи
действуют немедленно), а запись в кэше инвалидируется при изменении ролей или
профиля пользователя. Если `REDIS_URL` не задан, кэширование отключено и Redis
не требуется.

---

## 2. Демонстрационные данные

При запуске, если база данных пуста, создаётся набор прав, ролей и пользователей.

**Права (`ресурс:действие`):**

| id | право | назначение |
|----|-------|------------|
| 1 | `document:read` | просмотр документов |
| 2 | `document:create` | создание документов |
| 3 | `document:update` | редактирование документов |
| 4 | `document:delete` | удаление документов |
| 5 | `report:read` | просмотр отчётов |
| 6 | `report:export` | выгрузка отчётов |
| 7 | `access_control:manage` | управление ролями и правами (административный API) |

**Роли:**

| id | роль | права |
|----|------|-------|
| 1 | `admin` | все семь прав (пользователь также имеет признак `is_superuser`) |
| 2 | `editor` | document read/create/update, report read |
| 3 | `viewer` | document read, report read |

**Пользователи (email / пароль):**

| email | пароль | роль |
|-------|--------|------|
| `admin@example.com` | `admin123` | admin |
| `editor@example.com` | `editor123` | editor |
| `viewer@example.com` | `viewer123` | viewer |

> Демонстрационные учётные записи используют простые пароли и предназначены
> только для ознакомления.

---

## 3. Работа с учётной записью (модуль «Пользователь»)

В примерах используется утилита `curl`. Базовый URL вынесен в переменную:

```bash
B=https://api.saysogood.dev/auth-test
```

### 3.1. Регистрация

Требуются имя, адрес электронной почты, пароль и его повтор. Минимальная длина
пароля — 6 символов.

```bash
curl -X POST $B/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "ivan@example.com",
    "password": "secret123",
    "password_repeat": "secret123",
    "first_name": "Иван",
    "last_name": "Петров",
    "middle_name": "Сергеевич"
  }'
```

- `201 Created` — возвращается профиль (роли и, соответственно, права
  отсутствуют).
- `409 Conflict` — адрес электронной почты уже занят.
- `422 Unprocessable Entity` — пароли не совпадают либо не пройдена валидация
  полей.

### 3.2. Вход и получение токена

```bash
curl -X POST $B/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "ivan@example.com", "password": "secret123"}'
```

Ответ содержит пару токенов:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "access_expires_at": "2026-07-21T16:21:02.190725Z",
  "refresh_expires_at": "2026-07-28T16:06:02.190926Z"
}
```

`access_token` передаётся в заголовке `Authorization: Bearer`; `refresh_token`
подлежит защищённому хранению и используется только для запроса `/auth/refresh`
(см. п. 3.2.1).

Код `401` возвращается при неверном адресе электронной почты или пароле, а также
при деактивированной учётной записи. Ответ идентичен для всех случаев, что
исключает возможность перебором определить существующие адреса.

Для удобства токен можно сохранить в переменную окружения:

```bash
TOKEN=$(curl -s -X POST $B/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"ivan@example.com","password":"secret123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

### 3.2.1. Обновление токена (refresh)

По истечении срока действия access-токена (15 минут) повторный ввод пароля не
требуется. Для получения новой пары токенов выполняется обмен refresh-токена:

```bash
curl -X POST $B/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<refresh_token, полученный при входе>"}'
```

Возвращается новая пара `access_token` и `refresh_token`. Существенные условия:

- предыдущий `refresh_token` после обмена становится недействительным (ротация);
  следует использовать новый;
- refresh-токен не может использоваться в качестве Bearer-токена на обычных
  эндпоинтах — там требуется access-токен (в противном случае возвращается `401`);
- access-токен не может использоваться для запроса `/auth/refresh` (также `401`);
- недействительный, просроченный либо отозванный refresh-токен возвращает `401`.

### 3.3. Просмотр профиля

```bash
curl $B/auth/me -H "Authorization: Bearer $TOKEN"
```

Возвращается профиль пользователя с указанием ролей и сводного списка прав
(`permissions`).

### 3.4. Редактирование профиля

Изменяются только переданные поля; остальные сохраняют прежние значения.

```bash
curl -X PATCH $B/auth/me \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"first_name": "Иван", "last_name": "Иванов"}'
```

При изменении адреса электронной почты на уже занятый возвращается `409`.

### 3.5. Выход (logout)

```bash
curl -X POST $B/auth/logout -H "Authorization: Bearer $TOKEN"
```

Возвращается `204 No Content`. Сессия отзывается; переданный токен становится
недействительным (последующий запрос с ним вернёт `401`).

### 3.6. Мягкое удаление учётной записи

```bash
curl -X DELETE $B/auth/me -H "Authorization: Bearer $TOKEN"
```

Возвращается `204 No Content`. Выполняются следующие действия:

- учётной записи присваивается признак `is_active=false` (запись в базе данных
  сохраняется);
- все сессии пользователя отзываются, что эквивалентно немедленному выходу;
- повторный вход под этой учётной записью становится невозможным (`401` при
  попытке входа).

---

## 4. Проверка прав доступа (модули «Разграничение прав» и «Бизнес-объекты»)

Эндпоинты бизнес-объектов (mock) защищены конкретными правами. Ответ всегда
соответствует одному из трёх вариантов: **200** (доступ предоставлен, возвращаются
данные), **401** (пользователь не идентифицирован), **403** (пользователь
идентифицирован, но право отсутствует).

| эндпоинт | требуемое право |
|----------|-----------------|
| `GET /documents` | `document:read` |
| `POST /documents` | `document:create` |
| `PUT /documents/{id}` | `document:update` |
| `DELETE /documents/{id}` | `document:delete` |
| `GET /reports` | `report:read` |
| `POST /reports/export` | `report:export` |

### Пример: три варианта результата

```bash
# вход под учётной записью viewer (доступ только на чтение)
VT=$(curl -s -X POST $B/auth/login -H "Content-Type: application/json" \
  -d '{"email":"viewer@example.com","password":"viewer123"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# 401 — запрос без токена
curl -s -o /dev/null -w "%{http_code}\n" $B/documents

# 200 — роль viewer обладает правом document:read
curl -s -o /dev/null -w "%{http_code}\n" -H "Authorization: Bearer $VT" $B/documents

# 403 — у роли viewer отсутствует право document:create
curl -s -o /dev/null -w "%{http_code}\n" -X POST -H "Authorization: Bearer $VT" $B/documents
```

Пользователь с ролью `admin` (superuser) проходит любую проверку прав
автоматически.

---

## 5. Административный API: управление правилами доступа

Все эндпоинты в пространстве `/admin/*` требуют права `access_control:manage`
(предоставлено роли `admin`). Пользователь без данного права получает `403`,
неидентифицированный запрос — `401`.

Предварительно выполняется вход под учётной записью администратора:

```bash
AT=$(curl -s -X POST $B/auth/login -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
AUTH="Authorization: Bearer $AT"
```

### 5.1. Просмотр текущих правил

```bash
curl $B/admin/permissions -H "$AUTH"     # перечень прав
curl $B/admin/roles       -H "$AUTH"     # перечень ролей с их правами
curl $B/admin/users       -H "$AUTH"     # перечень пользователей с ролями
```

### 5.2. Создание права и роли

```bash
# создание права
curl -X POST $B/admin/permissions -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"resource":"invoice","action":"read","description":"Просмотр счетов"}'

# создание роли (без прав)
curl -X POST $B/admin/roles -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"name":"accountant","description":"Бухгалтер"}'
```

### 5.3. Назначение и отзыв права роли

```bash
# назначение роли 3 (viewer) права 6 (report:export)
curl -X POST $B/admin/roles/3/permissions -H "$AUTH" \
  -H "Content-Type: application/json" -d '{"permission_id": 6}'

# отзыв права
curl -X DELETE $B/admin/roles/3/permissions/6 -H "$AUTH"
```

### 5.4. Назначение и отзыв роли пользователю

```bash
# назначение пользователю (id=4) роли (id=2, editor)
curl -X POST $B/admin/users/4/roles -H "$AUTH" \
  -H "Content-Type: application/json" -d '{"role_id": 2}'

# отзыв роли
curl -X DELETE $B/admin/users/4/roles/2 -H "$AUTH"
```

### 5.5. Полный сценарий: предоставление доступа новому пользователю

```bash
# 1) регистрация пользователя (полномочия отсутствуют)
curl -s -X POST $B/auth/register -H "Content-Type: application/json" \
  -d '{"email":"anna@example.com","password":"secret123",
       "password_repeat":"secret123","first_name":"Анна"}' >/dev/null

# 2) получение токена; на данном этапе запрос /documents возвращает 403
NT=$(curl -s -X POST $B/auth/login -H "Content-Type: application/json" \
  -d '{"email":"anna@example.com","password":"secret123"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
curl -s -o /dev/null -w "до назначения роли: %{http_code}\n" -H "Authorization: Bearer $NT" $B/documents

# 3) определение идентификатора пользователя
UID=$(curl -s $B/admin/users -H "$AUTH" \
  | python3 -c "import sys,json;print(next(u['id'] for u in json.load(sys.stdin) if u['email']=='anna@example.com'))")

# 4) назначение роли viewer (id=3)
curl -s -X POST $B/admin/users/$UID/roles -H "$AUTH" \
  -H "Content-Type: application/json" -d '{"role_id": 3}' >/dev/null

# 5) с тем же токеном (повторный вход не требуется) — результат 200
curl -s -o /dev/null -w "после назначения роли: %{http_code}\n" -H "Authorization: Bearer $NT" $B/documents
```

---

## 6. Работа через Swagger UI

1. Откройте https://api.saysogood.dev/auth-test/docs
2. Выполните запрос `POST /auth/login` (кнопка **Try it out**) с учётными
   данными и скопируйте значение `access_token` из ответа.
3. Нажмите кнопку **Authorize** (значок замка в правом верхнем углу), вставьте
   токен и подтвердите. Все последующие запросы из Swagger будут выполняться с
   заголовком `Authorization: Bearer ...`.
4. Вызовите необходимые эндпоинты кнопкой **Try it out**; результат будет
   соответствовать кодам 200/401/403.

---

## 7. Справочник кодов ответа

| код | условие |
|-----|---------|
| `200 OK` | успешное выполнение |
| `201 Created` | объект создан (регистрация, создание роли или права) |
| `204 No Content` | успешное выполнение без тела ответа (logout, удаление учётной записи или роли) |
| `401 Unauthorized` | токен отсутствует, повреждён, истёк, сессия отозвана либо учётная запись неактивна |
| `403 Forbidden` | пользователь идентифицирован, но необходимое право отсутствует |
| `404 Not Found` | объект не найден (например, роль по идентификатору) |
| `409 Conflict` | конфликт данных (адрес электронной почты занят, право уже существует) |
| `422 Unprocessable Entity` | ошибка валидации (пароли не совпадают, некорректный адрес электронной почты и т. п.) |

Тело ответа при ошибке: `{"detail": "текст сообщения об ошибке"}`.

---

## 8. Эксплуатация (для администратора сервера)

### Управление сервисом (systemd)

```bash
systemctl status auth-test          # состояние
systemctl restart auth-test         # перезапуск
journalctl -u auth-test -f          # просмотр журнала в реальном времени
journalctl -u auth-test -n 100      # последние 100 строк журнала
```

Сервис включён в автозапуск (`enabled`).

### Конфигурация

Параметры расположены в файле `/root/auth_test/.env` (права доступа 600).
Основные переменные:

- `MOCK_DB` — используемая база данных: `True` — встроенное хранилище в памяти
  без сервера (данные существуют только в рамках процесса и сбрасываются при
  перезапуске), `False` — PostgreSQL;
- `DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME` — параметры подключения к
  PostgreSQL (используются только при `MOCK_DB=False`);
- `JWT_SECRET` — секрет подписи токенов (изменение приводит к аннулированию всех
  ранее выданных токенов);
- `ACCESS_TOKEN_EXPIRE_MINUTES` — срок действия access-токена (по умолчанию 15);
- `REFRESH_TOKEN_EXPIRE_MINUTES` — срок действия refresh-токена (по умолчанию
  10080, то есть 7 дней);
- `PASSWORD_HASHER` — алгоритм хэширования паролей: `argon2` (Argon2id, по
  умолчанию) либо `pbkdf2`. При изменении алгоритма ранее сохранённые хэши
  другого формата перестают проходить проверку — требуется повторная установка
  паролей либо повторное заполнение демонстрационными данными;
- `REDIS_URL` — адрес Redis для кэширования (необязательно). Если значение не
  задано, используется кэш-заглушка и Redis не требуется. Пример:
  `redis://localhost:6379/0`;
- `AUTH_CACHE_TTL_SECONDS` — время жизни записи пользователя в кэше в секундах
  (по умолчанию 30);
- `SEED_ON_STARTUP` — заполнение демонстрационными данными при пустой базе
  (`true`/`false`).

После изменения файла `.env` необходимо выполнить `systemctl restart auth-test`.

### База данных (PostgreSQL 16)

```bash
sudo -u postgres psql -d auth_test          # консоль psql
\dt                                          # перечень таблиц
SELECT id, email, is_active, is_superuser FROM users;
```

Таблицы: `users`, `roles`, `permissions`, `user_roles`, `role_permissions`,
`sessions`. Схема создаётся автоматически при запуске приложения.

### Удаление демонстрационных учётных записей перед промышленной эксплуатацией

1. В файле `/root/auth_test/.env` установите `SEED_ON_STARTUP=false`.
2. Измените пароли демонстрационных пользователей либо удалите их через
   административный API или средствами psql.
3. Выполните `systemctl restart auth-test`.

### Маршрутизация (nginx)

- `/auth-test/…` → uvicorn `127.0.0.1:8001`;
- файл конфигурации: `/etc/nginx/sites-available/api.saysogood.dev.conf`;
- применение изменений: `nginx -t && systemctl reload nginx`.

---

## 9. Перечень эндпоинтов

**Аутентификация и учётная запись**
- `POST /auth/register` — регистрация
- `POST /auth/login` — вход, выдача пары access + refresh
- `POST /auth/refresh` — обмен refresh-токена на новую пару (с ротацией)
- `POST /auth/logout` — выход (отзыв сессии)
- `GET /auth/me` — просмотр профиля
- `PATCH /auth/me` — редактирование профиля
- `DELETE /auth/me` — мягкое удаление учётной записи

**Административный API (право `access_control:manage`)**
- `GET/POST /admin/permissions` — перечень / создание права
- `GET/POST /admin/roles` — перечень / создание роли
- `DELETE /admin/roles/{id}` — удаление роли
- `POST /admin/roles/{id}/permissions` — назначение права роли
- `DELETE /admin/roles/{id}/permissions/{pid}` — отзыв права у роли
- `GET /admin/users` — перечень пользователей
- `POST /admin/users/{id}/roles` — назначение роли пользователю
- `DELETE /admin/users/{id}/roles/{rid}` — отзыв роли

**Бизнес-объекты (mock, защищены правами)**
- `GET/POST /documents`, `PUT/DELETE /documents/{id}`
- `GET /reports`, `POST /reports/export`

**Служебные**
- `GET /health` — проверка работоспособности
