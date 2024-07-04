project('bilge-impl', 'rust',
  version: '0.2.0',
  license: 'GPL-2.0-or-later',
  default_options: [])

itertools_dep = subproject('itertools').get_variable('itertools_dep')
proc_macro_error_attr_dep = subproject('proc-macro-error-attr').get_variable('proc_macro_error_attr_dep')
proc_macro_error_dep = subproject('proc-macro-error').get_variable('proc_macro_error_dep')
quote_dep = subproject('quote').get_variable('quote_dep')
syn_dep = subproject('syn').get_variable('syn_dep')
proc_macro2_dep = subproject('proc-macro2').get_variable('proc_macro2_dep')

rust = import('rust')

_bilge_impl_rs = rust.proc_macro(
  'bilge_impl',
  files('src/lib.rs'),
  rust_args: [
    '--edition', '2021',
    '--cfg', 'use_fallback',
    '--cfg', 'feature="syn-error"',
    '--cfg', 'feature="proc-macro"',
  ],
  dependencies: [
    itertools_dep,
    proc_macro_error_attr_dep,
    proc_macro_error_dep,
    quote_dep,
    syn_dep,
    proc_macro2_dep,
  ],
)

bilge_impl_dep = declare_dependency(
  link_with: _bilge_impl_rs,
)
