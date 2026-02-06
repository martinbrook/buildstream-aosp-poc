"""local_external - stage files from an external (non-project) directory.

Unlike the built-in ``local`` source, this plugin can reference absolute
paths outside the project directory. This is intended for large prebuilt
toolchains that should not be copied into the project tree.

**Usage:**

.. code:: yaml

   kind: local_external
   path: /home/user/aosp/prebuilts/clang/host/linux-x86/clang-r522817

.. warning::

   This source is NOT reproducible across machines — it relies on an
   absolute host path. It is intended for PoC/development workflows only.
"""

import os
import hashlib

from buildstream import Source, SourceError, Directory


class LocalExternalSource(Source):

    BST_MIN_VERSION = "2.0"
    BST_STAGE_VIRTUAL_DIRECTORY = True

    __digest = None

    def configure(self, node):
        node.validate_keys(["path", *Source.COMMON_CONFIG_KEYS])
        self.path = node.get_str("path")
        if not os.path.isabs(self.path):
            raise SourceError(
                "{}: local_external path must be absolute, got: {}".format(self, self.path),
                reason="path-not-absolute",
            )

    def preflight(self):
        if not os.path.exists(self.path):
            raise SourceError(
                "{}: path does not exist: {}".format(self, self.path),
                reason="path-not-found",
            )

    def is_resolved(self):
        return True

    def is_cached(self):
        return True

    def get_unique_key(self):
        # Use the path itself as part of the key, plus a shallow content hash.
        # For true reproducibility you'd hash the full tree; for a PoC the
        # path + mtime of the top-level directory is sufficient.
        try:
            stat = os.stat(self.path)
            content_tag = "{}:{}:{}".format(self.path, stat.st_mtime_ns, stat.st_size)
        except OSError:
            content_tag = self.path
        return hashlib.sha256(content_tag.encode()).hexdigest()

    def load_ref(self, node):
        pass

    def get_ref(self):
        return None

    def set_ref(self, ref, node):
        pass

    def fetch(self):
        pass

    def stage_directory(self, directory):
        assert isinstance(directory, Directory)
        with self.timed_activity("Staging external files from {}".format(self.path)):
            if os.path.isdir(self.path):
                directory.import_files(self.path)
            else:
                directory.import_single_file(self.path)


def setup():
    return LocalExternalSource
