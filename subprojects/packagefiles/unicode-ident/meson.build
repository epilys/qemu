project('unicode-ident', 'rust',
  version: '1.0.12',
  license: 'GPL-2.0-or-later',
  default_options: [])

_unicode_ident_rs = static_library(
  'unicode_ident',
  files('src/lib.rs'),
  gnu_symbol_visibility: 'hidden',
  rust_abi: 'rust',
  rust_args: [
    '--edition', '2021',
  ],
  dependencies: [],
)

unicode_ident_dep = declare_dependency(
  link_with: _unicode_ident_rs,
)
