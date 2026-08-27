fccase_h = custom_target(
  'fccase.h',
  output: 'fccase.h',
  input: ['CaseFolding.txt', 'fccase.tmpl.h'],
  command: [
    find_program('fc-case.py'),
    '@INPUT0@',
    '--template',
    '@INPUT1@',
    '--output',
    '@OUTPUT@',
  ],
)

curl = find_program('curl', required: false)
if curl.found()
  update_case = run_target(
    'update-case',
    command: [
      curl,
      '-s',
      '-o',
      meson.current_source_dir() / 'CaseFolding.txt',
      'https://www.unicode.org/Public/UNIDATA/CaseFolding.txt',
    ],
  )
endif
