= Модуль разбора OPC UA для Suricata <chap:module>

// Этап 3. Требование: какой код изменялся, комментарии к коду.

== Генерация шаблона <sec:module-template>

// TODO: setup-app-layer.py --parser OpcUa; перечень созданных/изменённых файлов.

== Определение протокола <sec:module-probe>

// TODO: сигнатура «HELF», probe(), порт 4840 в SCRegister...Parser, probing-парсер.

== Разбор сообщений <sec:module-parser>

// TODO: parser.rs: заголовок UA TCP, тип сервиса; транзакции; ключевые слова для правил.

== Сборка и проверка <sec:module-build>

// TODO: сборка, suricata.yaml (app-layer.protocols), лог «Rust ... parser registered».
