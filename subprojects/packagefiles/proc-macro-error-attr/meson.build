project('proc-macro-error-attr', 'rust',
  version: '1.12.0',
  license: 'GPL-2.0-or-later',
  default_options: [])

proc_macro2_dep = subproject('proc-macro2').get_variable('proc_macro2_dep')
quote_dep = subproject('quote').get_variable('quote_dep')

rust = import('rust')
_proc_macro_error_attr_rs = rust.proc_macro(
  'proc_macro_error_attr',
  files('src/lib.rs'),
  rust_args: [
    '--edition', '2018',
    '--cfg', 'use_fallback',
    '--cfg', 'feature="syn-error"',
    '--cfg', 'feature="proc-macro"'
  ],
  dependencies: [
    proc_macro2_dep,
    quote_dep,
  ],
)

proc_macro_error_attr_dep = declare_dependency(
  link_with: _proc_macro_error_attr_rs,
)
