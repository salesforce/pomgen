import common.label as label
import config.config as config
import generate.impl.js.jsgenerationstrategy as jsgenerationstrategy
import unittest


class JsGenerationStrategyTest(unittest.TestCase):

    def test_is_source_ref_hook__node_modules_prefix_match(self):
        """
        A label whose canonical form matches a configured node_modules
        label prefix is not a source ref.
        """
        strategy = _new_strategy(node_modules_label_prefixes=("//foo:node_modules",))

        lbl = label.Label("//foo:node_modules/bar-package")

        self.assertFalse(strategy.is_source_ref__hook(lbl))

    def test_is_source_ref_hook__regular_source_label(self):
        """
        A regular source label, unrelated to node_modules, is a source ref.
        """
        strategy = _new_strategy(node_modules_label_prefixes=("//foo:node_modules",))

        lbl = label.Label("//some/package:target")

        self.assertTrue(strategy.is_source_ref__hook(lbl))

    def test_is_source_ref_hook__unmatched_node_modules_label_raises(self):
        """
        A label that looks like a node_modules reference (its target
        contains "node_modules/"), but does not match any configured
        node_modules label prefix, indicates a misconfiguration and should
        raise an error instead of being silently treated as a source ref.
        """
        strategy = _new_strategy(node_modules_label_prefixes=("//foo:node_modules",))

        lbl = label.Label("//other:node_modules/bar-package")

        with self.assertRaises(Exception) as ctx:
            strategy.is_source_ref__hook(lbl)
        self.assertIn("node_modules/", str(ctx.exception))
        self.assertIn("pnpm_lockfile_paths", str(ctx.exception))


def _new_strategy(node_modules_label_prefixes):
    strategy = jsgenerationstrategy.JsGenerationStrategy("", config.Config(), verbose=False)
    strategy._node_modules_label_prefixes = node_modules_label_prefixes
    return strategy


if __name__ == '__main__':
    unittest.main()
