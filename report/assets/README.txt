Сюда положить рисунки и скриншоты для отчёта БДЗ (Typst-сборка ищет их здесь).

Раздел 1 (этап 1):
  stack.png          — стек протоколов OPC UA (слои)
  sequence.png       — последовательность Hello/Ack -> OPN -> CreateSession -> ... -> CLO

Раздел 2 (стенд):
  stand_console.png  — вывод клиента и сервера в консоль
  stand_wireshark.png — Wireshark, фильтр opcua

Раздел 3 (модуль Suricata):
  suricata_registered.png — лог запуска: «Rust ... parser registered»
  suricata_yaml.png       — app-layer.protocols: enabled: yes

Раздел 4 (правила):
  rule_NN.png        — сработка правила NN (fast.log + Wireshark)

Вставка: image("assets/<имя>.png", width: 100%)
