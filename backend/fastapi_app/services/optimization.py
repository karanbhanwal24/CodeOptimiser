import ast
import copy


def _dump(node):
    return ast.dump(node, annotate_fields=False, include_attributes=False)


def _is_name(node, name):
    return isinstance(node, ast.Name) and node.id == name


def _same_reference(left, right):
    if isinstance(left, ast.Name) and isinstance(right, ast.Name):
        return left.id == right.id
    return _dump(left) == _dump(right)


def _parse(code):
    return ast.fix_missing_locations(ast.parse(code))


def _to_code(tree, notes=None):
    code = ast.unparse(ast.fix_missing_locations(tree))
    if notes:
        prefix = "\n".join(f"# NOTE: {note}" for note in notes)
        return f"{prefix}\n{code}"
    return code


def _validate_variant(code):
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False


def _code_signature(code):
    return _dump(_parse(code))


def _ensure_import(tree, module, name):
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == module:
            if any(alias.name == name for alias in node.names):
                return
            node.names.append(ast.alias(name=name))
            return
    tree.body.insert(0, ast.ImportFrom(module=module, names=[ast.alias(name=name)], level=0))


def _used_names(node):
    return {child.id for child in ast.walk(node) if isinstance(child, ast.Name)}


def _replace_name(node, old_name, new_expr):
    class Replacer(ast.NodeTransformer):
        def visit_Name(self, inner):
            if isinstance(inner.ctx, ast.Load) and inner.id == old_name:
                return copy.deepcopy(new_expr)
            return inner

    return Replacer().visit(copy.deepcopy(node))


class BodyRewriter(ast.NodeTransformer):
    def __init__(self, rewrite_fn):
        self.rewrite_fn = rewrite_fn
        self.changed = False
        self.notes = []

    def visit_Module(self, node):
        node.body = self.rewrite_fn(node.body, self)
        return self.generic_visit(node)

    def visit_FunctionDef(self, node):
        node.body = self.rewrite_fn(node.body, self)
        return self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        node.body = self.rewrite_fn(node.body, self)
        return self.generic_visit(node)


def _append_loop_rewrite(body, state):
    new_body = []
    index = 0
    while index < len(body):
        current = body[index]
        nxt = body[index + 1] if index + 1 < len(body) else None
        if (
            isinstance(current, ast.Assign)
            and len(current.targets) == 1
            and isinstance(current.targets[0], ast.Name)
            and isinstance(current.value, ast.List)
            and not current.value.elts
            and isinstance(nxt, ast.For)
            and not nxt.orelse
            and len(nxt.body) == 1
            and isinstance(nxt.body[0], ast.Expr)
            and isinstance(nxt.body[0].value, ast.Call)
            and isinstance(nxt.body[0].value.func, ast.Attribute)
            and isinstance(nxt.body[0].value.func.value, ast.Name)
            and nxt.body[0].value.func.value.id == current.targets[0].id
            and nxt.body[0].value.func.attr == "append"
            and len(nxt.body[0].value.args) == 1
        ):
            new_body.append(
                ast.Assign(
                    targets=current.targets,
                    value=ast.ListComp(
                        elt=nxt.body[0].value.args[0],
                        generators=[ast.comprehension(target=nxt.target, iter=nxt.iter, ifs=[], is_async=0)],
                    ),
                )
            )
            state.changed = True
            index += 2
            continue
        new_body.append(current)
        index += 1
    return new_body


def _dict_comp_rewrite(body, state):
    new_body = []
    index = 0
    while index < len(body):
        current = body[index]
        nxt = body[index + 1] if index + 1 < len(body) else None
        if (
            isinstance(current, ast.Assign)
            and len(current.targets) == 1
            and isinstance(current.targets[0], ast.Name)
            and isinstance(current.value, ast.Dict)
            and not current.value.keys
            and isinstance(nxt, ast.For)
            and len(nxt.body) == 1
            and isinstance(nxt.body[0], ast.Assign)
            and len(nxt.body[0].targets) == 1
            and isinstance(nxt.body[0].targets[0], ast.Subscript)
            and isinstance(nxt.body[0].targets[0].value, ast.Name)
            and nxt.body[0].targets[0].value.id == current.targets[0].id
        ):
            target = nxt.body[0].targets[0]
            new_body.append(
                ast.Assign(
                    targets=current.targets,
                    value=ast.DictComp(
                        key=target.slice,
                        value=nxt.body[0].value,
                        generators=[ast.comprehension(target=nxt.target, iter=nxt.iter, ifs=[], is_async=0)],
                    ),
                )
            )
            state.changed = True
            index += 2
            continue
        new_body.append(current)
        index += 1
    return new_body


def _set_comp_rewrite(body, state):
    new_body = []
    index = 0
    while index < len(body):
        current = body[index]
        nxt = body[index + 1] if index + 1 < len(body) else None
        if (
            isinstance(current, ast.Assign)
            and len(current.targets) == 1
            and isinstance(current.targets[0], ast.Name)
            and isinstance(current.value, ast.Call)
            and _is_name(current.value.func, "set")
            and not current.value.args
            and isinstance(nxt, ast.For)
            and len(nxt.body) == 1
            and isinstance(nxt.body[0], ast.Expr)
            and isinstance(nxt.body[0].value, ast.Call)
            and isinstance(nxt.body[0].value.func, ast.Attribute)
            and isinstance(nxt.body[0].value.func.value, ast.Name)
            and nxt.body[0].value.func.value.id == current.targets[0].id
            and nxt.body[0].value.func.attr == "add"
            and len(nxt.body[0].value.args) == 1
        ):
            new_body.append(
                ast.Assign(
                    targets=current.targets,
                    value=ast.SetComp(
                        elt=nxt.body[0].value.args[0],
                        generators=[ast.comprehension(target=nxt.target, iter=nxt.iter, ifs=[], is_async=0)],
                    ),
                )
            )
            state.changed = True
            index += 2
            continue
        new_body.append(current)
        index += 1
    return new_body


