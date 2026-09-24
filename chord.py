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
        raise NotImplementedError

    def join(self, existing=None) -> None:
        raise NotImplementedError

    def find_successor(self, key: int) -> int:
        raise NotImplementedError

    def put(self, key: int, value) -> None:
        raise NotImplementedError

    def get(self, key: int):
        raise NotImplementedError

    def leave(self) -> None:
        raise NotImplementedError

    def stabilize(self) -> None:
        raise NotImplementedError

    def fix_fingers(self) -> None:
        raise NotImplementedError
