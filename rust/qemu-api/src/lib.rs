// Copyright 2024 Manos Pitsidianakis <manos.pitsidianakis@linaro.org>
// SPDX-License-Identifier: GPL-2.0 OR GPL-3.0-or-later

#![doc = include_str!("../README.md")]

#[cfg(MESON_BINDINGS_RS)]
extern crate _bindings_rs;

#[cfg_attr(not(MESON_BINDINGS_RS), allow(
    improper_ctypes_definitions,
    improper_ctypes,
    non_camel_case_types,
    non_snake_case,
    non_upper_case_globals
))]
#[cfg_attr(not(MESON_BINDINGS_RS), allow(
    clippy::missing_const_for_fn,
    clippy::too_many_arguments,
    clippy::approx_constant,
    clippy::use_self,
    clippy::useless_transmute,
    clippy::missing_safety_doc,
))]
#[cfg_attr(not(MESON_BINDINGS_RS), rustfmt::skip)]
pub mod bindings;

pub mod definitions;
pub mod device_class;

#[cfg(test)]
mod tests;

use std::alloc::{GlobalAlloc, Layout};

extern "C" {
    pub fn g_aligned_alloc0(
        n_blocks: bindings::gsize,
        n_block_bytes: bindings::gsize,
        alignment: bindings::gsize,
    ) -> bindings::gpointer;
    pub fn g_aligned_free(mem: bindings::gpointer);
    pub fn g_malloc0(n_bytes: bindings::gsize) -> bindings::gpointer;
    pub fn g_free(mem: bindings::gpointer);
}

/// An allocator that uses the same allocator as QEMU in C.
///
/// It is enabled by default with the `allocator` feature.
///
/// To set it up manually as a global allocator in your crate:
///
/// ```ignore
/// use qemu_api::QemuAllocator;
///
/// #[global_allocator]
/// static GLOBAL: QemuAllocator = QemuAllocator::new();
/// ```
#[derive(Clone, Copy, Debug)]
#[repr(C)]
pub struct QemuAllocator {
    _unused: [u8; 0],
}

#[cfg_attr(feature = "allocator", global_allocator)]
pub static GLOBAL: QemuAllocator = QemuAllocator::new();

impl QemuAllocator {
    pub const fn new() -> Self {
        Self { _unused: [] }
    }
}

impl Default for QemuAllocator {
    fn default() -> Self {
        Self::new()
    }
}

unsafe impl GlobalAlloc for QemuAllocator {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        if layout.align() == 0 {
            g_malloc0(layout.size().try_into().unwrap()).cast::<u8>()
        } else {
            g_aligned_alloc0(
                layout.size().try_into().unwrap(),
                1,
                layout.align().try_into().unwrap(),
            )
            .cast::<u8>()
        }
    }

    unsafe fn dealloc(&self, ptr: *mut u8, layout: Layout) {
        if layout.align() == 0 {
            g_free(ptr.cast::<_>())
        } else {
            g_aligned_free(ptr.cast::<_>())
        }
    }
}