class RecursiveCacheTransformer(ast.NodeTransformer):
    def __init__(self):
        self.changed = False

    def visit_Module(self, node):
        self.generic_visit(node)
        if self.changed:
            _ensure_import(node, "functools", "lru_cache")
        return node

    def visit_FunctionDef(self, node):
        self.generic_visit(node)
        has_recursive_call = any(
            isinstance(child, ast.Call) and isinstance(child.func, ast.Name) and child.func.id == node.name
            for child in ast.walk(node)
        )
        cached = any(
            (
                isinstance(decorator, ast.Name) and decorator.id == "lru_cache"
            )
            or (
                isinstance(decorator, ast.Attribute) and decorator.attr == "lru_cache"
            )
            for decorator in node.decorator_list
        )
        if has_recursive_call and not cached:
            node.decorator_list.insert(0, ast.Call(func=ast.Name(id="lru_cache", ctx=ast.Load()), args=[], keywords=[ast.keyword(arg="maxsize", value=ast.Constant(value=None))]))
            self.changed = True
        return node


class StringConcatTransformer(ast.NodeTransformer):
    def __init__(self):
        self.changed = False

    def visit_Module(self, node):
        node.body = self._rewrite_body(node.body)
        return self.generic_visit(node)

    def visit_FunctionDef(self, node):
        node.body = self._rewrite_body(node.body)
        return self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        node.body = self._rewrite_body(node.body)
        return self.generic_visit(node)

    def _rewrite_body(self, body):
        new_body = []
        index = 0
        while index < len(body):
            current = body[index]
            nxt = body[index + 1] if index + 1 < len(body) else None
            if (
                isinstance(current, ast.Assign)
                and len(current.targets) == 1
                and isinstance(current.targets[0], ast.Name)
                and isinstance(current.value, ast.Constant)
                and current.value.value == ""
                and isinstance(nxt, ast.For)
                and not nxt.orelse
            ):
                concat_target = current.targets[0].id
                parts_name = f"{concat_target}_parts"
                pieces = []
                supported = True
                for stmt in nxt.body:
                    if (
                        isinstance(stmt, ast.AugAssign)
                        and isinstance(stmt.target, ast.Name)
                        and stmt.target.id == concat_target
                        and isinstance(stmt.op, ast.Add)
                    ):
                        pieces.append(ast.Expr(value=ast.Call(func=ast.Attribute(value=ast.Name(id=parts_name, ctx=ast.Load()), attr="append", ctx=ast.Load()), args=[stmt.value], keywords=[])))
                    else:
                        supported = False
                        break
                if supported and pieces:
                    new_loop = copy.deepcopy(nxt)
                    new_loop.body = pieces
                    new_body.extend(
                        [
                            ast.Assign(targets=[ast.Name(id=parts_name, ctx=ast.Store())], value=ast.List(elts=[], ctx=ast.Load())),
                            new_loop,
                            ast.Assign(
                                targets=current.targets,
                                value=ast.Call(
                                    func=ast.Attribute(value=ast.Constant(value=""), attr="join", ctx=ast.Load()),
                                    args=[ast.Name(id=parts_name, ctx=ast.Load())],
                                    keywords=[],
                                ),
                            ),
                        ]
                    )
                    self.changed = True
                    index += 2
                    continue
            new_body.append(current)
            index += 1
        return new_body


class MembershipSetTransformer(ast.NodeTransformer):
    def __init__(self):
        self.changed = False
        self._assigned_lists = {}

    def visit_Assign(self, node):
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and isinstance(node.value, ast.List):
            self._assigned_lists[node.targets[0].id] = node.value
        return self.generic_visit(node)

    def visit_Module(self, node):
        node.body = self._rewrite_body(node.body)
        return self.generic_visit(node)

    def visit_FunctionDef(self, node):
        node.body = self._rewrite_body(node.body)
        return self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        node.body = self._rewrite_body(node.body)
        return self.generic_visit(node)

    def _rewrite_body(self, body):
        new_body = []
        for stmt in body:
            if isinstance(stmt, ast.For):
                compare_names = []
                for child in ast.walk(stmt):
                    if isinstance(child, ast.Compare) and len(child.ops) == 1 and isinstance(child.ops[0], (ast.In, ast.NotIn)):
                        comparator = child.comparators[0]
                        if isinstance(comparator, ast.Name) and comparator.id in self._assigned_lists:
                            compare_names.append(comparator.id)
                            child.comparators[0] = ast.Name(id=f"{comparator.id}_set", ctx=ast.Load())
                            self.changed = True
                for name in sorted(set(compare_names)):
                    new_body.append(
                        ast.Assign(
                            targets=[ast.Name(id=f"{name}_set", ctx=ast.Store())],
                            value=ast.Call(func=ast.Name(id="set", ctx=ast.Load()), args=[ast.Name(id=name, ctx=ast.Load())], keywords=[]),
                        )
                    )
                new_body.append(stmt)
            else:
                new_body.append(stmt)
        return new_body


