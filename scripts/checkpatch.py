#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later

"""

Check patches for submission.

Copyright (c) 2025 Linaro Ltd.

Authors:
 Manos Pitsidianakis <manos.pitsidianakis@linaro.org>

History
=======

This file has been adapted from the Perl script checkpatch.pl included in the
QEMU tree, which was in turn imported verbatim from the Linux kernel tree in
2011. Over the years it was adapted for QEMU-specific checks.

Design / How to implement new checks
====================================

This script tries to detect the format of each file changed in a patch
according to its filename suffix and/or file path. Then, it performs checks
specific to the file format.

Each file format corresponds to a class that inherits from `FileFormat` class.
Each staticmethod whose name starts with `check_` is automatically executed for
each file diff (i.e. collection of hunks) for each patch.

To add new checks, simply add a new `check_DESCRIPTIVE_CHECK_NAME` staticmethod
in the class of the appropriate file format.

To "throw" a warning or an error, this script (ab)uses Python's warnings
feature. Warnings can be thrown freely by default by creating an `Error` or
`Warn` instance and collected using a context manager without breaking
execution of tests:

    # Throw error
    Error("line over 90 characters")
    # Or warn
    # Warn("line over 80 characters")

"""

# pylint: disable=pointless-exception-statement

import argparse
import itertools
import pathlib
from functools import cached_property
import re
from email import message_from_string
import sys
import os
from collections.abc import Callable
import warnings

# Forward declarations of typing aliases
type FileDiffTy = "FileDiff"
type PatchTy = "Patch"
type HunkTy = "Hunk"
type Check = Callable[
    [
        FileDiffTy,
    ],
    None,
]


class Output(UserWarning):
    """
    Base class for checkpatch output items (error or warn)
    """

    # FIXME: Receive patch, hunk in constructor to calculate line numbers right
    # away.
    def __init__(
        self,
        msg: str,
        /,
        *args,
        file_diff: FileDiffTy | None = None,
        match: str | re.Match | None = None,
        hunk: HunkTy | None = None,
        **kwargs,
    ):

        super().__init__(*args, **kwargs)
        self.msg = msg
        self.line_no = 0
        self.file_diff = file_diff
        self.match = match
        self.hunk = hunk
        if file_diff and hunk and match:
            if isinstance(match, str):
                hunk_offset = hunk.contents.find(match)
            elif isinstance(match, re.Match):
                hunk_offset = match.start()
            self.line_no = hunk.find_line(match)
            patch_offset = hunk.offset + hunk_offset
            self.patch_line_no = 1 + file_diff.patch.raw_string.count(
                "\n", 0, patch_offset
            )
        else:
            self.line_no = None
            self.patch_line_no = None
        warnings.warn(self)

    def __str__(self):
        # Needs a unique __str__ value otherwise warnings will be deduplicated
        ret = self.msg
        if self.patch_line_no:
            ret = f"{self.patch_line_no} {ret}"
        if self.file_diff:
            ret = f"{ret} {self.file_diff.filename_b}"
            if self.line_no:
                ret = f"{ret}:{self.line_no}"
        return ret


class Error(Output):
    """
    A checkpatch error
    """


class Warn(Output):
    """
    A checkpatch warning
    """

    def into_error(self) -> Error:
        """
        Convert warning into error
        """
        return Error(
            self.msg,
            file_diff=self.file_diff,
            hunk=self.hunk,
            match=self.match,
        )


