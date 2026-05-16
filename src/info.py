"""
Copyright (c) 2026, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""


import common.common as common
import config.config as config
import common.manifestcontent as manifestcontent
import generate.generationstrategyfactory as generationstrategyfactory


if __name__ == "__main__":
    repo_root = common.get_repo_root(None)
    cfg = config.load(repo_root, verbose=False)
    fac = generationstrategyfactory.GenerationStrategyFactory(
        repo_root, cfg, manifestcontent.NOOP, verbose=False)
    print("poppy v3")
    print("Installed generators:")
    print("\n".join(["  %s" % n for n in fac.get_strategy_names()]))
