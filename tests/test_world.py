import unittest
from collections import defaultdict
from pathlib import Path
from tempfile import TemporaryDirectory

import game.textures as textures
from game import blocks
from game.core import world
from game.core.world import CHUNK_SIZE, WORLD_BOTTOM, chunks_to_rebuild, is_exposed


class WorldGenerationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        textures.blocks = defaultdict(lambda: None)
        blocks.BLOCKS.clear()
        blocks.load_all_blocks()

    def tearDown(self):
        world.clear_world()

    def test_seed_and_max_height_are_applied(self):
        world.create_world(size=8, max_height=2, seed=123, render_distance=0)
        first = dict(world.placed_blocks)
        self.assertEqual(world.get_world_seed(), 123)
        self.assertLessEqual(world.get_top_y(0, 0), 2)

        world.create_world(size=8, max_height=2, seed=123, render_distance=0)
        self.assertEqual(first, world.placed_blocks)

    def test_chunks_are_loaded_on_demand(self):
        world.create_world(size=32, max_height=4, seed=123, render_distance=0)
        self.assertEqual(world.get_loaded_chunks(), {(0, 0)})
        initial_count = len(world.placed_blocks)

        world.stream_world((20, 0, 0), render_distance=0)

        self.assertEqual(world.get_loaded_chunks(), {(1, 0)})
        self.assertLess(len(world.placed_blocks), initial_count * 2)

    def test_persistence_restores_seed_and_changes(self):
        world.create_world(size=8, max_height=4, seed=123, render_distance=0)
        self.assertTrue(world.place_block((0, 10, 0), "stone"))

        with TemporaryDirectory() as directory:
            path = Path(directory) / "world.json"
            world.save_world(path)
            world.clear_world()
            world.load_world(path)

        self.assertEqual(world.get_world_seed(), 123)
        self.assertEqual(world.get_block_at((0, 10, 0)), "stone")

def _solid_cube(size: int) -> dict:
    """Cubo maciço de blocos de pedra começando na camada mais baixa."""
    return {
        (x, y, z): "stone"
        for x in range(size)
        for y in range(WORLD_BOTTOM, WORLD_BOTTOM + size)
        for z in range(size)
    }

class IsExposedTest(unittest.TestCase):
    def test_buried_block_is_not_exposed(self):
        blocks = _solid_cube(3)
        self.assertFalse(is_exposed((1, WORLD_BOTTOM + 1, 1), blocks))

    def test_surface_block_is_exposed(self):
        blocks = _solid_cube(3)
        self.assertTrue(is_exposed((1, WORLD_BOTTOM + 2, 1), blocks))

    def test_world_floor_does_not_count_as_exposed(self):
        blocks = _solid_cube(3)
        self.assertFalse(is_exposed((1, WORLD_BOTTOM, 1), blocks))

    def test_digging_exposes_blocks_deep_underground(self):
        blocks = _solid_cube(5)
        deep = (2, WORLD_BOTTOM + 1, 2)
        self.assertFalse(is_exposed(deep, blocks))
        del blocks[(2, WORLD_BOTTOM + 2, 2)]
        self.assertTrue(is_exposed(deep, blocks))

class ChunksToRebuildTest(unittest.TestCase):
    def test_middle_of_chunk_rebuilds_only_its_chunk(self):
        self.assertEqual(chunks_to_rebuild((5, 0, 5)), {(0, 0)})

    def test_border_rebuilds_neighbor(self):
        self.assertEqual(chunks_to_rebuild((0, 0, 5)), {(0, 0), (-1, 0)})
        self.assertEqual(chunks_to_rebuild((CHUNK_SIZE - 1, 0, 5)), {(0, 0), (1, 0)})

    def test_corner_rebuilds_both_neighbors(self):
        self.assertEqual(chunks_to_rebuild((0, 0, 0)), {(0, 0), (-1, 0), (0, -1)})

    def test_negative_coordinates(self):
        self.assertEqual(chunks_to_rebuild((-1, 3, -5)), {(-1, -1), (0, -1)})

if __name__ == "__main__":
    unittest.main()