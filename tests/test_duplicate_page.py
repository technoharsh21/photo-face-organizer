import sys

from PySide6.QtWidgets import QApplication, QLabel, QMessageBox

from config import Config
from services.duplicate_service import DuplicateService
from ui.pages.duplicate_page import DuplicateFileCard, DuplicatePage, DuplicateScanWorker


def test_duplicate_page_counts_actual_copies_and_savings(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication(sys.argv)
    page = DuplicatePage(DuplicateService(Config(app_data_dir=tmp_path / "data")))
    files = [
        {"path": str(tmp_path / name), "filename": name, "size": size,
         "formatted_size": str(size), "formatted_mtime": "today", "scan_hash": "hash",
         "is_recommended_keep": keep, "is_selected_for_removal": not keep}
        for name, size, keep in (("keep.jpg", 100, True), ("small.jpg", 10, False), ("large.jpg", 30, False))
    ]
    page.duplicate_sets = [{"set_id": "set_1", "sample_name": "keep.jpg", "files": files}]
    page.refresh()

    assert page.lbl_sum_files.text().endswith("2")
    assert page.lbl_sum_savings.text().endswith("40 B")
    assert page.files_layout.itemAt(0).widget().btn_del_single.isEnabled() is False
    assert isinstance(page.files_layout.itemAt(1).widget(), DuplicateFileCard)

    errors = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: errors.append(args[-1]))
    page._on_scan_error("permission denied")
    assert "permission denied" in errors[0]
    assert len(page.duplicate_sets) == 1
    assert page.btn_scan.isEnabled()
    page.close()


def test_scan_worker_reports_failure_instead_of_empty_result(tmp_path):
    class BrokenService:
        def scan_directories_for_duplicates(self, **kwargs):
            raise RuntimeError("disk unavailable")

    worker = DuplicateScanWorker(BrokenService(), [str(tmp_path)], True)
    errors, results = [], []
    worker.error_signal.connect(errors.append)
    worker.finished_signal.connect(results.append)
    worker.run()
    assert errors == ["disk unavailable"]
    assert results == []


def test_ignore_group_moves_to_next_and_excludes_files_from_cleanup(tmp_path):
    app = QApplication.instance() or QApplication(sys.argv)
    service = DuplicateService(Config(app_data_dir=tmp_path / "data"))
    for name, content in (("a.jpg", b"pair one"), ("a-copy.jpg", b"pair one"),
                          ("b.jpg", b"pair two"), ("b-copy.jpg", b"pair two")):
        (tmp_path / name).write_bytes(content)
    groups = service.scan_directories_for_duplicates([tmp_path], method="exact")
    assert len(groups) == 2

    page = DuplicatePage(service)
    page._on_scan_finished(groups)
    ignored = page.duplicate_sets[0]
    ignored_paths = {f["path"] for f in ignored["files"]}
    remaining_id = page.duplicate_sets[1]["set_id"]
    page.txt_filter_sets.setText(ignored["sample_name"])
    page.btn_ignore.click()

    assert page.current_set_id == remaining_id
    assert page.txt_filter_sets.text() == ""
    assert len(page.duplicate_sets) == 1
    assert not ignored_paths.intersection(page._get_all_files_selected_for_removal())
    assert all((tmp_path / name).exists() for name in ("a.jpg", "a-copy.jpg", "b.jpg", "b-copy.jpg"))

    page.btn_ignore.click()
    assert page.duplicate_sets == []
    assert not page.btn_ignore.isEnabled()
    assert page._ignored_group_count == 2
    empty_labels = page.files_layout.itemAt(0).widget().findChildren(QLabel)
    assert any("Ignored groups" in label.text() for label in empty_labels)

    page._on_scan_finished(service.scan_directories_for_duplicates([tmp_path], method="exact"))
    assert len(page.duplicate_sets) == 2
    assert page._ignored_group_count == 0
    page.close()
