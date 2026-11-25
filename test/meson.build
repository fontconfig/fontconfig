if get_option('tests-external-fonts').allowed()
  fetch_test_fonts = custom_target(
    'fetch_test_fonts',
    output: 'testfonts',
    command: [
      python3,
      join_paths(meson.project_source_root(), 'build-aux', 'fetch-testfonts.py'),
      '--target-dir',
      '@0@/testfonts'.format(meson.project_build_root()),
      '--try-symlink',
    ],
    build_by_default: false,
    build_always_stale: true,
  )
  fetch_type1_test_fonts = custom_target(
    'fetch_type1_test_fonts',
    output: 'type1testfonts',
    command: [
      python3,
      join_paths(meson.project_source_root(), 'build-aux', 'fetch-type1-testfonts.py'),
      '--target-dir',
      '@0@/type1testfonts'.format(meson.project_build_root()),
      '--try-symlink',
    ],
    build_by_default: false,
    build_always_stale: true,
  )
  external_font_targets = [fetch_test_fonts, fetch_type1_test_fonts]
else
  fetch_test_fonts = []
  fetch_type1_test_fonts = []
  external_font_targets = []
endif

# A ready-to-use font environment for C tests that need fonts to look up but
# do not set up their own config.  Opt in per test with
# {'use_test_fonts': true}; the test then runs with FONTCONFIG_FILE pointing at
# the downloaded testfonts, mirroring what the pytest harness does, so the test
# itself needs no font or config setup.  This relies on tests-external-fonts;
# opted-in tests are built but not run when that option is disabled.
test_fonts_conf = configure_file(
  input: 'fonts.conf.in',
  output: 'test-fonts.conf',
  configuration: {
    'REMAPDIR': '',
    'FONTDIR': join_paths(meson.project_build_root(), 'testfonts'),
    'CACHEDIR': join_paths(meson.project_build_root(), 'test', 'fonts-cache'),
  },
)
fc_test_fonts_env = environment()
fc_test_fonts_env.set('FONTCONFIG_FILE', test_fonts_conf.full_path())

tests = [
  ['test-bz89617.c', {'c_args': ['-DSRCDIR="@0@"'.format(meson.current_source_dir())]}],
  ['test-bz131804.c'],
  ['test-bz96676.c'],
  ['test-name-parse.c'],
  ['test-bz106618.c'],
  ['test-bz1744377.c'],
  ['test-issue180.c'],
  ['test-family-matching.c'],
  ['test-ptrlist.c', {'include_directories': include_directories('../src'), 'dependencies': libintl_dep}],
  ['test-fcstr.c', {'include_directories': include_directories('../src'), 'dependencies': libintl_dep}],
  ['test-ostest.c'],
  ['test-y2038.c', {'include_directories': include_directories('../src'), 'dependencies': libintl_dep}],
  ['test-versioned-conf.c'],
  ['test-issue77.c'],
  ['test-charset-merge.c'],
]
tests_build_only = [
  ['test-gen-testcache.c', {'include_directories': include_directories('../src'), 'dependencies': libintl_dep}],
]
tests_not_parallel = []

if host_machine.system() != 'windows'
  tests += [
    # FIXME: ['test-migration.c'],
    ['test-bz106632.c', {'c_args': ['-DFONTFILE="@0@"'.format(join_paths(meson.current_source_dir(), '4x6.pcf'))]}],
    ['test-issue107.c'], # FIXME: fails on mingw
  ]
  tests_not_parallel += [
    # FIXME: this needs NotoSans-hinted.zip font downloaded and unpacked into test build directory! see run-test.sh
    ['test-crbug1004254.c', {'dependencies': dependency('threads')}], # for pthread
    ['test-pthread.c', {'dependencies': dependency('threads')}], # for pthread
    ['test-mt-fccfg.c', {'include_directories': include_directories('../src'), 'dependencies': dependency('threads')}],
    ['test-mt-fcinit.c', {'include_directories': include_directories('../src'), 'dependencies': [libintl_dep, dependency('threads')]}],
    ['test-mt-cache-stress.c', {'dependencies': dependency('threads'), 'c_args': ['-DFONTFILE="@0@"'.format(join_paths(meson.current_source_dir(), '4x6.pcf'))]}],
    ['test-appfont.c', {'c_args': ['-DSRCDIR="@0@"'.format(meson.current_source_dir())]}],
    ['test-mt-fontsort-race.c', {'dependencies': dependency('threads'), 'c_args': ['-DFONTFILE="@0@"'.format(join_paths(meson.current_source_dir(), 'no_family_name.ttf'))]}],
    ['test-mt-fontmatch-race.c', {'dependencies': dependency('threads'), 'c_args': ['-DFONTFILE="@0@"'.format(join_paths(meson.current_source_dir(), 'no_family_name.ttf'))]}],
    ['test-mt-fontlist-race.c', {'dependencies': dependency('threads'), 'c_args': ['-DFONTFILE="@0@"'.format(join_paths(meson.current_source_dir(), 'no_family_name.ttf'))]}],
    ['test-mt-appfontclear-race.c', {'dependencies': dependency('threads'), 'c_args': ['-DFONTFILE="@0@"'.format(join_paths(meson.current_source_dir(), 'no_family_name.ttf'))]}],
    ['test-rwlock.c', {'include_directories': include_directories('../src'), 'dependencies': dependency('threads')}],
  ]
  tests_build_only += [
    ['bench-cache.c', {'dependencies': dependency('threads')}], # POSIX/pthread only
  ]

  if get_option('default_library') == 'static'
    tests += [
      ['test-issue110.c'],
      ['test-d1f48f11.c'],
    ]
  endif