class FileFormat:
    """
    Base class for a file format and appropriate checks

    All @staticmethods that start with `check_` are collected as tests
    applicable for this format.

    If a file format is not detectable by filename suffix, its class should
    override the `is_of` classmethod.
    """

    suffixes: list[str]
    checks: dict[str, Check]
    is_source_file: bool = False
    is_executable_source_file: bool = False

    def __new__(cls):
        checks = {}
        suffixes = []
        for c in set([FileFormat, cls]):
            for k, v in c.__dict__.items():
                if isinstance(v, staticmethod) and k.startswith("check_"):
                    checks[k] = v
                elif k == "suffixes":
                    suffixes += v
        val = super().__new__(cls)
        val.checks = checks
        val.suffixes = suffixes
        return val

    @classmethod
    def is_of(cls, path: str) -> bool:
        """
        Returns `True` if path suffix matches this format
        """
        for suf in cls.suffixes:
            if path.endswith(f".{suf}"):
                return True
        return False

    @staticmethod
    def check_trailing_whitespace(file_diff: FileDiffTy):
        """
        Checks newly added lines for trailing whitespace
        """
        # ignore files that are being periodically imported from Linux
        if file_diff.filename_b.startswith(
            "linux-headers"
        ) or file_diff.filename_b.startswith("include/standard-headers"):
            return

        if re.search(
            r"^docs\/.+\.(?:(?:txt)|(?:md)|(?:rst))", file_diff.filename_a
        ):
            # TODO
            # "code blocks in documentation should have empty lines with
            # exactly 4 columns of whitespace
            pass

        for hunk in file_diff.hunks:
            hunk.find_matches(
                r"^\+.*\015", file_diff, Error, lambda _: "DOS line endings"
            )
            hunk.find_matches(
                r"^\+.*\S+[ ]+$",
                file_diff,
                Error,
                lambda _: "trailing whitespace",
            )

    @staticmethod
    def check_column_limit(file_diff: FileDiffTy):
        """
        Checks column widths
        """
        if not file_diff.format.is_source_file:
            return
        # FIXME: exempt URLs
        for hunk in file_diff.hunks:
            for line in hunk.contents.splitlines():
                if not line.startswith("+"):
                    continue
                if len(line) > 90:
                    Error(
                        "line over 90 characters",
                        file_diff=file_diff,
                        match=line,
                        hunk=hunk,
                    )
                elif len(line) > 80:
                    Warn(
                        "line over 80 characters",
                        file_diff=file_diff,
                        match=line,
                        hunk=hunk,
                    )

    @staticmethod
    def check_eof_newline(file_diff: FileDiffTy):
        """
        Require newline at end of file
        """
        # TODO: adding a line without newline at end of file

    @staticmethod
    def check_tabs(file_diff: FileDiffTy):
        """
        Reject indentation with tab character
        """
        # tabs are only allowed in assembly source code, and in
        # some scripts we imported from other projects.
        if isinstance(file_diff.format, (AssemblyFileFormat | PerlFileFormat)):
            return

        if file_diff.filename_b.startswith("target/hexagon/imported"):
            return

        file_diff.find_matches(
            r"^\+.*\t",
            Error,
            lambda _: "code indent should never use tabs",
        )

    @staticmethod
    def check_spdx_header(file_diff: FileDiffTy):
        """
        Check SPDX-License-Identifier exists and references a permitted license
        """
        # TODO: Check for spdx header

        boilerplate_re = r"^\+.*" + "|".join(
            [
                "licensed under the terms of the GNU GPL",
                "under the terms of the GNU General Public License",
                "under the terms of the GNU Lesser General Public",
                "Permission is hereby granted, free of charge",
                "GNU GPL, version 2 or later",
                "See the COPYING file",
            ]
        )
        # FIXME: show only first match for compatibility with checkpatch.pl
        file_diff.find_match(
            boilerplate_re,
            Error,
            lambda _: (
                f"New file '{file_diff.filename_b}' must "
                "not have license boilerplate header text, only "
                "the SPDX-License-Identifier, unless this file was "
                "copied from existing code already having such text."
            ),
        )

    @staticmethod
    def check_qemu(file_diff: FileDiffTy):
        """
        QEMU specific tests
        """
        # FIXME: check only C files for compatibility with checkpatch.pl
        if not isinstance(file_diff.format, CFileFormat):
            return
        file_diff.find_matches(
            r"^\+.*\b(?:Qemu|QEmu)\b",
            Error,
            lambda _: "use QEMU instead of Qemu or QEmu",
        )

    @staticmethod
    def check_file_permissions(fd: FileDiffTy):
        """
        Check for incorrect file permissions
        """
        if (
            fd.format.is_source_file
            and not fd.format.is_executable_source_file
            and fd.mode
            and fd.mode & 0o0111 > 0
        ):
            Error("do not set execute permissions for source files")


