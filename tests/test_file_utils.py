"""
Unit tests for domain/file_utils.py safe trashing and OS Recycle Bin functionality.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from domain.file_utils import send_to_trash


def test_send_to_trash_non_existent(tmp_path):
    assert send_to_trash(tmp_path / "non_existent.jpg") is False


def test_send_to_trash_send2trash_success(tmp_path):
    f = tmp_path / "test_file.jpg"
    f.write_text("dummy content")

    with patch("send2trash.send2trash") as mock_s2t:
        # Simulate send2trash deleting the file
        def side_effect(p):
            Path(p).unlink()

        mock_s2t.side_effect = side_effect
        assert send_to_trash(f) is True
        assert not f.exists()
        mock_s2t.assert_called_once_with(str(f.resolve()))


def test_send_to_trash_linux_gio_fallback(tmp_path):
    f = tmp_path / "test_gio.jpg"
    f.write_text("dummy content")

    with patch("send2trash.send2trash", side_effect=Exception("s2t failed")):
        with patch("sys.platform", "linux"):
            with patch("shutil.which", return_value="/usr/bin/gio"):
                with patch("subprocess.run") as mock_run:
                    def side_effect(*args, **kwargs):
                        f.unlink()
                        return MagicMock(returncode=0, stderr="")

                    mock_run.side_effect = side_effect
                    assert send_to_trash(f) is True
                    assert not f.exists()


def test_send_to_trash_macos_applescript_fallback(tmp_path):
    f = tmp_path / "test_mac.jpg"
    f.write_text("dummy content")

    with patch("send2trash.send2trash", side_effect=Exception("s2t failed")):
        with patch("sys.platform", "darwin"):
            with patch("subprocess.run") as mock_run:
                def side_effect(*args, **kwargs):
                    f.unlink()
                    return MagicMock(returncode=0, stderr="")

                mock_run.side_effect = side_effect
                assert send_to_trash(f) is True
                assert not f.exists()


def test_send_to_trash_windows_win32_shell(tmp_path):
    f = tmp_path / "test_win32.jpg"
    f.write_text("dummy content")

    with patch("send2trash.send2trash", side_effect=Exception("s2t failed")):
        with patch("sys.platform", "win32"):
            with patch("domain.file_utils._win32_recycle_bin", return_value=True) as mock_win32:
                # Simulate file unlinked/recycled
                f.unlink()
                assert send_to_trash(f) is False  # Because file was already unlinked before check

    # Now test normal successful win32 deletion
    f2 = tmp_path / "test_win32_2.jpg"
    f2.write_text("dummy content 2")
    with patch("send2trash.send2trash", side_effect=Exception("s2t failed")):
        with patch("sys.platform", "win32"):
            with patch("domain.file_utils._win32_recycle_bin") as mock_win32:
                def side_effect(p):
                    f2.unlink()
                    return True

                mock_win32.side_effect = side_effect
                assert send_to_trash(f2) is True
                assert not f2.exists()


def test_send_to_trash_windows_powershell_fallback(tmp_path):
    f = tmp_path / "test_win.jpg"
    f.write_text("dummy content")

    with patch("send2trash.send2trash", side_effect=Exception("s2t failed")):
        with patch("sys.platform", "win32"):
            with patch("domain.file_utils._win32_recycle_bin", return_value=False):
                with patch("subprocess.run") as mock_run:
                    def side_effect(*args, **kwargs):
                        f.unlink()
                        return MagicMock(returncode=0, stderr="")

                    mock_run.side_effect = side_effect
                    assert send_to_trash(f) is True
                    assert not f.exists()


def test_send_to_trash_all_fail(tmp_path):
    f = tmp_path / "test_fail.jpg"
    f.write_text("dummy content")

    with patch("send2trash.send2trash", side_effect=Exception("s2t failed")):
        with patch("shutil.which", return_value=None):
            with patch("domain.file_utils._win32_recycle_bin", return_value=False):
                with patch("subprocess.run", return_value=MagicMock(returncode=1, stderr="failed")):
                    assert send_to_trash(f) is False
                    assert f.exists()

