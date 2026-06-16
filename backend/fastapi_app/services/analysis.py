import ast


DECISION_NODES = (ast.If, ast.For, ast.While)


def _node_dump(node):
    return ast.dump(node, annotate_fields=False, include_attributes=False)


def _is_name(node, name):
    return isinstance(node, ast.Name) and node.id == name


def _is_empty_collection_assign(node, collection_type):
    if not isinstance(node, ast.Assign) or len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
        return False
    value = node.value
    if collection_type == "list":
        return isinstance(value, ast.List) and not value.elts
    if collection_type == "dict":
        return isinstance(value, ast.Dict) and not value.keys
    if collection_type == "set":
        return (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Name)
            and value.func.id == "set"
            and not value.args
            and not value.keywords
        )
    return False


class FunctionMetadataCollector(ast.NodeVisitor):
    def __init__(self):
        self.current_function = None
        self.recursive_calls = {}
        self.cached_functions = set()

    def visit_FunctionDef(self, node):
        cached = any(
            (
                isinstance(decorator, ast.Name) and decorator.id == "lru_cache"
            )
            or (
                isinstance(decorator, ast.Attribute) and decorator.attr == "lru_cache"
            )
            for decorator in node.decorator_list
        )
        if cached:
            self.cached_functions.add(node.name)

        previous = self.current_function
        self.current_function = node.name
        self.recursive_calls.setdefault(node.name, [])
        self.generic_visit(node)
        self.current_function = previous

    def visit_AsyncFunctionDef(self, node):
        self.visit_FunctionDef(node)

    def visit_Call(self, node):
        if self.current_function and isinstance(node.func, ast.Name) and node.func.id == self.current_function:
            self.recursive_calls.setdefault(self.current_function, []).append(node.lineno)
        self.generic_visit(node)


class UsageCollector(ast.NodeVisitor):
    def __init__(self):
        self.assigned = {}
        self.used = set()

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Store):
            self.assigned.setdefault(node.id, []).append(node.lineno)
        elif isinstance(node.ctx, ast.Load):
            self.used.add(node.id)


