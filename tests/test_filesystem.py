import stat
from pathlib import Path

from lab.filesystem import remove_tree


def test_remove_tree_cleans_nested_read_only_paths(tmp_path):
    generated = tmp_path / "scenarios" / "g3" / "remote-admin" / ".git" / "hooks"
    generated.mkdir(parents=True)
    readonly_hook = generated / "sample-hook"
    readonly_hook.write_text("sample hook", encoding="utf-8")
    readonly_hook.chmod(stat.S_IREAD)

    remove_tree(tmp_path / "scenarios")

    assert not (tmp_path / "scenarios").exists()


def test_remove_tree_ignores_missing_directory(tmp_path):
    remove_tree(tmp_path / "does-not-exist")
