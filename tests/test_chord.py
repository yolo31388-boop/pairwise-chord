"""Chord DHT 验收测试：环结构/finger/路由/put-get/离开迁移。"""
import pytest

from chord import ChordNode


def fresh():
    ChordNode._nodes.clear()


def ring_ids(node):
    """从 node 出发绕环一圈收集的节点 id（升序）。"""
    out = []
    cur = node
    for _ in range(len(ChordNode._nodes) + 1):
        out.append(cur.node_id)
        cur = ChordNode._nodes[cur.successor]
        if cur is node:
            break
    return out


def brute_successor(ids, key):
    """暴力：环上第一个 id >= key 的节点（绕回）。"""
    ids = sorted(ids)
    for i in ids:
        if i >= key:
            return i
    return ids[0]


# ------------------------------------------------------------ 单节点
def test_single_node_ring():
    fresh()
    n = ChordNode(10)
    n.join()
    assert n.successor == 10
    assert n.predecessor == 10
    assert n.find_successor(30) == 10
    assert n.find_successor(10) == 10


# ------------------------------------------------------------ 加入与环结构
def test_join_forms_ordered_ring():
    fresh()
    ids = [10, 20, 5, 40, 25]
    first = None
    for i in ids:
        n = ChordNode(i)
        n.join(first)
        first = n
    ring = ring_ids(ChordNode._nodes[5])
    assert ring == sorted(ids)


def test_successor_of_each_node():
    fresh()
    ids = [10, 20, 5, 40, 25]
    first = None
    for i in ids:
        n = ChordNode(i)
        n.join(first)
        first = n
    sorted_ids = sorted(ids)
    for pos, i in enumerate(sorted_ids):
        nxt = sorted_ids[(pos + 1) % len(sorted_ids)]
        assert ChordNode._nodes[i].successor == nxt


# ------------------------------------------------------------ 路由正确性
def test_find_successor_all_keys():
    fresh()
    ids = [10, 20, 5, 40, 25, 61, 2]
    first = None
    for i in ids:
        n = ChordNode(i)
        n.join(first)
        first = n
    for key in range(64):
        got = ChordNode._nodes[10].find_successor(key)
        assert got == brute_successor(ids, key), f"key={key}"


def test_find_successor_from_any_node():
    fresh()
    ids = [10, 20, 5, 40, 25]
    first = None
    for i in ids:
        n = ChordNode(i)
        n.join(first)
        first = n
    for start_id in ids:
        for key in range(64):
            assert ChordNode._nodes[start_id].find_successor(key) == \
                brute_successor(ids, key)


def test_finger_table():
    fresh()
    m = 6
    ids = [10, 20, 5, 40]
    first = None
    for i in ids:
        n = ChordNode(i)
        n.join(first)
        first = n
    n = ChordNode._nodes[10]
    for k in range(m):
        start = (10 + 2 ** k) % (2 ** m)
        assert n.finger[k] == brute_successor(ids, start), f"finger[{k}]"


# ------------------------------------------------------------ 数据存取
def test_put_get_routes_to_owner():
    fresh()
    ids = [10, 20, 5, 40, 25]
    first = None
    for i in ids:
        n = ChordNode(i)
        n.join(first)
        first = n
    for key in range(64):
        ChordNode._nodes[10].put(key, f"v{key}")
    for start_id in ids:
        for key in range(64):
            assert ChordNode._nodes[start_id].get(key) == f"v{key}"


def test_put_returns_none_for_missing():
    fresh()
    n = ChordNode(10)
    n.join()
    assert n.get(42) is None


# ------------------------------------------------------------ 离开与数据迁移
def test_leave_migrates_data():
    fresh()
    ids = [10, 20, 5, 40, 25]
    first = None
    for i in ids:
        n = ChordNode(i)
        n.join(first)
        first = n
    for key in range(64):
        ChordNode._nodes[10].put(key, key * 2)
    leaver = ChordNode._nodes[25]
    leaver.leave()
    assert 25 not in ChordNode._nodes
    # 数据仍可通过任意剩余节点读到
    for key in range(64):
        assert ChordNode._nodes[10].get(key) == key * 2


def test_leave_updates_ring():
    fresh()
    ids = [10, 20, 5, 40, 25]
    first = None
    for i in ids:
        n = ChordNode(i)
        n.join(first)
        first = n
    ChordNode._nodes[20].leave()
    assert 20 not in ChordNode._nodes
    ring = ring_ids(ChordNode._nodes[5])
    assert ring == [5, 10, 25, 40]


def test_leave_until_single():
    fresh()
    ids = [10, 20, 5]
    first = None
    for i in ids:
        n = ChordNode(i)
        n.join(first)
        first = n
    for key in range(64):
        ChordNode._nodes[5].put(key, key)
    ChordNode._nodes[10].leave()
    ChordNode._nodes[20].leave()
    assert list(ChordNode._nodes) == [5]
    n = ChordNode._nodes[5]
    assert n.successor == 5 and n.predecessor == 5
    for key in range(64):
        assert n.get(key) == key
