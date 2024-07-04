project('either', 'rust',
  version: '1.12.0',
  license: 'GPL-2.0-or-later',
  default_options: [])

_either_rs = static_library(
  'either',
  files('src/lib.rs'),
  gnu_symbol_visibility: 'hidden',
  rust_abi: 'rust',
  rust_args: [
    '--edition', '2018',
    '--cfg', 'feature="use_std"',
    '--cfg', 'feature="use_alloc"',
  ],
  dependencies: [],
)

either_dep = declare_dependency(
  link_with: _either_rs,
)