class PatternDetector(ast.NodeVisitor):
    def __init__(self, recursive_functions, cached_functions):
        self.recursive_functions = recursive_functions
        self.cached_functions = cached_functions
        self.issues = []
        self._seen = set()
        self._loop_depth = 0
        self._loop_stack = []
        self._range_index_loops = []
        self._assigned_values = {}

    def add_issue(self, line, severity, description, category, fix_available=True, effort="auto", impact="medium"):
        key = (line, description)
        if key in self._seen:
            return
        self._seen.add(key)
        self.issues.append(
            {
                "severity": severity,
                "description": description,
                "line": line,
                "category": category,
                "fix_available": fix_available,
                "effort": effort,
                "impact": impact,
            }
        )

    def visit_Assign(self, node):
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            self._assigned_values[node.targets[0].id] = node.value
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        if node.name in self.recursive_functions and node.name not in self.cached_functions:
            self.add_issue(
                node.lineno,
                "high",
                f"Recursive function '{node.name}' has no memoization cache.",
                "recursion",
                True,
                "auto",
                "high",
            )

        if self._looks_like_bubble_selection_or_insertion(node):
            self.add_issue(
                node.lineno,
                "high",
                "Manual sorting implementation detected; built-in sorting is usually faster and safer.",
                "algorithm",
                True,
                "auto",
                "high",
            )

        if self._looks_like_linear_search(node):
            self.add_issue(
                node.lineno,
                "medium",
                "Manual linear search returning an index can be replaced with next(...enumerate(...)).",
                "algorithm",
                True,
                "auto",
                "medium",
            )

        self.generic_visit(node)

    def visit_For(self, node):
        self._loop_depth += 1
        self._loop_stack.append(node)
        if self._loop_depth >= 2:
            self.add_issue(
                node.lineno,
                "high",
                "Nested loop detected; repeated scanning can cause O(n^2) behavior.",
                "performance",
                True,
                "auto",
                "high",
            )

        if self._is_range_len_loop(node):
            self.add_issue(
                node.lineno,
                "medium",
                "Loop iterates with range(len(...)) and indexes into the same collection.",
                "performance",
                True,
                "auto",
                "medium",
            )

        if self._has_list_membership_check(node):
            self.add_issue(
                node.lineno,
                "high",
                "Membership test against a list inside a loop should use a set lookup.",
                "performance",
                True,
                "auto",
                "high",
            )

        if self._has_append_candidate(node):
            self.add_issue(
                node.lineno,
                "low",
                "list.append() inside a loop can often be replaced with a comprehension.",
                "performance",
                True,
                "auto",
                "low",
            )

        if self._has_string_concat(node):
            self.add_issue(
                node.lineno,
                "medium",
                "String concatenation with += inside a loop is inefficient.",
                "string",
                True,
                "auto",
                "medium",
            )

        if self._has_split_reuse(node):
            self.add_issue(
                node.lineno,
                "medium",
                "Repeated split() on the same string inside a loop should be hoisted.",
                "string",
                True,
                "auto",
                "medium",
            )

        if self._builds_dict_with_loop(node):
            self.add_issue(
                node.lineno,
                "medium",
                "Dictionary is being built manually in a loop; a dict comprehension may be better.",
                "memory",
                True,
                "auto",
                "medium",
            )

        if self._builds_set_with_loop(node):
            self.add_issue(
                node.lineno,
                "medium",
                "Set is being built manually in a loop; a set comprehension may be better.",
                "memory",
                True,
                "auto",
                "medium",
            )

        if self._manual_counter(node):
            self.add_issue(
                node.lineno,
                "medium",
                "Manual loop counter detected; enumerate() is clearer and avoids bookkeeping.",
                "performance",
                True,
                "auto",
                "medium",
            )

        if self._uses_pop_zero(node):
            self.add_issue(
                node.lineno,
                "high",
                "list.pop(0) inside loop is O(n); use collections.deque for queue behavior.",
                "memory",
                True,
                "auto",
                "high",
            )

        if self._keys_only_for_values(node):
            self.add_issue(
                node.lineno,
                "low",
                "Iterating over dict.keys() while only reading values is unnecessary.",
                "performance",
                True,
                "auto",
                "low",
            )

        if self._constant_rebuild(node):
            self.add_issue(
                node.lineno,
                "medium",
                "Loop rebuilds a constant expression that can be hoisted outside.",
                "performance",
                True,
                "auto",
                "medium",
            )

        if self._formats_string_collection(node):
            self.add_issue(
                node.lineno,
                "medium",
                "Formatting strings inside a tight loop building output can often be joined more efficiently.",
                "string",
                True,
                "auto",
                "medium",
            )

        self.generic_visit(node)
        self._loop_stack.pop()
        self._loop_depth -= 1

    def visit_While(self, node):
        if isinstance(node.test, ast.Compare):
            for comparator in node.test.comparators:
                if isinstance(comparator, ast.Call) and _is_name(comparator.func, "len"):
                    self.add_issue(
                        node.lineno,
                        "low",
                        "Repeated len(...) call in loop condition can be hoisted.",
                        "performance",
                        True,
                        "auto",
                        "low",
                    )
        self.generic_visit(node)

    def visit_Call(self, node):
        if self._is_sorted_index_access(node):
            self.add_issue(
                node.lineno,
                "medium",
                "Sorting solely to access the smallest or largest element is wasteful.",
                "algorithm",
                True,
                "auto",
                "medium",
            )

        if self._is_generator_candidate_call(node):
            self.add_issue(
                node.lineno,
                "low",
                "A full list is being materialized where a generator expression would suffice.",
                "memory",
                True,
                "auto",
                "low",
            )

        self.generic_visit(node)

    def visit_ListComp(self, node):
        self.generic_visit(node)

    def _is_range_len_loop(self, node):
        iterator = node.iter
        if not (
            isinstance(iterator, ast.Call)
            and _is_name(iterator.func, "range")
            and len(iterator.args) == 1
            and isinstance(iterator.args[0], ast.Call)
            and _is_name(iterator.args[0].func, "len")
            and len(iterator.args[0].args) == 1
        ):
            return False
        target_id = node.target.id if isinstance(node.target, ast.Name) else None
        collection = iterator.args[0].args[0]
        if not target_id or not isinstance(collection, ast.Name):
            return False
        for child in ast.walk(node):
            if (
                isinstance(child, ast.Subscript)
                and isinstance(child.value, ast.Name)
                and child.value.id == collection.id
                and _node_dump(child.slice) == _node_dump(ast.Name(id=target_id, ctx=ast.Load()))
            ):
                return True
        return False

    def _has_append_candidate(self, node):
        return any(
            isinstance(child, ast.Call)
            and isinstance(child.func, ast.Attribute)
            and child.func.attr == "append"
            for child in ast.walk(node)
        )

    def _has_string_concat(self, node):
        return any(
            isinstance(child, ast.AugAssign)
            and isinstance(child.op, ast.Add)
            and isinstance(child.target, ast.Name)
            for child in ast.walk(node)
        )

    def _has_split_reuse(self, node):
        split_calls = {}
        for child in ast.walk(node):
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute) and child.func.attr == "split":
                key = _node_dump(child.func.value)
                split_calls[key] = split_calls.get(key, 0) + 1
        return any(count > 1 for count in split_calls.values())

    def _has_list_membership_check(self, node):
        for child in ast.walk(node):
            if isinstance(child, ast.Compare) and len(child.ops) == 1:
                comparator = child.comparators[0]
                if isinstance(child.ops[0], (ast.In, ast.NotIn)) and isinstance(comparator, ast.Name):
                    assigned = self._assigned_values.get(comparator.id)
                    if isinstance(assigned, ast.List):
                        return True
        return False

    def _builds_dict_with_loop(self, node):
        for child in node.body:
            if isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name):
                        return True
        return False

    def _builds_set_with_loop(self, node):
        return any(
            isinstance(child, ast.Call)
            and isinstance(child.func, ast.Attribute)
            and child.func.attr == "add"
            for child in ast.walk(node)
        )

    def _manual_counter(self, node):
        return any(
            isinstance(child, ast.AugAssign)
            and isinstance(child.op, ast.Add)
            and isinstance(child.target, ast.Name)
            and isinstance(child.value, ast.Constant)
            and child.value.value == 1
            for child in node.body
        )

    def _uses_pop_zero(self, node):
        return any(
            isinstance(child, ast.Call)
            and isinstance(child.func, ast.Attribute)
            and child.func.attr == "pop"
            and len(child.args) == 1
            and isinstance(child.args[0], ast.Constant)
            and child.args[0].value == 0
            for child in ast.walk(node)
        )

    def _keys_only_for_values(self, node):
        iterator = node.iter
        if not (
            isinstance(iterator, ast.Call)
            and isinstance(iterator.func, ast.Attribute)
            and iterator.func.attr == "keys"
            and isinstance(iterator.func.value, ast.Name)
            and isinstance(node.target, ast.Name)
        ):
            return False
        dict_name = iterator.func.value.id
        key_name = node.target.id
        for child in ast.walk(node):
            if isinstance(child, ast.Subscript) and isinstance(child.value, ast.Name) and child.value.id == dict_name:
                if _node_dump(child.slice) == _node_dump(ast.Name(id=key_name, ctx=ast.Load())):
                    return True
        return False

    def _constant_rebuild(self, node):
        loop_vars = {
            child.id
            for child in ast.walk(node.target)
            if isinstance(child, ast.Name)
        }
        for child in node.body:
            if isinstance(child, ast.Assign) and len(child.targets) == 1 and isinstance(child.targets[0], ast.Name):
                names = {name.id for name in ast.walk(child.value) if isinstance(name, ast.Name)}
                if not names.intersection(loop_vars) and names:
                    return True
                if isinstance(child.value, (ast.Constant, ast.Tuple, ast.List, ast.Dict, ast.Set)):
                    return True
        return False

    def _formats_string_collection(self, node):
        append_targets = set()
        for child in ast.walk(node):
            if (
                isinstance(child, ast.Call)
                and isinstance(child.func, ast.Attribute)
                and child.func.attr == "append"
                and isinstance(child.func.value, ast.Name)
                and child.args
                and isinstance(child.args[0], (ast.JoinedStr, ast.BinOp))
            ):
                append_targets.add(child.func.value.id)
        return bool(append_targets)

    def _is_sorted_index_access(self, node):
        if not (isinstance(node.func, ast.Name) and node.func.id == "sorted" and node.args):
            return False
        parent = getattr(node, "parent", None)
        return isinstance(parent, ast.Subscript)

    def _is_generator_candidate_call(self, node):
        return (
            isinstance(node.func, ast.Name)
            and node.func.id in {"sum", "any", "all", "max", "min", "tuple", "set"}
            and len(node.args) == 1
            and isinstance(node.args[0], ast.ListComp)
        )

    def _looks_like_bubble_selection_or_insertion(self, node):
        return (
            isinstance(node, ast.FunctionDef)
            and len([child for child in ast.walk(node) if isinstance(child, ast.For)]) >= 2
            and any(isinstance(child, ast.Assign) and any(isinstance(target, ast.Subscript) for target in child.targets) for child in ast.walk(node))
        )

    def _looks_like_linear_search(self, node):
        if not node.body:
            return False
        has_return_index = any(
            isinstance(child, ast.Return) and isinstance(child.value, ast.Name)
            for child in ast.walk(node)
        )
        has_return_minus_one = any(
            isinstance(child, ast.Return) and isinstance(child.value, ast.UnaryOp) and isinstance(child.value.op, ast.USub)
            for child in ast.walk(node)
        )
        return has_return_index and has_return_minus_one


