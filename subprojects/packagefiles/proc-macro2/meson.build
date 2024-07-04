project('proc-macro2', 'rust',
  version: '1.0.84',
  license: 'GPL-2.0-or-later',
  default_options: [])

unicode_ident_dep = subproject('unicode-ident').get_variable('unicode_ident_dep')

_proc_macro2_rs = static_library(
  'proc_macro2',
  files('src/lib.rs'),
  gnu_symbol_visibility: 'hidden',
  rust_abi: 'rust',
  rust_args: [
    '--edition', '2021',
    '--cfg', 'feature="proc-macro"',
    '--cfg', 'span_locations',
    '--cfg', 'wrap_proc_macro',
  ],
  dependencies: [
    unicode_ident_dep,
  ],
)

proc_macro2_dep = declare_dependency(
  link_with: _proc_macro2_rs,
)