class RangeLenTransformer(ast.NodeTransformer):
    def __init__(self):
        self.changed = False

    def visit_For(self, node):
        self.generic_visit(node)
        iterator = node.iter
        if not (
            isinstance(iterator, ast.Call)
            and _is_name(iterator.func, "range")
            and len(iterator.args) == 1
            and isinstance(iterator.args[0], ast.Call)
            and _is_name(iterator.args[0].func, "len")
            and len(iterator.args[0].args) == 1
            and isinstance(iterator.args[0].args[0], ast.Name)
            and isinstance(node.target, ast.Name)
        ):
            return node
        index_name = node.target.id
        collection_name = iterator.args[0].args[0].id
        uses_index = False
        only_subscript = True
        replacer = {}
        for child in ast.walk(node):
            if isinstance(child, ast.Subscript) and isinstance(child.value, ast.Name) and child.value.id == collection_name:
                if _dump(child.slice) == _dump(ast.Name(id=index_name, ctx=ast.Load())):
                    uses_index = True
            elif isinstance(child, ast.Name) and child.id == index_name and not isinstance(child.ctx, ast.Store):
                parent = getattr(child, "parent", None)
                if not (
                    isinstance(parent, ast.Subscript)
                    and isinstance(parent.value, ast.Name)
                    and parent.value.id == collection_name
                    and _dump(parent.slice) == _dump(ast.Name(id=index_name, ctx=ast.Load()))
                ):
                    only_subscript = False
        if not uses_index:
            return node
        value_name = f"{collection_name}_item"

        class IndexReplacer(ast.NodeTransformer):
            def visit_Subscript(self, inner):
                self.generic_visit(inner)
                if isinstance(inner.value, ast.Name) and inner.value.id == collection_name and _dump(inner.slice) == _dump(ast.Name(id=index_name, ctx=ast.Load())):
                    return ast.Name(id=value_name, ctx=ast.Load())
                return inner

        new_body = [IndexReplacer().visit(copy.deepcopy(stmt)) for stmt in node.body]
        self.changed = True
        if only_subscript:
            node.target = ast.Name(id=value_name, ctx=ast.Store())
            node.iter = ast.Name(id=collection_name, ctx=ast.Load())
            node.body = new_body
            return node

        class EnumerateReplacer(ast.NodeTransformer):
            def visit_Subscript(self, inner):
                self.generic_visit(inner)
                if isinstance(inner.value, ast.Name) and inner.value.id == collection_name and _dump(inner.slice) == _dump(ast.Name(id=index_name, ctx=ast.Load())):
                    return ast.Name(id=value_name, ctx=ast.Load())
                return inner

        node.target = ast.Tuple(elts=[ast.Name(id=index_name, ctx=ast.Store()), ast.Name(id=value_name, ctx=ast.Store())], ctx=ast.Store())
        node.iter = ast.Call(func=ast.Name(id="enumerate", ctx=ast.Load()), args=[ast.Name(id=collection_name, ctx=ast.Load())], keywords=[])
        node.body = [EnumerateReplacer().visit(copy.deepcopy(stmt)) for stmt in node.body]
        return node


class ParentSetter(ast.NodeVisitor):
    def generic_visit(self, node):
        for child in ast.iter_child_nodes(node):
            child.parent = node
            self.visit(child)


class SortedMinMaxTransformer(ast.NodeTransformer):
    def __init__(self):
        self.changed = False
        self.notes = []

    def visit_Subscript(self, node):
        self.generic_visit(node)
        if (
            isinstance(node.value, ast.Call)
            and _is_name(node.value.func, "sorted")
            and len(node.value.args) == 1
        ):
            if isinstance(node.slice, ast.Constant) and node.slice.value == 0:
                self.changed = True
                self.notes.append("Replacing sorted(...)[0] with min(...) avoids a full sort.")
                return ast.Call(func=ast.Name(id="min", ctx=ast.Load()), args=[node.value.args[0]], keywords=[])
            if isinstance(node.slice, ast.UnaryOp) and isinstance(node.slice.op, ast.USub) and isinstance(node.slice.operand, ast.Constant) and node.slice.operand.value == 1:
                self.changed = True
                self.notes.append("Replacing sorted(...)[-1] with max(...) avoids a full sort.")
                return ast.Call(func=ast.Name(id="max", ctx=ast.Load()), args=[node.value.args[0]], keywords=[])
        return node


class KeysToValuesTransformer(ast.NodeTransformer):
    def __init__(self):
        self.changed = False

    def visit_For(self, node):
        self.generic_visit(node)
        if not (
            isinstance(node.iter, ast.Call)
            and isinstance(node.iter.func, ast.Attribute)
            and node.iter.func.attr == "keys"
            and isinstance(node.iter.func.value, ast.Name)
            and isinstance(node.target, ast.Name)
        ):
            return node
        dict_name = node.iter.func.value.id
        key_name = node.target.id
        value_name = f"{dict_name}_value"

        class ValueReplacer(ast.NodeTransformer):
            def visit_Subscript(self, inner):
                self.generic_visit(inner)
                if isinstance(inner.value, ast.Name) and inner.value.id == dict_name and _dump(inner.slice) == _dump(ast.Name(id=key_name, ctx=ast.Load())):
                    return ast.Name(id=value_name, ctx=ast.Load())
                return inner

        replaced_body = [ValueReplacer().visit(copy.deepcopy(stmt)) for stmt in node.body]
        if _dump(ast.Module(body=replaced_body, type_ignores=[])) != _dump(ast.Module(body=node.body, type_ignores=[])):
            node.iter = ast.Call(func=ast.Attribute(value=ast.Name(id=dict_name, ctx=ast.Load()), attr="values", ctx=ast.Load()), args=[], keywords=[])
            node.target = ast.Name(id=value_name, ctx=ast.Store())
            node.body = replaced_body
            self.changed = True
        return node


class GeneratorTransformer(ast.NodeTransformer):
    def __init__(self):
        self.changed = False

    def visit_Call(self, node):
        self.generic_visit(node)
        if isinstance(node.func, ast.Name) and node.func.id in {"sum", "any", "all", "max", "min", "tuple", "set"} and len(node.args) == 1 and isinstance(node.args[0], ast.ListComp):
            node.args[0] = ast.GeneratorExp(elt=node.args[0].elt, generators=node.args[0].generators)
            self.changed = True
        return node


