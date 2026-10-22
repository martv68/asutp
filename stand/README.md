# Стенд OPC UA (БДЗ ИБ АСУ ТП, команда 8)

Два контейнера в изолированной сети `ics` (172.28.0.0/24):

| Контейнер      | IP          | Что делает |
|----------------|-------------|------------|
| `opcua-server` | 172.28.0.10 | OPC UA сервер (asyncua), `opc.tcp://:4840`, SecurityPolicy None, анонимный доступ. Печатает подключения и обращения клиента. |
| `opcua-client` | 172.28.0.20 | OPC UA клиент (asyncua). Консоль с постоянным сеансом: каждая команда — свой запрос. Режим `--auto` — циклический сценарий без ввода. Печатает запросы (`->`) и ответы (`<-`). |

Режим None выбран намеренно: в нём содержимое сообщений доступно Suricata.

## Программные средства

| Компонент | Назначение |
|-----------|------------|
| Python 3.12, [asyncua](https://github.com/FreeOpcUa/opcua-asyncio) 2.1.0 | Готовая открытая реализация стека OPC UA (бинарный протокол `opc.tcp`): и сервер, и клиент построены на ней |
| Docker, Docker Compose | Изолированная сеть с фиксированными адресами, одинаковый запуск на macOS / Linux / Windows |
| Wireshark 4.x | Разбор трафика OPC UA в реальном времени (встроенный диссектор `opcua`) |
| `nicolaka/netshoot` (tcpdump) | Захват трафика внутри сети Docker и передача его в Wireshark |

## Адресное пространство сервера

Пространство имён `urn:bdz:opcua:stand` (индекс 2), объект `Objects/Device`:

| Узел | NodeId | Тип | Доступ | Смысл |
|------|--------|-----|--------|-------|
| `Counter` | `ns=2;s=Counter` | UInt32 | чтение | Счётчик, сервер увеличивает его раз в секунду (0…999) |
| `Setpoint` | `ns=2;s=Setpoint` | Double | чтение/запись | Уставка |
| `Enabled` | `ns=2;s=Enabled` | Boolean | чтение/запись | Признак включения |
| `Reset()` | `ns=2;s=Reset` | метод → Boolean | вызов | Сбрасывает `Counter` в 0 |

## Требования

- Docker Desktop;
- Wireshark.

## Запуск

Все команды ниже выполняются из папки `stand/`:

```sh
cd stand
docker compose up --build
```

В консоли — лог сервера. Клиент запускается во втором терминале:

```sh
docker compose exec opcua-client python client.py
docker compose exec opcua-client python client.py --auto
```

Первая команда открывает консоль (список команд — `help`), вторая — циклический сценарий с паузой `CYCLE_PAUSE` из `docker-compose.yml`.

Трафик в Wireshark в реальном времени (в третьем терминале):

- macOS / Linux: `./capture.sh`
- Windows: `capture.cmd` — запускать из **cmd.exe**, не из PowerShell (PowerShell портит двоичный поток в конвейере).

Скрипт запускает контейнер с tcpdump в сетевом пространстве сервера и передаёт поток в Wireshark.
Wireshark разбирает порт 4840 как OPC UA; фильтр отображения: `opcua`.

Остановка: `quit` в клиенте, `Ctrl+C` в терминале сервера, затем `docker compose down`.

## Команды клиента

| Команда | Запросы OPC UA |
|---------|----------------|
| `endpoints` | Hello, OpenSecureChannel, GetEndpoints, CloseSecureChannel (отдельный канал) |
| `connect` | Hello, OpenSecureChannel, CreateSession, ActivateSession; затем Read NamespaceArray, TranslateBrowsePaths, Browse — клиент узнаёт имена узлов |
| `browse [узел]` | Browse (по умолчанию `Device`) |
| `read <узел>` | Read атрибута Value |
| `write <узел> <значение>` | Write; при первой записи в узел — ещё Read его DataType |
| `call <метод>` | Call метода объекта `Device` |
| `sub <узел>` | CreateSubscription (при первой подписке), CreateMonitoredItems; дальше Publish |
| `unsub [узел]` | DeleteMonitoredItems; без аргумента — DeleteSubscriptions |
| `disconnect` | CloseSession, CloseSecureChannel |
| `help`, `quit` | — (`quit` и `Ctrl+D` закрывают сеанс) |

Узел — имя (`Counter`, `Setpoint`, `Enabled`, `Reset`, `Device`, `Objects`, `Server`) или NodeId (`ns=2;s=Counter`, `i=2258`).

## Демонстрация на защите (этап 2)

Требование задания к этапу 2:

> Демонстрация реализованного стенда клиент-сервер в формате вывода переданных сообщений в консоль и параллельной демонстрации трафика в режиме реального времени в Wireshark. Для реализации стенда должны использоваться готовые решения по имитации соответствующего промышленного протокола.

Значит, нужно показать три вещи:

1. **Готовое решение** — сервер и клиент работают на открытой библиотеке asyncua, свой протокол не писали.
2. **Сообщения в консоли** — клиент печатает каждый запрос и ответ, сервер печатает, что получил.
3. **Тот же обмен в Wireshark в реальном времени** — каждая команда клиента сразу появляется в захвате, пакеты разобраны как OPC UA.

### Подготовка (заранее, не на защите)

1. Запустить Docker Desktop.
2. Собрать образы и скачать образ для захвата, чтобы на защите ничего не качалось:
   ```sh
   docker compose build
   docker pull nicolaka/netshoot
   ```
3. Проверить, что Wireshark установлен (на Windows — в `C:\Program Files\Wireshark`).
4. Один раз прогнать сценарий ниже целиком.

### Раскладка экрана

```
┌──────────────────────┬──────────────────────┐
│ Терминал 1: сервер   │                      │
├──────────────────────┤      Wireshark       │
│ Терминал 2: клиент   │                      │
└──────────────────────┴──────────────────────┘
```

Третий терминал нужен только для запуска `capture.sh`, его можно свернуть.

### Шаг 1. Запустить сервер

Терминал 1:

```sh
docker compose up
```

Ожидаемо: `** server listening on opc.tcp://0.0.0.0:4840/ (SecurityPolicy None, Anonymous)`.

Рассказать: сервер — `server/server.py` на asyncua; объект `Device` с тремя переменными и методом (таблица выше); `Counter` меняется сам — это имитация измеряемой величины; режим безопасности None — сообщения идут открытым текстом, поэтому их видит Wireshark (а на этапе 3 — Suricata).

### Шаг 2. Запустить Wireshark

Третий терминал: `./capture.sh` (Windows: `capture.cmd` из cmd.exe). Откроется Wireshark, захват уже идёт.

В Wireshark:
- фильтр отображения: `opcua`;
- `View → Time Display Format → Time of Day` — тогда время пакетов совпадает с временем в консолях (в контейнерах выставлено московское время).

Пока пакетов нет: клиент ещё ничего не отправлял.

### Шаг 3. Запустить клиента

Терминал 2:

```sh
docker compose exec opcua-client python client.py
```

Печатается список команд и приглашение `opcua>`. Трафика ещё нет.

### Шаг 4. Обнаружение сервера — `endpoints`

```
opcua> endpoints
```

- Клиент: `-> GetEndpoints`, `<- Endpoint ... mode=None policy=None`.
- Сервер: `** client connected: 172.28.0.20:…` и сразу `disconnected`.
- Wireshark: `Hello` → `Acknowledge` → `OpenSecureChannel` (×2) → `GetEndpointsRequest` → `GetEndpointsResponse` → `CloseSecureChannel`.

Показать: в `GetEndpointsResponse` у конечной точки `SecurityPolicyUri: …#None` — сервер сам сообщает, что не шифрует трафик.

### Шаг 5. Открыть сеанс — `connect`

```
opcua> connect
```

- Клиент: `-> Hello / OpenSecureChannel / CreateSession / ActivateSession`, `<- session active`, `<- ns=2, Device: Counter, Setpoint, Enabled, Reset`.
- Сервер: `** client connected: 172.28.0.20:…`.
- Wireshark: `Hello`, `OpenSecureChannel`, `CreateSessionRequest/Response`, `ActivateSessionRequest/Response`, затем `ReadRequest` (таблица пространств имён), `TranslateBrowsePathsToNodeIdsRequest`, `BrowseRequest`.

Показать: в `ActivateSessionRequest` маркер пользователя — анонимный (`AnonymousIdentityToken`), логина и пароля нет. Сеанс теперь держится до `disconnect`, дальше каждая команда — отдельный запрос в этом сеансе.

### Шаг 6. Обзор адресного пространства — `browse`

```
opcua> browse
```

- Клиент: четыре дочерних узла `Device` с классами (`Variable`, `Method`) и NodeId.
- Wireshark: одна пара `BrowseRequest` / `BrowseResponse`; в ответе те же имена.

### Шаг 7. Чтение — `read`

```
opcua> read Counter
opcua> read Setpoint
```

- Клиент: `<- Read  Counter = 37 (UInt32)`.
- Сервер: `<- Read  Counter = 37` — то же значение.
- Wireshark: `ReadRequest` / `ReadResponse`. В запросе — `Identifier String: Counter`, в ответе — значение.

Повторить `read Counter` — значение выросло: сервер меняет его сам.

### Шаг 8. Запись — `write`

```
opcua> write Setpoint 42.5
opcua> read Setpoint
opcua> write Enabled true
```

- Клиент: `-> Read  Setpoint.DataType` (только в первый раз), `-> Write Setpoint := 42.5`, `<- Write Setpoint Good`.
- Сервер: `<- Write Setpoint := 42.5 [Good]`.
- Wireshark: `WriteRequest` / `WriteResponse`.

Показать главное: раскрыть `WriteRequest` → `NodesToWrite` → `[0]` — там NodeId (`Identifier String: Setpoint`) и значение `Double: 42.5` открытым текстом. Это и есть команда управления, которую в режиме None может прочитать или подменить любой в сети. Следующий `read Setpoint` вернёт 42.5.

### Шаг 9. Отказ в записи — `write Counter`

```
opcua> write Counter 5
```

- Клиент: `<- BadUserAccessDenied`.
- Сервер: `<- Write Counter := 5 [BadUserAccessDenied]`.
- Wireshark: в `WriteResponse` → `Results` код `0x801F0000` (BadUserAccessDenied).

Рассказать: `Counter` доступен только на чтение, сервер проверяет права на уровне узла и отвечает кодом ошибки, а не разрывом соединения.

### Шаг 10. Вызов метода — `call Reset`

```
opcua> call Reset
opcua> read Counter
```

- Клиент: `-> Call  Device.Reset()`, `<- Call  Reset -> True`.
- Сервер: `<- Call  Reset() -> Counter = 0`.
- Wireshark: `CallRequest` (объект `Device`, метод `Reset`) / `CallResponse` с результатом `True`.

`read Counter` после этого — маленькое число: счётчик сброшен.

### Шаг 11. Подписка — `sub` / `unsub`

```
opcua> sub Counter
```

- Клиент: `CreateSubscription`, `CreateMonitoredItems`, затем каждую секунду `<- Publish Counter = …`.
- Сервер: `<- Subscribe Counter`.
- Wireshark: `CreateSubscriptionRequest`, `CreateMonitoredItemsRequest`, дальше непрерывно `PublishRequest` / `PublishResponse`.

Рассказать: при подписке клиент не опрашивает значение, а заранее отправляет `PublishRequest`, и сервер отвечает на него, когда значение изменилось. Так SCADA получает данные от ПЛК. В `PublishResponse` — `DataChangeNotification` с новым значением.

```
opcua> unsub
```

`DeleteSubscriptionsRequest`, поток `Publish` прекращается.

### Шаг 12. Закрыть сеанс — `disconnect`

```
opcua> disconnect
opcua> quit
```

- Клиент: `-> CloseSession / CloseSecureChannel`, `<- disconnected`.
- Сервер: `** client disconnected: 172.28.0.20:…`.
- Wireshark: `CloseSessionRequest/Response`, `CloseSecureChannel`.

### Шаг 13 (по желанию). Автоматический режим

```sh
docker compose exec opcua-client python client.py --auto
```

Клиент сам выполняет весь сценарий (шаги 4–12) с паузой `CYCLE_PAUSE` секунд — удобно, если нужно показать непрерывный поток трафика. Остановка — `Ctrl+C`.

### Завершение

`Ctrl+C` в терминале 1, закрыть Wireshark, затем `docker compose down`.

### Если что-то пошло не так

- `connect` → `ConnectionRefusedError`: сервер ещё не запустился или упал — смотреть терминал 1.
- `capture.sh` сразу завершается с ошибкой про `opcua-server`: скрипт запущен до `docker compose up` — сначала шаг 1, потом скрипт.
- Wireshark открылся, но пакетов нет при командах клиента: проверить, что фильтр — `opcua`, и что захват не остановлен (кнопка с акульим плавником должна быть неактивна).
- На Windows Wireshark пишет об ошибке формата захвата: `capture.cmd` запущен из PowerShell, нужен cmd.exe.
- Время в Wireshark не совпадает с консолью: не переключён формат времени (шаг 2).

### Полезные фильтры Wireshark

| Фильтр | Что останется |
|--------|---------------|
| `opcua` | Весь OPC UA |
| `opcua.transport.type == "OPN"` | Открытие защищённого канала |
| `opcua.servicenodeid.numeric == 673` | Только `WriteRequest` |
| `opcua.servicenodeid.numeric in {673, 676}` | Запись: запросы и ответы |
| `opcua.servicenodeid.numeric in {712, 715}` | Вызовы методов |
| `opcua.nodeid.string == "Setpoint"` | Все обращения к `Setpoint` |

## Полезное

- Лог сервера отдельно: `docker compose logs -f opcua-server`.
- Сервер доступен с хоста на `opc.tcp://localhost:4840/` (например, для UaExpert).
