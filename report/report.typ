#import "@preview/modern-g7-32:0.2.0": gost, custom-title-template
#import "title-bdz.typ" as title-bdz

// Этап БДЗ, под который собирается отчёт:
//   1 — промежуточный отчёт (введение + раздел 1), сдача до 8 недели;
//   5 — итоговый отчёт (введение + разделы 1–4 + заключение), сдача до 16 недели.
#let stage = 1

// шрифт до show-правила, иначе титульник уходит в дефолтный Libertinus
#set text(font: "Times New Roman", size: 14pt)

#show: gost.with(
  title-template: custom-title-template.from-module(title-bdz),
  ministry: [МИНИСТЕРСТВО НАУКИ И ВЫСШЕГО ОБРАЗОВАНИЯ\ РОССИЙСКОЙ ФЕДЕРАЦИИ],
  university: [Федеральное государственное автономное образовательное учреждение высшего образования «Национальный исследовательский ядерный университет «МИФИ»],
  department: [Кафедра №42 «Криптология и кибербезопасность»],
  stage: stage,
  subject: "Разработка модуля анализа промышленного протокола OPC UA для средства обнаружения вторжений Suricata",
  manager: (name: "М. А. Финошин", position: ""),
  city: "Москва",
)

#set enum(numbering: "1)")
#show figure.caption: it => text(size: 12pt)[#it]
#show table: set text(size: 12pt)
#show table: set par(justify: false)

#include "0_2_intro.typ"

#include "1_protocol.typ"

#if stage >= 5 {
  include "2_stand.typ"
  include "3_suricata_module.typ"
  include "4_rules.typ"
  include "5_conclusion.typ"
}
