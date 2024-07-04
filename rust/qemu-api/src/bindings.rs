// Copyright 2024 Manos Pitsidianakis <manos.pitsidianakis@linaro.org>
// SPDX-License-Identifier: GPL-2.0 OR GPL-3.0-or-later
#[cfg(not(MESON_BINDINGS_RS))]
include!("bindings.rs.inc");

#[cfg(MESON_BINDINGS_RS)]
pub use ::_bindings_rs::*;
