"""
Copyright (c) 2021, salesforce.com, inc.
All rights reserved.
SPDX-License-Identifier: BSD-3-Clause
For full license text, see the LICENSE file in the repo root or https://opensource.org/licenses/BSD-3-Clause
"""


SUPPORTED_OPERATORS = ("=", " is ", " startswith ")


class Predicate:

    def __init__(self, predicate):
        for op in SUPPORTED_OPERATORS:
            if op in predicate:
                self.lhs, self.rhs = [t.strip() for t in predicate.split(op)]
                self.op = op.strip()
                break
        else:
            raise Exception("Unsupported operator in predicate [%s]" % predicate)

    def matches(self, value):
        if self.op in ("=", "is"):
            if self.rhs == "empty":
                return len(value) == 0
            else:
                return self.rhs == str(value)
        elif self.op == "startswith":
            return value.startswith(self.rhs)
        return False

    def __str__(self):
        return "%s %s %s" % (self.lhs, self.op, self.rhs)


class InstanceQuery:
    """
    Simple matching on instance(s).

    EXPERIMENTAL
    """
    def __init__(self, predicate_str):
        self.predicates = []
        for part in [p.strip() for p in predicate_str.split("and")]:
             self.predicates.append(Predicate(part))

    def __call__(self, thing):
        if isinstance(thing, (list, tuple)):
            return [i for i in thing if self._query_single_instance(i) is not None]
        else:
            return self._query_single_instance(thing)

    def _query_single_instance(self, thing):
        if isinstance(thing, dict):
            class EmptyShell:
                pass
            thing_to_query = EmptyShell()
            thing_to_query.__dict__ = thing
        else:
            thing_to_query = thing
        for predicate in self.predicates:
            if hasattr(thing_to_query, predicate.lhs):
                value = getattr(thing_to_query, predicate.lhs)
                if not predicate.matches(value):
                    break
            else:
                break
        else:
            # if we didn't break out of the for loop, it is a match!
            return thing
        return None
