project(
  'bilge',
  'rust',
  version : '0.2.0',
  license : 'MIT or Apache-2.0',
)

arbitrary_int_dep = subproject('arbitrary-int').get_variable('arbitrary_int_dep')
bilge_impl_dep = subproject('bilge-impl').get_variable('bilge_impl_dep')

lib = static_library(
  'bilge',
  'src/lib.rs',
  override_options : ['rust_std=2021', 'build.rust_std=2021'],
  rust_abi : 'rust',
  native : true,
  dependencies: [
    arbitrary_int_dep,
    bilge_impl_dep,
  ],
)

bilge_dep = declare_dependency(
  link_with : [lib],
)