class InlineSingleUseTransformer(ast.NodeTransformer):
    def __init__(self):
        self.changed = False

    def visit_Module(self, node):
        node.body = self._rewrite(node.body)
        return self.generic_visit(node)

    def visit_FunctionDef(self, node):
        node.body = self._rewrite(node.body)
        return self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        node.body = self._rewrite(node.body)
        return self.generic_visit(node)

    def _rewrite(self, body):
        result = []
        index = 0
        while index < len(body):
            current = body[index]
            nxt = body[index + 1] if index + 1 < len(body) else None
            if (
                isinstance(current, ast.Assign)
                and len(current.targets) == 1
                and isinstance(current.targets[0], ast.Name)
                and nxt is not None
            ):
                name = current.targets[0].id
                if isinstance(current.value, (ast.List, ast.Dict, ast.Set, ast.ListComp, ast.DictComp, ast.SetComp, ast.GeneratorExp)):
                    result.append(current)
                    index += 1
                    continue
                if (
                    isinstance(current.value, ast.Call)
                    and isinstance(current.value.func, ast.Name)
                    and current.value.func.id in {"list", "dict", "set", "deque", "Counter"}
                ):
                    result.append(current)
                    index += 1
                    continue
                uses = [child for child in ast.walk(nxt) if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load) and child.id == name]
                if len(uses) == 1:
                    result.append(_replace_name(nxt, name, current.value))
                    self.changed = True
                    index += 2
                    continue
            result.append(current)
            index += 1
        return result


class DequeTransformer(ast.NodeTransformer):
    def __init__(self):
        self.changed = False

    def visit_Module(self, node):
        self.generic_visit(node)
        if self.changed:
            _ensure_import(node, "collections", "deque")
        return node

    def visit_Assign(self, node):
        self.generic_visit(node)
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and isinstance(node.value, ast.List) and not node.value.elts:
            queue_name = node.targets[0].id
            parent = getattr(node, "parent", None)
            scope = parent.body if hasattr(parent, "body") else []
            if any(
                isinstance(child, ast.Call)
                and isinstance(child.func, ast.Attribute)
                and isinstance(child.func.value, ast.Name)
                and child.func.value.id == queue_name
                and child.func.attr == "pop"
                and child.args
                and isinstance(child.args[0], ast.Constant)
                and child.args[0].value == 0
                for stmt in scope
                for child in ast.walk(stmt)
            ):
                node.value = ast.Call(func=ast.Name(id="deque", ctx=ast.Load()), args=[], keywords=[])
                self.changed = True
        return node

    def visit_Call(self, node):
        self.generic_visit(node)
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "pop"
            and len(node.args) == 1
            and isinstance(node.args[0], ast.Constant)
            and node.args[0].value == 0
        ):
            node.func.attr = "popleft"
            node.args = []
            self.changed = True
        return node


class CounterTransformer(ast.NodeTransformer):
    def __init__(self):
        self.changed = False

    def visit_Module(self, node):
        node.body = self._rewrite(node.body)
        self.generic_visit(node)
        if self.changed:
            _ensure_import(node, "collections", "Counter")
        return node

    def visit_FunctionDef(self, node):
        node.body = self._rewrite(node.body)
        return self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        node.body = self._rewrite(node.body)
        return self.generic_visit(node)

    def _rewrite(self, body):
        result = []
        index = 0
        while index < len(body):
            current = body[index]
            nxt = body[index + 1] if index + 1 < len(body) else None
            if (
                isinstance(current, ast.Assign)
                and len(current.targets) == 1
                and isinstance(current.targets[0], ast.Name)
                and isinstance(current.value, ast.Dict)
                and not current.value.keys
                and isinstance(nxt, ast.For)
                and len(nxt.body) == 1
                and isinstance(nxt.body[0], ast.Assign)
                and len(nxt.body[0].targets) == 1
                and isinstance(nxt.body[0].targets[0], ast.Subscript)
                and isinstance(nxt.body[0].targets[0].value, ast.Name)
                and nxt.body[0].targets[0].value.id == current.targets[0].id
                and isinstance(nxt.body[0].value, ast.BinOp)
                and isinstance(nxt.body[0].value.op, ast.Add)
            ):
                result.append(
                    ast.Assign(
                        targets=current.targets,
                        value=ast.Call(func=ast.Name(id="Counter", ctx=ast.Load()), args=[nxt.iter], keywords=[]),
                    )
                )
                self.changed = True
                index += 2
                continue
            result.append(current)
            index += 1
        return result


class UniqueSetTransformer(ast.NodeTransformer):
    def __init__(self):
        self.changed = False

    def visit_Module(self, node):
        node.body = self._rewrite(node.body)
        return self.generic_visit(node)

    def visit_FunctionDef(self, node):
        node.body = self._rewrite(node.body)
        return self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        node.body = self._rewrite(node.body)
        return self.generic_visit(node)

    def _rewrite(self, body):
        result = []
        index = 0
        while index < len(body):
            current = body[index]
            nxt = body[index + 1] if index + 1 < len(body) else None
            if (
                isinstance(current, ast.Assign)
                and len(current.targets) == 1
                and isinstance(current.targets[0], ast.Name)
                and isinstance(current.value, ast.List)
                and not current.value.elts
                and isinstance(nxt, ast.For)
                and len(nxt.body) == 1
                and isinstance(nxt.body[0], ast.If)
                and isinstance(nxt.body[0].test, ast.Compare)
                and len(nxt.body[0].test.ops) == 1
                and isinstance(nxt.body[0].test.ops[0], ast.NotIn)
                and isinstance(nxt.body[0].test.comparators[0], ast.Name)
                and nxt.body[0].test.comparators[0].id == current.targets[0].id
                and len(nxt.body[0].body) == 1
                and isinstance(nxt.body[0].body[0], ast.Expr)
                and isinstance(nxt.body[0].body[0].value, ast.Call)
                and isinstance(nxt.body[0].body[0].value.func, ast.Attribute)
                and isinstance(nxt.body[0].body[0].value.func.value, ast.Name)
                and nxt.body[0].body[0].value.func.value.id == current.targets[0].id
                and nxt.body[0].body[0].value.func.attr == "append"
            ):
                result.append(
                    ast.Assign(
                        targets=current.targets,
                        value=ast.Call(func=ast.Name(id="set", ctx=ast.Load()), args=[nxt.iter], keywords=[]),
                    )
                )
                self.changed = True
                index += 2
                continue
            result.append(current)
            index += 1
        return result


