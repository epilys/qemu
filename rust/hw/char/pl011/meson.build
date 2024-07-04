if not config_host_data.get('CONFIG_HAVE_RUST')
  subdir_done()
endif

add_languages('rust', required: true)


arbitrary_int_dep = subproject('arbitrary-int').get_variable('arbitrary_int_dep')
bilge_dep = subproject('bilge').get_variable('bilge_dep')
bilge_impl_dep = subproject('bilge-impl').get_variable('bilge_impl_dep')

_libpl011_rs = static_library(
  'pl011',
  files('src/lib.rs'),
  rust_abi: 'c',
  rust_args: rust_args + [
    '--edition', '2021',
  ],
  dependencies: [
    bilge_dep,
    bilge_impl_dep,
    qemu_api,
  ],
)

specific_ss.add(when: 'CONFIG_X_PL011_RUST', if_true: [declare_dependency(
  link_whole: [_libpl011_rs],
)])