def _annotate_parents(tree):
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            child.parent = parent


def _cyclomatic_complexity(tree):
    complexity = 1
    for node in ast.walk(tree):
        if isinstance(node, DECISION_NODES):
            complexity += 1
        elif isinstance(node, ast.BoolOp) and isinstance(node.op, (ast.And, ast.Or)):
            complexity += max(len(node.values) - 1, 1)
    return complexity


def analyze_code(code: str) -> dict:
    tree = ast.parse(code)
    _annotate_parents(tree)

    function_meta = FunctionMetadataCollector()
    function_meta.visit(tree)

    detector = PatternDetector(
        recursive_functions={name for name, calls in function_meta.recursive_calls.items() if calls},
        cached_functions=function_meta.cached_functions,
    )
    detector.visit(tree)

    usage = UsageCollector()
    usage.visit(tree)
    for name, lines in usage.assigned.items():
        if name.startswith("_") or name in usage.used:
            continue
        for line in lines:
            detector.add_issue(
                line,
                "medium",
                f"Variable '{name}' is assigned but never used.",
                "memory",
                False,
                "manual",
                "low",
            )

    complexity = _cyclomatic_complexity(tree)
    return {
        "issues": sorted(detector.issues, key=lambda issue: (issue["line"], issue["severity"])),
        "issue_count": len(detector.issues),
        "complexity_estimate": "high" if complexity >= 10 else "medium" if complexity >= 5 else "low",
        "cyclomatic_complexity": complexity,
    }