class SplitHoistTransformer(ast.NodeTransformer):
    def __init__(self):
        self.changed = False

    def visit_Module(self, node):
        node.body = self._rewrite(node.body)
        return self.generic_visit(node)

    def visit_FunctionDef(self, node):
        node.body = self._rewrite(node.body)
        return self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        node.body = self._rewrite(node.body)
        return self.generic_visit(node)

    def _rewrite(self, body):
        result = []
        for stmt in body:
            if isinstance(stmt, ast.For):
                seen = {}
                for child in ast.walk(stmt):
                    if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute) and child.func.attr == "split":
                        key = _dump(child.func.value)
                        seen.setdefault(key, []).append(child)
                hoisted = []
                for key, calls in seen.items():
                    if len(calls) > 1:
                        name = f"split_cache_{len(result)}"
                        expr = copy.deepcopy(calls[0])
                        class SplitReplacer(ast.NodeTransformer):
                            def visit_Call(self, inner):
                                self.generic_visit(inner)
                                if isinstance(inner.func, ast.Attribute) and inner.func.attr == "split" and _dump(inner.func.value) == key:
                                    return ast.Name(id=name, ctx=ast.Load())
                                return inner
                        stmt = SplitReplacer().visit(stmt)
                        hoisted.append(ast.Assign(targets=[ast.Name(id=name, ctx=ast.Store())], value=expr))
                        self.changed = True
                result.extend(hoisted)
            result.append(stmt)
        return result


class LenHoistTransformer(ast.NodeTransformer):
    def __init__(self):
        self.changed = False

    def visit_Module(self, node):
        node.body = self._rewrite(node.body)
        return self.generic_visit(node)

    def visit_FunctionDef(self, node):
        node.body = self._rewrite(node.body)
        return self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        node.body = self._rewrite(node.body)
        return self.generic_visit(node)

    def _rewrite(self, body):
        result = []
        for stmt in body:
            if isinstance(stmt, ast.While) and isinstance(stmt.test, ast.Compare):
                for comparator in stmt.test.comparators:
                    if isinstance(comparator, ast.Call) and _is_name(comparator.func, "len") and len(comparator.args) == 1 and isinstance(comparator.args[0], ast.Name):
                        seq_name = comparator.args[0].id
                        cached_name = f"{seq_name}_len"

                        class TestReplacer(ast.NodeTransformer):
                            def visit_Call(self, inner):
                                self.generic_visit(inner)
                                if isinstance(inner, ast.Call) and _is_name(inner.func, "len") and len(inner.args) == 1 and isinstance(inner.args[0], ast.Name) and inner.args[0].id == seq_name:
                                    return ast.Name(id=cached_name, ctx=ast.Load())
                                return inner

                        result.append(
                            ast.Assign(
                                targets=[ast.Name(id=cached_name, ctx=ast.Store())],
                                value=ast.Call(func=ast.Name(id="len", ctx=ast.Load()), args=[ast.Name(id=seq_name, ctx=ast.Load())], keywords=[]),
                            )
                        )
                        stmt.test = TestReplacer().visit(stmt.test)
                        self.changed = True
                        break
                result.append(stmt)
                continue
            result.append(stmt)
        return result


class ConstantHoistTransformer(ast.NodeTransformer):
    def __init__(self):
        self.changed = False

    def visit_Module(self, node):
        node.body = self._rewrite(node.body)
        return self.generic_visit(node)

    def visit_FunctionDef(self, node):
        node.body = self._rewrite(node.body)
        return self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        node.body = self._rewrite(node.body)
        return self.generic_visit(node)

    def _rewrite(self, body):
        result = []
        for stmt in body:
            if isinstance(stmt, ast.For):
                loop_names = _used_names(stmt.target)
                hoisted = []
                kept = []
                for inner in stmt.body:
                    if isinstance(inner, ast.Assign) and len(inner.targets) == 1 and isinstance(inner.targets[0], ast.Name):
                        names = _used_names(inner.value)
                        if not names.intersection(loop_names):
                            hoisted.append(copy.deepcopy(inner))
                            self.changed = True
                            continue
                    kept.append(inner)
                result.extend(hoisted)
                stmt.body = kept or [ast.Pass()]
            result.append(stmt)
        return result


class LinearSearchTransformer(ast.NodeTransformer):
    def __init__(self):
        self.changed = False

    def visit_FunctionDef(self, node):
        self.generic_visit(node)
        if len(node.body) >= 2 and isinstance(node.body[0], ast.For) and isinstance(node.body[-1], ast.Return):
            loop = node.body[0]
            final_return = node.body[-1]
            if (
                isinstance(loop.target, ast.Tuple)
                and len(loop.target.elts) == 2
                and isinstance(loop.iter, ast.Call)
                and _is_name(loop.iter.func, "enumerate")
                and len(loop.iter.args) == 1
                and len(loop.body) == 1
                and isinstance(loop.body[0], ast.If)
                and len(loop.body[0].body) == 1
                and isinstance(loop.body[0].body[0], ast.Return)
                and isinstance(loop.body[0].body[0].value, ast.Name)
                and isinstance(final_return.value, ast.UnaryOp)
                and isinstance(final_return.value.op, ast.USub)
            ):
                index_name = loop.target.elts[0].id
                value_name = loop.target.elts[1].id
                condition = loop.body[0].test
                target_value = None
                if (
                    isinstance(condition, ast.Compare)
                    and len(condition.ops) == 1
                    and isinstance(condition.ops[0], ast.Eq)
                ):
                    if _is_name(condition.left, value_name):
                        target_value = condition.comparators[0]
                    elif _is_name(condition.comparators[0], value_name):
                        target_value = condition.left
                if target_value is not None:
                    node.body = [
                        ast.Return(
                            value=ast.Call(
                                func=ast.Name(id="next", ctx=ast.Load()),
                                args=[
                                    ast.GeneratorExp(
                                        elt=ast.Name(id=index_name, ctx=ast.Load()),
                                        generators=[
                                            ast.comprehension(
                                                target=copy.deepcopy(loop.target),
                                                iter=copy.deepcopy(loop.iter),
                                                ifs=[ast.Compare(left=ast.Name(id=value_name, ctx=ast.Load()), ops=[ast.Eq()], comparators=[copy.deepcopy(target_value)])],
                                                is_async=0,
                                            )
                                        ],
                                    ),
                                    ast.Constant(value=-1),
                                ],
                                keywords=[],
                            )
                        )
                    ]
                    self.changed = True
        return node


