add_languages('rust', required: true)

_lib_bindings_rs = static_library(
  '_bindings_rs',
  bindings_rs,
  gnu_symbol_visibility: 'hidden',
  rust_abi: 'rust',
  rust_args: rust_args + [
    '--edition', '2021',
  ],
)

subdir('qemu-api')

subdir('hw')