class PythonFileFormat(FileFormat):
    """
    Python file format
    """

    is_source_file = True
    is_executable_source_file = True
    suffixes = ["py"]

    @staticmethod
    def check_python_interp(file_diff: FileDiffTy):
        """
        Only allow Python 3 interpreter
        """
        interp_re = r"^\+#![ ]*[/]usr[/]bin[/](?:env )?python\n"
        for h in file_diff.hunks:
            if h.line_no == 1 and re.search(
                interp_re, h.contents.partition("\n")[2]
            ):
                h.find_match(
                    interp_re,
                    file_diff,
                    Error,
                    lambda _: "please use python3 interpreter",
                )


class AssemblyFileFormat(FileFormat):
    """
    Assembly file format
    """

    is_source_file = True
    suffixes = ["s", "S"]


class PerlFileFormat(FileFormat):
    """
    Perl file format
    """

    is_source_file = True
    is_executable_source_file = True
    suffixes = ["pl"]


class MesonFileFormat(FileFormat):
    """
    Meson build file format
    """

    is_source_file = False
    suffixes = ["build"]


class ShellFileFormat(FileFormat):
    """
    Shell script file format
    """

    is_source_file = True
    is_executable_source_file = True
    suffixes = ["sh"]


class TraceEventFileFormat(FileFormat):
    """
    trace-events file format
    """

    suffixes = []

    @classmethod
    def is_of(cls, path: str) -> bool:
        return path.endswith("trace-events")

    @staticmethod
    def check_hex_specifier(file_diff: FileDiffTy):
        """
        Reject %# format specifier
        """
        # TODO: Don't use '#' flag of printf format ('%#') in trace-events, use
        # '0x' prefix instead

    @staticmethod
    def check_hex_prefix(file_diff: FileDiffTy):
        """
        Require 0x prefix for hex numbers
        """
        # TODO: Hex numbers must be prefixed with '0x'