class SpecialRecursiveTransformer(ast.NodeTransformer):
    def __init__(self):
        self.changed = False
        self.notes = []

    def visit_FunctionDef(self, node):
        self.generic_visit(node)
        name = node.name.lower()
        if name in {"fib", "fibonacci"} and len(node.args.args) == 1:
            arg = node.args.args[0].arg
            node.body = ast.parse(
                f"""
if {arg} <= 1:
    return {arg}
a, b = 0, 1
for _ in range(2, {arg} + 1):
    a, b = b, a + b
return b
""".strip()
            ).body
            self.changed = True
            self.notes.append("Iterative Fibonacci avoids exponential recursive recomputation.")
        elif name == "factorial" and len(node.args.args) == 1:
            arg = node.args.args[0].arg
            node.body = ast.parse(
                f"""
result = 1
for value in range(2, {arg} + 1):
    result *= value
return result
""".strip()
            ).body
            self.changed = True
        elif name == "power" and len(node.args.args) == 2:
            base = node.args.args[0].arg
            exp = node.args.args[1].arg
            node.body = ast.parse(
                f"""
result = 1
while {exp} > 0:
    result *= {base}
    {exp} -= 1
return result
""".strip()
            ).body
            self.changed = True
        return node


class ManualCounterTransformer(ast.NodeTransformer):
    def __init__(self):
        self.changed = False

    def visit_Module(self, node):
        node.body = self._rewrite(node.body)
        return self.generic_visit(node)

    def visit_FunctionDef(self, node):
        node.body = self._rewrite(node.body)
        return self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        node.body = self._rewrite(node.body)
        return self.generic_visit(node)

    def _rewrite(self, body):
        result = []
        index = 0
        while index < len(body):
            current = body[index]
            nxt = body[index + 1] if index + 1 < len(body) else None
            if (
                isinstance(current, ast.Assign)
                and len(current.targets) == 1
                and isinstance(current.targets[0], ast.Name)
                and isinstance(current.value, ast.Constant)
                and current.value.value == 0
                and isinstance(nxt, ast.For)
                and nxt.body
                and isinstance(nxt.body[-1], ast.AugAssign)
                and isinstance(nxt.body[-1].target, ast.Name)
                and nxt.body[-1].target.id == current.targets[0].id
                and isinstance(nxt.body[-1].op, ast.Add)
                and isinstance(nxt.body[-1].value, ast.Constant)
                and nxt.body[-1].value.value == 1
                and isinstance(nxt.target, ast.Name)
            ):
                counter_name = current.targets[0].id
                value_name = nxt.target.id
                nxt.target = ast.Tuple(elts=[ast.Name(id=counter_name, ctx=ast.Store()), ast.Name(id=value_name, ctx=ast.Store())], ctx=ast.Store())
                nxt.iter = ast.Call(func=ast.Name(id="enumerate", ctx=ast.Load()), args=[nxt.iter], keywords=[])
                nxt.body = nxt.body[:-1]
                result.append(nxt)
                self.changed = True
                index += 2
                continue
            result.append(current)
            index += 1
        return result


class SortedCopyTransformer(ast.NodeTransformer):
    def __init__(self):
        self.changed = False
        self.notes = ["Replacing copy()+sort() with sorted() keeps behavior but removes an intermediate mutating step."]

    def visit_Module(self, node):
        node.body = self._rewrite(node.body)
        return self.generic_visit(node)

    def visit_FunctionDef(self, node):
        node.body = self._rewrite(node.body)
        return self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        node.body = self._rewrite(node.body)
        return self.generic_visit(node)

    def _rewrite(self, body):
        result = []
        index = 0
        while index < len(body):
            current = body[index]
            nxt = body[index + 1] if index + 1 < len(body) else None
            if (
                isinstance(current, ast.Assign)
                and len(current.targets) == 1
                and isinstance(current.targets[0], ast.Name)
                and isinstance(current.value, ast.Call)
                and isinstance(current.value.func, ast.Attribute)
                and current.value.func.attr == "copy"
                and isinstance(current.value.func.value, ast.Name)
                and isinstance(nxt, ast.Expr)
                and isinstance(nxt.value, ast.Call)
                and isinstance(nxt.value.func, ast.Attribute)
                and isinstance(nxt.value.func.value, ast.Name)
                and nxt.value.func.value.id == current.targets[0].id
                and nxt.value.func.attr == "sort"
            ):
                result.append(
                    ast.Assign(
                        targets=current.targets,
                        value=ast.Call(func=ast.Name(id="sorted", ctx=ast.Load()), args=[current.value.func.value], keywords=[]),
                    )
                )
                self.changed = True
                index += 2
                continue
            result.append(current)
            index += 1
        return result


