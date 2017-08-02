/*
 * Test block device write threshold
 *
 * This work is licensed under the terms of the GNU LGPL, version 2 or later.
 * See the COPYING.LIB file in the top-level directory.
 *
 */

#include "qemu/osdep.h"
#include "block/block_int.h"
#include "block/write-threshold.h"


static void test_threshold_not_set_on_init(void)
{
    uint64_t res;
    BlockDriverState bs;
    memset(&bs, 0, sizeof(bs));

    g_assert(!bdrv_write_threshold_is_set_legacy(&bs));

    res = bdrv_write_threshold_get_legacy(&bs);
    g_assert_cmpint(res, ==, 0);
}

static void test_threshold_set_get(void)
{
    uint64_t threshold = 4 * 1024 * 1024;
    uint64_t res;
    BlockDriverState bs;
    memset(&bs, 0, sizeof(bs));

    bdrv_write_threshold_set_legacy(&bs, threshold);

    g_assert(bdrv_write_threshold_is_set_legacy(&bs));

    res = bdrv_write_threshold_get_legacy(&bs);
    g_assert_cmpint(res, ==, threshold);
}

static void test_threshold_multi_set_get(void)
{
    uint64_t threshold1 = 4 * 1024 * 1024;
    uint64_t threshold2 = 15 * 1024 * 1024;
    uint64_t res;
    BlockDriverState bs;
    memset(&bs, 0, sizeof(bs));

    bdrv_write_threshold_set_legacy(&bs, threshold1);
    bdrv_write_threshold_set_legacy(&bs, threshold2);
    res = bdrv_write_threshold_get_legacy(&bs);
    g_assert_cmpint(res, ==, threshold2);
}

static void test_threshold_not_trigger(void)
{
    uint64_t amount = 0;
    uint64_t threshold = 4 * 1024 * 1024;
    uint64_t offset = 1024;
    uint64_t bytes = 1024;

    amount = bdrv_write_threshold_exceeded(threshold, offset, bytes);
    g_assert_cmpuint(amount, ==, 0);
}


static void test_threshold_trigger(void)
{
    uint64_t amount = 0;
    uint64_t threshold = 4 * 1024 * 1024;
    uint64_t offset = (4 * 1024 * 1024) - 1024;
    uint64_t bytes = 2 * 1024;

    amount = bdrv_write_threshold_exceeded(threshold, offset, bytes);
    g_assert_cmpuint(amount, >=, 1024);
}

typedef struct TestStruct {
    const char *name;
    void (*func)(void);
} TestStruct;


int main(int argc, char **argv)
{
    size_t i;
    TestStruct tests[] = {
        { "/write-threshold/not-set-on-init",
          test_threshold_not_set_on_init },
        { "/write-threshold/set-get",
          test_threshold_set_get },
        { "/write-threshold/multi-set-get",
          test_threshold_multi_set_get },
        { "/write-threshold/not-trigger",
          test_threshold_not_trigger },
        { "/write-threshold/trigger",
          test_threshold_trigger },
        { NULL, NULL }
    };

    g_test_init(&argc, &argv, NULL);
    for (i = 0; tests[i].name != NULL; i++) {
        g_test_add_func(tests[i].name, tests[i].func);
    }
    return g_test_run();
}