class CFileFormat(FileFormat):
    """
    C file format
    """

    is_source_file = True
    suffixes = ["c", "h", "c.inc"]

    @staticmethod
    def check_non_portable_libc_calls(file_diff: FileDiffTy):
        """
        Check for non-portable libc calls that have portable alternatives in
        QEMU
        """
        replacements = {
            r"\bffs\(": "ctz32",
            r"\bffsl\(": "ctz32() or ctz64",
            r"\bffsll\(": "ctz64",
            r"\bbzero\(": "memset",
            r"\bsysconf\(_SC_PAGESIZE\)": "qemu_real_host_page_size",
            r"\b(?:g_)?assert\(0\)": "g_assert_not_reached",
            r"\b(:?g_)?assert\(false\)": "g_assert_not_reached",
            r"\bstrerrorname_np\(": "strerror",
        }
        non_exit_glib_asserts_re = r"^\+.*" + (
            r"g_assert_cmpstr"
            r"|g_assert_cmpint|g_assert_cmpuint"
            r"|g_assert_cmphex|g_assert_cmpfloat"
            r"|g_assert_true|g_assert_false|g_assert_nonnull"
            r"|g_assert_null|g_assert_no_error|g_assert_error"
            r"|g_test_assert_expected_messages|g_test_trap_assert_passed"
            r"|g_test_trap_assert_stdout|g_test_trap_assert_stdout_unmatched"
            r"|g_test_trap_assert_stderr|g_test_trap_assert_stderr_unmatched"
        )

        for hunk in file_diff.hunks:
            for r, w in replacements.items():
                hunk.find_matches(
                    r"^\+.*" + r,
                    file_diff,
                    Error,
                    lambda match: f"use {w}() instead of {match.group()}",
                )
            hunk.find_matches(
                non_exit_glib_asserts_re,
                file_diff,
                Error,
                lambda m: (
                    "Use g_assert or g_assert_not_reached instead of"
                    f" {m.group()}"
                ),
            )

    @staticmethod
    def check_qemu_error_functions(_: FileDiffTy):
        """
        QEMU error function tests
        """
        # TODO: Find newlines in error messages
        error_funcs_re = (
            r"error_setg|"
            r"error_setg_errno|"
            r"error_setg_win32|"
            r"error_setg_file_open|"
            r"error_set|"
            r"error_prepend|"
            r"warn_reportf_err|"
            r"error_reportf_err|"
            r"error_vreport|"
            r"warn_vreport|"
            r"info_vreport|"
            r"error_report|"
            r"warn_report|"
            r"info_report|"
            r"g_test_message"
        )

    @staticmethod
    def check_ops_structs_are_const(file_diff: FileDiffTy):
        """check for various ops structs, ensure they are const."""
        # TODO

    @staticmethod
    def check_comments(file_diff: FileDiffTy):
        # TODO: no C99 // comments
        for hunk in file_diff.hunks:
            hunk.find_matches(
                r"^\+\s*[/]\s*[*][ \t]*\S+",
                file_diff,
                Warn,
                lambda _: "Block comments use a leading /* on a separate line",
            )
            # TODO: WARN("Block comments use * on subsequent lines
            # FIXME: Check comment context for trailing */
            hunk.find_matches(
                r"^\+\s*[*][ \t]*\S+\s*[*][/]$",
                file_diff,
                Warn,
                lambda _: (
                    "Block comments use a trailing */ on a separate line"
                ),
            )
        # TODO: WARN("Block comments should align the * on each line

    # unimplemented:

    # TODO: switch and case should be at the same indent
    # TODO: that open brace { should be on the previous line
    # TODO: trailing semicolon indicates no statements, indent implies
    # otherwise
    # TODO: suspicious ; after while (0)
    # TODO: superfluous trailing semicolon
    # TODO: suspect code indent for conditional statements ($indent, $sindent)
    # TODO: \"(foo$from)\" should be \"(foo$to)\"
    # TODO: \"foo${from}bar\" should be \"foo${to}bar\"
    # TODO: open brace '{' following function declarations go on the next line
    # TODO: missing space after $1 definition
    # TODO: check for malformed paths in #include statements
    # TODO: check for global initialisers.
    # TODO: check for static initialisers.
    # TODO: * goes on variable not on type
    # TODO: function brace can't be on same line, except for #defines of do
    # while, or if closed on same line
    # TODO: open braces for enum, union and struct go on the same line.
    # TODO: missing space after union, struct or enum definition
    # TODO: check for spacing round square brackets; allowed:
    #  1. with a type on the left -- int [] a;
    #  2. at the beginning of a line for slice initialisers -- [0...10] = 5,
    #  3. inside a curly brace -- = { [0...10] = 5 }
    #  4. after a comma -- [1] = 5, [2] = 6
    #  5. in a macro definition -- #define abc(x) [x] = y
    # TODO: check for spaces between functions and their parentheses.
    # TODO: Check operator spacing.
    # TODO: need space before brace following if, while, etc
    # TODO: closing brace should have a space following it when it has anything
    # on the line
    # TODO: check spacing on square brackets
    # TODO: check spacing on parentheses
    # TODO: Return is not a function.
    # TODO: Return of what appears to be an errno should normally be -'ve
    # TODO: Need a space before open parenthesis after if, while etc
    # TODO: Check for illegal assignment in if conditional -- and check for
    # trailing statements after the conditional.
    # TODO: Check for bitwise tests written as boolean
    # TODO: if and else should not have general statements after it
    # TODO: if should not continue a brace
    # case and default should not have general statements after them
    # TODO: no spaces allowed after \ in define
    # TODO: multi-statement macros should be enclosed in a do while loop, grab
    # the first statement and ensure its the whole macro if its not enclosed
    # in a known good container
    # TODO: check for missing bracing around if etc
    # TODO: no volatiles please
    # TODO: warn about #if 0
    # TODO: check for needless g_free() checks
    # TODO: warn about spacing in #ifdefs
    # TODO: check for memory barriers without a comment.
    # TODO: check of hardware specific defines
    # we have e.g. CONFIG_LINUX and CONFIG_WIN32 for common cases
    # where they might be necessary.
    # TODO: Check that the storage class is at the beginning of a declaration
    # TODO: check the location of the inline attribute, that it is between
    # storage class and type.
    # TODO: check for sizeof(&)
    # TODO: check for new externs in .c files.
    # TODO: check for pointless casting of g_malloc return
    @staticmethod
    def check_misc_recommends(file_diff: FileDiffTy):
        # check for gcc specific __FUNCTION__
        file_diff.find_matches(
            r"^\+.*__FUNCTION__",
            Error,
            lambda _: (
                "__func__ should be used instead of gcc specific __FUNCTION__"
            ),
        )

        # recommend g_path_get_* over g_strdup(basename/dirname(...))
        file_diff.find_matches(
            r"^\+.*\bg_strdup\s*\(\s*(basename|dirname)\s*\(",
            Warn,
            lambda m: (
                "consider using g_path_get_{m.group(1)}() in preference to"
                " g_strdup({m.group(1)}())"
            ),
        )
        # enforce g_memdup2() over g_memdup()
        file_diff.find_matches(
            r"^\+.*\bg_memdup\s*\(",
            Error,
            lambda _: "use g_memdup2() instead of unsafe g_memdup()",
        )
        # TODO: recommend qemu_strto* over strto* for numeric conversions
        # TODO: recommend sigaction over signal for portability, when establishing
        # a handler
        # TODO: recommend qemu_bh_new_guarded instead of qemu_bh_new
        # TODO: recommend aio_bh_new_guarded instead of aio_bh_new
        # check for module_init(), use category-specific init macros
        # explicitly please
        file_diff.find_matches(
            r"^\+.*\bmodule_init\(",
            Error,
            lambda _: (
                "please use block_init(), type_init() etc. instead of"
                " module_init()"
            ),
        )


