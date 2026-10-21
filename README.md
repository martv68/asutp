# Стенд OPC UA (БДЗ ИБ АСУ ТП, команда 8)

Два контейнера в изолированной сети `ics` (172.28.0.0/24):

| Контейнер      | IP          | Что делает |
|----------------|-------------|------------|
| `opcua-server` | 172.28.0.10 | OPC UA сервер (asyncua), `opc.tcp://:4840`, SecurityPolicy None, анонимный доступ. Объект `Device`: `Counter` (растёт сам), `Setpoint`, `Enabled` (пишет клиент), метод `Reset()`. Печатает все обращения клиента. |
| `opcua-client` | 172.28.0.20 | OPC UA клиент (asyncua). Консоль с постоянным сеансом: каждая команда — свой запрос (Browse, Read, Write, Call, подписка). Режим `--auto` — циклический сценарий без ввода. Печатает запросы (`->`) и ответы (`<-`). |

Режим None выбран намеренно: в нём содержимое сообщений доступно Suricata.

## Требования

- Docker Desktop (на Windows — с бэкендом WSL2);
- Wireshark.

## Запуск

```sh
docker compose up --build          # сборка и запуск; в консоли лог сервера
```

Клиент (во втором терминале):

```sh
docker compose exec opcua-client python client.py          # консоль, команды — help
docker compose exec opcua-client python client.py --auto   # циклический сценарий
```

Пример сеанса:

```
opcua> connect
opcua> browse
opcua> read Counter
opcua> write Setpoint 42.5
opcua> write Counter 5          # сервер ответит BadUserAccessDenied
opcua> call Reset
opcua> sub Counter
opcua> unsub
opcua> disconnect
```

Трафик в Wireshark в реальном времени (в третьем терминале):

- macOS / Linux: `./capture.sh`
- Windows: `capture.cmd` — запускать из **cmd.exe**, не из PowerShell.

Скрипт запускает контейнер с tcpdump в сетевом пространстве сервера и передаёт поток в Wireshark.
Wireshark разбирает порт 4840 как OPC UA; фильтр отображения: `opcua`.

Остановка: `quit` в клиенте, `Ctrl+C` в терминале сервера, затем `docker compose down`.

## Полезное

- Лог сервера отдельно: `docker compose logs -f opcua-server`.
- Сервер доступен с хоста на `opc.tcp://localhost:4840/` (например, для UaExpert).
- Пауза между циклами режима `--auto`: `CYCLE_PAUSE` в `docker-compose.yml`.
