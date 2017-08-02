/*
 * QEMU System Emulator block write threshold notification
 *
 * Copyright Red Hat, Inc. 2014
 *
 * Authors:
 *  Francesco Romani <fromani@redhat.com>
 *
 * This work is licensed under the terms of the GNU LGPL, version 2 or later.
 * See the COPYING.LIB file in the top-level directory.
 */
#ifndef BLOCK_WRITE_THRESHOLD_H
#define BLOCK_WRITE_THRESHOLD_H

#include "qemu-common.h"

/*
 * bdrv_write_threshold_set_legacy:
 *
 * Set the write threshold for block devices, in bytes.
 * Notify when a write exceeds the threshold, meaning the device
 * is becoming full, so it can be transparently resized.
 * To be used with thin-provisioned block devices.
 *
 * Use threshold_bytes == 0 to disable.
 */
void bdrv_write_threshold_set_legacy(BlockDriverState *bs,
                                     uint64_t threshold_bytes);


/*
 * bdrv_write_threshold_get_legacy
 *
 * Get the configured write threshold, in bytes.
 * Zero means no threshold configured.
 *
 */
uint64_t bdrv_write_threshold_get_legacy(const BlockDriverState *bs);

/*
 * bdrv_write_threshold_is_set_legacy
 *
 * Tell if a write threshold is set for a given BDS.
 */
bool bdrv_write_threshold_is_set_legacy(const BlockDriverState *bs);

/*
 * bdrv_write_threshold_exceeded
 *
 * Return the extent of a write request that exceeded the threshold,
 * or zero if the request is below the threshold.
 * Return zero also if the threshold was not set.
 *
 * NOTE: here we assume the following holds for each request this code
 * deals with:
 *
 * assert((offset + bytes) <= UINT64_MAX)
 *
 * Please not there is *not* an actual C assert().
 */
uint64_t bdrv_write_threshold_exceeded(uint64_t threshold, uint64_t offset,
                                       uint64_t bytes);
#endif