class Hunk:
    """
    A single diff hunk
    """

    def __init__(self, offset: int, line_no: int, contents: str):
        self.offset = offset
        self.line_no = line_no
        self.contents = contents

    def __repr__(self):
        return self.contents

    def find_match(
        self,
        regex: str,
        file_diff: FileDiffTy,
        category: type[Output],
        cb: Callable[[re.Match], None],
    ) -> bool:
        assert regex.startswith(r"^\+")
        match = re.search(regex, self.contents, re.MULTILINE)
        if match:
            category(
                cb(match),
                file_diff=file_diff,
                match=match,
                hunk=self,
            )
        return match is not None

    def find_matches(
        self,
        regex: str,
        file_diff: FileDiffTy,
        category: type[Output],
        cb: Callable[[re.Match], None],
    ):
        assert regex.startswith(r"^\+")
        for match in re.finditer(regex, self.contents, re.MULTILINE):
            category(
                cb(match),
                file_diff=file_diff,
                match=match,
                hunk=self,
            )

    def find_line(self, match: str | re.Match) -> int:
        if isinstance(match, str):
            offset = self.offset + self.contents.find(match)
        elif isinstance(match, re.Match):
            offset = self.offset + match.start()
        return self.contents.count("\n", 0, offset)


class FileDiff:
    """
    Representation of a batch of diff hunks for a single file in a patch/diff
    """

    def __init__(
        self,
        patch_offset: int,
        patch: PatchTy,
        filename_a: str,
        filename_b: str,
        hunks: list[Hunk],
        mode: int | None = None,
    ):
        self.patch_offset = patch_offset
        self.patch = patch
        self.filename_a = filename_a
        self.filename_b = filename_b
        self.hunks = hunks
        self.mode = mode
        # TODO: add file action (modified/new/deleted/renamed)

    def find_match(
        self,
        regex: str,
        category: type[Output],
        cb: Callable[[re.Match], None],
    ) -> bool:
        for h in self.hunks:
            if h.find_match(regex, self, category, cb):
                return True
        return False

    def find_matches(
        self,
        regex: str,
        category: type[Output],
        cb: Callable[[re.Match], None],
    ):
        for h in self.hunks:
            h.find_matches(regex, self, category, cb)

    def __repr__(self):
        return f"{self.filename_a} {len(self.hunks)} hunks"

    @cached_property
    def format(self) -> FileFormat:
        """
        Returns the detected file format for this file diff
        """

        # Hack(?): discover all subclasses of FileFormat by calling the
        # __subclasses__ method. Classes that might have not been
        # imported/parsed will not appear, but we assume that this code is
        # called after everything has been loaded.
        for subclass in FileFormat.__subclasses__():
            if subclass.is_of(self.filename_b):
                return subclass()
        return FileFormat()


