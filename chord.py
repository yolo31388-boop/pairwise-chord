"""Chord DHT（分布式哈希表）骨架（确定性单机模拟版）。

id 空间：0 .. 2^m - 1（测试 m=6）
环路由：find_successor(key) 沿 finger 表跳转，返回负责节点 id
数据：put/get 路由到负责节点存取

公开 API：
  ChordNode(node_id, m=6)
  join(existing=None)            加入环（existing 为空则自成环）
  find_successor(key) -> node_id
  put(key, value)                存到负责节点
  get(key) -> value | None
  leave()                        离开：数据迁移给后继，摘链
  stabilize()                    修复 predecessor/successor 关系
  fix_fingers()                  重建 finger 表
  successor / predecessor / finger / keys  结构可测
"""
from __future__ import annotations


class ChordNode:
    _nodes: dict = {}

    def __init__(self, node_id: int, m: int = 6):
        self.m = m
        self._mod = 1 << m
        if not 0 <= node_id < self._mod:
            raise ValueError(f"node_id {node_id} out of range [0, {self._mod})")
        self.node_id = node_id
        self.successor = node_id
        self.predecessor = node_id
        self.finger = [node_id] * m
        self.keys: dict = {}

    def join(self, existing=None) -> None:
        type(self)._nodes[self.node_id] = self
        if existing is None:
            self.successor = self.node_id
            self.predecessor = self.node_id
            self.finger = [self.node_id] * self.m
            return
        succ = type(self)._nodes[existing.find_successor(self.node_id)]
        pred = type(self)._nodes[succ.predecessor]
        self.successor = succ.node_id
        self.predecessor = pred.node_id
        pred.successor = self.node_id
        succ.predecessor = self.node_id
        # 迁移现在归自己负责的键（区间 (pred, self]）
        for key in list(succ.keys):
            if self._between(key, pred.node_id, self.node_id, True, True):
                self.keys[key] = succ.keys.pop(key)
        self._refresh_all_fingers()

    def find_successor(self, key: int) -> int:
        key %= self._mod
        node = self
        for _ in range(len(type(self)._nodes) + 1):
            if key == node.node_id:
                return node.node_id
            if self._between(key, node.node_id, node.successor, False, True):
                return node.successor
            nxt = node._closest_preceding(key)
            if nxt == node.node_id:
                return node.successor
            node = type(self)._nodes[nxt]
        return node.successor

    def put(self, key: int, value) -> None:
        owner = type(self)._nodes[self.find_successor(key)]
        owner.keys[key] = value

    def get(self, key: int):
        owner = type(self)._nodes[self.find_successor(key)]
        return owner.keys.get(key)

    def leave(self) -> None:
        nodes = type(self)._nodes
        if self.successor != self.node_id:
            succ = nodes[self.successor]
            pred = nodes[self.predecessor]
            succ.keys.update(self.keys)
            succ.predecessor = pred.node_id
            pred.successor = succ.node_id
        self.keys.clear()
        nodes.pop(self.node_id, None)
        self.successor = self.node_id
        self.predecessor = self.node_id
        self.finger = [self.node_id] * self.m
        if nodes:
            self._refresh_all_fingers()

    def stabilize(self) -> None:
        nodes = type(self)._nodes
        succ = nodes[self.successor]
        x = succ.predecessor
        if x in nodes and self._between(x, self.node_id, succ.node_id, False, False):
            self.successor = x
            succ = nodes[x]
        # notify(successor)
        if succ is self or self._between(
            self.node_id, succ.predecessor, succ.node_id, False, False
        ):
            succ.predecessor = self.node_id

    def fix_fingers(self) -> None:
        for k in range(self.m):
            start = (self.node_id + (1 << k)) % self._mod
            self.finger[k] = self.find_successor(start)

    # -------------------------------------------------------- 内部工具
    def _closest_preceding(self, key: int) -> int:
        for k in range(self.m - 1, -1, -1):
            f = self.finger[k]
            if f in type(self)._nodes and self._between(
                f, self.node_id, key, False, False
            ):
                return f
        return self.node_id

    def _between(self, x: int, lo: int, hi: int, lo_closed: bool, hi_closed: bool) -> bool:
        """环上判断 x 是否落在 (lo, hi) 区间（端点含/不含由参数控制）。"""
        if lo == hi:
            return (x == lo) and (lo_closed or hi_closed)
        if lo < hi:
            inside = lo <= x <= hi
        else:  # 绕回
            inside = x >= lo or x <= hi
        if not inside:
            return False
        if not lo_closed and x == lo:
            return False
        if not hi_closed and x == hi:
            return False
        return True

    def _refresh_all_fingers(self) -> None:
        for node in list(type(self)._nodes.values()):
            node.fix_fingers()
