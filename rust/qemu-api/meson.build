add_languages('rust', required: true)

_qemu_api_rs = static_library(
  'qemu_api',
  [files('src/lib.rs')],
  gnu_symbol_visibility: 'hidden',
  rust_abi: 'rust',
  rust_args: rust_args + [
    '--edition', '2021',
    '--cfg', 'MESON_BINDINGS_RS',
  ],
  link_with: [
    _lib_bindings_rs,
  ],
)

qemu_api = declare_dependency(
  link_with: _qemu_api_rs,
)
