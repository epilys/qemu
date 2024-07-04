project('arbitrary-int', 'rust',
  version: '1.2.7',
  license: 'GPL-2.0-or-later',
  default_options: [])

_arbitrary_int_rs = static_library(
  'arbitrary_int',
  files('src/lib.rs'),
  gnu_symbol_visibility: 'hidden',
  rust_abi: 'rust',
  rust_args: [
    '--edition', '2021',
  ],
  dependencies: [],
)

arbitrary_int_dep = declare_dependency(
  link_with: _arbitrary_int_rs,
)