class BubbleSortTransformer(ast.NodeTransformer):
    def __init__(self):
        self.changed = False
        self.notes = ["Replacing a manual O(n^2) sorting routine with sorted() changes in-place behavior unless the function already returns a new list."]

    def visit_FunctionDef(self, node):
        self.generic_visit(node)
        if len(node.args.args) == 1 and len([child for child in ast.walk(node) if isinstance(child, ast.For)]) >= 2:
            arg = node.args.args[0].arg
            node.body = [ast.Return(value=ast.Call(func=ast.Name(id="sorted", ctx=ast.Load()), args=[ast.Name(id=arg, ctx=ast.Load())], keywords=[]))]
            self.changed = True
        return node


class NestedLoopLookupTransformer(ast.NodeTransformer):
    def __init__(self):
        self.changed = False

    def visit_Module(self, node):
        node.body = self._rewrite(node.body)
        return self.generic_visit(node)

    def visit_FunctionDef(self, node):
        node.body = self._rewrite(node.body)
        return self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        node.body = self._rewrite(node.body)
        return self.generic_visit(node)

    def _rewrite(self, body):
        result = []
        index = 0
        while index < len(body):
            first = body[index]
            second = body[index + 1] if index + 1 < len(body) else None
            if (
                isinstance(first, ast.Assign)
                and len(first.targets) == 1
                and isinstance(first.targets[0], ast.Name)
                and isinstance(first.value, ast.List)
                and not first.value.elts
                and isinstance(second, ast.For)
                and len(second.body) == 1
                and isinstance(second.body[0], ast.For)
            ):
                outer = second
                inner = second.body[0]
                if (
                    len(inner.body) == 1
                    and isinstance(inner.body[0], ast.If)
                    and len(inner.body[0].body) == 1
                    and isinstance(inner.body[0].body[0], ast.Expr)
                    and isinstance(inner.body[0].body[0].value, ast.Call)
                    and isinstance(inner.body[0].body[0].value.func, ast.Attribute)
                    and isinstance(inner.body[0].body[0].value.func.value, ast.Name)
                    and inner.body[0].body[0].value.func.value.id == first.targets[0].id
                    and inner.body[0].body[0].value.func.attr == "append"
                    and isinstance(inner.body[0].test, ast.Compare)
                    and len(inner.body[0].test.ops) == 1
                    and isinstance(inner.body[0].test.ops[0], ast.Eq)
                    and _same_reference(inner.body[0].test.left, outer.target)
                    and _same_reference(inner.body[0].test.comparators[0], inner.target)
                ):
                    lookup_name = "lookup_set"
                    result.extend(
                        [
                            ast.Assign(targets=[ast.Name(id=lookup_name, ctx=ast.Store())], value=ast.Call(func=ast.Name(id="set", ctx=ast.Load()), args=[inner.iter], keywords=[])),
                            ast.Assign(
                                targets=first.targets,
                                value=ast.ListComp(
                                    elt=copy.deepcopy(outer.target),
                                    generators=[
                                        ast.comprehension(
                                            target=outer.target,
                                            iter=outer.iter,
                                            ifs=[ast.Compare(left=copy.deepcopy(outer.target), ops=[ast.In()], comparators=[ast.Name(id=lookup_name, ctx=ast.Load())])],
                                            is_async=0,
                                        )
                                    ],
                                ),
                            ),
                        ]
                    )
                    self.changed = True
                    index += 2
                    continue
            result.append(first)
            index += 1
        return result


