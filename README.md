# Стенд OPC UA (БДЗ ИБ АСУ ТП, команда 8)

Два контейнера в изолированной сети `ics` (172.28.0.0/24):

| Контейнер      | IP          | Что делает |
|----------------|-------------|------------|
| `opcua-server` | 172.28.0.10 | OPC UA сервер (asyncua), `opc.tcp://:4840`, SecurityPolicy None, анонимный доступ. Объект `Device`: `Counter` (растёт сам), `Setpoint`, `Enabled` (пишет клиент), метод `Reset()`. Печатает все обращения клиента. |
| `opcua-client` | 172.28.0.20 | OPC UA клиент (asyncua). Каждые 5 с: GetEndpoints → сеанс → Browse → Read → Write → Call → подписка на `Counter` → закрытие. Печатает запросы (`->`) и ответы (`<-`). |

Режим None выбран намеренно: в нём содержимое сообщений доступно Suricata.

## Требования

- Docker Desktop (на Windows — с бэкендом WSL2);
- Wireshark.

## Запуск

```sh
docker compose up --build          # сборка и запуск, логи обоих контейнеров в консоли
```

Трафик в Wireshark в реальном времени (во втором терминале):

- macOS / Linux: `./capture.sh`
- Windows: `capture.cmd` — запускать из **cmd.exe**, не из PowerShell.

Скрипт запускает контейнер с tcpdump в сетевом пространстве сервера и передаёт поток в Wireshark.
Wireshark разбирает порт 4840 как OPC UA; фильтр отображения: `opcua`.

Остановка: `Ctrl+C`, затем `docker compose down`.

## Полезное

- Логи по отдельности: `docker compose logs -f opcua-server`, `docker compose logs -f opcua-client`.
- Сервер доступен с хоста на `opc.tcp://localhost:4840/` (например, для UaExpert).
- Пауза между циклами клиента: `CYCLE_PAUSE` в `docker-compose.yml`.
