project('itertools', 'rust',
  version: '0.11.0',
  license: 'GPL-2.0-or-later',
  default_options: [])

either_dep = subproject('either').get_variable('either_dep')

_itertools_rs = static_library(
  'itertools',
  files('src/lib.rs'),
  gnu_symbol_visibility: 'hidden',
  rust_abi: 'rust',
  rust_args: [
    '--edition', '2018',
    '--cfg', 'feature="use_std"',
    '--cfg', 'feature="use_alloc"',
  ],
  dependencies: [
    either_dep,
  ],
)

itertools_dep = declare_dependency(
  link_with: _itertools_rs,
)
