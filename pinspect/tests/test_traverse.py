import unittest
import pinspect
from pinspect import to_string, to_pyvis

from pinspect.utils import check_edge


class Spell:
    pass


class Wizard:
    def __init__(self, name, capacity=10):
        self.name = name
        self.points = capacity
        self.hidden_spells = [Spell(), Spell()]

    def cast_spell(self):
        spell = Spell()
        self.points -= 1
        return spell

    def die(self):
        raise ValueError("A wizard never dies!")


class MagicWorld:
    def __init__(self):
        self.wizards = [Wizard("Harry"), Wizard("Voldemort")]
        self.wizards_dict = dict(wiz1=Wizard("Unknown"))


class TestTraverse(unittest.TestCase):

    def setUp(self):
        self.world = MagicWorld()

    def test_find(self):
        graph = pinspect.find(self.world, key='spell', verbose=True, visualize=False)
        self.assertEqual(len(graph), 4)

    def test_to_string(self):
        graph = pinspect.find(self.world, key='spell', verbose=False, visualize=False)
        matches = list(to_string(graph, source=id(self.world), prefix=self.world.__class__.__name__))
        expected_matches = [
            "MagicWorld.wizards[0].hidden_spells[0] -> 'Spell'",
            "MagicWorld.wizards[0].cast_spell() -> 'Spell'",
        ]
        self.assertEqual(matches, expected_matches)

    def test_to_pyvis(self):
        graph = pinspect.find(self.world, key='spell', verbose=False, visualize=False)
        net = to_pyvis(graph)
        self.assertEqual(len(net.node_ids), len(graph))
        self.assertEqual(sorted(net.node_ids), sorted(graph.nodes))

    def test_check_edge(self):
        graph = pinspect.find(self.world, key='spell', verbose=False, visualize=False)
        self.assertEqual(check_edge(graph, edge_label='spell'), 2)
        self.assertEqual(check_edge(graph, edge_label='wizards'), 1)


if __name__ == '__main__':
    unittest.main()
