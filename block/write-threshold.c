/*
 * QEMU System Emulator block write threshold notification
 *
 * Copyright Red Hat, Inc. 2014
 * Copyright 2017 Manos Pitsidianakis
 *
 * Authors:
 *  Francesco Romani <fromani@redhat.com>
 *  Manos Pitsidianakis <el13635@mail.ntua.gr>
 *
 * This work is licensed under the terms of the GNU LGPL, version 2 or later.
 * See the COPYING.LIB file in the top-level directory.
 */

#include "qemu/osdep.h"
#include "block/block_int.h"
#include "qemu/coroutine.h"
#include "block/write-threshold.h"
#include "qemu/notify.h"
#include "qapi-event.h"
#include "qmp-commands.h"


uint64_t bdrv_write_threshold_get_legacy(const BlockDriverState *bs)
{
    return bs->write_threshold_offset;
}

bool bdrv_write_threshold_is_set_legacy(const BlockDriverState *bs)
{
    return bs->write_threshold_offset > 0;
}

static void write_threshold_disable_legacy(BlockDriverState *bs)
{
    if (bdrv_write_threshold_is_set_legacy(bs)) {
        notifier_with_return_remove(&bs->write_threshold_notifier);
        bs->write_threshold_offset = 0;
    }
}

static int coroutine_fn before_write_notify(NotifierWithReturn *notifier,
                                            void *opaque)
{
    BdrvTrackedRequest *req = opaque;
    BlockDriverState *bs = req->bs;
    uint64_t amount = 0;
    uint64_t threshold = bdrv_write_threshold_get_legacy(bs);
    uint64_t offset = req->offset;
    uint64_t bytes = req->bytes;

    amount = bdrv_write_threshold_exceeded(threshold, offset, bytes);
    if (amount > 0) {
        qapi_event_send_block_write_threshold(
            bs->node_name,
            amount,
            bs->write_threshold_offset,
            &error_abort);

        /* autodisable to avoid flooding the monitor */
        write_threshold_disable_legacy(bs);
    }

    return 0; /* should always let other notifiers run */
}

static void write_threshold_register_notifier(BlockDriverState *bs)
{
    bs->write_threshold_notifier.notify = before_write_notify;
    bdrv_add_before_write_notifier(bs, &bs->write_threshold_notifier);
}

static void write_threshold_update_legacy(BlockDriverState *bs,
                                          int64_t threshold_bytes)
{
    bs->write_threshold_offset = threshold_bytes;
}

void bdrv_write_threshold_set_legacy(BlockDriverState *bs,
                                     uint64_t threshold_bytes)
{
    if (bdrv_write_threshold_is_set_legacy(bs)) {
        if (threshold_bytes > 0) {
            write_threshold_update_legacy(bs, threshold_bytes);
        } else {
            write_threshold_disable_legacy(bs);
        }
    } else {
        if (threshold_bytes > 0) {
            /* avoid multiple registration */
            write_threshold_register_notifier(bs);
            write_threshold_update_legacy(bs, threshold_bytes);
        }
        /* discard bogus disable request */
    }
}

void qmp_block_set_write_threshold(const char *node_name,
                                   uint64_t threshold_bytes,
                                   Error **errp)
{
    BlockDriverState *bs;
    AioContext *aio_context;

    bs = bdrv_find_node(node_name);
    if (!bs) {
        error_setg(errp, "Device '%s' not found", node_name);
        return;
    }

    aio_context = bdrv_get_aio_context(bs);
    aio_context_acquire(aio_context);

    bdrv_write_threshold_set_legacy(bs, threshold_bytes);

    aio_context_release(aio_context);
}


/* The write-threshold filter drivers delivers a one-time BLOCK_WRITE_THRESHOLD
 * event when a passing write request exceeds the configured write threshold
 * offset of the filter.
 *
 * This is useful to transparently resize thin-provisioned drives without
 * the guest OS noticing.
 */

#define QEMU_OPT_WRITE_THRESHOLD "write-threshold"
static BlockDriver write_threshold;
static QemuOptsList write_threshold_opts = {
    .name = "write-threshold",
    .head = QTAILQ_HEAD_INITIALIZER(write_threshold_opts.head),
    .desc = {
        {
            .name = QEMU_OPT_WRITE_THRESHOLD,
            .type = QEMU_OPT_NUMBER,
            .help = "configured threshold for the block device, bytes. Use 0"
                    "to disable the threshold",
        },
        { /* end of list */ }
    },
};

static bool bdrv_write_threshold_is_set(const BlockDriverState *bs)
{
    uint64_t threshold = *(uint64_t *)bs->opaque;
    return threshold > 0;
}

static void bdrv_write_threshold_disable(BlockDriverState *bs)
{
    uint64_t *threshold = (uint64_t *)bs->opaque;
    if (bdrv_write_threshold_is_set(bs)) {
        *threshold = 0;
    }
}

uint64_t bdrv_write_threshold_exceeded(uint64_t threshold, uint64_t offset,
                                       uint64_t bytes)
{
    if (threshold) {
        if (offset > threshold) {
            return (offset - threshold) + bytes;
        }
        if ((offset + bytes) > threshold) {
            return (offset + bytes) - threshold;
        }
    }
    return 0;
}


