#import "@preview/modern-g7-32:0.2.0": custom-title-template
#import custom-title-template: *

// Титульный лист БДЗ (по образцу title-mephi.typ из НИР и title-lab.typ из ЛР).
// Отличия от ЛР: «большого домашнего задания», строка этапа,
// без списка участников (состав команды — во введении).

#let arguments(..args, year: auto) = {
  return args.named()
}

#let unbreak-name(name) = {
  if name == none { return }
  return name.replace(" ", "\u{00A0}")
}

#let custom-sign-field(name, position, label: none, part: none, details: "подпись, дата", is-student: false) = {
  let part-cell = []
  if part != none {
    part-cell = table.cell(align: top)[(#small-text[#part])]
  }
  let position-text = if is-student { "Группа " + position } else { position }
  set par(justify: false)
  table(
    stroke: none,
    inset: (x: 0pt, y: 3pt),
    columns: (5fr, 1fr, 3fr, 1fr, 3fr),
    table.cell(colspan: 5)[#if label != none { label }],
    [#position-text], [], [], [], table.cell(align: bottom)[#unbreak-name(name)],
    [], [], table.cell(align: center)[], [], part-cell
  )
}

#let stage-names = (
  "1": "Этап 1. Описание протокола",
  "5": none, // итоговый отчёт — без строки этапа
)

#let template(
  ministry: none,
  university: none,
  department: none,
  stage: 1,
  subject: none,
  manager: (position: none, name: none),
  city: none,
  year: auto,
  ..rest,
) = {
  let stage-name = stage-names.at(str(stage), default: none)
  align(center)[
    #upper(ministry)
    #v(0.15fr)
    #university
    #v(0.15fr)
    #department
    #v(1fr)
    #text(weight: "bold", size: 16pt)[ОТЧЕТ]
    #v(0.3fr)
    #text([о выполнении большого домашнего задания])
    #linebreak()
    #text[«#subject»]
    #linebreak()
    #text[по дисциплине «Информационная безопасность АСУ ТП»]
    #if stage-name != none [
      #v(0.2fr)
      #text[#stage-name]
    ]
    #v(0.4fr)
    #v(1fr)
  ]
  v(0.1fr)
  custom-sign-field(manager.name, manager.position, label: "Преподаватель:")
  v(0.6fr)
}
