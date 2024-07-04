project('quote', 'rust',
  version: '1.12.0',
  license: 'GPL-2.0-or-later',
  default_options: [])

proc_macro2_dep = subproject('proc-macro2').get_variable('proc_macro2_dep')

_quote_rs = static_library(
  'quote',
  files('src/lib.rs'),
  gnu_symbol_visibility: 'hidden',
  rust_abi: 'rust',
  rust_args: [
    '--edition', '2021',
    '--cfg', 'feature="proc-macro"',
  ],
  dependencies: [
    proc_macro2_dep,
    ],
)

quote_dep = declare_dependency(
  link_with: _quote_rs,
)