class Configuration:
    def __init__(self, /, signoff: bool = True):
        self.signoff = signoff


class Patch:
    """
    Representation of a patch/diff
    """

    def __init__(
        self,
        configuration: Configuration,
        raw_string: str,
    ):
        """Attempt to parse `raw_string` as a patch"""

        self.raw_string = raw_string
        self.configuration = configuration
        self.msg = None
        self.description = None
        self.body = None
        self.file_diffs = []
        self.parse_exception = None

        self.msg = message_from_string(raw_string)
        if self.msg.is_multipart():
            self.parse_exception = ValueError("multipart")
            return
        # FIXME: verify "\n---\n", normalize for CRLF(?)
        try:
            self.description, self.body = self.msg.get_payload().split(
                "\n---\n", maxsplit=1
            )
        except ValueError as exc:
            self.parse_exception = ValueError(
                "Does not appear to be a unified-diff format patch"
            ).with_traceback(exc.__traceback__)
            return

        body_offset = raw_string.find(self.body)
        files = []
        prev = None
        for match in re.finditer(r"^diff --git ", self.body, re.MULTILINE):
            if prev is not None:
                files.append(
                    (body_offset + prev, self.body[prev : match.start()])
                )
            prev = match.start()

        if prev is not None:
            files.append((body_offset + prev, self.body[prev:]))

        self.file_diffs = []
        for offset, f in files:
            matches = re.search(
                r"^diff --git a\/(?P<filename_a>[^ ]+) b\/(?P<filename_b>[^"
                r" ]+)$",
                f,
                re.MULTILINE,
            )
            if not matches:
                self.parse_exception = ValueError(
                    "Does not appear to be a unified-diff format patch"
                )
                return
            filename_a = matches.groups("filename_a")[0]
            filename_b = matches.groups("filename_b")[0]
            hunks: list[Hunk] = []
            prev = None
            for match in re.finditer(
                r"^@@ [-]\d+,\d+ [+](?P<line_no>\d+),\d+ @@", f, re.MULTILINE
            ):
                if prev is not None:
                    hunks.append(
                        Hunk(
                            offset + prev[0],
                            prev[1],
                            f[prev[0] : match.start()],
                        )
                    )
                prev = (match.start(), int(match.group("line_no")))

            if prev is not None:
                hunks.append(Hunk(offset + prev[0], prev[1], f[prev[0] :]))
            matches = re.search(
                r"^new (?:file )?mode\s+([0-7]+)$",
                f[: hunks[0].offset],
                re.MULTILINE,
            )
            if matches:
                mode = int(matches.group(1), 8)
            else:
                mode = None
            self.file_diffs.append(
                FileDiff(
                    offset, self, filename_a, filename_b, hunks, mode=mode
                )
            )

    def check_author_address(self):
        """Check for invalid author address"""
        if self.parse_exception:
            return
        regex = r".*? via .*?<qemu-\w+@nongnu\.org>"

        authors = itertools.chain(
            self.msg.get_all("From") or [], self.msg.get_all("Author") or []
        )
        for val in authors:
            if re.search(regex, val):
                Error(
                    "Author email address is mangled by the mailing list",
                )

    def check_signoff(self):
        """Check patch for valid signoff (DCO)"""
        if self.parse_exception:
            return
        for match in re.finditer(
            r"^\s*signed-off-by",
            self.description,
            re.MULTILINE | re.IGNORECASE,
        ):
            match_start = self.description[match.start() :]
            if not re.search(
                r"^\s*Signed-off-by:.*$", match_start, re.MULTILINE
            ):
                Error(
                    'The correct form is "Signed-off-by" found'
                    f" {match_start=}",
                )
            if re.search(r"\s*signed-off-by:\S", match_start):
                Error(
                    "Space required after Signed-off-by:",
                )
            break
        else:
            Error(
                "Missing Signed-off-by: line(s)",
            )

    def check(self):
        """Check patch and all files in patch according to their file format"""
        if self.parse_exception:
            Error(str(self.parse_exception))
            return
        self.check_author_address()
        self.check_addition_deletions()
        if self.configuration.signoff:
            self.check_signoff()
        for f in self.file_diffs:
            for v in f.format.checks.values():
                v(f)

    def check_addition_deletions(self):
        """
        Check that all additions/deletions/renames are reflected in MAINTAINERS
        file
        """
        if self.parse_exception:
            return
        # TODO:
        pass


