"""
Layer 1 — Unit Tests: File Path Resolution
Validates the pathlib fix so the server works from any CWD.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from pathlib import Path
from med_agents import POLICIES_PATH, PDF_DIR


class TestPaths:
    def test_policies_file_exists(self):
        assert POLICIES_PATH.exists(), f"clinic_policies.md not found at {POLICIES_PATH}"

    def test_policies_is_a_file(self):
        assert POLICIES_PATH.is_file()

    def test_policies_is_markdown(self):
        assert POLICIES_PATH.suffix == ".md"

    def test_pdf_dir_exists(self):
        assert PDF_DIR.exists(), f"data/ directory not found at {PDF_DIR}"

    def test_pdf_dir_is_directory(self):
        assert PDF_DIR.is_dir()

    def test_pdf_dir_contains_pdfs(self):
        pdfs = list(PDF_DIR.glob("*.pdf"))
        assert len(pdfs) > 0, f"No PDF files found in {PDF_DIR}"

    def test_paths_are_absolute(self):
        assert POLICIES_PATH.is_absolute()
        assert PDF_DIR.is_absolute()

    def test_path_independent_of_cwd(self, tmp_path, monkeypatch):
        """Paths resolve correctly even when CWD is /tmp."""
        monkeypatch.chdir(tmp_path)
        # Re-import to trigger module-level path resolution from new CWD
        import importlib, med_agents
        importlib.reload(med_agents)
        assert med_agents.POLICIES_PATH.exists()
        assert med_agents.PDF_DIR.exists()
