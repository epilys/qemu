project('proc-macro-error', 'rust',
  version: '1.0.4',
  license: 'GPL-2.0-or-later',
  default_options: [])

proc_macro_error_attr_dep = subproject('proc-macro-error-attr').get_variable('proc_macro_error_attr_dep')
proc_macro2_dep = subproject('proc-macro2').get_variable('proc_macro2_dep')
quote_dep = subproject('quote').get_variable('quote_dep')
syn_dep = subproject('syn').get_variable('syn_dep')

_proc_macro_error_rs = static_library(
  'proc_macro_error',
  files('src/lib.rs'),
  rust_abi: 'rust',
  rust_args: [
    '--edition', '2018',
    '--cfg', 'use_fallback',
    '--cfg', 'feature="syn-error"',
    '--cfg', 'feature="proc-macro"',
    '-A', 'non_fmt_panics'
  ],
  dependencies: [
    proc_macro_error_attr_dep,
    proc_macro2_dep,
    quote_dep,
    syn_dep,
  ],
)

proc_macro_error_dep = declare_dependency(
  link_with: _proc_macro_error_rs,
)
