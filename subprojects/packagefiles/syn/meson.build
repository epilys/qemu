project('syn', 'rust',
  version: '2.0.66',
  license: 'GPL-2.0-or-later',
  default_options: [])

quote_dep = subproject('quote').get_variable('quote_dep')
proc_macro2_dep = subproject('proc-macro2').get_variable('proc_macro2_dep')
unicode_ident_dep = subproject('unicode-ident').get_variable('unicode_ident_dep')

_syn_rs = static_library(
  'syn',
  files('src/lib.rs'),
  gnu_symbol_visibility: 'hidden',
  rust_abi: 'rust',
  rust_args: [
    '--edition', '2021',
    '--cfg', 'feature="full"',
    '--cfg', 'feature="derive"',
    '--cfg', 'feature="parsing"',
    '--cfg', 'feature="printing"',
    '--cfg', 'feature="clone-impls"',
    '--cfg', 'feature="proc-macro"',
  ],
  dependencies: [
    quote_dep,
    proc_macro2_dep,
    unicode_ident_dep,
  ],
)

syn_dep = declare_dependency(
  link_with: _syn_rs,
)
