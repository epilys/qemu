// Copyright 2024 Manos Pitsidianakis <manos.pitsidianakis@linaro.org>
// SPDX-License-Identifier: GPL-2.0 OR GPL-3.0-or-later

use std::path::Path;

fn main() {
    if !Path::new("src/bindings.rs.inc").exists() {
        panic!(
            "No generated C bindings found! Either build them manually with bindgen or with meson \
             (`ninja bindings.rs`) and copy them to src/bindings.rs.inc, or build through meson."
        );
    }
}