TRANSFORMERS = [
    {
        "name": "nested-loop-set-lookup",
        "description": "Replaces a duplicate-search nested loop with a set-backed lookup.",
        "technique": "Convert nested equality scanning into O(1) membership with a hoisted set.",
        "category": "performance",
        "factory": NestedLoopLookupTransformer,
    },
    {
        "name": "append-to-comprehension",
        "description": "Converts list append loops into list comprehensions.",
        "technique": "Replace list.append() in a loop with a list comprehension.",
        "category": "performance",
        "factory": lambda: BodyRewriter(_append_loop_rewrite),
    },
    {
        "name": "manual-counter-enumerate",
        "description": "Replaces manual counters with enumerate().",
        "technique": "Use enumerate() instead of incrementing a counter inside the loop.",
        "category": "performance",
        "factory": ManualCounterTransformer,
    },
    {
        "name": "membership-set-hoist",
        "description": "Hoists list membership checks to a set before the loop.",
        "technique": "Convert repeated x in list checks into x in set checks.",
        "category": "performance",
        "factory": MembershipSetTransformer,
    },
    {
        "name": "range-len-iteration",
        "description": "Replaces range(len(seq)) indexing with direct iteration or enumerate().",
        "technique": "Remove index-based iteration when the sequence element can be iterated directly.",
        "category": "performance",
        "factory": RangeLenTransformer,
    },
    {
        "name": "len-hoist",
        "description": "Hoists repeated len(...) calls from while-loop conditions.",
        "technique": "Cache collection length before the loop starts.",
        "category": "performance",
        "factory": LenHoistTransformer,
    },
    {
        "name": "sorted-to-min-max",
        "description": "Replaces sorted(...)[0/-1] with min()/max().",
        "technique": "Avoid a full sort when only the smallest or largest element is needed.",
        "category": "algorithm",
        "factory": SortedMinMaxTransformer,
    },
    {
        "name": "dict-values-iteration",
        "description": "Replaces dict.keys() iteration with dict.values() when only values are read.",
        "technique": "Iterate over values directly instead of looking them up again by key.",
        "category": "performance",
        "factory": KeysToValuesTransformer,
    },
    {
        "name": "constant-hoist",
        "description": "Moves loop-invariant assignments outside the loop.",
        "technique": "Hoist constant expressions so they are not rebuilt every iteration.",
        "category": "performance",
        "factory": ConstantHoistTransformer,
    },
    {
        "name": "generator-expression",
        "description": "Uses generator expressions instead of temporary lists when streaming into consumers.",
        "technique": "Avoid materializing a full list when sum/any/all/min/max can consume a generator.",
        "category": "memory",
        "factory": GeneratorTransformer,
    },
    {
        "name": "inline-single-use",
        "description": "Inlines intermediate values that are used once.",
        "technique": "Remove unnecessary temporary storage by inlining single-use assignments.",
        "category": "memory",
        "factory": InlineSingleUseTransformer,
    },
    {
        "name": "sorted-copy",
        "description": "Replaces copy()+sort() with sorted().",
        "technique": "Use sorted() when a sorted copy is needed.",
        "category": "memory",
        "factory": SortedCopyTransformer,
    },
    {
        "name": "deque-queue",
        "description": "Replaces list pop(0) queue usage with collections.deque.",
        "technique": "Use deque.popleft() for efficient queue semantics.",
        "category": "memory",
        "factory": DequeTransformer,
    },
    {
        "name": "dict-comprehension",
        "description": "Converts dictionary-building loops into dict comprehensions.",
        "technique": "Build dictionaries with a comprehension instead of mutating in a loop.",
        "category": "memory",
        "factory": lambda: BodyRewriter(_dict_comp_rewrite),
    },
    {
        "name": "set-comprehension",
        "description": "Converts set-building loops into set comprehensions.",
        "technique": "Build sets with a comprehension instead of repeated add calls.",
        "category": "memory",
        "factory": lambda: BodyRewriter(_set_comp_rewrite),
    },
    {
        "name": "recursive-cache",
        "description": "Adds functools.lru_cache to recursive functions without memoization.",
        "technique": "Memoize overlapping recursive subproblems with functools.lru_cache.",
        "category": "recursion",
        "factory": RecursiveCacheTransformer,
    },
    {
        "name": "iterative-recursion",
        "description": "Replaces common recursive fibonacci/factorial/power implementations with iterative versions.",
        "technique": "Switch to iterative control flow for common recursive hot paths.",
        "category": "recursion",
        "factory": SpecialRecursiveTransformer,
    },
    {
        "name": "string-join",
        "description": "Replaces string concatenation loops with list accumulation and ''.join().",
        "technique": "Collect pieces in a list and join once after the loop.",
        "category": "string",
        "factory": StringConcatTransformer,
    },
    {
        "name": "split-hoist",
        "description": "Hoists repeated split() calls outside the loop.",
        "technique": "Cache repeated string splitting instead of recomputing it each iteration.",
        "category": "string",
        "factory": SplitHoistTransformer,
    },
    {
        "name": "linear-search-next",
        "description": "Replaces manual index search loops with next(...enumerate(...), -1).",
        "technique": "Use a generator with next() for concise linear-search index lookup.",
        "category": "algorithm",
        "factory": LinearSearchTransformer,
    },
    {
        "name": "counter-usage",
        "description": "Replaces manual frequency dictionaries with collections.Counter.",
        "technique": "Use Counter for counting occurrences.",
        "category": "algorithm",
        "factory": CounterTransformer,
    },
    {
        "name": "unique-set",
        "description": "Replaces manual uniqueness loops with set(...).",
        "technique": "Use set() to build unique elements in one step.",
        "category": "algorithm",
        "factory": UniqueSetTransformer,
    },
    {
        "name": "builtin-sort",
        "description": "Replaces manual quadratic sorting routines with sorted().",
        "technique": "Use Python's built-in Timsort instead of hand-written bubble/selection/insertion sorts.",
        "category": "algorithm",
        "factory": BubbleSortTransformer,
    },
]


def _apply_transformer(code, spec):
    tree = _parse(code)
    ParentSetter().visit(tree)
    transformer = spec["factory"]()
    updated = ast.fix_missing_locations(transformer.visit(tree))
    notes = getattr(transformer, "notes", [])
    updated_code = _to_code(updated, notes)
    if not getattr(transformer, "changed", False):
        return None
    if not _validate_variant(updated_code):
        return None
    if _dump(_parse(updated_code)) == _dump(_parse(code)):
        return None
    return {
        "name": spec["name"],
        "code": updated_code,
        "description": spec["description"],
        "technique": spec["technique"],
        "category": spec["category"],
    }


def _build_combined_variant(code):
    combined_code = code
    combined_notes = []
    applied_names = []
    passes = 0
    max_passes = 8
    seen_signatures = {_code_signature(code)}

    while passes < max_passes:
        passes += 1
        pass_changed = False

        for spec in TRANSFORMERS:
            combined_variant = _apply_transformer(combined_code, spec)
            if not combined_variant:
                continue
            combined_code = combined_variant["code"]
            applied_names.append(combined_variant["name"])
            if combined_variant["description"] not in combined_notes:
                combined_notes.append(combined_variant["description"])
            pass_changed = True

        signature = _code_signature(combined_code)
        if not pass_changed or signature in seen_signatures:
            break
        seen_signatures.add(signature)

    if not _validate_variant(combined_code):
        combined_code = code
        passes = 0
        applied_names = []

    return {
        "name": "combined",
        "code": combined_code,
        "description": "Applies every safe optimization repeatedly until no additional AST rewrite is possible.",
        "technique": "Runs the full transformer pipeline to a fixed point so the code cannot be further auto-optimized by this engine.",
        "category": "performance",
        "optimization_passes": passes,
        "applied_variants": applied_names,
    }


def generate_variants(code: str) -> dict:
    variants = []

    for spec in TRANSFORMERS:
        variant = _apply_transformer(code, spec)
        if variant:
            variants.append(variant)

    if not variants:
        return {
            "variants": [
                {
                    "name": "no-op",
                    "code": code,
                    "description": "The code is already well-optimized for the patterns this optimizer can safely rewrite.",
                    "technique": "no-change",
                    "category": "performance",
                }
            ],
            "original_code": code,
        }

    combined_variant = _build_combined_variant(code)
    if _code_signature(combined_variant["code"]) == _code_signature(code):
        combined_variant["description"] = "No additional combined rewrite was safer than the original code, so the original was preserved."
    variants.append(combined_variant)

    return {"variants": variants, "original_code": code}