static void bdrv_write_threshold_update(BlockDriverState *bs,
                                        int64_t threshold_bytes)
{
    uint64_t *threshold = (uint64_t *)bs->opaque;
    *threshold = threshold_bytes;
}

static void bdrv_write_threshold_check_amount(BlockDriverState *bs,
                                              uint64_t offset,
                                              uint64_t bytes)
{
    uint64_t threshold = *(uint64_t *)bs->opaque;
    uint64_t amount = 0;

    amount = bdrv_write_threshold_exceeded(threshold, offset, bytes);
    if (amount > 0) {
        qapi_event_send_block_write_threshold(child_bs(bs)->node_name,
                                              amount,
                                              threshold,
                                              &error_abort);
        /* autodisable to avoid flooding the monitor */
        bdrv_write_threshold_disable(bs);
    }
}

/* Filter driver methods */

static int coroutine_fn write_threshold_co_preadv(BlockDriverState *bs,
                                                  uint64_t offset,
                                                  uint64_t bytes,
                                                  QEMUIOVector *qiov,
                                                  int flags)
{
    return bdrv_co_preadv(bs->file, offset, bytes, qiov, flags);
}

static int coroutine_fn write_threshold_co_pwritev(BlockDriverState *bs,
                                                   uint64_t offset,
                                                   uint64_t bytes,
                                                   QEMUIOVector *qiov,
                                                   int flags)
{
    bdrv_write_threshold_check_amount(bs, offset, bytes);
    return bdrv_co_pwritev(bs->file, offset, bytes, qiov, flags);
}

static int coroutine_fn write_threshold_co_pwrite_zeroes(
                                                        BlockDriverState *bs,
                                                        int64_t offset,
                                                        int bytes,
                                                        BdrvRequestFlags flags)
{
    bdrv_write_threshold_check_amount(bs, offset, bytes);
    return bdrv_co_pwrite_zeroes(bs->file, offset, bytes, flags);
}

static int coroutine_fn write_threshold_co_pdiscard(BlockDriverState *bs,
                                                    int64_t offset, int bytes)
{
    bdrv_write_threshold_check_amount(bs, offset, bytes);
    return bdrv_co_pdiscard(bs->file->bs, offset, bytes);
}


static int64_t write_threshold_getlength(BlockDriverState *bs)
{
    return bdrv_getlength(bs->file->bs);
}

static int write_threshold_open(BlockDriverState *bs, QDict *options,
                                int flags, Error **errp)
{
    Error *local_err = NULL;
    int ret = 0;
    QemuOpts *opts = NULL;
    uint64_t threshold = 0;

    bs->file = bdrv_open_child(NULL, options, "file", bs, &child_file,
                               false, errp);
    if (!bs->file) {
        return -EINVAL;
    }

    bs->supported_write_flags = bs->file->bs->supported_write_flags;
    bs->supported_zero_flags = bs->file->bs->supported_zero_flags;

    opts = qemu_opts_create(&write_threshold_opts, NULL, 0, &error_abort);

    qemu_opts_absorb_qdict(opts, options, &local_err);
    if (local_err) {
        error_propagate(errp, local_err);
        ret = -EINVAL;
        goto ret;
    }

    threshold = qemu_opt_get_number(opts, QEMU_OPT_WRITE_THRESHOLD, 0);
    bdrv_write_threshold_update(bs, threshold);

ret:
    qemu_opts_del(opts);
    return ret;
}

static void write_threshold_close(BlockDriverState *bs)
{
}

static int write_threshold_co_flush(BlockDriverState *bs)
{
    return bdrv_co_flush(bs->file->bs);
}

static int64_t coroutine_fn write_threshold_co_get_block_status(
                                                       BlockDriverState *bs,
                                                       int64_t sector_num,
                                                       int nb_sectors,
                                                       int *pnum,
                                                       BlockDriverState **file)
{
    assert(child_bs(bs));
    *pnum = nb_sectors;
    *file = child_bs(bs);
    return BDRV_BLOCK_RAW | BDRV_BLOCK_OFFSET_VALID |
           (sector_num << BDRV_SECTOR_BITS);
}

static bool write_threshold_recurse_is_first_non_filter(
                                                   BlockDriverState *bs,
                                                   BlockDriverState *candidate)
{
    return bdrv_recurse_is_first_non_filter(bs->file->bs, candidate);
}

static BlockDriver write_threshold = {
    .format_name                      = "write-threshold",
    .instance_size                    = sizeof(uint64_t),

    .bdrv_open                        = write_threshold_open,
    .bdrv_close                       = write_threshold_close,

    .bdrv_co_flush                    = write_threshold_co_flush,
    .bdrv_co_preadv                   = write_threshold_co_preadv,
    .bdrv_co_pwritev                  = write_threshold_co_pwritev,
    .bdrv_co_pwrite_zeroes            = write_threshold_co_pwrite_zeroes,
    .bdrv_co_pdiscard                 = write_threshold_co_pdiscard,

    .bdrv_getlength                   = write_threshold_getlength,
    .bdrv_child_perm                  = bdrv_filter_default_perms,
    .bdrv_co_get_block_status         = write_threshold_co_get_block_status,
    .bdrv_recurse_is_first_non_filter =
                                   write_threshold_recurse_is_first_non_filter,

    .is_filter                        = true,
};

static void bdrv_write_threshold_init(void)
{
    bdrv_register(&write_threshold);
}

block_init(bdrv_write_threshold_init);
