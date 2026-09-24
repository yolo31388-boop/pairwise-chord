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
        if not isinstance(m, int) or m <= 0:
            raise ValueError("m must be a positive integer")
        self.m = m
        size = 1 << m
        if not isinstance(node_id, int) or not (0 <= node_id < size):
            raise ValueError(f"node_id must be in 0..{size - 1}")
        if node_id in type(self)._nodes:
            raise ValueError(f"node {node_id} already exists")
        self.node_id = node_id
        self._size = size
        self.successor = node_id
        self.predecessor = node_id
        self.finger = [node_id] * m
        self.keys: dict = {}
        type(self)._nodes[node_id] = self

    # ---------------------------------------------------------- 区间工具
    def _norm(self, key: int) -> int:
        return key % self._size

    @staticmethod
    def _in_open_right(x: int, lo: int, hi: int) -> bool:
        """x 是否属于环上的左开右闭区间 (lo, hi]。"""
        if lo == hi:
            return True
        if lo < hi:
            return lo < x <= hi
        return x > lo or x <= hi

    @staticmethod
    def _in_open(x: int, lo: int, hi: int) -> bool:
        """x 是否属于环上的开区间 (lo, hi)。"""
        if lo == hi:
            return False
        if lo < hi:
            return lo < x < hi
        return x > lo or x < hi

    def _closest_preceding_node(self, key: int):
        """finger 表中落在 (self.id, key) 开区间内、距 key 最近的节点。"""
        nodes = type(self)._nodes
        for k in range(self.m - 1, -1, -1):
            fid = self.finger[k]
            if fid in nodes and fid != self.node_id and self._in_open(
                fid, self.node_id, key
            ):
                return fid
        return None

    def join(self, existing=None) -> None:
        nodes = type(self)._nodes
        if existing is None:
            # 空引导节点：自成环
            self.successor = self.node_id
            self.predecessor = self.node_id
            self.finger = [self.node_id] * self.m
            return
        succ_id = existing.find_successor(self.node_id)
        succ_node = nodes[succ_id]
        pred_id = succ_node.predecessor
        pred_node = nodes[pred_id]
        self.predecessor = pred_id
        self.successor = succ_id
        pred_node.successor = self.node_id
        succ_node.predecessor = self.node_id
        # successor 交出现在归本节点负责的键：(pred_id, self.id]
        for key in list(succ_node.keys):
            if self._in_open_right(key, pred_id, self.node_id):
                self.keys[key] = succ_node.keys.pop(key)
        for node in list(nodes.values()):
            node.fix_fingers()

    def find_successor(self, key: int) -> int:
        key = self._norm(key)
        nodes = type(self)._nodes
        cur = self
        for _ in range(len(nodes) + 1):
            if key == cur.node_id:
                return cur.node_id
            if cur.successor == cur.node_id or self._in_open_right(
                key, cur.node_id, cur.successor
            ):
                return cur.successor
            hop = cur._closest_preceding_node(key)
            if hop is None:
                hop = cur.successor  # finger 不足时沿 successor 链推进
            cur = nodes[hop]
        return cur.successor

    def put(self, key: int, value) -> None:
        key = self._norm(key)
        owner = type(self)._nodes[self.find_successor(key)]
        owner.keys[key] = value

    def get(self, key: int):
        key = self._norm(key)
        owner = type(self)._nodes[self.find_successor(key)]
        return owner.keys.get(key)

    def leave(self) -> None:
        nodes = type(self)._nodes
        succ_node = nodes[self.successor]
        pred_node = nodes[self.predecessor]
        if succ_node is self:
            # 环上只剩自己
            del nodes[self.node_id]
            return
        succ_node.keys.update(self.keys)
        self.keys.clear()
        pred_node.successor = self.successor
        succ_node.predecessor = self.predecessor
        del nodes[self.node_id]
        for node in list(nodes.values()):
            node.fix_fingers()

    def stabilize(self) -> None:
        nodes = type(self)._nodes
        succ_node = nodes[self.successor]
        candidate = succ_node.predecessor
        changed = False
        if candidate is not None and candidate != self.node_id:
            # successor == self 时本节点是单节点环，任何别的候选都在中间
            if self.successor == self.node_id or self._in_open(
                candidate, self.node_id, self.successor
            ):
                self.successor = candidate
                changed = True
        succ_node = nodes[self.successor]
        old_pred = succ_node.predecessor
        if (
            old_pred is None
            or (old_pred == succ_node.node_id
                and self.node_id != succ_node.node_id)
            or self._in_open(self.node_id, old_pred, succ_node.node_id)
        ):
            succ_node.predecessor = self.node_id
            changed = True
        if changed:
            self.fix_fingers()

    def fix_fingers(self) -> None:
        for k in range(self.m):
            start = (self.node_id + (1 << k)) % self._size
            self.finger[k] = self.find_successor(start)
