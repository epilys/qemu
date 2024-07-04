// Copyright 2024 Manos Pitsidianakis <manos.pitsidianakis@linaro.org>
// SPDX-License-Identifier: GPL-2.0 OR GPL-3.0-or-later

//! Definitions required by QEMU when registering the device.

use core::mem::MaybeUninit;

use qemu_api::bindings::*;

use crate::device::PL011State;
use qemu_api::definitions::ObjectImpl;

pub const TYPE_PL011: &std::ffi::CStr = c"pl011";

#[used]
pub static VMSTATE_PL011: VMStateDescription = VMStateDescription {
    name: PL011State::TYPE_INFO.name,
    unmigratable: true,
    ..unsafe { MaybeUninit::<VMStateDescription>::zeroed().assume_init() }
};

qemu_api::module_init! {
    qom: register_type => {
        type_register_static(&PL011State::TYPE_INFO);
    }
}