endif

# FcFreeTypeQuery is only available with the FreeType backend
if not get_option('fontations').enabled()
  tests += [
    ['test-foundry.c', {'dependencies': freetype_dep, 'c_args': ['-DFONTFILE="@0@"'.format(join_paths(meson.current_source_dir(), 'no_family_name.ttf'))]}],
    ['test-spacing.c', {'include_directories': include_directories('../src'), 'dependencies': freetype_dep}],
  ]
endif

link_with_libs = [libfontconfig_internal]
if get_option('fontations').enabled()
  link_with_libs += [fc_fontations]
endif

foreach test_data : tests + tests_not_parallel + tests_build_only
  fname = test_data[0]
  opts = test_data.length() > 1 ? test_data[1] : {}
  extra_c_args = opts.get('c_args', [])
  extra_deps = opts.get('dependencies', [])
  extra_incdir = opts.get('include_directories', [])

  test_name = fname.split('.')[0].underscorify()

  exe = executable(
    test_name,
    fname,
    fcstdint_h,
    fclang_h,
    c_args: c_args + extra_c_args,
    include_directories: [incbase] + extra_incdir,
    link_with: link_with_libs,
    dependencies: [fcint_dep, extra_deps],
  )

  if test_data not in tests_build_only
    is_par = test_data in tests
    if opts.get('use_test_fonts', false)
      # use_test_fonts relies on the downloaded testfonts, so it requires
      # tests-external-fonts.  When that is disabled the test is still built
      # (to catch compile errors) but not run, as it would have no fonts.
      if get_option('tests-external-fonts').allowed()
        test(
          test_name,
          exe,
          timeout: 600,
          is_parallel: is_par,
          env: fc_test_fonts_env,
          depends: external_font_targets,
        )
      else
        message('test @0@ needs tests-external-fonts; built but not run'.format(test_name))
      endif
    else
      test(test_name, exe, timeout: 600, is_parallel: is_par)
    endif
  endif
endforeach


if get_option('fontations').enabled()
  rust = import('rust')
  rust.test('fc_fontations_rust_tests', fc_fontations, link_with: [libfontconfig_internal], depends: external_font_targets, env: ['builddir=@0@'.format(meson.project_build_root())],)
endif

fs = import('fs')

if conf.get('FREETYPE_PCF_LONG_FAMILY_NAMES')
  out_expected = fs.copyfile('out.expected-long-family-names',
                             'out.expected')
else
  out_expected = fs.copyfile('out.expected-no-long-family-names',
                             'out.expected')
endif

if pytest.found()
  pytest_args = ['--tap', '-vv', '--assert=plain']
  if not get_option('tests-external-fonts').allowed()
    pytest_args += ['-m', 'not network']
  endif
  test(
    'pytest',
    pytest,
    args: pytest_args,
    workdir: meson.current_source_dir(),
    env: [
      'builddir=@0@'.format(meson.project_build_root()),
      'srcdir=@0@'.format(meson.project_source_root()),
      'EXEEXT=@0@'.format(conf.get('EXEEXT')),
      'CC=@0@'.format(meson.get_compiler('c').cmd_array()[0]),
      'FC_DISABLE_BWRAP=@0@'.format(
        (not get_option('tests-bwrap').allowed()).to_int(),
      ),
      'FC_CACHE_VERSION=@0@'.format(cacheversion),
      'FC_CACHE_SNAP_VERSION=@0@'.format(cachesnapversion),
      'HAVE_LIBWOFF2DEC=@0@'.format(conf.get('HAVE_LIBWOFF2DEC', 0)),
    ],
    protocol: 'tap',
    timeout: 600,
    depends: external_font_targets,
  )
endif

if jsonc_dep.found()
  test_conf = executable(
    'test-conf',
    'test-conf.c',
    dependencies: [fontconfig_dep, jsonc_dep],
    c_args: ['-DSRCDIR="@0@"'.format(meson.current_source_dir())],
  )
endif

test_const_name = executable(
  'test_const_name',
  test_const_name_c,
  include_directories: [incbase],
  link_with: libfontconfig,
)
test('test_const_name', test_const_name)
