import subprocess
import sys
import textwrap
import unittest

ROOT = __file__.replace("\\tests\\test_runtime.py", "")


def _run_script(script: str) -> subprocess.CompletedProcess:
    headless_setup = """
    from panda3d.core import loadPrcFileData
    loadPrcFileData("", "window-type none")
    """
    return subprocess.run(
        [sys.executable, "-c", textwrap.dedent(headless_setup) + "\n" + textwrap.dedent(script)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )


class RuntimeSmokeTest(unittest.TestCase):
    def test_main_imports_without_starting_the_loop(self):
        result = _run_script(
            """
            import main
            assert main.game.state.name == "MENU"
            print("ok")
            """
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ok", result.stdout)

    def test_main_transitions_through_start_and_menu(self):
        result = _run_script(
            """
            import main
            main.start_game("creative")
            assert main.game.state.name == "PLAYING"
            main.quit_to_menu()
            assert main.game.state.name == "MENU"
            print("ok")
            """
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ok", result.stdout)

    def test_real_textures_build_a_chunk_mesh(self):
        result = _run_script(
            """
            from ursina import Ursina
            app = Ursina()
            import game.blocks as blocks
            import game.textures as textures
            from game.core import world

            textures.load_all_textures()
            blocks.load_all_blocks()
            world.create_world(size=4, max_height=3, seed=7, render_distance=0)
            assert world.get_loaded_chunks() == {(0, 0)}
            assert world.world_parent.children
            print("ok")
            """
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ok", result.stdout)


class MissingAssetTest(unittest.TestCase):
    def test_missing_sound_is_reported_as_unavailable(self):
        result = _run_script(
            """
            from game.sounds import load_sound
            assert load_sound("missing-test.ogg") is None
            print("ok")
            """
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("arquivo não encontrado", result.stdout)