def top_of_kernel_tree(path: pathlib.Path) -> bool:
    """Verify path is the root directory of project"""
    for item in [
        "COPYING",
        "MAINTAINERS",
        "Makefile",
        "README.rst",
        "docs",
        "VERSION",
        "linux-user",
        "system",
    ]:
        if not (path / item).exists():
            return False
    return True


def main():
    """
    Read CLI arguments and print result to stdout
    """
    parser = argparse.ArgumentParser(prog="checkpatch.py")
    parser.add_argument("FILE", type=pathlib.Path, action="extend", nargs="*")
    parser.add_argument("--version", action="version", version="%(prog)s 1.0")
    parser.add_argument("-q", "--quiet", action="store_true")
    parser.add_argument(
        "--no-tree", action="store_true", help="run without a qemu tree"
    )
    parser.add_argument(
        "--no-signoff",
        action="store_true",
        help="do not check for 'Signed-off-by' line",
    )
    parser.add_argument(
        "--patch", action="store_true", help="treat FILE as patchfile"
    )
    # TODO:
    # parser.add_argument(
    #     "--branch", action="store_true",
    #     help="treat args as GIT revision list"
    # )
    # parser.add_argument(
    #     "--emacs", action="store_true", help="emacs compile window format"
    # )
    parser.add_argument(
        "--terse", action="store_true", help="one line per report"
    )
    # TODO:
    # parser.add_argument(
    #     "-f,",
    #     "--file",
    #     action="store_true",
    #     help="treat FILE as regular source file",
    # )
    parser.add_argument(
        "--strict", action="store_true", help="fail if only warnings are found"
    )
    # TODO:
    parser.add_argument(
        "--root", type=pathlib.Path, help="PATH to the qemu tree root"
    )
    parser.add_argument(
        "--no-summary",
        action="store_true",
        help="suppress the per-file summary",
    )
    parser.add_argument(
        "--mailback",
        action="store_true",
        help="only produce a report in case of warnings/errors",
    )
    parser.add_argument(
        "--summary-file",
        action="store_true",
        default=False,
        help="include the filename in summary",
    )
    # TODO:
    # parser.add_argument(
    #     "--debug",
    #     action="store_true",
    #     help=(
    #         "KEY=[0|1]turn on/off debugging of KEY, where KEY is one of"
    #         " 'values', 'possible', 'type', and 'attr' (default is all off)"
    #     ),
    # )
    parser.add_argument(
        "--test-only",
        type=str,
        metavar="WORD",
        help="report only warnings/errors containing WORD literally",
    )

    # TODO:
    # parser.add_argument(
    #     "--codespell",
    #     action="store_true",
    #     help=(
    #         "Use the codespell dictionary for spelling/typos (default:"
    #         " $codespellfile)"
    #     ),
    # )
    # parser.add_argument(
    #     "--codespellfile",
    #     action="store_true",
    #     help="Use this codespell dictionary",
    # )
    def parse_color(s: str) -> bool | None:
        if s == "always":
            return True
        if s == "never":
            return False
        if s == "auto":
            return None
        raise ValueError("always,never,auto")

    parser.register("type", "color", parse_color)
    parser.add_argument(
        "--color",
        type="color",
        metavar="WHEN",
        default=None,
        help=(
            "Use colors 'always', 'never', or only when output is a terminal"
            " ('auto'). Default is 'auto'."
        ),
    )
    args = parser.parse_args()

    if args.color is None:
        args.color = sys.stdout.isatty()

    if not args.no_tree:
        if args.root:
            root = pathlib.Path(args.root)
            if not top_of_kernel_tree(root):
                print("--root does not point at a valid tree")
        else:
            if top_of_kernel_tree(pathlib.Path(os.getcwd())):
                root = pathlib.Path(os.getcwd())
            else:
                root = (pathlib.Path(sys.argv[0]) / ".." / "..").resolve()
        if not top_of_kernel_tree(root):
            print("Must be run from the top-level dir. of a qemu tree")
            sys.exit(2)

    configuration = Configuration(signoff=not args.no_signoff)

    any_error = 0
    for filename in args.FILE:
        output = []
        errors_no = 0
        warnings_no = 0
        lines_no = 0

        with open(filename, encoding="utf-8") as file:
            p = Patch(configuration, file.read())
            lines_no += len(p.raw_string.splitlines())
            with warnings.catch_warnings(record=True) as w:
                p.check()
                if args.strict:
                    for i in w:
                        if isinstance(i.message, Warn):
                            i.message = i.message.into_error()
                output += w

        for o in output:
            if isinstance(o.message, Warn):
                warnings_no += 1
            else:
                errors_no += 1
        any_error = errors_no
        for o in output:

            class Colors:
                WARNING = "\033[35m" if args.color else ""
                ERROR = "\033[91m" if args.color else ""
                ENDC = "\033[0m" if args.color else ""
                BOLD = "\033[1m" if args.color else ""

            if args.terse:
                print(
                    f"{Colors.BOLD}{filename}:"
                    f"{o.message.patch_line_no(p) or ''}{Colors.ENDC}: ",
                    end="",
                )

            if isinstance(o.message, Warn):
                print(
                    f"{Colors.WARNING}{Colors.BOLD}WARNING:{Colors.ENDC} ",
                    end="",
                )
            else:
                print(
                    f"{Colors.ERROR}{Colors.BOLD}ERROR:{Colors.ENDC} ",
                    end="",
                )
            print(o.message.msg)
            if not args.terse and o.message.file_diff:
                print(
                    f"#{o.message.patch_line_no or ''}: FILE:"
                    f" {o.message.file_diff.filename_b}:{o.message.line_no or ''}"
                )
                if o.message.patch_line_no:
                    line = p.raw_string.splitlines()[
                        o.message.patch_line_no - 1
                    ]

                    print(
                        line.translate(
                            str.maketrans(
                                {
                                    "\000": r"\0",
                                    "\011": r"^I",
                                }
                            )
                        )
                    )
            if not args.terse:
                print()

        if not (args.mailback and (errors_no, warnings_no) == (0, 0)):
            if args.summary_file:
                print(f"{filename} ", end="")
            print(
                f"total: {errors_no} error{'s'[:errors_no^1]},"
                f" {warnings_no} warning{'s'[:warnings_no^1]},"
                f" {lines_no} line{'s'[:lines_no^1]} checked"
            )

            if not args.no_summary and not args.terse:
                print()
                if errors_no == 0:
                    print(
                        filename,
                        "has no obvious style problems and is ready for"
                        " submission.",
                    )
                else:
                    print(
                        filename,
                        "has style problems, please review.  If any of these"
                        " errors\nare false positives report them to the"
                        " maintainer, see\nCHECKPATCH in MAINTAINERS.",
                    )
    return any_error


if __name__ == "__main__":
    sys.exit(main())
